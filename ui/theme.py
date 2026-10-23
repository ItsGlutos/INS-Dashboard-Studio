"""Paleta de cores e folha de estilo (QSS) do INS Dashboard Studio.

O visual segue o estilo "Frutiger Aero" (Windows Vista/7): céu em degradê,
painéis de vidro translúcido, botões glossy com brilho superior e paleta
azul/ciano/verde-água.  Nada aqui depende de imagens externas: apenas cores
e QSS.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Identidade do aplicativo
# --------------------------------------------------------------------------
APP_NAME = "INS Dashboard Studio"
APP_ORG = "INS"
APP_FONT = "Segoe UI"

# --------------------------------------------------------------------------
# Paleta
# --------------------------------------------------------------------------
DEEP_BLUE = "#062a52"
BLUE = "#0a4d8c"
BLUE_BRIGHT = "#1e90ff"
CYAN = "#7fd4ff"
AQUA = "#63d8c4"
MINT = "#d8fbf3"
WHITE = "#f5fbff"
TEXT_DARK = "#0b2b46"
TEXT_MUTED = "#3f5f7d"
TEXT_LIGHT = "#eaf6ff"

# Cores do log (texto claro sobre painel escuro)
LOG_COLORS: dict[str, str] = {
    "info": "#bfe8ff",
    "success": "#8ff0c0",
    "warning": "#ffd97a",
    "error": "#ff9d9d",
}

# Cores do indicador de status (LED), escuras o bastante para 3:1 no vidro.
LED_COLORS: dict[str, str] = {
    "idle": "#5c748c",
    "running": "#9a6700",
    "ok": "#0f766e",
    "error": "#b42318",
    "cancelled": "#b45309",
}


def build_stylesheet() -> str:
    """Devolve a folha de estilo QSS completa da aplicação.

    Returns:
        str: conteúdo QSS pronto para ``QApplication.setStyleSheet``.
    """
    return _QSS


_QSS = """
/* ------------------------------------------------------------------ */
/* Base                                                                */
/* ------------------------------------------------------------------ */
* {
    font-family: "Segoe UI";
}

QWidget {
    color: #0b2b46;
}

QMainWindow,
QWidget#skyBackground {
    background: transparent;
}

/* ------------------------------------------------------------------ */
/* Cabeçalho (vidro escuro sobre o céu)                                */
/* ------------------------------------------------------------------ */
QFrame#headerPanel {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(4, 32, 64, 235),
        stop:0.55 rgba(10, 77, 140, 220),
        stop:1 rgba(13, 86, 143, 220)
    );
    border: 1px solid rgba(190, 235, 255, 200);
    border-radius: 16px;
}

QLabel#appTitle {
    color: #f5fbff;
    font-size: 17px;
    font-weight: 700;
}

QLabel#appSubtitle {
    color: #bfe8ff;
    font-size: 11px;
}

/* ------------------------------------------------------------------ */
/* Painéis de vidro claro                                              */
/* ------------------------------------------------------------------ */
QFrame#glassPanel {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 225),
        stop:0.55 rgba(240, 250, 255, 205),
        stop:1 rgba(205, 236, 252, 190)
    );
    border: 1px solid rgba(255, 255, 255, 235);
    border-radius: 16px;
}

QLabel#sectionTitle {
    color: #062a52;
    font-size: 13px;
    font-weight: 700;
}

QLabel#sectionHint {
    color: #3f5f7d;
    font-size: 11px;
}

QLabel#fieldCaption {
    color: #0a4d8c;
    font-size: 11px;
    font-weight: 600;
}

QLabel#fieldPath {
    color: #0b2b46;
    font-size: 11px;
}

QLabel#fieldPath[empty="true"] {
    color: #4a6a86;
    font-style: italic;
}

QLabel#descriptionText {
    color: #123f61;
    font-size: 11px;
}

QLabel#chip {
    background: rgba(255, 255, 255, 205);
    border: 1px solid rgba(255, 255, 255, 245);
    border-radius: 9px;
    color: #06345c;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 9px;
}

