"""Janela principal do INS Dashboard Studio.

Reúne a configuração do trabalho (tipo de relatório, arquivo de origem,
template e pasta de saída), a área de execução (progresso, log e resumo) e
o controle do backend, que roda sempre em uma ``QThread`` separada.

.. note::
   **O layout será refeito.** Toda a hierarquia visual é montada em
   ``_build_*``; trocar a aparência significa reescrever esses métodos
   mantendo os mesmos atributos (``self._segmented``, ``self._source_selector``
   etc.), pois a lógica de execução e persistência os referencia diretamente.
   Não mova para a camada visual os sinais/slots, o controle de
   ``_running``/``_cancel_flag`` nem a persistência via ``QSettings``.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QThread
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from backend import JobConfig, JobError, JobResult, get_report_type

from .envios_tab import EnviosTab
from .widgets import (
    FileSelector,
    GlassPanel,
    GlossyButton,
    LogView,
    SegmentedSelector,
    StatusLed,
    SkyBackground,
    create_app_icon,
)

__all__ = ["MainWindow"]

# Identificadores usados nas preferências persistidas.
_SETTING_REPORT_TYPE = "report_type"
_SETTING_SOURCE = "source_file"
_SETTING_TEMPLATE = "template_file"
_SETTING_OUTPUT = "output_dir"


class MainWindow(QMainWindow):
    """Janela principal da aplicação."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("INS Dashboard Studio")
        self.setWindowIcon(create_app_icon())
        self.setMinimumSize(860, 480)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            disponivel = screen.availableGeometry()
            largura = min(1180, max(860, disponivel.width() - 80))
            altura = min(860, max(480, disponivel.height() - 80))
            self.resize(largura, altura)
        else:
            self.resize(1180, 860)

        self._settings = QSettings("INS", "INS Dashboard Studio")
        # Estado de execução: _running bloqueia a UI, _cancel_flag é lida pela
        # thread de trabalho e _close_after_cancel adia o fechamento da janela
        # até a thread terminar com segurança.
        self._cancel_flag = threading.Event()
        self._thread: QThread | None = None
        self._worker = None
        self._running = False
        self._output_dir: Path | None = None
        self._total_groups = 0
        self._close_after_cancel = False

        self._build_ui()
        self._restore_settings()
        self._update_report_type(self._segmented.current, save=False)
        self._set_running(False)

    # ------------------------------------------------------------------
    # Construção da interface
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """Monta a hierarquia de widgets da janela.

        Estrutura: cabeçalho fixo -> QTabWidget com as abas "Geração de
        dashboards" e "Envios de INS" -> rodapé. A aba de geração usa um
        QScrollArea para continuar utilizável em telas baixas.
        """
        background = SkyBackground(self)
        self.setCentralWidget(background)

        outer = QVBoxLayout(background)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)

        outer.addWidget(self._build_header())

        self._tabs = QTabWidget(background)
        self._tabs.setObjectName("mainTabs")
        self._tabs.setDocumentMode(True)

        geracao = QWidget(self._tabs)
        geracao_layout = QHBoxLayout(geracao)
        geracao_layout.setContentsMargins(0, 0, 0, 0)
        geracao_layout.setSpacing(12)
        geracao_layout.addWidget(self._build_config_panel(), 0)
        geracao_layout.addWidget(self._build_run_panel(), 1)

        geracao_scroll = QScrollArea(self._tabs)
        geracao_scroll.setObjectName("contentScroll")
        geracao_scroll.setWidgetResizable(True)
        geracao_scroll.setFrameShape(QFrame.Shape.NoFrame)
        geracao_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        geracao_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        geracao_scroll.setAccessibleName("Conteúdo da geração de dashboards")
        geracao_scroll.viewport().setObjectName("contentScrollViewport")
        geracao_scroll.setWidget(geracao)
        self._tabs.addTab(geracao_scroll, "Geração de dashboards")

        self._envios_tab = EnviosTab(self._tabs)
        self._tabs.addTab(self._envios_tab, "Envios de INS")

        outer.addWidget(self._tabs, 1)
        outer.addWidget(self._build_footer())

    def _build_header(self) -> QWidget:
        """Cria o cabeçalho com o ícone e o título do aplicativo."""
        panel = GlassPanel()
        # Vidro escuro: garante contraste para o título branco.
        panel.setObjectName("headerPanel")
        panel.setFixedHeight(84)

        layout = QHBoxLayout(panel)
        layout.setContentsMargins(16, 10, 18, 10)
        layout.setSpacing(14)

        icon_label = QLabel(panel)
        icon_label.setPixmap(
            create_app_icon(64).pixmap(56, 56)
        )
        icon_label.setFixedSize(58, 58)
        icon_label.setScaledContents(False)
        layout.addWidget(icon_label)

        texts = QVBoxLayout()
        texts.setSpacing(2)

        title = QLabel("INS Dashboard Studio", panel)
        title.setObjectName("appTitle")
        subtitle = QLabel(
            "Geração de dashboards INS e envio dos relatórios por transportadora",
            panel,
        )
        subtitle.setObjectName("appSubtitle")

        texts.addWidget(title)
        texts.addWidget(subtitle)
        layout.addLayout(texts, 1)

        chip = QLabel("Frutiger Aero", panel)
        chip.setObjectName("chip")
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(chip)

        return panel

    def _build_config_panel(self) -> QWidget:
        """Cria o painel de configuração (tipo de relatório e caminhos).

        Os widgets guardados em ``self._*`` não são decoração: cada um é lido
        por ``_build_config``/``_save_settings``/``_set_running``. Se o layout
        mudar, mantenha esses atributos.
        """
        panel = GlassPanel()
        panel.setFixedWidth(430)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Configuração", panel)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        hint = QLabel(
            "Escolha o tipo de relatório e os arquivos utilizados na geração.",
            panel,
        )
        hint.setObjectName("sectionHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Seletor segmentado Motorista | Transportador.
        self._segmented = SegmentedSelector(
            [("motorista", "Motorista"), ("transportador", "Transportador")],
            parent=panel,
        )
        self._segmented.changed.connect(self._update_report_type)
        layout.addWidget(self._segmented)

        self._description = QLabel("", panel)
        self._description.setObjectName("descriptionText")
        self._description.setWordWrap(True)
        layout.addWidget(self._description)

        group_row = QHBoxLayout()
        group_row.setSpacing(8)
        group_caption = QLabel("Agrupamento por:", panel)
        group_caption.setObjectName("fieldCaption")
        self._group_chip = QLabel("", panel)
        self._group_chip.setObjectName("chip")
        group_row.addWidget(group_caption)
        group_row.addWidget(self._group_chip)
        group_row.addStretch(1)
        layout.addLayout(group_row)

        separator = QFrame(panel)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(1)
        separator.setStyleSheet(
            "background: rgba(255, 255, 255, 220); border: none;"
        )
        layout.addWidget(separator)

        self._source_selector = FileSelector(
            "Arquivo do relatório (.xlsx)",
            button_text="Procurar…",
            mode="file",
            dialog_title="Selecionar o relatório INS",
            file_filter="Planilhas do Excel (*.xlsx *.xlsm)",
            parent=panel,
        )
        layout.addWidget(self._source_selector)

        self._template_selector = FileSelector(
            "Template do dashboard (.xlsx)",
            button_text="Procurar…",
            mode="file",
            dialog_title="Selecionar o template do dashboard",
            file_filter="Templates do Excel (*.xlsx *.xlsm *.xltx *.xltm)",
            parent=panel,
        )
        layout.addWidget(self._template_selector)

        self._output_selector = FileSelector(
            "Pasta de saída dos dashboards",
            button_text="Escolher…",
            mode="directory",
            dialog_title="Selecionar a pasta de saída",
            parent=panel,
        )
        layout.addWidget(self._output_selector)

        layout.addStretch(1)
        return panel

    def _build_run_panel(self) -> QWidget:
        """Cria o painel de execução (progresso, log e botões).

        Além da aparência, cada controle é o destino dos callbacks de
        ``JobWorker`` (progresso, log, conclusão, falha e cancelamento).
        """
        panel = GlassPanel()

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        title = QLabel("Execução", panel)
        title.setObjectName("sectionTitle")
        header_row.addWidget(title)

        self._led = StatusLed(panel)
        header_row.addWidget(self._led)

        self._status_label = QLabel("Pronto para gerar", panel)
        self._status_label.setObjectName("statusText")
        header_row.addWidget(self._status_label, 1)

        clear_log_button = GlossyButton("Limpar log", panel)
        clear_log_button.setObjectName("miniButton")
        clear_log_button.setFixedHeight(26)
        clear_log_button.clicked.connect(self._clear_log)
        header_row.addWidget(clear_log_button)
        layout.addLayout(header_row)

        self._progress = QProgressBar(panel)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("%p%")
        self._progress.setTextVisible(True)
        layout.addWidget(self._progress)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)

        self._counter_label = QLabel("0 de 0", panel)
        self._counter_label.setObjectName("groupText")
        progress_row.addWidget(self._counter_label)

        self._group_label = QLabel("", panel)
        self._group_label.setObjectName("groupText")
        self._group_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        progress_row.addWidget(self._group_label, 1)
        layout.addLayout(progress_row)

        self._summary_label = QLabel("", panel)
        self._summary_label.setObjectName("summaryText")
        self._summary_label.setWordWrap(True)
        layout.addWidget(self._summary_label)

        self._log = LogView(panel)
        self._log.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._log, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        self._open_folder_button = GlossyButton("Abrir pasta de saída", panel)
        self._open_folder_button.setObjectName("miniButton")
        self._open_folder_button.setEnabled(False)
        self._open_folder_button.clicked.connect(self._open_output_folder)
        buttons.addWidget(self._open_folder_button)

        buttons.addStretch(1)

        self._cancel_button = GlossyButton("Cancelar", panel)
        self._cancel_button.setObjectName("dangerButton")
        self._cancel_button.setEnabled(False)
        self._cancel_button.clicked.connect(self._cancel_job)
        buttons.addWidget(self._cancel_button)

        self._generate_button = GlossyButton("Gerar dashboards", panel)
        self._generate_button.setObjectName("primaryButton")
        self._generate_button.clicked.connect(self._start_job)
        buttons.addWidget(self._generate_button)

        layout.addLayout(buttons)
        return panel

    def _build_footer(self) -> QWidget:
        """Cria a barra inferior com atalhos e dicas de uso (só informativa)."""
        footer = QFrame(self)
        footer.setObjectName("glassPanel")
        footer.setFixedHeight(34)

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(14, 2, 14, 2)
        layout.setSpacing(12)

        left = QLabel(
            "Arquivos e pastas são sempre escolhidos por você — nada é fixo no aplicativo.",
            footer,
        )
        left.setObjectName("sectionHint")
        layout.addWidget(left)
        layout.addStretch(1)

        right = QLabel(
            "Excel para gerar dashboards · Outlook para os envios", footer
        )
        right.setObjectName("sectionHint")
        layout.addWidget(right)
        return footer

    # ------------------------------------------------------------------
    # Tipo de relatório
    # ------------------------------------------------------------------
    def _update_report_type(self, key: str, save: bool = True) -> None:
        """Atualiza textos auxiliares conforme o tipo de relatório ativo."""
        try:
            report = get_report_type(key)
        except KeyError:
            return

        self._description.setText(report.description)
        self._group_chip.setText(report.group_column)
        self._group_chip.setToolTip(
            f"Coluna de agrupamento do relatório: {report.group_column}"
        )
        if save:
            self._settings.setValue(_SETTING_REPORT_TYPE, report.key)

    # ------------------------------------------------------------------
    # Persistência de preferências
    # ------------------------------------------------------------------
    def _restore_settings(self) -> None:
        """Restaura tipo de relatório e últimos caminhos utilizados."""
        report_type = str(
            self._settings.value(_SETTING_REPORT_TYPE, "motorista")
        )
        if report_type in ("motorista", "transportador"):
            self._segmented.set_current(report_type, emit=False)

        source = str(self._settings.value(_SETTING_SOURCE, "") or "")
        template = str(self._settings.value(_SETTING_TEMPLATE, "") or "")
        output = str(self._settings.value(_SETTING_OUTPUT, "") or "")

        if source:
            self._source_selector.set_path(source)
        if template:
            self._template_selector.set_path(template)
        if output:
            self._output_selector.set_path(output)
            self._output_dir = Path(output)
            self._open_folder_button.setEnabled(Path(output).exists())

    def _save_settings(self) -> None:
        """Grava as preferências atuais."""
        self._settings.setValue(
            _SETTING_REPORT_TYPE, self._segmented.current
        )
        self._settings.setValue(
            _SETTING_SOURCE, self._source_selector.path
        )
        self._settings.setValue(
            _SETTING_TEMPLATE, self._template_selector.path
        )
        self._settings.setValue(
            _SETTING_OUTPUT, self._output_selector.path
        )
        self._envios_tab.save_settings()

    # ------------------------------------------------------------------
    # Execução
    # ------------------------------------------------------------------
    def _build_config(self) -> JobConfig:
        """Monta a configuração do job a partir da interface."""
        report = get_report_type(self._segmented.current)
        return JobConfig(
            report_type=report,
            source_file=Path(self._source_selector.path),
            template_file=Path(self._template_selector.path),
            output_dir=Path(self._output_selector.path),
        )

    def _start_job(self) -> None:
        """Valida as entradas e inicia a geração em uma thread de trabalho."""
        if self._running:
            return

        missing: list[str] = []
        if not self._source_selector.path:
            missing.append("Selecione o arquivo do relatório (.xlsx).")
        if not self._template_selector.path:
            missing.append("Selecione o template do dashboard (.xlsx).")
        if not self._output_selector.path:
            missing.append("Selecione a pasta de saída dos dashboards.")
        if missing:
            self._show_error("Configuração incompleta", "\n\n".join(missing))
            return

        try:
            config = self._build_config()
            config.validate()
        except JobError as erro:
            self._show_error("Não foi possível gerar", str(erro))
            return
        except Exception as erro:  # noqa: BLE001 - rede de segurança
            self._show_error(
                "Não foi possível gerar",
                f"Ocorreu um erro ao validar os arquivos escolhidos.\n\n"
                f"Detalhe técnico: {erro}",
            )
            return

        self._save_settings()
        self._output_dir = config.output_dir
        self._cancel_flag = threading.Event()
        self._total_groups = 0
        self._summary_label.clear()
        self._group_label.clear()
        self._progress.setRange(0, 0)
        self._progress.setValue(0)
        self._counter_label.setText("0 de 0")
        self._led.set_state("running")
        self._status_label.setText("Gerando dashboards…")
        self._log.append_log(
            f"Iniciando geração do relatório "
            f"'{config.report_type.label}'.",
            "info",
        )

        from .worker import JobWorker

        # O processamento (Excel/COM) é bloqueante: roda em QThread e conversa
        # com a interface apenas por sinais Qt (thread-safety).
        self._thread = QThread(self)
        self._worker = JobWorker(self._cancel_flag)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.cancelled.connect(self._on_cancelled)

        # Qualquer desfecho encerra a thread; só depois dela terminar a UI é
        # reabilitada (ver _on_thread_finished).
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._worker.cancelled.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)

        self._worker.set_config(config)
        self._set_running(True)
        self._thread.start()

    def _cancel_job(self) -> None:
        """Solicita o cancelamento da geração em andamento."""
        if not self._running:
            return
        self._cancel_flag.set()
        self._cancel_button.setEnabled(False)
        self._status_label.setText("Cancelando…")
        self._led.set_state("cancelled")
        self._log.append_log(
            "Cancelamento solicitado — finalizando o dashboard atual…",
            "warning",
        )

    # ------------------------------------------------------------------
    # Callbacks da thread de trabalho
    # ------------------------------------------------------------------
    def _on_progress(self, atual: int, total: int, grupo: str) -> None:
        """Atualiza a barra de progresso e o nome do grupo atual."""
        if total > 0:
            self._progress.setRange(0, total)
            self._progress.setValue(atual)
            self._progress.setFormat("%p%")
            self._total_groups = total
        self._counter_label.setText(f"{atual} de {total}")
        self._group_label.setText(f"Grupo: {grupo}")

    def _on_log(self, mensagem: str, nivel: str) -> None:
        """Adiciona uma mensagem ao log colorido."""
        self._log.append_log(mensagem, nivel)

    def _on_finished(self, resultado: JobResult) -> None:
        """Trata a conclusão bem-sucedida da geração."""
        self._led.set_state("ok")
        self._status_label.setText("Geração concluída")
        self._progress.setRange(0, max(1, self._progress.maximum()))
        self._progress.setValue(self._progress.maximum())
        self._counter_label.setText(
            f"{resultado.dashboard_count} de "
            f"{max(self._total_groups, resultado.dashboard_count)}"
        )
        self._group_label.clear()

        resumo = (
            f"{resultado.dashboard_count} dashboard(s) gerado(s) · "
            f"{resultado.total_rows} linha(s) · "
            f"{self._format_duration(resultado.duration_seconds)}"
        )
        if resultado.warnings:
            resumo += f" · {len(resultado.warnings)} aviso(s) no log"
        self._summary_label.setText(resumo)
        # Os avisos já foram registrados no log pelo backend durante a execução.
        self._summary_label.setToolTip(
            "\n\n".join(resultado.warnings) if resultado.warnings else ""
        )

        self._log.append_log(resumo, "success")
        self._open_folder_button.setEnabled(
            bool(self._output_dir and self._output_dir.exists())
        )

    def _on_failed(self, mensagem: str) -> None:
        """Mostra o erro do backend em uma caixa de diálogo amigável."""
        self._led.set_state("error")
        self._status_label.setText("Falha na geração")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._counter_label.setText("0 de 0")
        self._log.append_log(mensagem, "error")
        self._show_error("Não foi possível gerar os dashboards", mensagem)

    def _on_cancelled(self) -> None:
        """Informa que a geração foi cancelada pelo usuário."""
        self._led.set_state("cancelled")
        self._status_label.setText("Geração cancelada")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._counter_label.setText("Cancelado")
        self._group_label.clear()
        self._log.append_log(
            "Geração cancelada pelo usuário. Os dashboards já salvos "
            "foram mantidos.",
            "warning",
        )

    def _on_thread_finished(self) -> None:
        """Libera a thread de trabalho e restaura o estado da interface."""
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None
        self._set_running(False)

        if self._close_after_cancel:
            self._close_after_cancel = False
            self.close()

    # ------------------------------------------------------------------
    # Utilidades da interface
    # ------------------------------------------------------------------
    def _set_running(self, running: bool) -> None:
        """Habilita/desabilita os controles conforme o estado da execução.

        Ponto único de bloqueio da interface: se novos controles forem criados
        no redesign e precisarem ser bloqueados durante a geração, adicione-os
        aqui (e não espalhe chamadas de setEnabled pelas telas).
        """
        self._running = running
        self._generate_button.setEnabled(not running)
        self._cancel_button.setEnabled(running)
        self._segmented.setEnabled(not running)
        self._source_selector.setEnabled(not running)
        self._template_selector.setEnabled(not running)
        self._output_selector.setEnabled(not running)

    def _clear_log(self) -> None:
        """Limpa a área de log."""
        self._log.clear_log()

    def _open_output_folder(self) -> None:
        """Abre a pasta de saída no Explorador de Arquivos (Windows)."""
        target = self._output_dir
        if target is None:
            return
        if not target.exists():
            self._show_error(
                "Pasta não encontrada",
                f"A pasta de saída não existe mais:\n{target}",
            )
            return
        if sys.platform == "win32":
            try:
                os.startfile(str(target))  # noqa: S606 - ação do usuário
            except OSError as erro:
                self._show_error(
                    "Não foi possível abrir a pasta",
                    f"Detalhe técnico: {erro}",
                )
        else:
            self._show_error(
                "Recurso indisponível",
                "A abertura da pasta no Explorador só funciona no Windows.",
            )

    def _show_error(self, titulo: str, mensagem: str) -> None:
        """Exibe uma mensagem de erro sem traceback cru."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(titulo)
        box.setText(mensagem)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Formata a duração da geração de forma legível."""
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

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Fecha a janela com segurança durante uma geração em andamento."""
        if self._envios_tab.is_running:
            QMessageBox.information(
                self,
                "Envio em andamento",
                "Aguarde a conclusão do envio ou use o botão Cancelar na "
                "aba Envios antes de fechar o aplicativo.",
            )
            event.ignore()
            return

        if self._running:
            resposta = QMessageBox.question(
                self,
                "Geração em andamento",
                "Deseja cancelar a geração e sair?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

            # Cancela e espera a thread terminar para fechar com segurança.
            self._cancel_flag.set()
            self._cancel_button.setEnabled(False)
            self._status_label.setText("Cancelando…")
            self._led.set_state("cancelled")
            self._log.append_log(
                "Fechando o aplicativo: cancelando a geração em andamento…",
                "warning",
            )
            self._close_after_cancel = True
            event.ignore()
            return

        self._save_settings()
        super().closeEvent(event)
