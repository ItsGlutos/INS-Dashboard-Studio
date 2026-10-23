"""Aba de envio dos relatórios INS por transportadora.

A aba reúne quatro etapas:

* **Envios** — escolha da planilha de contatos, da pasta com os arquivos INS
  e disparo do planejamento/confirmação;
* **Corpo do e-mail** — assunto e corpo editáveis por tipo de relatório, com
  ``{transportadora}`` substituído automaticamente;
* **Em cópia** — lista manual de endereços que entram em CC em todos os
  envios;
* **Log** — resultado por transportadora (enviado, falho, não encontrado),
  com exportação para CSV.

O envio real só começa depois da confirmação visual no
:class:`~ui.envios_dialog.EnviosConfirmDialog`.
"""

from __future__ import annotations

import csv
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QThread
from PyQt6.QtGui import QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from backend.envios import (
    DEFAULT_ASSUNTOS,
    DEFAULT_CORPOS,
    PREFIXOS,
    EnvioError,
    EnvioResultado,
    PlanoEnvios,
    dividir_emails,
    validar_email,
)

from .envios_dialog import EnviosConfirmDialog
from .envios_worker import PlanWorker, SendWorker
from .widgets import (
    AeroCheckBox,
    FileSelector,
    GlassPanel,
    GlossyButton,
    LogView,
    SegmentedSelector,
    StatusLed,
)

__all__ = ["EnviosTab"]

_SET_TYPE = "envios/report_type"
_SET_CONTACTS = "envios/contacts_file"
_SET_FOLDER = "envios/files_folder"
_SET_DEBUG = "envios/debug"
_SET_COPY = "envios/copy_list"
_SET_SUBJECT = "envios/subject_{key}"
_SET_BODY = "envios/body_{key}"


