"""Componentes reutilizáveis da interface do INS Dashboard Studio.

Todos os elementos visuais são desenhados em código (``QPainter``/QSS),
sem imagens externas:

* :class:`SkyBackground` -- céu em degradê com sol, nuvens e bolhas em movimento;
* :class:`GlassPanel` -- painel de vidro translúcido com sombra;
* :class:`GlossyButton` -- botão glossy com brilho superior;
* :class:`SegmentedSelector` -- seletor segmentado (Motorista/Transportador);
* :class:`FileSelector` -- seletor de arquivo/pasta com ``QFileDialog``;
* :class:`LogView` -- área de log colorida por nível;
* :class:`StatusLed` -- indicador de status tipo LED.
"""

from __future__ import annotations

import random
from pathlib import Path

from PyQt6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .theme import LED_COLORS, LOG_COLORS

__all__ = [
    "AeroCheckBox",
    "FileSelector",
    "GlassPanel",
    "GlossyButton",
    "LogView",
    "SegmentedSelector",
    "StatusLed",
    "SkyBackground",
    "create_app_icon",
]


# ---------------------------------------------------------------------------
# Fundo animado
# ---------------------------------------------------------------------------
class SkyBackground(QWidget):
    """Fundo com céu em degradê, sol, nuvens e bolhas translúcidas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("skyBackground")
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._bubbles: list[dict[str, float]] = []
        self._spawn_initial_bubbles()
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._advance_bubbles)
        self._timer.start()

    # -- criação das bolhas -------------------------------------------------
    def _spawn_initial_bubbles(self) -> None:
        """Distribui as bolhas iniciais pela tela."""
        random.seed(20260101)
        for _ in range(26):
            self._bubbles.append(self._new_bubble(spread=True))

    def _new_bubble(self, spread: bool = True) -> dict[str, float]:
        """Cria os parâmetros de uma bolha translúcida."""
        radius = random.uniform(10, 46) if spread else random.uniform(8, 30)
        return {
            "x": random.uniform(0.0, 1.0),
            "y": random.uniform(0.0, 1.0),
            "r": radius,
            "speed": random.uniform(0.00018, 0.00065),
            "alpha": random.uniform(28, 78),
        }

    def _advance_bubbles(self) -> None:
        """Move as bolhas para cima e redesenha o fundo."""
        height = max(1, self.height())
        width = max(1, self.width())
        for bubble in self._bubbles:
            bubble["y"] -= bubble["speed"]
            if bubble["y"] < -0.12:
                bubble.update(self._new_bubble(False))
                bubble["x"] = random.uniform(0.0, 1.0)
                bubble["y"] = 1.05
                bubble["r"] = random.uniform(8, 40)
        self.update()

    # -- pintura ------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Desenha o céu, o sol, as nuvens e as bolhas."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = max(1, self.width())
        height = max(1, self.height())

        # Céu em degradê vertical.
        sky = QLinearGradient(0, 0, 0, height)
        sky.setColorAt(0.0, QColor("#04305f"))
        sky.setColorAt(0.18, QColor("#0a4d8c"))
        sky.setColorAt(0.42, QColor("#1e90ff"))
        sky.setColorAt(0.66, QColor("#63c8f5"))
        sky.setColorAt(0.86, QColor("#a9e6fb"))
        sky.setColorAt(1.0, QColor("#e6faff"))
        painter.fillRect(self.rect(), sky)

        # Brilho do sol (canto superior direito).
        sun_center = QPointF(width * 0.80, height * 0.06)
        glow = QRadialGradient(sun_center, max(width, height) * 0.55)
        glow.setColorAt(0.0, QColor(255, 253, 226, 210))
        glow.setColorAt(0.12, QColor(255, 246, 190, 120))
        glow.setColorAt(0.35, QColor(255, 255, 255, 45))
        glow.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(sun_center, max(width, height) * 0.55, max(width, height) * 0.55)

        # Discos do sol.
        painter.setBrush(QBrush(QColor(255, 255, 235, 235)))
        painter.drawEllipse(sun_center, 34, 34)
        painter.setBrush(QBrush(QColor(255, 255, 255, 90)))
        painter.drawEllipse(sun_center, 52, 52)

        # Nuvens translúcidas.
        self._draw_cloud(painter, QPointF(width * 0.18, height * 0.13), 1.0)
        self._draw_cloud(painter, QPointF(width * 0.62, height * 0.27), 0.7)
        self._draw_cloud(painter, QPointF(width * 0.88, height * 0.55), 0.5)

        # Reflexos em faixas (água) na parte inferior.
        self._draw_water_reflections(painter, width, height)

        # Bolhas translúcidas subindo.
        for bubble in self._bubbles:
            self._draw_bubble(painter, bubble, width, height)

        painter.end()

    @staticmethod
    def _draw_cloud(painter: QPainter, center: QPointF, scale: float) -> None:
        """Desenha uma nuvem macia composta por elipses."""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 46)))
        for offset, radius in (
            (-46, 30),
            (-14, 42),
            (24, 34),
            (52, 22),
        ):
            painter.drawEllipse(
                QPointF(center.x() + offset * scale, center.y() - radius * 0.18),
                radius * scale,
                radius * 0.62 * scale,
            )

    @staticmethod
    def _draw_water_reflections(painter: QPainter, width: int, height: int) -> None:
        """Desenha faixas de reflexo onduladas na base do céu."""
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(7):
            y = height * 0.74 + index * (height * 0.035)
            alpha = max(6, 42 - index * 5)
            painter.setBrush(QBrush(QColor(255, 255, 255, alpha)))
            painter.drawRect(
                QRectF(
                    width * 0.02,
                    y,
                    width * 0.96,
                    max(2.0, height * 0.008),
                )
            )

    @staticmethod
    def _draw_bubble(
        painter: QPainter,
        bubble: dict[str, float],
        width: int,
        height: int,
    ) -> None:
        """Desenha uma bolha translúcida com reflexo."""
        center = QPointF(
            bubble["x"] * width,
            bubble["y"] * height,
        )
        radius = bubble["r"]
        alpha = int(bubble["alpha"])

        halo = QRadialGradient(center, radius * 1.5)
        halo.setColorAt(0.0, QColor(255, 255, 255, int(alpha * 0.35)))
        halo.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(halo))
        painter.drawEllipse(center, radius * 1.5, radius * 1.5)

        body = QRadialGradient(
            QPointF(center.x() - radius * 0.3, center.y() - radius * 0.35),
            radius * 1.25,
        )
        body.setColorAt(0.0, QColor(255, 255, 255, int(alpha * 1.25)))
        body.setColorAt(0.55, QColor(190, 240, 255, int(alpha * 0.55)))
        body.setColorAt(1.0, QColor(120, 205, 255, int(alpha * 0.18)))
        painter.setBrush(QBrush(body))
        painter.setPen(QPen(QColor(255, 255, 255, min(210, alpha + 90)), 1.4))
        painter.drawEllipse(center, radius, radius)

        # Reflexo pontual no topo da bolha.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, min(235, alpha + 130))))
        painter.drawEllipse(
            QPointF(center.x() - radius * 0.34, center.y() - radius * 0.42),
            radius * 0.17,
            radius * 0.11,
        )


# ---------------------------------------------------------------------------
# Painel de vidro
# ---------------------------------------------------------------------------
class GlassPanel(QFrame):
    """Painel translúcido com borda clara, cantos arredondados e sombra."""

    def __init__(self, parent: QWidget | None = None, shadow: bool = True) -> None:
        super().__init__(parent)
        self.setObjectName("glassPanel")
        if shadow:
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(26)
            effect.setOffset(0, 6)
            effect.setColor(QColor(2, 24, 48, 90))
            self.setGraphicsEffect(effect)


# ---------------------------------------------------------------------------
# Botão glossy
# ---------------------------------------------------------------------------
class GlossyButton(QPushButton):
    """Botão com brilho glossy desenhado pelo QSS e foco visível."""

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        variant: str = "glossButton",
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName(variant)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Desenha o QSS e um contorno sutil de foco."""
        super().paintEvent(event)
        if not self.hasFocus():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 220), 2))
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 8, 8)
        painter.end()


