"""Janela principal do INS Dashboard Studio.

A janela segue o manual institucional GrupoSC: barra superior azul-marinho,
faixa de contexto, dois cartões de conteúdo (Configuração e Execução), banner
informativo e rodapé normativo.  O tema claro/escuro é alternado no cabeçalho.

.. note::
   Toda a lógica de execução, cancelamento, persistência e callbacks de thread
   é a mesma da versão anterior.  Os atributos ``self._*`` referenciados por
   essa lógica (``_segmented``, ``_source_selector``, ``_led``, ``_progress``,
   ``_log`` etc.) são mantidos.  A camada visual fica em ``_build_*``.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QThread
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
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
from .theme import build_stylesheet, current_theme, is_dark, set_theme
from .widgets import (
    AccentCard,
    Badge,
    FileSelector,
    GlossyButton,
    IconTile,
    IconWidget,
    LogView,
    NavButton,
    SegmentedSelector,
    SkyBackground,
    StatusLed,
    ThemeToggle,
    create_app_icon,
)

__all__ = ["MainWindow"]

# Identificadores usados nas preferências persistidas.
_SETTING_REPORT_TYPE = "report_type"
_SETTING_SOURCE = "source_file"
_SETTING_TEMPLATE = "template_file"
_SETTING_OUTPUT = "output_dir"
_SETTING_THEME = "ui/theme"

_MONO_META = "Motor: OfficeOpenXML / GrupoSC Kernel"

# Rótulo exibido na interface para o critério de agrupamento. O motorista
# continua sendo agrupado internamente por ``Apelido``; este texto é apenas
# de apresentação ao usuário.
_GROUP_DISPLAY = "Transportador"


class _ResponsiveColumns(QWidget):
    """Duas colunas que empilham em janelas estreitas.

    Puramente de layout: os cartões continuam os mesmos widgets, com os mesmos
    sinais e atributos.  Em larguras menores que ``breakpoint`` o painel de
    execução desce para baixo da configuração.
    """

    def __init__(
        self,
        left: QWidget,
        right: QWidget,
        parent: QWidget | None = None,
        breakpoint: int = 1000,
        spacing: int = 24,
    ) -> None:
        super().__init__(parent)
        self._left = left
        self._right = right
        self._breakpoint = breakpoint
        self._narrow: bool | None = None

        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(spacing)
        self._grid.setVerticalSpacing(spacing)
        self._grid.setColumnStretch(0, 5)
        self._grid.setColumnStretch(1, 7)
        self._apply(False)

    def _apply(self, narrow: bool) -> None:
        if self._narrow == narrow:
            return
        self._narrow = narrow
        self._grid.removeWidget(self._left)
        self._grid.removeWidget(self._right)
        if narrow:
            self._grid.setColumnStretch(0, 1)
            self._grid.setColumnStretch(1, 0)
            self._grid.addWidget(self._left, 0, 0, 1, 2)
            self._grid.addWidget(self._right, 1, 0, 1, 2)
        else:
            self._grid.setColumnStretch(0, 5)
            self._grid.setColumnStretch(1, 7)
            self._grid.addWidget(self._left, 0, 0)
            self._grid.addWidget(self._right, 0, 1)

    def resizeEvent(self, event) -> None:  # noqa: N802 (API Qt)
        super().resizeEvent(event)
        self._apply(self.width() < self._breakpoint)


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
            largura = min(1280, max(860, disponivel.width() - 80))
            altura = min(880, max(480, disponivel.height() - 80))
            self.resize(largura, altura)
        else:
            self.resize(1280, 880)

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

        self._restore_theme()
        self._build_ui()
        self._restore_settings()
        self._update_report_type(self._segmented.current, save=False)
        self._set_running(False)
        self._on_tab_changed(0)
        self._apply_theme(current_theme())

    # ------------------------------------------------------------------
    # Tema
    # ------------------------------------------------------------------
    def _restore_theme(self) -> None:
        """Restaura o tema salvo antes de montar os widgets."""
        tema = str(self._settings.value(_SETTING_THEME, "light") or "light")
        if tema not in ("light", "dark"):
            tema = "light"
        set_theme(tema)

    def _apply_theme(self, theme: str) -> None:
        """Reaplica o QSS global e repinta todos os componentes."""
        set_theme(theme)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(theme))
        self._theme_toggle.blockSignals(True)
        self._theme_toggle.setChecked(theme == "dark")
        self._theme_toggle.blockSignals(False)
        self._theme_toggle.refresh_theme()
        self.setWindowIcon(create_app_icon())
        for widget in self.findChildren(QWidget):
            refresh = getattr(widget, "refresh_theme", None)
            if callable(refresh):
                refresh()
        self._on_tab_changed(self._tabs.currentIndex())
        self._settings.setValue(_SETTING_THEME, theme)

    def _on_theme_toggled(self, escuro: bool) -> None:
        """Alterna entre o tema claro e o escuro."""
        self._apply_theme("dark" if escuro else "light")

    # ------------------------------------------------------------------
    # Construção da interface
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """Monta cabeçalho, faixa de contexto, abas e rodapé.

        Estrutura: cabeçalho fixo -> faixa de contexto + ``QTabWidget`` (com a
        barra nativa oculta, substituída pela navegação do cabeçalho) -> rodapé.
        As abas usam ``QScrollArea`` para continuar utilizáveis em telas baixas.
        """
        background = SkyBackground(self)
        self.setCentralWidget(background)

        outer = QVBoxLayout(background)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_header())

        content = QWidget(background)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 14, 24, 0)
        content_layout.setSpacing(12)
        content_layout.addWidget(self._build_ribbon())

        self._tabs = QTabWidget(content)
        self._tabs.setObjectName("mainTabs")
        self._tabs.setDocumentMode(True)
        self._tabs.tabBar().hide()

        geracao = QWidget(self._tabs)
        geracao.setObjectName("scrollContent")
        geracao_layout = QVBoxLayout(geracao)
        geracao_layout.setContentsMargins(0, 0, 0, 0)
        geracao_layout.setSpacing(16)
        geracao_layout.addWidget(self._build_generation_page())
        geracao_layout.addWidget(self._build_info_banner())
        geracao_layout.addStretch(1)

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

        self._tabs.currentChanged.connect(self._on_tab_changed)
        content_layout.addWidget(self._tabs, 1)
        outer.addWidget(content, 1)
        outer.addWidget(self._build_footer())

    def _build_header(self) -> QWidget:
        """Cria a barra institucional: marca, produto, navegação e tema."""
        header = QFrame(self)
        header.setObjectName("headerPanel")
        header.setFixedHeight(80)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        brand = QLabel("GrupoSC", header)
        brand.setObjectName("brandCard")
        brand.setFixedHeight(40)
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setAccessibleName("GrupoSC")
        layout.addWidget(brand)

        divider = QFrame(header)
        divider.setObjectName("verticalDivider")
        divider.setFixedSize(1, 30)
        layout.addWidget(divider)

        product = QVBoxLayout()
        product.setSpacing(1)
        product_name = QLabel("INS Dashboard Studio", header)
        product_name.setObjectName("productName")
        self._product_meta = QLabel(
            "Qualidade • Transporte & Segurança", header
        )
        self._product_meta.setObjectName("productMeta")
        product.addWidget(product_name)
        product.addWidget(self._product_meta)
        layout.addLayout(product)

        layout.addStretch(1)

        nav = QHBoxLayout()
        nav.setSpacing(4)
        self._nav_buttons: list[NavButton] = []
        for indice, (texto, icone) in enumerate(
            (
                ("Geração de Dashboards", "grid"),
                ("Envios de INS", "mail"),
            )
        ):
            botao = NavButton(texto, icone, header)
            botao.clicked.connect(
                lambda _=False, i=indice: self._tabs.setCurrentIndex(i)
            )
            nav.addWidget(botao)
            self._nav_buttons.append(botao)
        layout.addLayout(nav)

        layout.addStretch(1)

        self._theme_toggle = ThemeToggle(header)
        self._theme_toggle.blockSignals(True)
        self._theme_toggle.setChecked(is_dark())
        self._theme_toggle.blockSignals(False)
        self._theme_toggle.refresh_theme()
        self._theme_toggle.toggled.connect(self._on_theme_toggled)
        layout.addWidget(self._theme_toggle)

        return header

    def _build_ribbon(self) -> QWidget:
        """Cria a faixa de contexto com o título da área ativa."""
        ribbon = QFrame(self)
        ribbon.setObjectName("ribbonBar")

        layout = QHBoxLayout(ribbon)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)

        self._ribbon_icon = IconWidget("grid", 16, "accent", ribbon)
        self._ribbon_title = QLabel("Geração de Dashboards INS", ribbon)
        self._ribbon_title.setObjectName("ribbonTitle")

        layout.addWidget(self._ribbon_icon)
        layout.addWidget(self._ribbon_title)
        layout.addStretch(1)
        return ribbon

    def _build_generation_page(self) -> QWidget:
        """Cria a página com os cartões de configuração e execução."""
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self._columns = _ResponsiveColumns(
            self._build_config_panel(),
            self._build_run_panel(),
            page,
        )
        layout.addWidget(self._columns)
        return page

    def _build_config_panel(self) -> QWidget:
        """Cria o cartão de configuração (tipo de relatório e caminhos).

        Os widgets guardados em ``self._*`` são lidos por
        ``_build_config``/``_save_settings``/``_set_running``.
        """
        card = AccentCard(accent="orange")
        card.setMinimumWidth(360)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(0)

        eyebrow_row = QHBoxLayout()
        eyebrow_row.setSpacing(8)
        eyebrow = QLabel("PARÂMETROS DE ENTRADA", card)
        eyebrow.setObjectName("cardEyebrow")
        eyebrow_row.addWidget(eyebrow)
        eyebrow_row.addStretch(1)
        layout.addLayout(eyebrow_row)

        title_row = QHBoxLayout()
        title_row.setSpacing(9)
        title_icon = IconWidget("sliders", 20, "accent", card)
        title = QLabel("Configuração", card)
        title.setObjectName("cardTitle")
        title_row.addWidget(title_icon)
        title_row.addWidget(title)
        title_row.addStretch(1)
        layout.addSpacing(6)
        layout.addLayout(title_row)

        hint = QLabel(
            "Defina o critério de agrupamento e os caminhos de origem e "
            "gravação do lote.",
            card,
        )
        hint.setObjectName("descriptionText")
        hint.setWordWrap(True)
        layout.addSpacing(4)
        layout.addWidget(hint)

        layout.addSpacing(14)
        divider = QFrame(card)
        divider.setObjectName("divider")
        layout.addWidget(divider)
        layout.addSpacing(16)

        group_label = QLabel("AGRUPAMENTO DO LOTE", card)
        group_label.setObjectName("fieldCaption")
        layout.addWidget(group_label)
        layout.addSpacing(8)

        self._segmented = SegmentedSelector(
            [("motorista", "Motorista"), ("transportador", "Transportador")],
            parent=card,
        )
        self._segmented.changed.connect(self._update_report_type)
        layout.addWidget(self._segmented)
        layout.addSpacing(14)

        info_box = QFrame(card)
        info_box.setObjectName("infoBox")
        info_layout = QVBoxLayout(info_box)
        info_layout.setContentsMargins(14, 12, 14, 10)
        info_layout.setSpacing(8)

        self._description = QLabel("", info_box)
        self._description.setObjectName("descriptionText")
        self._description.setWordWrap(True)
        info_layout.addWidget(self._description)

        info_divider = QFrame(info_box)
        info_divider.setObjectName("divider")
        info_layout.addWidget(info_divider)

        group_row = QHBoxLayout()
        group_row.setSpacing(8)
        group_caption = QLabel("AGRUPAMENTO ATIVO:", info_box)
        group_caption.setObjectName("fieldCaption")
        self._group_chip = QLabel("", info_box)
        self._group_chip.setObjectName("activeChip")
        group_row.addWidget(group_caption)
        group_row.addWidget(self._group_chip)
        group_row.addStretch(1)
        info_layout.addLayout(group_row)
        layout.addWidget(info_box)

        layout.addSpacing(14)

        self._source_selector = FileSelector(
            "Arquivo do relatório (.xlsx)",
            button_text="Procurar...",
            mode="file",
            dialog_title="Selecionar o relatório INS",
            file_filter="Planilhas do Excel (*.xlsx *.xlsm)",
            parent=card,
        )
        self._source_selector.selectionChanged.connect(
            self._refresh_structure_badge
        )
        self._template_selector = FileSelector(
            "Template do dashboard (.xlsx)",
            button_text="Procurar...",
            mode="file",
            dialog_title="Selecionar o template do dashboard",
            file_filter="Templates do Excel (*.xlsx *.xlsm *.xltx *.xltm)",
            parent=card,
        )
        self._output_selector = FileSelector(
            "Pasta de saída dos dashboards",
            button_text="Escolher...",
            mode="directory",
            dialog_title="Selecionar a pasta de saída",
            parent=card,
        )
        for seletor in (
            self._source_selector,
            self._template_selector,
            self._output_selector,
        ):
            layout.addWidget(seletor)
            layout.addSpacing(10)

        quick = QFrame(card)
        quick.setObjectName("quickBox")
        quick_layout = QHBoxLayout(quick)
        quick_layout.setContentsMargins(12, 10, 12, 10)
        quick_layout.setSpacing(12)

        quick_icon = IconTile("layers", 36, "accent", radius=4, parent=quick)
        quick_text = QVBoxLayout()
        quick_text.setSpacing(1)
        quick_title = QLabel("Estrutura de Origem Mapeada", quick)
        quick_title.setObjectName("quickTitle")
        self._structure_meta = QLabel(
            f"Aba INS • agrupamento por {_GROUP_DISPLAY}", quick
        )
        self._structure_meta.setObjectName("quickMeta")
        quick_text.addWidget(quick_title)
        quick_text.addWidget(self._structure_meta)

        self._structure_badge = Badge("AGUARDANDO", "idle")
        self._structure_badge.setAccessibleName(
            "Situação da estrutura de origem"
        )
        quick_layout.addWidget(quick_icon)
        quick_layout.addLayout(quick_text, 1)
        quick_layout.addWidget(self._structure_badge)
        layout.addWidget(quick)

        layout.addStretch(1)
        return card

    def _build_run_panel(self) -> QWidget:
        """Cria o cartão de execução (progresso, console e ações).

        Cada controle é o destino dos callbacks de ``JobWorker`` (progresso,
        log, conclusão, falha e cancelamento).
        """
        card = AccentCard(accent="accent")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        play_icon = IconTile("play", 34, "accent", radius=4, parent=card)
        header_row.addWidget(play_icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("Execução", card)
        title.setObjectName("cardTitle")
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self._led = StatusLed(card)
        self._status_label = QLabel("Pronto para gerar", card)
        self._status_label.setObjectName("statusText")
        self._status_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        status_row.addWidget(self._led)
        status_row.addWidget(self._status_label, 1)
        title_box.addWidget(title)
        title_box.addLayout(status_row)
        header_row.addLayout(title_box, 1)

        clear_log_button = GlossyButton(
            "Limpar log",
            card,
            variant="glossButton",
            icon_name="trash",
            icon_role="muted",
            icon_size=13,
        )
        clear_log_button.setObjectName("miniButton")
        clear_log_button.setFixedHeight(30)
        clear_log_button.clicked.connect(self._clear_log)
        header_row.addWidget(clear_log_button)
        layout.addLayout(header_row)

        layout.addSpacing(2)
        divider = QFrame(card)
        divider.setObjectName("divider")
        layout.addWidget(divider)
        layout.addSpacing(2)

        progress_head = QHBoxLayout()
        progress_head.setSpacing(8)
        progress_caption = QLabel("PROGRESSO DO LOTE", card)
        progress_caption.setObjectName("fieldCaption")
        self._counter_label = QLabel("0 de 0", card)
        self._counter_label.setObjectName("statusText")
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        progress_head.addWidget(progress_caption)
        progress_head.addStretch(1)
        progress_head.addWidget(self._counter_label)
        layout.addLayout(progress_head)

        self._progress = QProgressBar(card)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("%p%")
        self._progress.setTextVisible(True)
        layout.addWidget(self._progress)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        self._group_label = QLabel("Fila ociosa • Aguardando operador", card)
        self._group_label.setObjectName("groupText")
        engine_label = QLabel(_MONO_META, card)
        engine_label.setObjectName("groupText")
        engine_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        progress_row.addWidget(self._group_label, 1)
        progress_row.addWidget(engine_label)
        layout.addLayout(progress_row)

        self._log = LogView(card)
        self._log.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._log, 1)

        self._summary_label = QLabel("", card)
        self._summary_label.setObjectName("summaryText")
        self._summary_label.setWordWrap(True)
        layout.addWidget(self._summary_label)

        action_divider = QFrame(card)
        action_divider.setObjectName("divider")
        layout.addWidget(action_divider)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self._open_folder_button = GlossyButton(
            "Abrir pasta de saída",
            card,
            variant="glossButton",
            icon_name="folder",
            icon_role="accent",
            icon_size=15,
        )
        self._open_folder_button.setEnabled(False)
        self._open_folder_button.clicked.connect(self._open_output_folder)
        actions.addWidget(self._open_folder_button)
        actions.addStretch(1)

        self._cancel_button = GlossyButton("Cancelar", card)
        self._cancel_button.setObjectName("dangerButton")
        self._cancel_button.setEnabled(False)
        self._cancel_button.clicked.connect(self._cancel_job)
        actions.addWidget(self._cancel_button)

        self._generate_button = GlossyButton(
            "Gerar dashboards",
            card,
            variant="primaryButton",
            icon_name="bolt",
            icon_role="navy",
            icon_size=16,
        )
        self._generate_button.clicked.connect(self._start_job)
        actions.addWidget(self._generate_button)
        layout.addLayout(actions)

        return card

    def _build_info_banner(self) -> QWidget:
        """Cria o banner informativo com os protocolos disponíveis."""
        banner = QFrame(self)
        banner.setObjectName("infoBanner")
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        icon = IconTile(
            "shield",
            34,
            "warn_bg",
            "warn_border",
            icon_role="warn_text",
            radius=4,
            parent=banner,
        )
        layout.addWidget(icon)

        texto = QLabel(
            "Arquivos e pastas são sempre escolhidos por você — nada é gravado "
            "de forma fixa ou rígida no aplicativo.",
            banner,
        )
        texto.setObjectName("sectionHint")
        texto.setWordWrap(True)
        layout.addWidget(texto, 1)

        excel = QLabel("• Excel para gerar dashboards", banner)
        excel.setObjectName("connectionChip")
        excel.setAccessibleName("Protocolo Excel disponível para geração")
        layout.addWidget(excel)

        outlook = QLabel("• Outlook para os envios", banner)
        outlook.setObjectName("connectionChip")
        outlook.setProperty("variant", "info")
        outlook.setAccessibleName("Protocolo Outlook disponível para envios")
        layout.addWidget(outlook)
        return banner

    def _build_footer(self) -> QWidget:
        """Cria o rodapé normativo institucional."""
        footer = QFrame(self)
        footer.setObjectName("footerBar")
        footer.setFixedHeight(52)

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(10)

        left = QLabel(
            "GrupoSC • Qualidade • Transporte & Segurança", footer
        )
        left.setObjectName("footerText")
        layout.addWidget(left)
        layout.addStretch(1)

        self._footer_right = QLabel(
            "Conformidade WCAG 2.2 AA / LGPD   •   "
            "INS Dashboard Studio • Núcleo de Logística Farmacêutica",
            footer,
        )
        self._footer_right.setObjectName("footerFaint")
        layout.addWidget(self._footer_right)
        return footer

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------
    def _on_tab_changed(self, index: int) -> None:
        """Sincroniza a navegação, a faixa de contexto e os ícones."""
        if not hasattr(self, "_nav_buttons"):
            return
        for i, botao in enumerate(self._nav_buttons):
            botao.set_active(i == index)
        if index == 0:
            self._ribbon_icon.set_icon("grid")
            self._ribbon_title.setText("Geração de Dashboards INS")
        else:
            self._ribbon_icon.set_icon("mail")
            self._ribbon_title.setText("Envios de INS por Transportadora")
        self._ribbon_icon.set_role("accent")

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
        self._group_chip.setText(_GROUP_DISPLAY)
        self._group_chip.setToolTip("Agrupamento por transportador")
        self._structure_meta.setText(
            f"Aba INS • agrupamento por {_GROUP_DISPLAY}"
        )
        if save:
            self._settings.setValue(_SETTING_REPORT_TYPE, report.key)

    def _refresh_structure_badge(self, *_: object) -> None:
        """Indica visualmente se há arquivo de origem selecionado."""
        if not hasattr(self, "_structure_badge"):
            return
        if self._source_selector.path:
            self._structure_badge.set_status("PRONTO", "ok")
        else:
            self._structure_badge.set_status("AGUARDANDO", "idle")

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
        self._refresh_structure_badge()

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
        self._group_label.setText("Preparando fila de grupos…")
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
        self._group_label.setText("Fila concluída • Operador liberado")

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
        self._group_label.setText("Fila interrompida • Aguardando operador")
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

        Ponto único de bloqueio da interface.
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
    def resizeEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Adapta o cabeçalho e o rodapé em janelas estreitas."""
        super().resizeEvent(event)
        largura = self.width()
        self._product_meta.setVisible(largura >= 1040)
        if hasattr(self, "_footer_right"):
            self._footer_right.setVisible(largura >= 1040)
        if hasattr(self, "_nav_buttons"):
            if largura < 940:
                for botao, curto in zip(
                    self._nav_buttons,
                    ("Geração", "Envios"),
                ):
                    botao.setText(curto)
            else:
                for botao, longo in zip(
                    self._nav_buttons,
                    ("Geração de Dashboards", "Envios de INS"),
                ):
                    botao.setText(longo)

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
