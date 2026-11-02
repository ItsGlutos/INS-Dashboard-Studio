"""Tokens de design e folha de estilo (QSS) do INS Dashboard Studio.

O visual segue o manual institucional GrupoSC: base clara ``#F8FAFC``, cartões
brancos de aresta 8 px, tipografia Chivo, azul operacional ``#0090D0`` e laranja
de destaque ``#FF9F00`` sobre azul-marinho ``#1C2445``.  O mesmo vocabulário é
oferecido em **tema escuro** (fundo ``#101B33``, cartões ``#16224A``), alternável
em tempo de execução.

.. note::
   Este módulo não contém lógica de negócio. Ele expõe:

   * :func:`build_stylesheet` -- API usada por ``main.py`` e pelos testes;
   * :func:`set_theme`, :func:`current_theme`, :func:`is_dark` e
     :func:`palette` -- usados pelo alternador de tema;
   * :data:`LOG_COLORS` -- cores do console (sempre escuro) lidas por
     ``ui.widgets.LogView``;
   * :func:`led_color` -- cor do LED de status conforme o tema atual.

   Ao trocar o tema, os ``objectName`` e as propriedades dinâmicas
   (``active``, ``variant``, ``empty``) precisam continuar iguais: o QSS e os
   componentes de ``ui/widgets.py`` dependem deles.
"""

from __future__ import annotations

from pathlib import Path
from string import Template

# --------------------------------------------------------------------------
# Identidade do aplicativo
# --------------------------------------------------------------------------
APP_NAME = "INS Dashboard Studio"
APP_ORG = "INS"
APP_FONT = "Chivo"
APP_FONT_FALLBACK = "Segoe UI"
MONO_FONT = "Cascadia Mono"

# --------------------------------------------------------------------------
# Paletas
# --------------------------------------------------------------------------
LIGHT: dict[str, str] = {
    "theme": "light",
    # Superfícies
    "bg": "#F8FAFC",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFC",
    "surface_sunken": "#F1F5F9",
    "hover": "#F8FAFC",
    "pressed": "#E2E8F0",
    # Bordas
    "border": "#E2E8F0",
    "border_strong": "#CBD5E1",
    "divider": "#E2E8F0",
    # Texto
    "text": "#1C2445",
    "body": "#334155",
    "muted": "#475569",
    "subtle": "#64748B",
    "faint": "#94A3B8",
    "inverse": "#FFFFFF",
    # Institucional
    "navy": "#1C2445",
    "orange": "#FF9F00",
    "orange_hover": "#FFB020",
    "orange_pressed": "#E58A00",
    "orange_deep": "#F17626",
    "eyebrow": "#A34700",
    "accent": "#0090D0",
    "accent_deep": "#005C8A",
    "accent_soft": "#EFF6FF",
    # Cabeçalho / rodapé
    "header_bg": "#1C2445",
    "header_border": "#F17626",
    "header_text": "#FFFFFF",
    "header_muted": "#CBD5E1",
    "brand_bg": "#FFFFFF",
    "brand_border": "#FFFFFF",
    "brand_text": "#1C2445",
    "footer_bg": "#1C2445",
    "footer_border": "#334155",
    "footer_text": "#CBD5E1",
    "footer_faint": "#94A3B8",
    # Navegação
    "nav_text": "#CBD5E1",
    "nav_hover": "#223057",
    "nav_active_bg": "#0090D0",
    "nav_active_border": "#0090D0",
    "nav_active_text": "#FFFFFF",
    "nav_icon": "#CBD5E1",
    "nav_icon_active": "#FFFFFF",
    # Faixa de contexto
    "ribbon_bg": "#FFFFFF",
    "ribbon_border": "#E2E8F0",
    # Segmentos
    "seg_bg": "#F1F5F9",
    "seg_border": "#E2E8F0",
    "seg_item_bg": "transparent",
    "seg_item_border": "transparent",
    "seg_text": "#475569",
    "seg_icon": "#475569",
    "seg_hover": "#E2E8F0",
    "seg_active_bg": "#1C2445",
    "seg_active_border": "#1C2445",
    "seg_active_text": "#FFFFFF",
    "seg_active_icon": "#FF9F00",
    # Campos
    "field_bg": "#FFFFFF",
    "field_border": "#E2E8F0",
    "field_focus": "#0090D0",
    # Badges e avisos
    "ok_bg": "#ECFDF5",
    "ok_border": "#A7F3D0",
    "ok_text": "#047857",
    "ok_strong": "#065F46",
    "ok_dot": "#059669",
    "warn_bg": "#FFF7ED",
    "warn_border": "#FED7AA",
    "warn_text": "#A34700",
    "danger": "#B42318",
    "danger_bg": "#FEF2F2",
    "danger_border": "#FECACA",
    "info_bg": "#EFF6FF",
    "info_border": "#BFDBFE",
    "info_text": "#005C8A",
    "neutral_bg": "#F1F5F9",
    "neutral_border": "#E2E8F0",
    "neutral_text": "#475569",
    # Botões
    "btn_bg": "#FFFFFF",
    "btn_border": "#CBD5E1",
    "btn_text": "#1C2445",
    "btn_disabled_bg": "#F1F5F9",
    "btn_disabled_text": "#94A3B8",
    "cancel_bg": "#F1F5F9",
    "cancel_border": "#E2E8F0",
    "cancel_text": "#64748B",
    "cancel_hover": "#E2E8F0",
    # Console (sempre escuro)
    "console_bg": "#101B33",
    "console_header": "#16224A",
    "console_border": "#23335A",
    "console_text": "#CBD5E1",
    "console_title": "#CBD5E1",
    "console_meta": "#94A3B8",
    # Abas internas
    "tab_bg": "#FFFFFF",
    "tab_border": "#E2E8F0",
    "tab_text": "#475569",
    "tab_hover": "#F1F5F9",
    "tab_active_bg": "#1C2445",
    "tab_active_border": "#1C2445",
    "tab_active_text": "#FFFFFF",
    # Diálogo
    "dialog_bg": "#F8FAFC",
}