QLabel#statusText {
    color: #062a52;
    font-size: 12px;
    font-weight: 600;
}

QLabel#groupText {
    color: #0a4d8c;
    font-size: 11px;
    font-weight: 600;
}

QLabel#summaryText {
    color: #06345c;
    font-size: 12px;
    font-weight: 600;
}

/* ------------------------------------------------------------------ */
/* Botões glossy                                                      */
/* ------------------------------------------------------------------ */
QPushButton#glossButton {
    color: #06345c;
    font-size: 12px;
    font-weight: 600;
    padding: 9px 18px;
    border: 1px solid rgba(255, 255, 255, 240);
    border-radius: 9px;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 250),
        stop:0.48 rgba(226, 245, 255, 245),
        stop:0.52 rgba(150, 215, 250, 240),
        stop:1 rgba(107, 200, 255, 235)
    );
}

QPushButton#glossButton:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 255),
        stop:0.48 rgba(240, 252, 255, 250),
        stop:0.52 rgba(170, 225, 255, 245),
        stop:1 rgba(127, 212, 255, 240)
    );
}

QPushButton#glossButton:pressed {
    color: #f5fbff;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(6, 52, 92, 245),
        stop:1 rgba(10, 77, 140, 245)
    );
}

QPushButton#glossButton:disabled {
    color: #7f93a8;
    border: 1px solid rgba(255, 255, 255, 160);
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(236, 244, 250, 220),
        stop:0.5 rgba(205, 220, 235, 210),
        stop:1 rgba(175, 195, 215, 205)
    );
}

QPushButton#primaryButton {
    color: #043a33;
    font-size: 13px;
    font-weight: 700;
    padding: 11px 24px;
    border: 1px solid rgba(255, 255, 255, 245);
    border-radius: 10px;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 250),
        stop:0.48 rgba(216, 251, 243, 248),
        stop:0.52 rgba(120, 229, 211, 245),
        stop:1 rgba(76, 199, 181, 240)
    );
}

QPushButton#primaryButton:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 255),
        stop:0.48 rgba(232, 255, 250, 252),
        stop:0.52 rgba(150, 240, 224, 250),
        stop:1 rgba(102, 216, 198, 245)
    );
}

QPushButton#primaryButton:pressed {
    color: #f5fbff;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(10, 110, 98, 245),
        stop:1 rgba(6, 78, 70, 245)
    );
}

QPushButton#primaryButton:disabled {
    color: #7f93a8;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(236, 244, 250, 220),
        stop:1 rgba(175, 195, 215, 205)
    );
}

QPushButton#dangerButton {
    color: #5c1414;
    font-size: 12px;
    font-weight: 600;
    padding: 11px 20px;
    border: 1px solid rgba(255, 255, 255, 235);
    border-radius: 10px;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 245),
        stop:0.48 rgba(255, 226, 226, 245),
        stop:0.52 rgba(255, 190, 190, 240),
        stop:1 rgba(255, 154, 154, 235)
    );
}

QPushButton#dangerButton:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 255),
        stop:0.48 rgba(255, 236, 236, 250),
        stop:0.52 rgba(255, 205, 205, 245),
        stop:1 rgba(255, 179, 179, 240)
    );
}

QPushButton#dangerButton:pressed {
    color: #f5fbff;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(143, 29, 29, 245),
        stop:1 rgba(92, 20, 20, 245)
    );
}

QPushButton#dangerButton:disabled {
    color: #9aa9b8;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(236, 244, 250, 220),
        stop:1 rgba(175, 195, 215, 205)
    );
}

QPushButton#miniButton {
    color: #06345c;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 12px;
    border: 1px solid rgba(255, 255, 255, 235);
    border-radius: 7px;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 250),
        stop:0.48 rgba(232, 247, 255, 245),
        stop:0.52 rgba(160, 220, 255, 240),
        stop:1 rgba(107, 200, 255, 235)
    );
}

