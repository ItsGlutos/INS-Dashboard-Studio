"""Diálogo de confirmação visual dos grupos de e-mail antes do envio.

Cada linha representa uma transportadora e mostra arquivo, destinatários,
cópias e situação. Somente linhas marcadas e prontas são enviadas. Em modo
debug o diálogo serve apenas para validação: nenhum e-mail é disparado.
"""

from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from backend.envios import GrupoEnvio, PlanoEnvios

from .widgets import AeroCheckBox, GlossyButton

__all__ = ["EnviosConfirmDialog"]

_COLUNAS = ["", "Transportadora", "Arquivo", "Para", "Cópia", "Situação"]
_COR_OK = QColor("#0b6b4f")
_COR_ERRO = QColor("#a12424")
_COR_NEUTRA = QColor("#52667a")


class EnviosConfirmDialog(QDialog):
    """Tabela de revisão dos e-mails, com seleção por transportadora."""

    def __init__(
        self,
        plano: PlanoEnvios,
        debug: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._plano = plano
        self._debug = debug
        self._groups = list(plano.grupos)
        self._checks: list[AeroCheckBox] = []
        self._building = True
        self._fitted = False

        self.setWindowTitle(
            "Validação de envios (modo debug)"
            if debug
            else "Confirmar envio dos INS"
        )
        self.setModal(True)
        self.setMinimumSize(720, 480)
        self.resize(1100, 720)
        self.setSizeGripEnabled(True)
        self.setAccessibleName(
            "Validação de envios dos INS"
            if debug
            else "Confirmação de envio dos INS"
        )

        self._build_ui()
        self._populate()
        self._building = False
        self._update_selection()

        if debug:
            self.confirm_button.hide()
            self.cancel_button.setText("Fechar")
            self.cancel_button.setAccessibleName("Fechar validação")
        self.table.setFocus()

    # ------------------------------------------------------------------
    # Construção
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(8)

        titulo = QLabel(
            "Validação por transportadora"
            if self._debug
            else "Confirme os grupos antes de enviar"
        )
        titulo.setObjectName("dialogTitle")
        layout.addWidget(titulo)

        if self._debug:
            subtitulo_texto = (
                "Nenhum e-mail será enviado. Confira abaixo se cada "
                "transportadora foi encontrada e se os destinatários estão "
                "corretos."
            )
        else:
            subtitulo_texto = (
                "Revise os grupos abaixo. Ao confirmar, os e-mails marcados "
                "serão enviados imediatamente pelo Outlook Desktop, com o "
                "arquivo INS anexado."
            )
        subtitulo = QLabel(subtitulo_texto)
        subtitulo.setObjectName("dialogSubtitle")
        subtitulo.setWordWrap(True)
        layout.addWidget(subtitulo)

        resumo = (
            f"{len(self._plano.grupos)} grupo(s) · "
            f"{len(self._plano.prontos)} pronto(s) · "
            f"{len(self._plano.nao_encontrados)} não encontrado(s)"
        )
        stats = QLabel(resumo)
        stats.setObjectName("chip")
        stats.setToolTip(self._plano.resumo())
        stats.setMinimumHeight(24)
        stats.setAccessibleName("Resumo dos grupos de envio")
        stats.setAccessibleDescription(resumo)

        self.select_all = AeroCheckBox(
            "Selecionar todos os grupos prontos", self
        )
        self.select_all.setChecked(True)
        self.select_all.setEnabled(not self._debug)
        self.select_all.setAccessibleName(
            "Selecionar todos os grupos prontos para envio"
        )
        self.select_all.setAccessibleDescription(
            "Marca ou desmarca todas as transportadoras que possuem "
            "arquivo e e-mail válido."
        )
        self.select_all.toggled.connect(self._toggle_all)

        topo = QHBoxLayout()
        topo.setSpacing(10)
        topo.addWidget(stats)
        topo.addWidget(self.select_all)
        topo.addStretch(1)
        layout.addLayout(topo)

        self.table = QTableWidget(0, len(_COLUNAS), self)
        self.table.setObjectName("confirmTable")
        self.table.setHorizontalHeaderLabels(_COLUNAS)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setTabKeyNavigation(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setMinimumHeight(170)
        self.table.setAccessibleName("Transportadoras e situação do envio")
        self.table.setAccessibleDescription(
            "Selecione uma linha para ver a prévia. Pressione Espaço para "
            "incluir ou remover a transportadora selecionada do envio."
        )
        self.table.installEventFilter(self)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(0, 38)
        self.table.setColumnWidth(1, 190)
        self.table.setColumnWidth(2, 250)
        self.table.itemSelectionChanged.connect(self._update_preview)
        layout.addWidget(self.table, 1)

        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("dialogScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._scroll.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._scroll.setMinimumHeight(100)
        self._scroll.setMaximumHeight(230)
        self._scroll.setAccessibleName("Prévia do e-mail e avisos")

        previa = QWidget(self._scroll)
        previa.setObjectName("dialogScrollContent")
        previa_layout = QVBoxLayout(previa)
        previa_layout.setContentsMargins(0, 0, 4, 0)
        previa_layout.setSpacing(3)

        rotulo_previa = QLabel("Prévia do e-mail selecionado", previa)
        rotulo_previa.setObjectName("fieldCaption")
        previa_layout.addWidget(rotulo_previa)

        self._preview_subject = QLabel("", previa)
        self._preview_subject.setObjectName("previewSubject")
        self._preview_subject.setWordWrap(True)
        self._preview_subject.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._preview_subject.setAccessibleName(
            "Assunto do e-mail selecionado"
        )
        previa_layout.addWidget(self._preview_subject)

        self._preview_recipients = QLabel("", previa)
        self._preview_recipients.setObjectName("previewRecipients")
        self._preview_recipients.setWordWrap(True)
        self._preview_recipients.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._preview_recipients.setAccessibleName(
            "Destinatários e cópia do e-mail selecionado"
        )
        previa_layout.addWidget(self._preview_recipients)

        self._preview_body = QLabel("", previa)
        self._preview_body.setObjectName("previewBody")
        self._preview_body.setTextFormat(Qt.TextFormat.RichText)
        self._preview_body.setWordWrap(True)
        self._preview_body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._preview_body.setOpenExternalLinks(False)
        self._preview_body.setMinimumHeight(70)
        self._preview_body.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        self._preview_body.setAccessibleName(
            "Corpo do e-mail selecionado"
        )
        previa_layout.addWidget(self._preview_body)

        if self._plano.avisos:
            avisos = QLabel(previa)
            avisos.setObjectName("dialogWarnings")
            avisos.setWordWrap(True)
            avisos.setTextFormat(Qt.TextFormat.PlainText)
            avisos.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            avisos.setText(
                "\n".join(f"• {aviso}" for aviso in self._plano.avisos)
            )
            avisos.setToolTip("\n".join(self._plano.avisos))
            avisos.setAccessibleName("Avisos da preparação do envio")
            previa_layout.addWidget(avisos)

        self._scroll.setWidget(previa)
        layout.addWidget(self._scroll, 0)

        rodape = QHBoxLayout()
        rodape.setSpacing(10)

        self.selection_label = QLabel("", self)
        self.selection_label.setObjectName("dialogSelection")
        self.selection_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.selection_label.setAccessibleName("Seleção dos grupos")
        rodape.addWidget(self.selection_label, 1)

        self.cancel_button = GlossyButton("Cancelar", self)
        self.cancel_button.setObjectName("miniButton")
        self.cancel_button.setMinimumSize(96, 32)
        self.cancel_button.setAccessibleName("Cancelar envio e fechar")
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.clicked.connect(self.reject)
        rodape.addWidget(self.cancel_button)

        self.confirm_button = GlossyButton("Confirmar envio", self)
        self.confirm_button.setObjectName("primaryButton")
        self.confirm_button.setMinimumHeight(36)
        self.confirm_button.setAccessibleName(
            "Confirmar envio dos e-mails selecionados"
        )
        self.confirm_button.setAutoDefault(False)
        self.confirm_button.clicked.connect(self._on_confirm)
        rodape.addWidget(self.confirm_button)

        layout.addLayout(rodape)

        self.setTabOrder(self.select_all, self.table)
        self.setTabOrder(self.table, self._scroll)
        self.setTabOrder(self._scroll, self.cancel_button)
        self.setTabOrder(self.cancel_button, self.confirm_button)

    def _populate(self) -> None:
        """Preenche a tabela com os grupos do plano."""
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._groups))
        for linha, grupo in enumerate(self._groups):
            self._fill_row(linha, grupo)
        self.table.blockSignals(False)
        if self._groups:
            self.table.selectRow(0)

    def _update_preview(self) -> None:
        """Mostra o assunto e o corpo renderizados do grupo selecionado."""
        if not self._groups:
            return
        selecionadas = self.table.selectionModel().selectedRows()
        indice = selecionadas[0].row() if selecionadas else 0
        if not 0 <= indice < len(self._groups):
            indice = 0
        grupo = self._groups[indice]
        self._preview_subject.setText(grupo.assunto)
        para = ", ".join(grupo.para) if grupo.para else "—"
        copia = ", ".join(grupo.copia) if grupo.copia else "—"
        self._preview_recipients.setText(
            f"Para: {para}\nCópia: {copia}"
        )
        self._preview_body.setText(grupo.corpo)

    def _fill_row(self, linha: int, grupo: GrupoEnvio) -> None:
        container = QWidget(self.table)
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        check = AeroCheckBox("", container)
        check.setChecked(grupo.pronto)
        check.setEnabled(grupo.pronto and not self._debug)
        check.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        check.setProperty("chave", grupo.chave)
        check.setToolTip(
            f"Incluir {grupo.nome} no envio"
            if grupo.pronto
            else grupo.rotulo_status
        )
        check.setAccessibleName(
            f"Incluir {grupo.nome} no envio"
            if grupo.pronto
            else f"{grupo.nome}: {grupo.rotulo_status}"
        )
        check.setAccessibleDescription(
            grupo.detalhe or grupo.rotulo_status
        )
        check.toggled.connect(self._update_selection)
        container_layout.addWidget(check)
        self.table.setCellWidget(linha, 0, container)
        self._checks.append(check)

        nome = QTableWidgetItem(grupo.nome)
        fonte = QFont(nome.font())
        fonte.setBold(True)
        nome.setFont(fonte)
        nome.setToolTip(grupo.nome)
        self.table.setItem(linha, 1, nome)

        arquivo = QTableWidgetItem(grupo.arquivo.name)
        arquivo.setToolTip(str(grupo.arquivo))
        self.table.setItem(linha, 2, arquivo)

        para = QTableWidgetItem(
            "; ".join(grupo.para) if grupo.para else "—"
        )
        para.setToolTip("\n".join(grupo.para))
        para.setForeground(
            QBrush(_COR_NEUTRA) if not grupo.para else QBrush(_COR_OK)
        )
        self.table.setItem(linha, 3, para)

        copia = QTableWidgetItem(
            "; ".join(grupo.copia) if grupo.copia else "—"
        )
        copia.setToolTip("\n".join(grupo.copia))
        copia.setForeground(QBrush(_COR_NEUTRA))
        self.table.setItem(linha, 4, copia)

        situacao = QTableWidgetItem(
            ("✔ " if grupo.pronto else "✖ ") + grupo.rotulo_status
        )
        situacao.setForeground(
            QBrush(_COR_OK) if grupo.pronto else QBrush(_COR_ERRO)
        )
        dica = grupo.detalhe or grupo.rotulo_status
        situacao.setToolTip(dica)
        self.table.setItem(linha, 5, situacao)

    # ------------------------------------------------------------------
    # Seleção
    # ------------------------------------------------------------------
    def selected_keys(self) -> list[str]:
        """Chaves dos grupos marcados e realmente prontos para envio."""
        chaves: list[str] = []
        for indice, grupo in enumerate(self._groups):
            if not grupo.pronto:
                continue
            if indice < len(self._checks) and self._checks[indice].isChecked():
                chaves.append(grupo.chave)
        return chaves

    def _toggle_all(self, marcado: bool) -> None:
        if self._building:
            return
        for indice, grupo in enumerate(self._groups):
            if not grupo.pronto:
                continue
            check = self._checks[indice]
            check.blockSignals(True)
            check.setChecked(marcado)
            check.blockSignals(False)
        self._update_selection()

    def _update_selection(self, *_: object) -> None:
        if self._building:
            return
        selecionados = len(self.selected_keys())
        prontos = len(self._plano.prontos)
        self.selection_label.setText(
            f"{selecionados} de {prontos} grupo(s) pronto(s) selecionado(s)"
        )
        self.selection_label.setAccessibleDescription(
            f"{selecionados} de {prontos} grupos prontos selecionados"
        )
        self.confirm_button.setEnabled(selecionados > 0)
        self.confirm_button.setText(f"Confirmar envio ({selecionados})")
        if self._debug:
            self.confirm_button.setText("Validar")
            return

        self.select_all.blockSignals(True)
        self.select_all.setChecked(selecionados == prontos and prontos > 0)
        self.select_all.blockSignals(False)

    def _on_confirm(self) -> None:
        if not self.selected_keys():
            return
        self.accept()

    # ------------------------------------------------------------------
    # Dimensionamento e teclado
    # ------------------------------------------------------------------
    def showEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Ajusta o diálogo à tela e mantém o rodapé sempre visível."""
        super().showEvent(event)
        if not self._fitted:
            self._fitted = True
            self._fit_to_screen()
        if self.select_all.isEnabled():
            self.select_all.setFocus()
        else:
            self.table.setFocus()

    def _fit_to_screen(self) -> None:
        """Limita o diálogo à área útil da tela, deixando margem para a moldura."""
        screen = self.screen()
        if screen is None:
            return
        disponivel = screen.availableGeometry()
        if disponivel.width() <= 0 or disponivel.height() <= 0:
            return
        largura = min(
            1100,
            max(self.minimumWidth(), disponivel.width() - 80),
            disponivel.width() - 20,
        )
        altura = min(
            720,
            max(self.minimumHeight(), disponivel.height() - 80),
            disponivel.height() - 20,
        )
        self.resize(max(320, largura), max(320, altura))
        self.move(
            disponivel.center().x() - self.width() // 2,
            disponivel.center().y() - self.height() // 2,
        )

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (API Qt)
        """Permite marcar/desmarcar a linha selecionada pressionando Espaço."""
        if (
            obj is self.table
            and event.type() == QEvent.Type.KeyPress
            and event.key()
            in (
                Qt.Key.Key_Space,
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
            )
        ):
            linhas = self.table.selectionModel().selectedRows()
            if linhas:
                indice = linhas[0].row()
                if 0 <= indice < len(self._checks):
                    check = self._checks[indice]
                    if check.isEnabled():
                        check.toggle()
                        return True
        return super().eventFilter(obj, event)