# ---------------------------------------------------------------------------
# Checkbox Aero
# ---------------------------------------------------------------------------
class AeroCheckBox(QCheckBox):
    """Checkbox com indicador de vidro e checkmark desenhados em código.

    O indicador padrão do Fusion herda cores do tema e fica ilegível sobre o
    painel de vidro; este desenho mantém o mesmo vocabulário visual dos
    botões glossy.
    """

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(22)

    def sizeHint(self):  # noqa: N802 (API Qt)
        """Reserva espaço extra para o indicador desenhado manualmente."""
        hint = super().sizeHint()
        hint.setWidth(hint.width() + 8)
        return hint

    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Desenha o indicador e o texto sem depender do estilo do sistema."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        box = 16.0
        x = 2.0
        y = (self.height() - box) / 2.0
        rect = QRectF(x, y, box, box)

        if self.isEnabled():
            borda = QColor("#0a4d8c")
            fundo = QColor(255, 255, 255, 235)
        else:
            borda = QColor("#9db2c6")
            fundo = QColor(232, 240, 247, 210)

        painter.setPen(QPen(borda, 1.2))
        painter.setBrush(QBrush(fundo))
        painter.drawRoundedRect(rect, 4, 4)

        if self.isChecked():
            gradiente = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            gradiente.setColorAt(0.0, QColor("#7fd4ff"))
            gradiente.setColorAt(1.0, QColor("#1e90ff"))
            painter.setPen(QPen(QColor("#0a4d8c"), 1.0))
            painter.setBrush(QBrush(gradiente))
            painter.drawRoundedRect(rect, 4, 4)

            check = QPainterPath()
            check.moveTo(x + 4.0, y + 8.0)
            check.lineTo(x + 7.0, y + 11.0)
            check.lineTo(x + 12.0, y + 5.0)
            painter.setPen(
                QPen(
                    QColor(255, 255, 255, 245),
                    2.0,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(check)

        painter.setPen(
            QColor("#06345c") if self.isEnabled() else QColor("#8fa3b6")
        )
        painter.setFont(self.font())
        painter.drawText(
            self.rect().adjusted(int(box + 8), 0, -2, 0),
            int(
                Qt.AlignmentFlag.AlignVCenter
                | Qt.AlignmentFlag.AlignLeft
            ),
            self.text(),
        )

        if self.hasFocus():
            painter.setPen(
                QPen(QColor(30, 144, 255, 170), 1, Qt.PenStyle.DotLine)
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 5, 5)
        painter.end()


# ---------------------------------------------------------------------------
# Seletor segmentado
# ---------------------------------------------------------------------------
class SegmentedSelector(QWidget):
    """Controle segmentado com dois estados mutuamente exclusivos."""

    changed = pyqtSignal(str)

    def __init__(
        self,
        options: list[tuple[str, str]],
        initial: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._buttons: dict[str, QPushButton] = {}
        self._current = ""

        frame = QFrame(self)
        frame.setObjectName("segmentFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        for key, label in options:
            button = QPushButton(label, frame)
            button.setObjectName("segmentButton")
            button.setCheckable(False)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, k=key: self.set_current(k))
            layout.addWidget(button)
            self._buttons[key] = button

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

        if initial:
            self.set_current(initial, emit=False)
        elif options:
            self.set_current(options[0][0], emit=False)

    @property
    def current(self) -> str:
        """Chave da opção atualmente ativa."""
        return self._current

    def set_current(self, key: str, emit: bool = True) -> None:
        """Ativa uma opção e (opcionalmente) emite o sinal de mudança."""
        if key not in self._buttons:
            return
        changed = key != self._current
        self._current = key
        for button_key, button in self._buttons.items():
            active = button_key == key
            button.setProperty("active", "true" if active else "false")
            button.style().unpolish(button)
            button.style().polish(button)
        if emit and changed:
            self.changed.emit(key)

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 (API Qt)
        """Habilita/desabilita todas as opções."""
        super().setEnabled(enabled)
        for button in self._buttons.values():
            button.setEnabled(enabled)


# ---------------------------------------------------------------------------
# Seletor de arquivo / pasta
# ---------------------------------------------------------------------------
class FileSelector(QWidget):
    """Campo que exibe um caminho e permite escolher/limpar via QFileDialog."""

    selectionChanged = pyqtSignal(str)

    def __init__(
        self,
        caption: str,
        button_text: str = "Procurar…",
        mode: str = "file",
        dialog_title: str = "Selecionar arquivo",
        file_filter: str = "Planilhas do Excel (*.xlsx *.xlsm)",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._dialog_title = dialog_title
        self._file_filter = file_filter
        self._path = ""

        caption_label = QLabel(caption, self)
        caption_label.setObjectName("fieldCaption")

        self._field = QFrame(self)
        self._field.setObjectName("glassPanel")
        self._field.setMinimumHeight(38)
        field_layout = QHBoxLayout(self._field)
        field_layout.setContentsMargins(9, 4, 5, 4)
        field_layout.setSpacing(6)

        self._path_label = QLabel("Nenhum arquivo selecionado", self._field)
        self._path_label.setObjectName("fieldPath")
        self._path_label.setProperty("empty", "true")
        self._path_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._path_label.setMinimumWidth(40)

        self._browse_button = QPushButton(button_text, self._field)
        self._browse_button.setObjectName("miniButton")
        self._browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_button.clicked.connect(self._open_dialog)

        self._clear_button = QToolButton(self._field)
        self._clear_button.setObjectName("clearButton")
        self._clear_button.setText("✕")
        self._clear_button.setToolTip("Limpar seleção")
        self._clear_button.setFixedSize(20, 20)
        self._clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_button.clicked.connect(self.clear)
        self._clear_button.setEnabled(False)

        field_layout.addWidget(self._path_label, 1)
        field_layout.addWidget(self._browse_button)
        field_layout.addWidget(self._clear_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(caption_label)
        layout.addWidget(self._field)

    # -- API ----------------------------------------------------------------
    @property
    def path(self) -> str:
        """Caminho selecionado (string vazia quando nada foi escolhido)."""
        return self._path

    def set_path(self, value: str | Path | None) -> None:
        """Define o caminho exibido (sem emitir o sinal de mudança)."""
        self._path = str(value) if value else ""
        self._refresh_display()
        self.selectionChanged.emit(self._path)

    def clear(self) -> None:
        """Limpa a seleção atual."""
        if not self._path:
            self._refresh_display()
            return
        self._path = ""
        self._refresh_display()
        self.selectionChanged.emit("")

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 (API Qt)
        """Habilita/desabilita o seletor inteiro."""
        super().setEnabled(enabled)
        self._browse_button.setEnabled(enabled)
        self._clear_button.setEnabled(enabled and bool(self._path))

    # -- interno ------------------------------------------------------------
    def _open_dialog(self) -> None:
        """Abre o QFileDialog correspondente ao modo do seletor."""
        if self._mode == "directory":
            initial = self._path or ""
            selected = QFileDialog.getExistingDirectory(
                self,
                self._dialog_title,
                initial,
                QFileDialog.Option.ShowDirsOnly,
            )
        else:
            initial = self._path or ""
            selected, _ = QFileDialog.getOpenFileName(
                self,
                self._dialog_title,
                initial,
                self._file_filter,
            )
        if selected:
            self._path = str(selected)
            self._refresh_display()
            self.selectionChanged.emit(self._path)

    def _refresh_display(self) -> None:
        """Atualiza o texto exibido, a dica e o botão de limpar."""
        if self._path:
            self._path_label.setProperty("empty", "false")
            self._path_label.setToolTip(self._path)
            self._field.setToolTip(self._path)
            self._clear_button.setEnabled(self.isEnabled())
        else:
            placeholder = (
                "Nenhuma pasta selecionada"
                if self._mode == "directory"
                else "Nenhum arquivo selecionado"
            )
            self._path_label.setProperty("empty", "true")
            self._path_label.setToolTip("")
            self._field.setToolTip("")
            self._clear_button.setEnabled(False)
        self._path_label.style().unpolish(self._path_label)
        self._path_label.style().polish(self._path_label)
        self._elide()

    def _elide(self) -> None:
        """Elide o caminho no meio, conforme a largura disponível."""
        if not self._path:
            self._path_label.setText(
                "Nenhuma pasta selecionada"
                if self._mode == "directory"
                else "Nenhum arquivo selecionado"
            )
            return
        width = max(40, self._path_label.width())
        metrics = self._path_label.fontMetrics()
        self._path_label.setText(
            metrics.elidedText(self._path, Qt.TextElideMode.ElideMiddle, width)
        )

    def resizeEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Recalcula o elide quando o widget é redimensionado."""
        super().resizeEvent(event)
        self._elide()


# ---------------------------------------------------------------------------
# Área de log
# ---------------------------------------------------------------------------
class LogView(QWidget):
    """Área de log com cores por nível (info/success/warning/error)."""

    LEVEL_ICONS = {
        "info": "•",
        "success": "✔",
        "warning": "!",
        "error": "✖",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._view = QPlainTextEdit(self)
        self._view.setObjectName("logView")
        self._view.setReadOnly(True)
        self._view.setMaximumBlockCount(800)
        self._view.setFont(QFont("Consolas", 9))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

    def append_log(self, message: str, level: str = "info") -> None:
        """Adiciona uma linha colorida ao log."""
        color = LOG_COLORS.get(level, LOG_COLORS["info"])
        icon = self.LEVEL_ICONS.get(level, "•")
        safe = (
            str(message)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        self._view.appendHtml(
            f'<span style="color:{color};">'
            f'<b>{icon}</b>&nbsp;&nbsp;{safe}</span>'
        )
        self._view.verticalScrollBar().setValue(
            self._view.verticalScrollBar().maximum()
        )

    def clear_log(self) -> None:
        """Remove todas as linhas do log."""
        self._view.clear()

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 (API Qt)
        """Habilita/desabilita a leitura do log."""
        super().setEnabled(enabled)
        self._view.setReadOnly(not enabled)


# ---------------------------------------------------------------------------
# LED de status
# ---------------------------------------------------------------------------
class StatusLed(QWidget):
    """Indicador luminoso de status (parado / executando / ok / erro)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self._state = "idle"
        self._pulse = 0.0
        self._animation = QPropertyAnimation(self, b"pulse", self)
        self._animation.setDuration(900)
        self._animation.setLoopCount(-1)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._animation.valueChanged.connect(self._on_pulse)
        self._animation.start()

    def set_state(self, state: str) -> None:
        """Define o estado visual: idle, running, ok, error ou cancelled."""
        self._state = state if state in LED_COLORS else "idle"
        self.update()

    @property
    def state(self) -> str:
        """Estado atual do LED."""
        return self._state

    @pyqtProperty(float)
    def pulse(self) -> float:
        """Valor da animação de pulso (0..1)."""
        return self._pulse

    @pulse.setter
    def pulse(self, value: float) -> None:
        """Define o valor do pulso e força a repintura."""
        self._pulse = value
        self.update()

    def _on_pulse(self, value: float) -> None:
        """Recebe as atualizações da animação."""
        self._pulse = value
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Desenha o LED com halo e reflexo."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = QColor(LED_COLORS.get(self._state, LED_COLORS["idle"]))

        center = QPointF(9, 9)
        glow_strength = 0.35 + 0.65 * self._pulse if self._state == "running" else 0.45
        halo = QRadialGradient(center, 9)
        halo.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 190))
        halo.setColorAt(0.45, QColor(color.red(), color.green(), color.blue(), 70))
        halo.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(halo))
        painter.drawEllipse(center, 9, 9)

        painter.setBrush(QBrush(color))
        painter.setPen(QPen(QColor(255, 255, 255, 210), 1))
        painter.drawEllipse(center, 5.4, 5.4)

        painter.setBrush(QBrush(QColor(255, 255, 255, 190)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(7.4, 7.4), 1.7, 1.2)
        painter.end()


# ---------------------------------------------------------------------------
# Ícone do aplicativo
# ---------------------------------------------------------------------------
def create_app_icon(size: int = 64) -> QIcon:
    """Desenha o ícone do aplicativo (bolha/onda) com QPainter."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    # Base quadrada arredondada com degradê azul.
    path = QPainterPath()
    margin = size * 0.04
    path.addRoundedRect(
        QRectF(margin, margin, size - 2 * margin, size - 2 * margin),
        size * 0.22,
        size * 0.22,
    )
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor("#0a4d8c"))
    gradient.setColorAt(0.5, QColor("#1e90ff"))
    gradient.setColorAt(1.0, QColor("#63d8c4"))
    painter.fillPath(path, QBrush(gradient))

    painter.setPen(QPen(QColor(255, 255, 255, 170), max(1.0, size * 0.02)))
    painter.drawPath(path)

    # Bolha principal.
    bubble_center = QPointF(size * 0.42, size * 0.44)
    bubble_radius = size * 0.24
    body = QRadialGradient(
        QPointF(bubble_center.x() - bubble_radius * 0.3, bubble_center.y() - bubble_radius * 0.35),
        bubble_radius * 1.3,
    )
    body.setColorAt(0.0, QColor(255, 255, 255, 245))
    body.setColorAt(0.6, QColor(210, 245, 255, 165))
    body.setColorAt(1.0, QColor(140, 220, 255, 70))
    painter.setPen(QPen(QColor(255, 255, 255, 220), max(1.0, size * 0.018)))
    painter.setBrush(QBrush(body))
    painter.drawEllipse(bubble_center, bubble_radius, bubble_radius)

    # Onda na base.
    wave = QPainterPath()
    wave.moveTo(size * 0.16, size * 0.76)
    wave.cubicTo(
        size * 0.32, size * 0.62,
        size * 0.44, size * 0.90,
        size * 0.60, size * 0.76,
    )
    wave.cubicTo(
        size * 0.72, size * 0.66,
        size * 0.80, size * 0.82,
        size * 0.88, size * 0.74,
    )
    painter.setPen(QPen(QColor(255, 255, 255, 210), max(1.5, size * 0.035)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(wave)

    painter.end()
    return QIcon(pixmap)