QPushButton#miniButton:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 255),
        stop:0.48 rgba(242, 252, 255, 250),
        stop:0.52 rgba(180, 230, 255, 245),
        stop:1 rgba(127, 212, 255, 240)
    );
}

QPushButton#miniButton:pressed {
    color: #f5fbff;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(6, 52, 92, 245),
        stop:1 rgba(10, 77, 140, 245)
    );
}

QPushButton#miniButton:disabled {
    color: #8fa3b6;
    background: rgba(215, 228, 240, 200);
}

/* Botão de limpar caminho */
QToolButton#clearButton {
    color: #4a6a86;
    background: rgba(255, 255, 255, 120);
    border: 1px solid rgba(255, 255, 255, 220);
    border-radius: 11px;
    font-size: 11px;
    font-weight: 700;
    padding: 0px;
}

QToolButton#clearButton:hover {
    color: #7a1010;
    background: rgba(255, 190, 190, 220);
}

QToolButton#clearButton:disabled {
    color: #a9bccd;
    background: rgba(230, 240, 248, 140);
}

/* ------------------------------------------------------------------ */
/* Seletor segmentado                                                 */
/* ------------------------------------------------------------------ */
QFrame#segmentFrame {
    background: rgba(255, 255, 255, 150);
    border: 1px solid rgba(255, 255, 255, 235);
    border-radius: 11px;
}

QPushButton#segmentButton {
    color: #0a4d8c;
    font-size: 12px;
    font-weight: 600;
    padding: 8px 14px;
    border: 1px solid transparent;
    border-radius: 9px;
    background: transparent;
}

QPushButton#segmentButton:hover {
    background: rgba(255, 255, 255, 170);
}

QPushButton#segmentButton[active="true"] {
    color: #f5fbff;
    border: 1px solid rgba(255, 255, 255, 245);
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(26, 111, 176, 250),
        stop:0.48 rgba(20, 102, 170, 248),
        stop:0.52 rgba(13, 86, 143, 245),
        stop:1 rgba(6, 52, 92, 242)
    );
}

QPushButton#segmentButton:disabled {
    color: #8fa3b6;
}

/* ------------------------------------------------------------------ */
/* Log e barra de progresso                                            */
/* ------------------------------------------------------------------ */
QPlainTextEdit#logView {
    background: rgba(6, 30, 60, 210);
    color: #d9f0ff;
    border: 1px solid rgba(255, 255, 255, 90);
    border-radius: 10px;
    selection-background-color: rgba(99, 216, 196, 180);
    selection-color: #062a52;
}

QProgressBar {
    min-height: 18px;
    max-height: 18px;
    border: 1px solid rgba(255, 255, 255, 230);
    border-radius: 9px;
    background: rgba(255, 255, 255, 165);
    color: #06345c;
    font-size: 11px;
    font-weight: 600;
    text-align: center;
}

QProgressBar::chunk {
    border-radius: 8px;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(214, 246, 255, 250),
        stop:0.45 rgba(168, 228, 255, 248),
        stop:0.55 rgba(127, 212, 255, 245),
        stop:1 rgba(80, 190, 255, 240)
    );
}

QScrollBar:vertical {
    background: rgba(255, 255, 255, 40);
    width: 11px;
    margin: 0px;
    border: none;
}

QScrollBar::handle:vertical {
    background: rgba(127, 212, 255, 190);
    min-height: 28px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(190, 235, 255, 235);
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}

/* ------------------------------------------------------------------ */
/* Caixas de diálogo                                                   */
/* ------------------------------------------------------------------ */
QMessageBox {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 250),
        stop:1 rgba(215, 238, 252, 245)
    );
}

QMessageBox QLabel {
    color: #0b2b46;
    font-size: 12px;
}

QToolTip {
    background-color: rgba(6, 42, 82, 240);
    color: #eaf6ff;
    border: 1px solid rgba(127, 212, 255, 190);
    padding: 4px 6px;
}