class EnviosTab(QWidget):
    """Interface completa de envio, com confirmação e modo debug."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = QSettings("INS", "INS Dashboard Studio")
        self._cancel_flag = threading.Event()
        self._thread: QThread | None = None
        self._worker = None
        self._running = False
        self._mode = ""
        self._plano: PlanoEnvios | None = None
        self._pending_plan: PlanoEnvios | None = None
        self._pending_result: EnvioResultado | None = None
        self._pending_error: str | None = None
        self._editing_key = "motorista"
        self._templates: dict[str, dict[str, str]] = {}
        self._log_records: list[dict[str, str]] = []
        self._dialog_factory = EnviosConfirmDialog

        self._build_ui()
        self._restore_settings()
        self._update_mode()
        self._set_running(False)

    # ------------------------------------------------------------------
    # Propriedades
    # ------------------------------------------------------------------
    @property
    def is_running(self) -> bool:
        """Indica se há planejamento ou envio em andamento."""
        return self._running

    @property
    def plano(self) -> PlanoEnvios | None:
        """Último plano montado (``None`` antes do primeiro preparo)."""
        return self._plano

    # ------------------------------------------------------------------
    # Construção
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        root.addWidget(self._build_top())
        self._tabs = QTabWidget(self)
        self._tabs.setObjectName("enviosTabs")
        self._tabs.setDocumentMode(True)

        self._tabs.addTab(self._build_send_page(), "Envios")
        self._body_tab_index = self._tabs.addTab(
            self._build_body_page(), "Corpo do e-mail"
        )
        self._copy_tab_index = self._tabs.addTab(
            self._build_copy_page(), "Em cópia"
        )
        self._log_tab_index = self._tabs.addTab(
            self._build_log_page(), "Log"
        )
        root.addWidget(self._tabs, 1)

    def _build_top(self) -> QWidget:
        panel = GlassPanel(self)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(14)

        textos = QVBoxLayout()
        textos.setSpacing(2)
        titulo = QLabel("Envios de INS", panel)
        titulo.setObjectName("sectionTitle")
        self._mode_hint = QLabel("", panel)
        self._mode_hint.setObjectName("sectionHint")
        self._mode_hint.setWordWrap(True)
        textos.addWidget(titulo)
        textos.addWidget(self._mode_hint)
        layout.addLayout(textos, 1)

        self._segmented = SegmentedSelector(
            [("motorista", "Motorista"), ("transportador", "Transportador")],
            parent=panel,
        )
        self._segmented.changed.connect(self._on_type_changed)
        layout.addWidget(self._segmented)

        self._debug_check = AeroCheckBox(
            "Modo debug (validar sem enviar)", panel
        )
        self._debug_check.toggled.connect(self._update_mode)
        layout.addWidget(self._debug_check)
        return panel

    def _build_send_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        panel = GlassPanel(page)
        content = QVBoxLayout(panel)
        content.setContentsMargins(18, 16, 18, 16)
        content.setSpacing(9)

        titulo = QLabel("1. Fontes e confirmação", panel)
        titulo.setObjectName("sectionTitle")
        content.addWidget(titulo)

        self._source_hint = QLabel("", panel)
        self._source_hint.setObjectName("sectionHint")
        self._source_hint.setWordWrap(True)
        content.addWidget(self._source_hint)

        self._contacts_selector = FileSelector(
            "Planilha de contatos (colunas Transportadora + E-mail)",
            button_text="Procurar…",
            mode="file",
            dialog_title="Selecionar a planilha de contatos",
            file_filter="Planilhas do Excel (*.xlsx *.xlsm)",
            parent=panel,
        )
        content.addWidget(self._contacts_selector)

        self._folder_selector = FileSelector(
            "Pasta com os arquivos INS",
            button_text="Escolher…",
            mode="directory",
            dialog_title="Selecionar a pasta com os arquivos INS",
            parent=panel,
        )
        self._folder_selector.selectionChanged.connect(
            self._refresh_folder_button
        )
        content.addWidget(self._folder_selector)

        status_row = QHBoxLayout()
        status_row.setSpacing(9)
        self._led = StatusLed(panel)
        self._status_label = QLabel("Pronto para preparar os envios", panel)
        self._status_label.setObjectName("statusText")
        self._status_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._counter_label = QLabel("0 de 0", panel)
        self._counter_label.setObjectName("groupText")
        status_row.addWidget(self._led)
        status_row.addWidget(self._status_label, 1)
        status_row.addWidget(self._counter_label)
        content.addLayout(status_row)

        self._progress = QProgressBar(panel)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        content.addWidget(self._progress)

        self._summary_label = QLabel("", panel)
        self._summary_label.setObjectName("summaryText")
        self._summary_label.setWordWrap(True)
        content.addWidget(self._summary_label)

        aviso = QLabel(
            "Nada é enviado ao clicar em preparar: primeiro você revisa "
            "cada grupo e só então confirma o disparo.",
            panel,
        )
        aviso.setObjectName("sectionHint")
        aviso.setWordWrap(True)
        content.addWidget(aviso)

        botoes = QHBoxLayout()
        botoes.setSpacing(9)
        self._open_folder_button = GlossyButton("Abrir pasta", panel)
        self._open_folder_button.setObjectName("miniButton")
        self._open_folder_button.setEnabled(False)
        self._open_folder_button.clicked.connect(self._open_folder)
        botoes.addWidget(self._open_folder_button)
        botoes.addStretch(1)

        self._cancel_button = GlossyButton("Cancelar", panel)
        self._cancel_button.setObjectName("dangerButton")
        self._cancel_button.setEnabled(False)
        self._cancel_button.clicked.connect(self._cancel)
        botoes.addWidget(self._cancel_button)

        self._prepare_button = GlossyButton("Preparar envios", panel)
        self._prepare_button.setObjectName("primaryButton")
        self._prepare_button.clicked.connect(self._prepare)
        botoes.addWidget(self._prepare_button)
        content.addLayout(botoes)

        content.addStretch(1)
        layout.addWidget(panel, 1)
        return page

    def _build_body_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        panel = GlassPanel(page)
        content = QVBoxLayout(panel)
        content.setContentsMargins(18, 14, 18, 14)
        content.setSpacing(6)

        titulo = QLabel("2. Corpo do e-mail", panel)
        titulo.setObjectName("sectionTitle")
        content.addWidget(titulo)

        dica = QLabel(
            "Escreva o assunto e o corpo exatamente como devem chegar ao "
            "transportador. Use {transportadora} onde o nome do grupo deve "
            "entrar automaticamente.",
            panel,
        )
        dica.setObjectName("sectionHint")
        dica.setWordWrap(True)
        content.addWidget(dica)

        rotulo_assunto = QLabel("Assunto", panel)
        rotulo_assunto.setObjectName("fieldCaption")
        content.addWidget(rotulo_assunto)

        self._subject = QLineEdit(panel)
        self._subject.setObjectName("bodySubject")
        self._subject.setPlaceholderText(
            "{transportadora} - INS do Transportador 2026"
        )
        content.addWidget(self._subject)

        rotulo_corpo = QLabel("Corpo (editor com formatação)", panel)
        rotulo_corpo.setObjectName("fieldCaption")
        content.addWidget(rotulo_corpo)

        formatos = QHBoxLayout()
        formatos.setSpacing(5)
        formatos.addWidget(
            self._format_button("B", "Negrito (Ctrl+B)", self._toggle_bold, True)
        )
        formatos.addWidget(
            self._format_button("I", "Itálico (Ctrl+I)", self._toggle_italic, False, True)
        )
        formatos.addWidget(
            self._format_button("U", "Sublinhado (Ctrl+U)", self._toggle_underline, False, False, True)
        )
        formatos.addSpacing(10)

        inserir = GlossyButton("Inserir {transportadora}", panel)
        inserir.setObjectName("miniButton")
        inserir.clicked.connect(self._insert_placeholder)
        formatos.addWidget(inserir)

        restaurar = GlossyButton("Restaurar padrão", panel)
        restaurar.setObjectName("miniButton")
        restaurar.clicked.connect(self._restore_defaults)
        formatos.addWidget(restaurar)
        formatos.addStretch(1)
        content.addLayout(formatos)

        self._body = QTextEdit(panel)
        self._body.setObjectName("bodyEditor")
        self._body.setAcceptRichText(True)
        self._body.setPlaceholderText(
            "Olá, time {transportadora}!\n\nEscreva aqui o corpo do e-mail…"
        )
        self._body.setMinimumHeight(150)
        content.addWidget(self._body, 1)

        rodape = QLabel(
            "O Outlook envia o HTML gerado por este editor. O assunto e o "
            "corpo são salvos separadamente para Motorista e Transportador.",
            panel,
        )
        rodape.setObjectName("sectionHint")
        rodape.setWordWrap(True)
        content.addWidget(rodape)

        layout.addWidget(panel, 1)
        return page

    def _format_button(
        self,
        texto: str,
        dica: str,
        slot,
        negrito: bool = False,
        italico: bool = False,
        sublinhado: bool = False,
    ) -> QToolButton:
        botao = QToolButton(self)
        botao.setObjectName("formatButton")
        botao.setText(texto)
        botao.setToolTip(dica)
        botao.setCursor(Qt.CursorShape.PointingHandCursor)
        fonte = QFont(botao.font())
        fonte.setBold(negrito)
        fonte.setItalic(italico)
        fonte.setUnderline(sublinhado)
        botao.setFont(fonte)
        botao.clicked.connect(slot)
        return botao

    def _build_copy_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        panel = GlassPanel(page)
        content = QVBoxLayout(panel)
        content.setContentsMargins(18, 16, 18, 16)
        content.setSpacing(8)

        titulo = QLabel("3. Em cópia (CC)", panel)
        titulo.setObjectName("sectionTitle")
        content.addWidget(titulo)

        dica = QLabel(
            "Cada endereço desta lista entra em CÓPIA em todos os envios, "
            "independentemente da transportadora. Cole vários separados por "
            "ponto e vírgula, vírgula ou quebra de linha.",
            panel,
        )
        dica.setObjectName("sectionHint")
        dica.setWordWrap(True)
        content.addWidget(dica)

        entrada = QHBoxLayout()
        entrada.setSpacing(8)
        self._copy_input = QLineEdit(panel)
        self._copy_input.setPlaceholderText(
            "ex.: transporte.qualidade@gruposc.com.br"
        )
        self._copy_input.returnPressed.connect(self._add_copy_emails)
        entrada.addWidget(self._copy_input, 1)

        adicionar = GlossyButton("Adicionar", panel)
        adicionar.setObjectName("miniButton")
        adicionar.clicked.connect(self._add_copy_emails)
        entrada.addWidget(adicionar)
        content.addLayout(entrada)

        self._copy_list = QListWidget(panel)
        self._copy_list.setObjectName("copyList")
        self._copy_list.setAlternatingRowColors(False)
        self._copy_list.setMinimumHeight(180)
        content.addWidget(self._copy_list, 1)

        self._copy_hint = QLabel("0 endereço(s) em cópia", panel)
        self._copy_hint.setObjectName("groupText")
        content.addWidget(self._copy_hint)

        botoes = QHBoxLayout()
        botoes.setSpacing(8)
        remover = GlossyButton("Remover selecionado", panel)
        remover.setObjectName("miniButton")
        remover.clicked.connect(self._remove_copy_email)
        botoes.addWidget(remover)

        limpar = GlossyButton("Limpar lista", panel)
        limpar.setObjectName("miniButton")
        limpar.clicked.connect(self._clear_copy_emails)
        botoes.addWidget(limpar)
        botoes.addStretch(1)
        content.addLayout(botoes)

        layout.addWidget(panel, 1)
        return page

    def _build_log_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        panel = GlassPanel(page)
        content = QVBoxLayout(panel)
        content.setContentsMargins(18, 16, 18, 16)
        content.setSpacing(8)

        titulo = QLabel("4. Log de envios", panel)
        titulo.setObjectName("sectionTitle")
        content.addWidget(titulo)

        dica = QLabel(
            "Cada transportadora aparece com o resultado do último envio. "
            "Falhas individuais não interrompem as demais.",
            panel,
        )
        dica.setObjectName("sectionHint")
        dica.setWordWrap(True)
        content.addWidget(dica)

        contadores = QHBoxLayout()
        contadores.setSpacing(8)
        self._sent_count = QLabel("Enviados: 0", panel)
        self._failed_count = QLabel("Falhos: 0", panel)
        self._missing_count = QLabel("Não encontrados: 0", panel)
        for label in (
            self._sent_count,
            self._failed_count,
            self._missing_count,
        ):
            label.setObjectName("countChip")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            contadores.addWidget(label)
        contadores.addStretch(1)
        content.addLayout(contadores)

        self._log_view = LogView(panel)
        self._log_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        content.addWidget(self._log_view, 1)

        botoes = QHBoxLayout()
        botoes.setSpacing(8)
        exportar = GlossyButton("Exportar CSV", panel)
        exportar.setObjectName("miniButton")
        exportar.clicked.connect(self._export_log)
        botoes.addWidget(exportar)

        limpar = GlossyButton("Limpar log", panel)
        limpar.setObjectName("miniButton")
        limpar.clicked.connect(self._clear_log)
        botoes.addWidget(limpar)
        botoes.addStretch(1)
        content.addLayout(botoes)

        layout.addWidget(panel, 1)
        return page

    # ------------------------------------------------------------------
    # Tipo de relatório, modo debug e modelos
    # ------------------------------------------------------------------
    def _current_key(self) -> str:
        return self._segmented.current or "motorista"

    def _on_type_changed(self, key: str) -> None:
        if not key:
            return
        self._save_current_template()
        self._editing_key = key
        self._load_template(key)
        self._plano = None
        self._summary_label.clear()
        self._status_label.setText(
            "Tipo alterado — prepare os envios novamente."
        )
        self._led.set_state("idle")
        self._update_type_hint()
        self._update_mode()

    def _update_type_hint(self) -> None:
        prefixo = PREFIXOS.get(self._current_key(), "")
        self._source_hint.setText(
            "A pasta deve conter arquivos que começam com "
            f"'{prefixo}'. O nome entre o final desse prefixo e o .xlsx é "
            "usado para localizar o e-mail na planilha de contatos."
        )

    def _update_mode(self, *_: object) -> None:
        debug = self._debug_check.isChecked()
        self._prepare_button.setText(
            "Validar envios (debug)" if debug else "Preparar envios"
        )
        self._mode_hint.setText(
            "Modo debug: valida cada transportadora e mostra os "
            "destinatários, sem enviar nada."
            if debug
            else "Selecione as fontes, prepare os grupos e confirme o envio "
            "na revisão final."
        )

    def _load_template(self, key: str) -> None:
        modelo = self._templates.get(
            key,
            {
                "assunto": DEFAULT_ASSUNTOS.get(key, ""),
                "corpo": DEFAULT_CORPOS.get(key, ""),
            },
        )
        self._subject.setText(modelo.get("assunto", ""))
        self._body.setHtml(modelo.get("corpo", ""))

    def _save_current_template(self) -> None:
        assunto = self._subject.text().strip()
        corpo = self._body.toHtml()
        if not assunto and not self._body.toPlainText().strip():
            return
        self._templates[self._editing_key] = {
            "assunto": assunto,
            "corpo": corpo,
        }

    def _toggle_bold(self) -> None:
        formato = QTextCharFormat()
        negrito = self._body.fontWeight() >= int(QFont.Weight.Bold.value)
        formato.setFontWeight(
            QFont.Weight.Normal if negrito else QFont.Weight.Bold
        )
        self._merge_format(formato)

    def _toggle_italic(self) -> None:
        formato = QTextCharFormat()
        formato.setFontItalic(not self._body.fontItalic())
        self._merge_format(formato)

    def _toggle_underline(self) -> None:
        formato = QTextCharFormat()
        formato.setFontUnderline(not self._body.fontUnderline())
        self._merge_format(formato)

    def _merge_format(self, formato: QTextCharFormat) -> None:
        cursor = self._body.textCursor()
        cursor.mergeCharFormat(formato)
        self._body.mergeCurrentCharFormat(formato)
        self._body.setFocus()

    def _insert_placeholder(self) -> None:
        self._body.textCursor().insertText("{transportadora}")
        self._body.setFocus()

    def _restore_defaults(self) -> None:
        chave = self._current_key()
        resposta = QMessageBox.question(
            self,
            "Restaurar padrão",
            "Substituir o assunto e o corpo atuais pelo texto padrão "
            f"do INS do {chave.title()}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        self._subject.setText(DEFAULT_ASSUNTOS[chave])
        self._body.setHtml(DEFAULT_CORPOS[chave])
        self._templates[chave] = {
            "assunto": DEFAULT_ASSUNTOS[chave],
            "corpo": DEFAULT_CORPOS[chave],
        }

    # ------------------------------------------------------------------
    # Cópia (CC)
    # ------------------------------------------------------------------
    def _add_copy_emails(self) -> None:
        texto = self._copy_input.text().strip()
        if not texto:
            return
        emails = dividir_emails(texto)
        validos = [email for email in emails if validar_email(email)]
        invalidos = [email for email in emails if not validar_email(email)]

        existentes = {
            self._copy_list.item(indice).text().lower()
            for indice in range(self._copy_list.count())
        }
        for email in validos:
            if email.lower() in existentes:
                continue
            existentes.add(email.lower())
            QListWidgetItem(email, self._copy_list)

        self._copy_input.clear()
        self._refresh_copy_hint()

        if invalidos:
            QMessageBox.warning(
                self,
                "E-mails inválidos",
                "Estes endereços não foram adicionados porque não parecem "
                "válidos:\n\n" + "\n".join(invalidos),
            )

    def _remove_copy_email(self) -> None:
        for item in self._copy_list.selectedItems():
            self._copy_list.takeItem(self._copy_list.row(item))
        self._refresh_copy_hint()

    def _clear_copy_emails(self) -> None:
        if self._copy_list.count() == 0:
            return
        resposta = QMessageBox.question(
            self,
            "Limpar cópias",
            "Remover todos os endereços em cópia?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta == QMessageBox.StandardButton.Yes:
            self._copy_list.clear()
            self._refresh_copy_hint()

    def _refresh_copy_hint(self) -> None:
        total = self._copy_list.count() if hasattr(self, "_copy_list") else 0
        self._copy_hint.setText(f"{total} endereço(s) em cópia")

    def copy_emails(self) -> list[str]:
        """Endereços atualmente na lista de cópia, na ordem exibida."""
        return [
            self._copy_list.item(indice).text()
            for indice in range(self._copy_list.count())
        ]

    # ------------------------------------------------------------------
    # Preparação do plano
    # ------------------------------------------------------------------
    def _prepare(self) -> None:
        if self._running:
            return

        faltando: list[str] = []
        if not self._contacts_selector.path:
            faltando.append("Selecione a planilha de contatos (.xlsx).")
        if not self._folder_selector.path:
            faltando.append("Selecione a pasta com os arquivos INS.")
        if not self._subject.text().strip():
            faltando.append("Escreva o assunto do e-mail.")
        if not self._body.toPlainText().strip():
            faltando.append("Escreva o corpo do e-mail.")
        if faltando:
            self._show_error("Configuração incompleta", "\n\n".join(faltando))
            return

        self.save_settings()
        self._plano = None
        self._summary_label.clear()
        self._counter_label.setText("…")
        self._progress.setRange(0, 0)
        self._progress.setValue(0)
        self._led.set_state("running")
        self._status_label.setText("Preparando os grupos de envio…")
        self._log_view.append_log(
            f"Preparando envios de {self._segmented.current.title()}…",
            "info",
        )

        worker = PlanWorker(
            report_key=self._current_key(),
            contatos_path=self._contacts_selector.path,
            pasta_arquivos=self._folder_selector.path,
            copia_manual=self.copy_emails(),
            assunto=self._subject.text(),
            corpo=self._body.toHtml(),
        )
        self._start_thread("plan", worker)

    def _start_send(self, plano: PlanoEnvios, chaves: list[str]) -> None:
        if not chaves:
            return
        self._cancel_flag = threading.Event()
        total = len(chaves)
        self._progress.setRange(0, total)
        self._progress.setValue(0)
        self._progress.setFormat("%v de %m")
        self._counter_label.setText(f"0 de {total}")
        self._led.set_state("running")
        self._status_label.setText(f"Enviando 0 de {total}…")
        self._log_view.append_log(
            f"Iniciando envio de {total} e-mail(s).", "info"
        )
        worker = SendWorker(plano, chaves, self._cancel_flag)
        self._start_thread("send", worker)

    # ------------------------------------------------------------------
    # Threads
    # ------------------------------------------------------------------
    def _start_thread(self, modo: str, worker) -> None:
        self._mode = modo
        self._pending_plan = None
        self._pending_result = None
        self._pending_error = None

        self._thread = QThread(self)
        self._worker = worker
        worker.moveToThread(self._thread)
        self._thread.started.connect(worker.run)
        worker.log.connect(self._on_worker_log)
        worker.failed.connect(self._on_worker_failed)
        worker.finished.connect(self._thread.quit)
        worker.failed.connect(self._thread.quit)

        if modo == "plan":
            worker.finished.connect(self._on_plan_finished)
        else:
            worker.progress.connect(self._on_progress)
            worker.finished.connect(self._on_send_finished)

        self._thread.finished.connect(self._on_thread_finished)
        self._set_running(True)
        self._thread.start()

    def _on_worker_log(self, mensagem: str, nivel: str) -> None:
        self._log_view.append_log(mensagem, nivel)

    def _on_worker_failed(self, mensagem: str) -> None:
        self._pending_error = mensagem

    def _on_plan_finished(self, plano: PlanoEnvios) -> None:
        self._pending_plan = plano

    def _on_send_finished(self, resultado: EnvioResultado) -> None:
        self._pending_result = resultado

    def _on_progress(self, atual: int, total: int, nome: str) -> None:
        if total > 0:
            self._progress.setRange(0, total)
            self._progress.setValue(atual)
        self._counter_label.setText(f"{atual} de {total}")
        self._status_label.setText(f"Enviando {atual} de {total} — {nome}")

    def _on_thread_finished(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None

        modo = self._mode
        self._mode = ""
        self._set_running(False)

        if self._pending_error is not None:
            mensagem = self._pending_error
            self._pending_error = None
            self._handle_error(mensagem)
            return

        if modo == "plan" and self._pending_plan is not None:
            plano = self._pending_plan
            self._pending_plan = None
            self._handle_plan(plano)
        elif modo == "send" and self._pending_result is not None:
            resultado = self._pending_result
            self._pending_result = None
            self._handle_send_result(resultado)

    # ------------------------------------------------------------------
    # Resultados
    # ------------------------------------------------------------------
    def _handle_plan(self, plano: PlanoEnvios) -> None:
        self._plano = plano
        self._summary_label.setText(plano.resumo())
        self._progress.setRange(0, max(1, len(plano.grupos)))
        self._progress.setValue(0)
        self._progress.setFormat("%p%")
        self._counter_label.setText(f"0 de {len(plano.grupos)}")
        self._log_view.append_log(
            f"Plano montado: {plano.resumo()}", "info"
        )
        for aviso in plano.avisos:
            self._log_view.append_log(aviso, "warning")

        debug = self._debug_check.isChecked()
        if debug:
            for grupo in plano.grupos:
                nivel = "success" if grupo.pronto else "warning"
                marca = "OK" if grupo.pronto else grupo.rotulo_status.upper()
                detalhe = (
                    ", ".join(grupo.para) if grupo.para else grupo.detalhe
                )
                self._log_view.append_log(
                    f"DEBUG {marca}: {grupo.nome} — {detalhe}", nivel
                )
                self._record(
                    "validado" if grupo.pronto else "nao_encontrado",
                    grupo,
                    grupo.detalhe,
                )
            self._status_label.setText("Validação concluída (nada foi enviado)")
            self._led.set_state(
                "ok" if not plano.nao_encontrados else "cancelled"
            )
            self._progress.setValue(len(plano.grupos))
            self._counter_label.setText(
                f"{len(plano.prontos)} de {len(plano.grupos)} prontos"
            )
            self._tabs.setCurrentIndex(self._log_tab_index)
            dialogo = self._dialog_factory(plano, debug=True, parent=self)
            dialogo.exec()
            self._atualizar_contadores()
            return

        for grupo in plano.nao_encontrados:
            self._log_view.append_log(
                f"NÃO ENCONTRADO: {grupo.nome} — {grupo.rotulo_status}"
                + (f" ({grupo.detalhe})" if grupo.detalhe else ""),
                "warning",
            )

        self._status_label.setText("Plano pronto — confirme o envio")
        self._led.set_state("ok" if plano.prontos else "cancelled")
        dialogo = self._dialog_factory(plano, debug=False, parent=self)
        resposta = dialogo.exec()
        if resposta != QDialog.DialogCode.Accepted:
            self._status_label.setText("Envio cancelado antes do disparo")
            self._led.set_state("cancelled")
            self._log_view.append_log(
                "Envio cancelado na revisão. Nenhum e-mail foi disparado.",
                "warning",
            )
            return

        chaves = dialogo.selected_keys()
        if not chaves:
            self._status_label.setText("Nenhum grupo selecionado")
            self._led.set_state("cancelled")
            self._log_view.append_log(
                "Nenhum grupo foi selecionado para envio.", "warning"
            )
            return

        self._start_send(plano, chaves)

    def _handle_send_result(self, resultado: EnvioResultado) -> None:
        total = resultado.total
        self._progress.setRange(0, max(1, total))
        self._progress.setValue(total)
        self._counter_label.setText(f"{len(resultado.enviados)} de {total}")

        for grupo in resultado.enviados:
            self._record("enviado", grupo, "E-mail enviado pelo Outlook.")
        for grupo in resultado.falhos:
            self._record("falho", grupo, "Falha ao enviar pelo Outlook.")
        for grupo in resultado.nao_encontrados:
            self._record("nao_encontrado", grupo, grupo.detalhe)
        for grupo in resultado.ignorados:
            self._record("ignorado", grupo, "Não enviado por cancelamento.")
        self._atualizar_contadores()

        resumo = (
            f"{len(resultado.enviados)} enviado(s) · "
            f"{len(resultado.falhos)} falha(s) · "
            f"{len(resultado.nao_encontrados)} não encontrado(s) · "
            f"{self._format_duration(resultado.duracao_segundos)}"
        )
        if len(resultado.ignorados):
            resumo += f" · {len(resultado.ignorados)} ignorado(s)"
        self._summary_label.setText(resumo)

        if resultado.cancelado:
            self._status_label.setText("Envio cancelado")
            self._led.set_state("cancelled")
            nivel = "warning"
        elif resultado.falhos:
            self._status_label.setText("Envio concluído com falhas")
            self._led.set_state("error")
            nivel = "warning"
        else:
            self._status_label.setText("Envio concluído")
            self._led.set_state("ok")
            nivel = "success"

        self._log_view.append_log(resumo, nivel)
        if resultado.falhos or resultado.cancelado or resultado.nao_encontrados:
            self._tabs.setCurrentIndex(self._log_tab_index)

        icone = (
            QMessageBox.Icon.Warning
            if resultado.falhos or resultado.cancelado
            else QMessageBox.Icon.Information
        )
        caixa = QMessageBox(self)
        caixa.setIcon(icone)
        caixa.setWindowTitle("Envios INS")
        caixa.setText("Envio finalizado.\n\n" + resumo)
        caixa.setInformativeText("Os detalhes estão na aba Log.")
        caixa.exec()

    def _handle_error(self, mensagem: str) -> None:
        self._led.set_state("error")
        self._status_label.setText("Falha nos envios")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._counter_label.setText("0 de 0")
        self._log_view.append_log(mensagem, "error")
        self._show_error("Envios INS", mensagem)

    def _cancel(self) -> None:
        if not self._running or self._mode != "send":
            return
        self._cancel_flag.set()
        self._cancel_button.setEnabled(False)
        self._status_label.setText("Cancelando após o e-mail atual…")
        self._led.set_state("cancelled")
        self._log_view.append_log(
            "Cancelamento solicitado. O e-mail em andamento será concluído "
            "e os próximos não serão disparados.",
            "warning",
        )

    # ------------------------------------------------------------------
    # Log e persistência
    # ------------------------------------------------------------------
    def _record(
        self, categoria: str, grupo, detalhe: str = ""
    ) -> None:
        self._log_records.append(
            {
                "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "categoria": categoria,
                "tipo": self._segmented.current,
                "transportadora": grupo.nome,
                "arquivo": str(grupo.arquivo),
                "para": "; ".join(grupo.para),
                "copia": "; ".join(grupo.copia),
                "situacao": grupo.rotulo_status,
                "detalhe": detalhe,
            }
        )

    def _atualizar_contadores(self) -> None:
        enviados = sum(
            1 for registro in self._log_records
            if registro["categoria"] == "enviado"
        )
        falhos = sum(
            1 for registro in self._log_records
            if registro["categoria"] == "falho"
        )
        ausentes = sum(
            1 for registro in self._log_records
            if registro["categoria"] == "nao_encontrado"
        )
        self._sent_count.setText(f"Enviados: {enviados}")
        self._failed_count.setText(f"Falhos: {falhos}")
        self._missing_count.setText(f"Não encontrados: {ausentes}")

    def _clear_log(self) -> None:
        self._log_records.clear()
        self._log_view.clear_log()
        self._atualizar_contadores()
        self._log_view.append_log("Log limpo.", "info")

    def _export_log(self) -> None:
        if not self._log_records:
            self._show_info(
                "Log vazio",
                "Ainda não há envios ou validações para exportar.",
            )
            return
        carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
        sugerido = str(Path.home() / f"log_envios_{carimbo}.csv")
        caminho, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar log de envios",
            sugerido,
            "Arquivos CSV (*.csv)",
        )
        if not caminho:
            return
        colunas = [
            "data_hora",
            "categoria",
            "tipo",
            "transportadora",
            "arquivo",
            "para",
            "copia",
            "situacao",
            "detalhe",
        ]
        try:
            with open(caminho, "w", encoding="utf-8-sig", newline="") as arquivo:
                escritor = csv.DictWriter(
                    arquivo, fieldnames=colunas, delimiter=";"
                )
                escritor.writeheader()
                escritor.writerows(self._log_records)
        except OSError as erro:
            self._show_error(
                "Não foi possível exportar",
                f"Detalhe técnico: {erro}",
            )
            return
        self._show_info(
            "Log exportado",
            f"Arquivo salvo em:\n{caminho}",
        )

    def save_settings(self) -> None:
        """Persiste caminhos, listas e modelos no ``QSettings``."""
        self._save_current_template()
        self._settings.setValue(_SET_TYPE, self._segmented.current)
        self._settings.setValue(_SET_CONTACTS, self._contacts_selector.path)
        self._settings.setValue(_SET_FOLDER, self._folder_selector.path)
        self._settings.setValue(_SET_DEBUG, self._debug_check.isChecked())
        self._settings.setValue(_SET_COPY, self.copy_emails())
        for chave, modelo in self._templates.items():
            self._settings.setValue(
                _SET_SUBJECT.format(key=chave), modelo.get("assunto", "")
            )
            self._settings.setValue(
                _SET_BODY.format(key=chave), modelo.get("corpo", "")
            )

    def _restore_settings(self) -> None:
        tipo = str(self._settings.value(_SET_TYPE, "motorista") or "")
        if tipo not in PREFIXOS:
            tipo = "motorista"
        self._segmented.set_current(tipo, emit=False)
        self._editing_key = tipo

        contatos = str(self._settings.value(_SET_CONTACTS, "") or "")
        pasta = str(self._settings.value(_SET_FOLDER, "") or "")
        if contatos:
            self._contacts_selector.set_path(contatos)
        if pasta:
            self._folder_selector.set_path(pasta)

        debug = self._settings.value(_SET_DEBUG, False)
        if isinstance(debug, str):
            debug = debug.strip().lower() in ("true", "1", "yes", "sim")
        self._debug_check.setChecked(bool(debug))

        copias = self._settings.value(_SET_COPY, [])
        if isinstance(copias, str):
            copias = [copias] if copias else []
        for email in copias or []:
            texto = str(email).strip()
            if texto:
                QListWidgetItem(texto, self._copy_list)

        self._templates = {}
        for chave in PREFIXOS:
            assunto = str(
                self._settings.value(
                    _SET_SUBJECT.format(key=chave),
                    DEFAULT_ASSUNTOS[chave],
                )
                or DEFAULT_ASSUNTOS[chave]
            )
            corpo = str(
                self._settings.value(
                    _SET_BODY.format(key=chave), DEFAULT_CORPOS[chave]
                )
                or DEFAULT_CORPOS[chave]
            )
            self._templates[chave] = {"assunto": assunto, "corpo": corpo}
        self._load_template(tipo)

        self._update_type_hint()
        self._refresh_copy_hint()
        self._refresh_folder_button()

    # ------------------------------------------------------------------
    # Utilidades da interface
    # ------------------------------------------------------------------
    def _set_running(self, running: bool) -> None:
        self._running = running
        self._prepare_button.setEnabled(not running)
        self._cancel_button.setEnabled(
            running and self._mode == "send"
        )
        self._segmented.setEnabled(not running)
        self._debug_check.setEnabled(not running)
        self._contacts_selector.setEnabled(not running)
        self._folder_selector.setEnabled(not running)
        self._open_folder_button.setEnabled(
            not running and self._folder_exists()
        )
        self._tabs.setTabEnabled(self._body_tab_index, not running)
        self._tabs.setTabEnabled(self._copy_tab_index, not running)

    def _folder_exists(self) -> bool:
        caminho = self._folder_selector.path
        return bool(caminho) and Path(caminho).is_dir()

    def _refresh_folder_button(self, *_: object) -> None:
        self._open_folder_button.setEnabled(
            not self._running and self._folder_exists()
        )

    def _open_folder(self) -> None:
        caminho = Path(self._folder_selector.path)
        if not caminho.is_dir():
            self._show_error(
                "Pasta não encontrada",
                f"A pasta não existe mais:\n{caminho}",
            )
            return
        if sys.platform != "win32":
            self._show_error(
                "Recurso indisponível",
                "A abertura da pasta no Explorador só funciona no Windows.",
            )
            return
        try:
            os.startfile(str(caminho))  # noqa: S606 - ação do usuário
        except OSError as erro:
            self._show_error(
                "Não foi possível abrir a pasta",
                f"Detalhe técnico: {erro}",
            )

    def _show_error(self, titulo: str, mensagem: str) -> None:
        caixa = QMessageBox(self)
        caixa.setIcon(QMessageBox.Icon.Warning)
        caixa.setWindowTitle(titulo)
        caixa.setText(mensagem)
        caixa.setStandardButtons(QMessageBox.StandardButton.Ok)
        caixa.exec()

    def _show_info(self, titulo: str, mensagem: str) -> None:
        caixa = QMessageBox(self)
        caixa.setIcon(QMessageBox.Icon.Information)
        caixa.setWindowTitle(titulo)
        caixa.setText(mensagem)
        caixa.setStandardButtons(QMessageBox.StandardButton.Ok)
        caixa.exec()

    @staticmethod
    def _format_duration(seconds: float) -> str:
        try:
            total = float(seconds)
        except (TypeError, ValueError):
            return "0 s"
        if total < 60:
            return f"{total:.1f} s"
        minutos, restantes = divmod(int(total), 60)
        if minutos < 60:
            return f"{minutos} min {restantes} s"
        horas, minutos = divmod(minutos, 60)
        return f"{horas} h {minutos} min {restantes} s"
