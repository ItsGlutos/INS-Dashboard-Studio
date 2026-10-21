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

# Cores do indicador de status (LED)
LED_COLORS: dict[str, str] = {
    "idle": "#7f93a8",
    "running": "#ffd97a",
    "ok": "#63d8c4",
    "error": "#ff7b7b",
    "cancelled": "#ffb366",
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
        stop:1 rgba(31, 144, 255, 190)
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
    color: #6d8aa3;
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
        stop:0.52 rgba(120, 200, 245, 240),
        stop:1 rgba(30, 144, 255, 235)
    );
}

QPushButton#glossButton:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 255),
        stop:0.48 rgba(240, 252, 255, 250),
        stop:0.52 rgba(150, 215, 250, 245),
        stop:1 rgba(56, 165, 255, 240)
    );
}

QPushButton#glossButton:pressed {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(190, 225, 245, 240),
        stop:0.48 rgba(150, 205, 240, 235),
        stop:0.52 rgba(30, 130, 235, 235),
        stop:1 rgba(10, 77, 140, 235)
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
        stop:0.52 rgba(99, 216, 196, 245),
        stop:1 rgba(20, 150, 135, 240)
    );
}

QPushButton#primaryButton:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 255),
        stop:0.48 rgba(232, 255, 250, 252),
        stop:0.52 rgba(128, 235, 215, 250),
        stop:1 rgba(30, 175, 155, 245)
    );
}

QPushButton#primaryButton:pressed {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(190, 235, 225, 240),
        stop:0.48 rgba(140, 220, 205, 235),
        stop:0.52 rgba(30, 160, 140, 235),
        stop:1 rgba(10, 110, 98, 235)
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
        stop:0.52 rgba(255, 170, 170, 240),
        stop:1 rgba(214, 92, 92, 235)
    );
}

QPushButton#dangerButton:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 255),
        stop:0.48 rgba(255, 236, 236, 250),
        stop:0.52 rgba(255, 190, 190, 245),
        stop:1 rgba(228, 110, 110, 240)
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
        stop:0.52 rgba(140, 210, 250, 240),
        stop:1 rgba(30, 144, 255, 235)
    );
}

QPushButton#miniButton:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 255),
        stop:0.48 rgba(242, 252, 255, 250),
        stop:0.52 rgba(170, 225, 255, 245),
        stop:1 rgba(56, 165, 255, 240)
    );
}

QPushButton#miniButton:pressed {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(190, 225, 245, 240),
        stop:1 rgba(20, 120, 215, 235)
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
        stop:0 rgba(120, 205, 255, 250),
        stop:0.48 rgba(45, 155, 250, 248),
        stop:0.52 rgba(16, 105, 195, 245),
        stop:1 rgba(10, 77, 140, 240)
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
        stop:0 rgba(190, 240, 255, 250),
        stop:0.45 rgba(80, 190, 255, 248),
        stop:0.55 rgba(20, 130, 240, 245),
        stop:1 rgba(10, 90, 190, 240)
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
"""