/* ------------------------------------------------------------------ */
/* Abas principais e internas                                          */
/* ------------------------------------------------------------------ */
QTabWidget#mainTabs::pane,
QTabWidget#enviosTabs::pane {
    background: transparent;
    border: none;
    top: -1px;
}

QTabBar {
    background: transparent;
}

QTabWidget#mainTabs QTabBar::tab,
QTabWidget#enviosTabs QTabBar::tab {
    color: #06345c;
    font-size: 12px;
    font-weight: 600;
    padding: 8px 18px;
    margin-right: 4px;
    border: 1px solid rgba(255, 255, 255, 235);
    border-bottom: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 235),
        stop:0.55 rgba(236, 249, 255, 220),
        stop:1 rgba(196, 232, 250, 205)
    );
}

QTabWidget#enviosTabs QTabBar::tab {
    font-size: 11px;
    padding: 6px 14px;
}

QTabWidget#mainTabs QTabBar::tab:hover,
QTabWidget#enviosTabs QTabBar::tab:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 255),
        stop:1 rgba(214, 242, 255, 235)
    );
}

QTabWidget#mainTabs QTabBar::tab:selected,
QTabWidget#enviosTabs QTabBar::tab:selected {
    color: #f5fbff;
    border: 1px solid rgba(255, 255, 255, 245);
    border-bottom: none;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(26, 111, 176, 250),
        stop:0.48 rgba(20, 102, 170, 248),
        stop:0.52 rgba(13, 86, 143, 245),
        stop:1 rgba(6, 52, 92, 242)
    );
}

QTabBar::tab:disabled {
    color: #8fa3b6;
}

/* ------------------------------------------------------------------ */
/* Campos de entrada, editores e listas                                */
/* ------------------------------------------------------------------ */
QLineEdit,
QTextEdit#bodyEditor,
QListWidget#copyList,
QTableWidget#confirmTable {
    background: rgba(255, 255, 255, 232);
    color: #0b2b46;
    border: 1px solid rgba(255, 255, 255, 240);
    border-radius: 9px;
    padding: 6px 8px;
    selection-background-color: rgba(214, 239, 255, 230);
    selection-color: #062a52;
}

QLineEdit:focus,
QTextEdit#bodyEditor:focus {
    border: 1px solid rgba(30, 144, 255, 235);
}

QLineEdit:disabled,
QTextEdit#bodyEditor:disabled,
QListWidget#copyList:disabled {
    background: rgba(225, 235, 245, 185);
    color: #7f93a8;
}

QLineEdit#bodySubject {
    font-size: 12px;
    font-weight: 600;
}

QListWidget#copyList::item {
    padding: 5px 8px;
    border-radius: 6px;
}

QListWidget#copyList {
    alternate-background-color: rgba(232, 246, 255, 205);
}

QListWidget#copyList::item:selected {
    background: rgba(30, 144, 255, 155);
    color: #062a52;
}

QTableWidget#confirmTable {
    alternate-background-color: rgba(232, 246, 255, 205);
    gridline-color: rgba(10, 77, 140, 35);
}

QTableWidget#confirmTable::item {
    padding: 4px 6px;
}

QTableWidget#confirmTable::item:selected {
    background: rgba(214, 239, 255, 240);
    color: #062a52;
    border-top: 2px solid #0a4d8c;
    border-bottom: 2px solid #0a4d8c;
}

QHeaderView::section {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(245, 252, 255, 245),
        stop:1 rgba(190, 228, 248, 235)
    );
    color: #06345c;
    font-size: 11px;
    font-weight: 700;
    padding: 6px;
    border: none;
    border-right: 1px solid rgba(10, 77, 140, 45);
    border-bottom: 1px solid rgba(10, 77, 140, 55);
}

QTableCornerButton::section {
    background: rgba(210, 236, 250, 235);
    border: none;
}

QCheckBox {
    color: #06345c;
    font-size: 12px;
    font-weight: 600;
    spacing: 7px;
}

QToolButton#formatButton {
    color: #06345c;
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 245),
        stop:1 rgba(206, 238, 252, 235)
    );
    border: 1px solid rgba(255, 255, 255, 240);
    border-radius: 6px;
    min-width: 26px;
    min-height: 24px;
}