DARK: dict[str, str] = {
    "theme": "dark",
    "bg": "#101B33",
    "surface": "#16224A",
    "surface_alt": "#101B33",
    "surface_sunken": "#0E1830",
    "hover": "#1B2C57",
    "pressed": "#23335A",
    "border": "#23335A",
    "border_strong": "#5E7191",
    "divider": "#23335A",
    "text": "#FFFFFF",
    "body": "#C9D6E8",
    "muted": "#8FA5C7",
    "subtle": "#7CC6EA",
    "faint": "#5E7191",
    "inverse": "#101B33",
    "navy": "#1C2445",
    "orange": "#FF9F00",
    "orange_hover": "#FFB020",
    "orange_pressed": "#E58A00",
    "orange_deep": "#F17626",
    "eyebrow": "#FF9F00",
    "accent": "#33A6DE",
    "accent_deep": "#7CC6EA",
    "accent_soft": "#1B2C57",
    "header_bg": "#08132B",
    "header_border": "#23335A",
    "header_text": "#FFFFFF",
    "header_muted": "#8896A6",
    "brand_bg": "#101B33",
    "brand_border": "#23335A",
    "brand_text": "#FFFFFF",
    "footer_bg": "#08132B",
    "footer_border": "#23335A",
    "footer_text": "#C9D6E8",
    "footer_faint": "#8896A6",
    "nav_text": "#8896A6",
    "nav_hover": "#16224A",
    "nav_active_bg": "#16224A",
    "nav_active_border": "#33A6DE",
    "nav_active_text": "#FFFFFF",
    "nav_icon": "#8FA5C7",
    "nav_icon_active": "#33A6DE",
    "ribbon_bg": "transparent",
    "ribbon_border": "#23335A",
    "seg_bg": "transparent",
    "seg_border": "transparent",
    "seg_item_bg": "#16224A",
    "seg_item_border": "#5E7191",
    "seg_text": "#C9D6E8",
    "seg_icon": "#8FA5C7",
    "seg_hover": "#1B2C57",
    "seg_active_bg": "#101B33",
    "seg_active_border": "#33A6DE",
    "seg_active_text": "#FFFFFF",
    "seg_active_icon": "#33A6DE",
    "field_bg": "#101B33",
    "field_border": "#5E7191",
    "field_focus": "#33A6DE",
    "ok_bg": "#0A2619",
    "ok_border": "#15803D",
    "ok_text": "#86EFAC",
    "ok_strong": "#86EFAC",
    "ok_dot": "#86EFAC",
    "warn_bg": "#2B1D08",
    "warn_border": "#B45309",
    "warn_text": "#FCD34D",
    "danger": "#FCA5A5",
    "danger_bg": "#2B1214",
    "danger_border": "#7F1D1D",
    "info_bg": "#1B2C57",
    "info_border": "#33A6DE",
    "info_text": "#7CC6EA",
    "neutral_bg": "#101B33",
    "neutral_border": "#23335A",
    "neutral_text": "#8FA5C7",
    "btn_bg": "#16224A",
    "btn_border": "#5E7191",
    "btn_text": "#FFFFFF",
    "btn_disabled_bg": "#1B2C57",
    "btn_disabled_text": "#5E7191",
    "cancel_bg": "transparent",
    "cancel_border": "#23335A",
    "cancel_text": "#8FA5C7",
    "cancel_hover": "#1B2C57",
    "console_bg": "#08132B",
    "console_header": "#101B33",
    "console_border": "#23335A",
    "console_text": "#C9D6E8",
    "console_title": "#C9D6E8",
    "console_meta": "#8FA5C7",
    "tab_bg": "#101B33",
    "tab_border": "#23335A",
    "tab_text": "#8FA5C7",
    "tab_hover": "#16224A",
    "tab_active_bg": "#16224A",
    "tab_active_border": "#33A6DE",
    "tab_active_text": "#FFFFFF",
    "dialog_bg": "#101B33",
}