QToolButton#formatButton:hover {
    background: rgba(235, 250, 255, 245);
}

QToolButton#formatButton:pressed {
    background: rgba(30, 144, 255, 190);
}

/* ------------------------------------------------------------------ */
/* Diálogo de confirmação e contadores                                 */
/* ------------------------------------------------------------------ */
QDialog {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(250, 254, 255, 252),
        stop:1 rgba(214, 238, 252, 250)
    );
}

QLabel#dialogTitle {
    color: #062a52;
    font-size: 17px;
    font-weight: 700;
}

QLabel#dialogSubtitle {
    color: #2d5677;
    font-size: 11px;
}

QLabel#dialogSelection {
    color: #0a4d8c;
    font-size: 11px;
    font-weight: 600;
}

QLabel#previewSubject {
    color: #06345c;
    font-size: 12px;
    font-weight: 700;
    padding: 1px 2px;
}

QLabel#previewRecipients {
    color: #2d5677;
    font-size: 10px;
    padding: 0px 2px 2px 2px;
}

QLabel#previewBody {
    background: rgba(255, 255, 255, 238);
    color: #0b2b46;
    border: 1px solid rgba(255, 255, 255, 240);
    border-radius: 8px;
    padding: 5px 7px;
}

QLabel#countChip {
    background: rgba(255, 255, 255, 215);
    border: 1px solid rgba(255, 255, 255, 245);
    border-radius: 9px;
    color: #06345c;
    font-size: 11px;
    font-weight: 700;
    padding: 5px 12px;
    min-width: 100px;
}

QLabel#dialogWarnings {
    background: rgba(255, 248, 219, 235);
    color: #6b4b00;
    border: 1px solid rgba(220, 190, 90, 180);
    border-radius: 8px;
    padding: 5px 7px;
    font-size: 10px;
}

QScrollBar:horizontal {
    background: rgba(255, 255, 255, 40);
    height: 11px;
    margin: 0px;
    border: none;
}

QScrollBar::handle:horizontal {
    background: rgba(127, 212, 255, 190);
    min-width: 28px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(190, 235, 255, 235);
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
}

/* ------------------------------------------------------------------ */
/* Acessibilidade: foco, alvos e rolagem do diálogo                    */
/* ------------------------------------------------------------------ */
QLineEdit {
    placeholder-text-color: #4a6a86;
}

QLineEdit:focus,
QTextEdit#bodyEditor:focus,
QListWidget#copyList:focus,
QTableWidget#confirmTable:focus,
QScrollArea#dialogScroll:focus {
    border: 2px solid #0a4d8c;
}

QPushButton#miniButton:focus,
QPushButton#segmentButton:focus,
QToolButton#clearButton:focus,
QToolButton#formatButton:focus {
    border: 2px solid #06345c;
}

QTabBar:focus {
    border: 2px solid #0a4d8c;
    border-radius: 8px;
}

QScrollArea#dialogScroll {
    background: transparent;
    border: none;
    border-radius: 8px;
}

QScrollArea#dialogScroll > QWidget > QWidget {
    background: transparent;
}

QScrollArea#contentScroll {
    background: transparent;
    border: none;
}

QWidget#contentScrollViewport {
    background: transparent;
}

QScrollArea#contentScroll:focus {
    border: 2px solid #0a4d8c;
    border-radius: 10px;
}

QScrollBar:vertical {
    width: 24px;
}

QScrollBar::handle:vertical {
    min-height: 32px;
    background: rgba(48, 133, 195, 220);
}

QScrollBar::handle:vertical:hover {
    background: rgba(30, 111, 176, 245);
}

QScrollBar:horizontal {
    height: 24px;
}

QScrollBar::handle:horizontal {
    min-width: 32px;
    background: rgba(48, 133, 195, 220);
}

QScrollBar::handle:horizontal:hover {
    background: rgba(30, 111, 176, 245);
}
"""