# Cores do log (texto claro sobre o console escuro, que é escuro nos dois temas).
LOG_COLORS: dict[str, str] = {
    "info": "#7CC6EA",
    "success": "#86EFAC",
    "warning": "#FCD34D",
    "error": "#FCA5A5",
}

#: Rótulos de nível exibidos no console.
LOG_LABELS: dict[str, str] = {
    "info": "INFO",
    "success": "OK",
    "warning": "REGRAS",
    "error": "ERRO",
}

_LED = {
    "light": {
        "idle": "#64748B",
        "running": "#0090D0",
        "ok": "#059669",
        "error": "#B42318",
        "cancelled": "#D97706",
    },
    "dark": {
        "idle": "#8FA5C7",
        "running": "#33A6DE",
        "ok": "#86EFAC",
        "error": "#FCA5A5",
        "cancelled": "#FCD34D",
    },
}

# Compatibilidade com imports antigos (widgets LÊ estas cores em runtime).
LED_COLORS: dict[str, str] = dict(_LED["light"])

_theme = "light"
_fonts_loaded = False


# --------------------------------------------------------------------------
# API de tema
# --------------------------------------------------------------------------
def palette(theme: str | None = None) -> dict[str, str]:
    """Devolve a paleta do tema pedido (ou do tema atual)."""
    escolhido = theme or _theme
    return DARK if escolhido == "dark" else LIGHT


def current_theme() -> str:
    """Nome do tema ativo: ``"light"`` ou ``"dark"``."""
    return _theme


def is_dark() -> bool:
    """Diz se o tema escuro está ativo."""
    return _theme == "dark"


def set_theme(theme: str) -> None:
    """Define o tema ativo (``"light"``/``"dark"``) sem reaplicar o QSS."""
    global _theme
    if theme not in ("light", "dark"):
        return
    _theme = theme
    LED_COLORS.update(_LED[_theme])


def led_color(state: str) -> str:
    """Cor do LED de status no tema atual."""
    return _LED[_theme].get(state, _LED[_theme]["idle"])


def font_stack() -> str:
    """Famílias de fonte usadas pelo QSS (Chivo com fallback do sistema)."""
    return f'"{APP_FONT}", "{APP_FONT_FALLBACK}"'


def load_fonts() -> None:
    """Carrega as fontes Chivo embarcadas em ``ui/assets/fonts``.

    Silenciosamente não faz nada quando não há ``QGuiApplication`` (por
    exemplo em testes que só importam a paleta).  As fontes são OFL e vão
    junto do projeto: o aplicativo continua idêntico sem internet.
    """
    global _fonts_loaded
    if _fonts_loaded:
        return
    try:
        from PyQt6.QtGui import QFontDatabase
        from PyQt6.QtWidgets import QApplication
    except ImportError:  # pragma: no cover - PyQt6 é dependência obrigatória
        return
    if QApplication.instance() is None:
        return
    pasta = Path(__file__).resolve().parent / "assets" / "fonts"
    if pasta.is_dir():
        for arquivo in sorted(pasta.glob("*.ttf")):
            QFontDatabase.addApplicationFont(str(arquivo))
    _fonts_loaded = True


def build_stylesheet(theme: str | None = None) -> str:
    """Devolve a folha de estilo QSS completa para o tema pedido.

    Quando ``theme`` é informado, ele também passa a ser o tema ativo: assim
    os componentes desenhados com ``QPainter`` usam a mesma paleta do QSS.
    """
    if theme is not None:
        set_theme(theme)
    load_fonts()
    p = palette()
    return _QSS_TEMPLATE.substitute(font=font_stack(), **p)


# --------------------------------------------------------------------------
# Folha de estilo
# --------------------------------------------------------------------------
_QSS_TEMPLATE = Template(
    """
/* =================================================================== */
/* Base                                                                */
/* =================================================================== */
* {
    font-family: $font;
}
QWidget {
    color: $text;
    font-size: 12px;
}
QMainWindow,
QWidget#appBackground {
    background: transparent;
}
QScrollArea#contentScroll,
QScrollArea#dialogScroll {
    background: transparent;
    border: none;
}
QWidget#contentScrollViewport,
QWidget#scrollContent {
    background: transparent;
}
QFrame#glassPanel,
QFrame#card {
    background: $surface;
    border: 1px solid $border;
    border-radius: 8px;
}
QFrame#divider {
    background: $divider;
    border: none;
    max-height: 1px;
    min-height: 1px;
}
QFrame#verticalDivider {
    background: $border_strong;
    border: none;
}

/* =================================================================== */
/* Cabeçalho institucional                                             */
/* =================================================================== */
QFrame#headerPanel {
    background: $header_bg;
    border: none;
    border-bottom: 1px solid $header_border;
}
QLabel#brandCard {
    background: $brand_bg;
    border: 1px solid $brand_border;
    border-radius: 0px;
    color: $brand_text;
    font-size: 21px;
    font-weight: 800;
    letter-spacing: -0.5px;
    padding: 4px 14px;
}
QLabel#productName {
    color: $header_text;
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0px;
}
QLabel#productMeta {
    color: $header_muted;
    font-size: 11px;
    letter-spacing: 0.2px;
}
QLabel#versionChip {
    background: transparent;
    border: 1px solid $border_strong;
    border-radius: 3px;
    color: $accent;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 2px 7px;
}
QToolButton#themeToggle {
    background: transparent;
    border: 1px solid $border_strong;
    border-radius: 8px;
    padding: 0px;
}
QToolButton#themeToggle:hover {
    background: $nav_hover;
    border-color: $accent;
}
QToolButton#themeToggle:focus {
    border: 2px solid $accent;
}

/* =================================================================== */
/* Navegação principal                                                 */
/* =================================================================== */
QPushButton#navButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: $nav_text;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 12px;
    text-align: left;
}
QPushButton#navButton:hover {
    background: $nav_hover;
    color: $header_text;
}
QPushButton#navButton[active="true"] {
    background: $nav_active_bg;
    border: 2px solid $nav_active_border;
    color: $nav_active_text;
    font-weight: 700;
}
QPushButton#navButton:focus {
    border: 2px solid $accent;
}

/* =================================================================== */
/* Faixa de contexto                                                   */
/* =================================================================== */
QFrame#ribbonBar {
    background: $ribbon_bg;
    border: 1px solid $ribbon_border;
    border-radius: 8px;
}
QLabel#ribbonTitle {
    color: $text;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.2px;
}

/* =================================================================== */
/* Cartões e tipografia                                                */
/* =================================================================== */
QLabel#cardEyebrow {
    color: $eyebrow;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.1px;
}
QLabel#cardTitle {
    color: $text;
    font-size: 25px;
    font-weight: 700;
    letter-spacing: -0.6px;
}
QLabel#pageTitle {
    color: $text;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.3px;
}
QLabel#sectionTitle {
    color: $text;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: -0.2px;
}
QLabel#sectionHint,
QLabel#descriptionText,
QLabel#infoText {
    color: $body;
    font-size: 13px;
}
QLabel#fieldCaption {
    color: $muted;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#fieldLabel {
    color: $text;
    font-size: 13px;
    font-weight: 600;
}
QLabel#fieldPath {
    color: $text;
    font-size: 13px;
}
QLabel#fieldPath[empty="true"] {
    color: $faint;
    font-style: italic;
}
QLabel#groupText {
    color: $muted;
    font-size: 11px;
}
QLabel#summaryText {
    color: $muted;
    font-size: 11px;
}
QLabel#statusText {
    color: $text;
    font-size: 13px;
    font-weight: 600;
}
QLabel#chip {
    background: $info_bg;
    border: 1px solid $info_border;
    border-radius: 4px;
    color: $info_text;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
}
QLabel#countChip {
    background: $surface_sunken;
    border: 1px solid $border;
    border-radius: 4px;
    color: $text;
    font-size: 10px;
    font-weight: 700;
    padding: 5px 10px;
}

/* Caixa informativa / resumo */
QFrame#infoBox {
    background: $surface_alt;
    border: 1px solid $border;
    border-radius: 6px;
}
QLabel#activeChip {
    background: $info_bg;
    border: 1px solid $info_border;
    border-radius: 3px;
    color: $info_text;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.4px;
    padding: 3px 7px;
}
QFrame#quickBox {
    background: $info_bg;
    border: 1px solid $info_border;
    border-radius: 6px;
}
QLabel#quickTitle {
    color: $text;
    font-size: 13px;
    font-weight: 700;
}
QLabel#quickMeta {
    color: $muted;
    font-size: 11px;
}
QLabel#quickIcon {
    background: $accent;
    border-radius: 4px;
}
QLabel#codeChip {
    background: $field_bg;
    border: 1px solid $border;
    border-radius: 3px;
    color: $accent_deep;
    font-size: 11px;
    padding: 1px 6px;
}

/* Badges */
QLabel#badge {
    border-radius: 3px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 3px 8px;
}
QLabel#badge[variant="ok"] {
    background: $ok_bg;
    border: 1px solid $ok_border;
    color: $ok_text;
}
QLabel#badge[variant="idle"] {
    background: $neutral_bg;
    border: 1px solid $neutral_border;
    color: $neutral_text;
}
QLabel#badge[variant="warn"] {
    background: $warn_bg;
    border: 1px solid $warn_border;
    color: $warn_text;
}
QLabel#badge[variant="info"] {
    background: $info_bg;
    border: 1px solid $info_border;
    color: $info_text;
}
QLabel#badge[variant="danger"] {
    background: $danger_bg;
    border: 1px solid $danger_border;
    color: $danger;
}

/* =================================================================== */
/* Campos                                                              */
/* =================================================================== */
QFrame#fieldFrame {
    background: $field_bg;
    border: 1px solid $field_border;
    border-radius: 6px;
}
QFrame#fieldFrame[invalid="true"] {
    border: 1px solid $danger_border;
}
QLineEdit,
QTextEdit#bodyEditor,
QListWidget#copyList,
QTableWidget#confirmTable {
    background: $field_bg;
    border: 1px solid $border;
    border-radius: 5px;
    color: $text;
    padding: 6px 8px;
    selection-background-color: $info_bg;
    selection-color: $text;
}
QLineEdit:focus,
QTextEdit#bodyEditor:focus,
QListWidget#copyList:focus {
    border: 1px solid $field_focus;
}
QLineEdit:disabled,
QTextEdit#bodyEditor:disabled,
QListWidget#copyList:disabled {
    background: $surface_sunken;
    color: $faint;
}
QLineEdit#bodySubject {
    font-size: 12px;
    font-weight: 600;
}
QListWidget#copyList::item {
    border-radius: 3px;
    padding: 5px 8px;
}
QListWidget#copyList::item:selected {
    background: $info_bg;
    color: $accent_deep;
}

/* =================================================================== */
/* Botões                                                              */
/* =================================================================== */
QPushButton#glossButton,
QPushButton#miniButton {
    background: $btn_bg;
    border: 1px solid $btn_border;
    border-radius: 6px;
    color: $btn_text;
    font-size: 11px;
    font-weight: 600;
    padding: 7px 14px;
}
QPushButton#glossButton:hover,
QPushButton#miniButton:hover {
    background: $hover;
    border-color: $accent;
}
QPushButton#glossButton:pressed,
QPushButton#miniButton:pressed {
    background: $pressed;
}
QPushButton#glossButton:disabled,
QPushButton#miniButton:disabled {
    background: $btn_disabled_bg;
    border-color: $border;
    color: $btn_disabled_text;
}
QPushButton#glossButton:focus,
QPushButton#miniButton:focus {
    border: 2px solid $accent;
}

QPushButton#primaryButton {
    background: $orange;
    border: 1px solid $orange;
    border-radius: 6px;
    color: $navy;
    font-size: 14px;
    font-weight: 800;
    padding: 11px 22px;
}
QPushButton#primaryButton:hover {
    background: $orange_hover;
    border-color: $orange_hover;
}
QPushButton#primaryButton:pressed {
    background: $orange_pressed;
    border-color: $orange_pressed;
}
QPushButton#primaryButton:disabled {
    background: $btn_disabled_bg;
    border-color: $border;
    color: $btn_disabled_text;
}
QPushButton#primaryButton:focus {
    border: 2px solid $text;
}

QPushButton#dangerButton {
    background: $cancel_bg;
    border: 1px solid $cancel_border;
    border-radius: 6px;
    color: $cancel_text;
    font-size: 11px;
    font-weight: 600;
    padding: 9px 16px;
}
QPushButton#dangerButton:hover {
    background: $danger_bg;
    border-color: $danger_border;
    color: $danger;
}
QPushButton#dangerButton:disabled {
    background: transparent;
    border-color: $border;
    color: $faint;
}
QPushButton#dangerButton:focus {
    border: 2px solid $accent;
}

QToolButton#clearButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    color: $subtle;
    padding: 0px;
}
QToolButton#clearButton:hover {
    background: $danger_bg;
    border-color: $danger_border;
    color: $danger;
}
QToolButton#clearButton:disabled {
    background: transparent;
    color: $faint;
}
QToolButton#clearButton:focus {
    border: 2px solid $accent;
}
QToolButton#formatButton {
    background: $btn_bg;
    border: 1px solid $btn_border;
    border-radius: 4px;
    color: $btn_text;
    min-width: 28px;
    min-height: 26px;
}
QToolButton#formatButton:hover {
    background: $hover;
    border-color: $accent;
}
QToolButton#formatButton:pressed {
    background: $pressed;
}
QToolButton#formatButton:focus {
    border: 2px solid $accent;
}

/* =================================================================== */
/* Seletor segmentado                                                  */
/* =================================================================== */
QFrame#segmentFrame {
    background: $seg_bg;
    border: 1px solid $seg_border;
    border-radius: 8px;
}
QPushButton#segmentButton {
    background: $seg_item_bg;
    border: 1px solid $seg_item_border;
    border-radius: 5px;
    color: $seg_text;
    font-size: 12px;
    font-weight: 600;
    padding: 9px 14px;
}
QPushButton#segmentButton:hover {
    background: $seg_hover;
}
QPushButton#segmentButton[active="true"] {
    background: $seg_active_bg;
    border: 2px solid $seg_active_border;
    color: $seg_active_text;
    font-weight: 700;
}
QPushButton#segmentButton:disabled {
    color: $faint;
}
QPushButton#segmentButton:focus {
    border: 2px solid $accent;
}

/* =================================================================== */
/* Progresso                                                           */
/* =================================================================== */
QProgressBar {
    background: $surface_sunken;
    border: none;
    border-radius: 8px;
    color: $text;
    font-size: 9px;
    font-weight: 700;
    max-height: 16px;
    min-height: 16px;
    text-align: center;
}
QProgressBar::chunk {
    background: $orange;
    border-radius: 8px;
}
QProgressBar:disabled {
    color: $faint;
}

/* =================================================================== */
/* Console de log                                                      */
/* =================================================================== */
QFrame#consoleFrame {
    background: $console_bg;
    border: 1px solid $console_border;
    border-radius: 6px;
}
QFrame#consoleHeader {
    background: $console_header;
    border: none;
    border-bottom: 1px solid $console_border;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QLabel#consoleTitle {
    color: $console_title;
    font-family: "Cascadia Mono", "Consolas", "Courier New";
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.55px;
}
QLabel#consoleMeta {
    color: $console_meta;
    font-family: "Cascadia Mono", "Consolas", "Courier New";
    font-size: 9px;
}
QPlainTextEdit#logView {
    background: $console_bg;
    border: none;
    color: $console_text;
    font-family: "Cascadia Mono", "Consolas", "Courier New";
    font-size: 12px;
    padding: 8px;
    placeholder-text-color: $console_meta;
    selection-background-color: $accent_deep;
    selection-color: #FFFFFF;
}
QPlainTextEdit#logView:focus {
    border: 1px solid $accent;
}

/* =================================================================== */
/* Abas internas                                                       */
/* =================================================================== */
QTabWidget#enviosTabs {
    border: none;
    background: transparent;
}
QTabBar {
    background: transparent;
    border: none;
}
QTabWidget#enviosTabs::pane,
QTabWidget#mainTabs::pane {
    background: transparent;
    border: none;
    top: 0px;
}
QTabWidget#enviosTabs QTabBar::tab {
    background: $tab_bg;
    border: 1px solid $tab_border;
    border-radius: 5px;
    color: $tab_text;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.4px;
    margin-right: 6px;
    padding: 7px 14px;
}
QTabWidget#enviosTabs QTabBar::tab:hover {
    background: $tab_hover;
}
QTabWidget#enviosTabs QTabBar::tab:selected {
    background: $tab_active_bg;
    border: 1px solid $tab_active_border;
    color: $tab_active_text;
}
QTabWidget#enviosTabs QTabBar::tab:disabled {
    background: $surface_sunken;
    border-color: $border;
    color: $faint;
}
QTabBar:focus {
    border: 2px solid $accent;
    border-radius: 4px;
}

/* =================================================================== */
/* Tabelas                                                             */
/* =================================================================== */
QTableWidget#confirmTable {
    alternate-background-color: $surface_alt;
    gridline-color: $border;
}
QTableWidget#confirmTable::item {
    padding: 4px 6px;
}
QTableWidget#confirmTable::item:selected {
    background: $info_bg;
    color: $text;
}
QHeaderView::section {
    background: $surface_sunken;
    border: none;
    border-right: 1px solid $border;
    border-bottom: 1px solid $border;
    color: $muted;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.6px;
    padding: 7px 6px;
}
QTableCornerButton::section {
    background: $surface_sunken;
    border: none;
}
QCheckBox {
    color: $text;
    font-size: 11px;
    spacing: 7px;
}

/* =================================================================== */
/* Rodapé institucional                                                */
/* =================================================================== */
QFrame#footerBar {
    background: $footer_bg;
    border: none;
    border-top: 1px solid $footer_border;
}
QLabel#footerText {
    color: $footer_text;
    font-size: 11px;
}
QLabel#footerFaint {
    color: $footer_faint;
    font-size: 11px;
}

/* =================================================================== */
/* Banner informativo                                                  */
/* =================================================================== */
QFrame#infoBanner {
    background: $surface;
    border: 1px solid $border;
    border-radius: 8px;
}
QLabel#bannerIcon {
    background: $warn_bg;
    border: 1px solid $warn_border;
    border-radius: 4px;
}
QLabel#connectionChip {
    background: $ok_bg;
    border: 1px solid $ok_border;
    border-radius: 4px;
    color: $ok_text;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.3px;
    padding: 4px 9px;
}
QLabel#connectionChip[variant="info"] {
    background: $info_bg;
    border: 1px solid $info_border;
    color: $info_text;
}

/* =================================================================== */
/* Diálogo                                                             */
/* =================================================================== */
QDialog {
    background: $dialog_bg;
}
QLabel#dialogTitle {
    color: $text;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.4px;
}
QLabel#dialogSubtitle {
    color: $body;
    font-size: 11px;
}
QLabel#dialogSelection {
    color: $muted;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.3px;
}
QLabel#previewSubject {
    color: $text;
    font-size: 12px;
    font-weight: 700;
}
QLabel#previewRecipients {
    color: $muted;
    font-size: 10px;
}
QLabel#previewBody {
    background: $field_bg;
    border: 1px solid $border;
    border-radius: 5px;
    color: $text;
    padding: 6px 8px;
}
QLabel#dialogWarnings {
    background: $warn_bg;
    border: 1px solid $warn_border;
    border-radius: 4px;
    color: $warn_text;
    font-size: 10px;
    padding: 5px 7px;
}
QScrollArea#dialogScroll > QWidget > QWidget {
    background: transparent;
}

/* =================================================================== */
/* Mensagens, tooltips e barras de rolagem                             */
/* =================================================================== */
QMessageBox {
    background: $dialog_bg;
}
QMessageBox QLabel {
    color: $text;
    font-size: 11px;
}
QToolTip {
    background-color: $navy;
    border: 1px solid $border_strong;
    color: #F8FAFC;
    padding: 4px 6px;
}
QScrollBar:vertical {
    background: transparent;
    border: none;
    margin: 0px;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: $border_strong;
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: $subtle;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: transparent;
    border: none;
    height: 10px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: $border_strong;
    border-radius: 4px;
    min-width: 28px;
}
QScrollBar::handle:horizontal:hover {
    background: $subtle;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
}

/* =================================================================== */
/* Acessibilidade: foco visível                                        */
/* =================================================================== */
QLineEdit:focus,
QTextEdit#bodyEditor:focus,
QListWidget#copyList:focus,
QTableWidget#confirmTable:focus {
    border: 2px solid $accent;
}
QTabWidget#enviosTabs QTabBar::tab:focus {
    border: 2px solid $accent;
}
"""
)
