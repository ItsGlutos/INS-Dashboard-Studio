"""Componentes reutilizáveis da interface do INS Dashboard Studio.

O vocabulário visual é o do manual institucional GrupoSC: cartões de aresta
8 px, tipografia Chivo, azul operacional e laranja de destaque.  Dois temas
(claro e escuro) compartilham os mesmos componentes; as cores vêm de
:mod:`ui.theme` em tempo de pintura, então a troca de tema é imediata.

Componentes:

* :class:`SkyBackground` -- fundo institucional (gradiente + malha discreta);
* :class:`GlassPanel` / :class:`AccentCard` -- cartões de conteúdo;
* :class:`GlossyButton`, :class:`NavButton`, :class:`ThemeToggle` -- botões;
* :class:`SegmentedSelector` -- seletor Motorista/Transportador;
* :class:`FileSelector` -- caminho de arquivo/pasta com ``QFileDialog``;
* :class:`Badge`, :class:`IconWidget`, :class:`IconTile` -- detalhes visuais;
* :class:`LogView` -- console de processamento colorido por nível;
* :class:`StatusLed` -- indicador de estado.

.. note::
   As APIs consumidas pelas telas (``path``, ``set_path``, ``current``,
   ``set_current``, ``changed``, ``selectionChanged``, ``append_log``,
   ``set_state``) e os ``objectName`` usados pelo QSS devem ser preservados.
   Os métodos ``refresh_theme`` são visuais: repintam ícones/pixmaps quando o
   tema muda.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .icons import icon as vector_icon
from .icons import icon_pixmap
from .theme import (
    APP_FONT,
    LOG_COLORS,
    LOG_LABELS,
    led_color,
    palette,
)

__all__ = [
    "AccentCard",
    "AeroCheckBox",
    "Badge",
    "FileSelector",
    "GlassPanel",
    "GlossyButton",
    "IconTile",
    "IconWidget",
    "LogView",
    "NavButton",
    "SegmentedSelector",
    "SkyBackground",
    "StatusLed",
    "ThemeToggle",
    "create_app_icon",
]

# Mapeamento papel semântico -> chave da paleta.
_ROLE_KEYS = {
    "text": "text",
    "body": "body",
    "muted": "muted",
    "subtle": "subtle",
    "faint": "faint",
    "accent": "accent",
    "accent_deep": "accent_deep",
    "orange": "orange",
    "orange_deep": "orange_deep",
    "success": "ok_text",
    "danger": "danger",
    "inverse": "inverse",
    "header_text": "header_text",
    "header_muted": "header_muted",
    "nav_text": "nav_text",
    "nav_active": "nav_active_text",
    "warning": "warn_text",
    "white": "#FFFFFF",
}


def tone(role: str) -> str:
    """Resolve um papel semântico para uma cor hexadecimal do tema atual."""
    if role.startswith("#"):
        return role
    chave = _ROLE_KEYS.get(role, "text")
    if chave.startswith("#"):
        return chave
    return palette()[chave]


# ---------------------------------------------------------------------------
# Fundo institucional
# ---------------------------------------------------------------------------
class SkyBackground(QWidget):
    """Fundo institucional: gradiente sutil + malha discreta.

    Substitui o antigo céu Frutiger Aero.  Não há animação nem imagens; o
    desenho é 100% decorativo e acompanha o tema ativo.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("appBackground")
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Pinta o degradê, a malha e os brilhos de canto."""
        p = palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = max(1, self.width())
        height = max(1, self.height())

        escuro = p["theme"] == "dark"
        gradiente = QLinearGradient(0, 0, 0, height)
        if escuro:
            gradiente.setColorAt(0.0, QColor("#0C1730"))
            gradiente.setColorAt(0.55, QColor("#101B33"))
            gradiente.setColorAt(1.0, QColor("#0B1428"))
        else:
            gradiente.setColorAt(0.0, QColor("#F4F7FC"))
            gradiente.setColorAt(0.55, QColor("#F8FAFC"))
            gradiente.setColorAt(1.0, QColor("#EEF3FA"))
        painter.fillRect(self.rect(), gradiente)

        # Brilho azul discreto no canto superior direito.
        brilho = QRadialGradient(
            QPointF(width * 0.86, height * 0.02), max(width, height) * 0.55
        )
        brilho.setColorAt(
            0.0,
            QColor(51, 166, 222, 34 if escuro else 26),
        )
        brilho.setColorAt(1.0, QColor(51, 166, 222, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(brilho))
        painter.drawRect(self.rect())

        # Malha técnica de 40 px (institucional, quase imperceptível).
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(
            QPen(QColor(148, 163, 184, 16 if escuro else 22), 1)
        )
        passo = 40
        for x in range(0, width, passo):
            painter.drawLine(x, 0, x, height)
        for y in range(0, height, passo):
            painter.drawLine(0, y, width, y)
        painter.end()

    def refresh_theme(self) -> None:
        """Repinta o fundo após a troca de tema."""
        self.update()


# ---------------------------------------------------------------------------
# Cartões
# ---------------------------------------------------------------------------
class GlassPanel(QFrame):
    """Cartão de conteúdo (aresta 8 px, borda discreta).

    O nome histórico ``GlassPanel`` foi mantido para não alterar as telas que
    já o utilizam; visualmente é um cartão plano institucional.
    """

    def __init__(self, parent: QWidget | None = None, shadow: bool = True) -> None:
        super().__init__(parent)
        self.setObjectName("glassPanel")


class AccentCard(QFrame):
    """Cartão com filete institucional de 40×4 px no canto superior esquerdo."""

    def __init__(
        self,
        parent: QWidget | None = None,
        accent: str = "orange",
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self._accent = accent

    def set_accent(self, accent: str) -> None:
        """Troca a cor do filete (``orange`` ou ``accent``)."""
        self._accent = accent
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Desenha o cartão (QSS) e o filete de acento sobreposto."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(tone(self._accent)))
        painter.drawRoundedRect(QRectF(1, 1, 40, 4), 2, 2)
        painter.end()


# ---------------------------------------------------------------------------
# Ícones e selos
# ---------------------------------------------------------------------------
class IconWidget(QWidget):
    """Ícone vetorial colorido pelo tema atual."""

    def __init__(
        self,
        name: str,
        size: int = 16,
        role: str = "accent",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._size = size
        self._role = role
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAccessibleName("")

    def set_icon(self, name: str, role: str | None = None) -> None:
        """Troca o desenho (e opcionalmente a cor)."""
        self._name = name
        if role:
            self._role = role
        self.update()

    def set_role(self, role: str) -> None:
        """Troca apenas a cor semântica do ícone."""
        self._role = role
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Desenha o ícone centralizado."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pixmap = icon_pixmap(self._name, self._size, tone(self._role))
        painter.drawPixmap(
            QPointF(
                (self.width() - self._size) / 2,
                (self.height() - self._size) / 2,
            ),
            pixmap,
        )
        painter.end()

    def refresh_theme(self) -> None:
        """Repinta o ícone após a troca de tema."""
        self.update()


class IconTile(QFrame):
    """Quadro colorido com um ícone central (usado em resumos e avisos).

    No tema claro o tile de acento é azul sólido com ícone branco; no tema
    escuro ele vira um quadro escuro com borda/ícone azuis, como no design.
    """

    def __init__(
        self,
        name: str,
        size: int = 36,
        bg_key: str = "accent",
        border_key: str | None = None,
        icon_role: str = "white",
        radius: int = 4,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._bg_key = bg_key
        self._border_key = border_key
        self._icon_role = icon_role
        self._radius = radius
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Desenha fundo, borda e ícone conforme o tema ativo."""
        p = palette()
        escuro = p["theme"] == "dark"
        accent_tile = self._bg_key == "accent"

        if accent_tile and escuro:
            fundo = p["surface_sunken"]
            borda = QColor(p["accent"])
            borda.setAlpha(90)
            cor_icone = p["accent"]
        else:
            fundo = p.get(self._bg_key, self._bg_key)
            borda = (
                QColor(p.get(self._border_key, self._border_key))
                if self._border_key
                else None
            )
            cor_icone = tone(self._icon_role)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QColor(fundo))
        painter.setPen(QPen(borda, 1) if borda else Qt.PenStyle.NoPen)
        painter.drawRoundedRect(
            QRectF(0.5, 0.5, self.width() - 1, self.height() - 1),
            self._radius,
            self._radius,
        )
        tamanho = max(10, int(self.width() * 0.48))
        pixmap = icon_pixmap(self._name, tamanho, cor_icone, 1.7)
        painter.drawPixmap(
            QPointF(
                (self.width() - tamanho) / 2,
                (self.height() - tamanho) / 2,
            ),
            pixmap,
        )
        painter.end()

    def refresh_theme(self) -> None:
        """Repinta o quadro e o ícone após a troca de tema."""
        self.update()


class Badge(QLabel):
    """Selo de estado com variantes de cor (``ok``, ``idle``, ``warn``...)."""

    def __init__(
        self,
        text: str = "",
        variant: str = "idle",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("badge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._variant = variant
        self.setProperty("variant", variant)

    def set_variant(self, variant: str) -> None:
        """Troca a variante visual e reaplica o QSS."""
        self._variant = variant
        self.setProperty("variant", variant)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_status(self, text: str, variant: str) -> None:
        """Atalho para trocar texto e variante de uma vez."""
        self.setText(text)
        self.set_variant(variant)


# ---------------------------------------------------------------------------
# Botões
# ---------------------------------------------------------------------------
class GlossyButton(QPushButton):
    """Botão institucional, com variantes definidas pelo ``objectName``.

    ``primaryButton`` (laranja), ``glossButton``/``miniButton`` (secundário) e
    ``dangerButton`` (cancelar).  O ícone opcional é repintado no tema.
    """

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        variant: str = "glossButton",
        icon_name: str | None = None,
        icon_role: str = "accent_deep",
        icon_size: int = 15,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName(variant)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._icon_name = icon_name
        self._icon_role = icon_role
        self._icon_size = icon_size
        if text:
            self.setAccessibleName(text)
        self._refresh_icon()

    def _refresh_icon(self) -> None:
        """Recria o ícone do botão conforme o tema/estado."""
        if not self._icon_name:
            return
        self.setIcon(
            vector_icon(
                self._icon_name,
                self._icon_size,
                tone(self._icon_role),
            )
        )
        self.setIconSize(QSize(self._icon_size, self._icon_size))

    def refresh_theme(self) -> None:
        """Repinta o ícone após a troca de tema."""
        self._refresh_icon()
        self.update()


class NavButton(QPushButton):
    """Botão de navegação principal com ícone e estado ativo."""

    def __init__(
        self,
        text: str,
        icon_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("navButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCheckable(False)
        self._icon_name = icon_name
        self._active = False
        self.setAccessibleName(text)
        self.setIconSize(QSize(15, 15))
        self.setProperty("active", "false")
        self._refresh_icon()

    def set_active(self, active: bool) -> None:
        """Marca o botão como aba ativa e atualiza o ícone."""
        self._active = active
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self._refresh_icon()

    def setText(self, text: str) -> None:  # noqa: N802 (API Qt)
        """Atualiza o rótulo e garante largura suficiente para ele."""
        super().setText(text)
        metrics = QFontMetrics(self.font())
        self.setMinimumWidth(metrics.horizontalAdvance(text) + 70)

    def _refresh_icon(self) -> None:
        """Recria o ícone com a cor do estado atual."""
        role = "nav_active" if self._active else "nav_text"
        self.setIcon(vector_icon(self._icon_name, 15, tone(role)))

    def refresh_theme(self) -> None:
        """Repinta o ícone após a troca de tema."""
        self._refresh_icon()


class ThemeToggle(QToolButton):
    """Alternador claro/escuro (única função nova do redesign)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("themeToggle")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Alternar tema claro e escuro")
        self.setToolTip("Ativar modo escuro")
        self._update_icon()

    def _update_icon(self) -> None:
        """Mostra a lua quando o escuro está ativo e o sol quando não está."""
        escuro = self.isChecked()
        self.setIcon(
            vector_icon(
                "moon" if escuro else "sun",
                16,
                tone("header_text"),
            )
        )
        self.setIconSize(QSize(16, 16))
        self.setToolTip("Ativar tema claro" if escuro else "Ativar modo escuro")

    def refresh_theme(self) -> None:
        """Reavalia o ícone conforme o tema atual."""
        self._update_icon()


# ---------------------------------------------------------------------------
# Checkbox institucional
# ---------------------------------------------------------------------------
class AeroCheckBox(QCheckBox):
    """Checkbox desenhado em código, com alvo mínimo de 26 px.

    A semântica é a de um ``QCheckBox`` normal: ``isChecked``/``toggled`` são
    usados pela lógica das telas.
    """

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(26, 26)
        if text:
            self.setAccessibleName(text)

    def sizeHint(self) -> QSize:  # noqa: N802 (API Qt)
        """Reserva espaço para o indicador desenhado manualmente."""
        hint = super().sizeHint()
        hint.setWidth(hint.width() + 8)
        hint.setHeight(max(26, hint.height()))
        return hint

    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Desenha indicador, marca e texto conforme o tema."""
        p = palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        box = 16.0
        x = 4.0
        y = (self.height() - box) / 2.0
        rect = QRectF(x, y, box, box)

        if not self.isEnabled():
            borda = QColor(p["faint"])
            fundo = QColor(p["surface_sunken"])
        else:
            borda = QColor(p["border_strong"])
            fundo = QColor(p["field_bg"])

        painter.setPen(QPen(borda, 1.4))
        painter.setBrush(QBrush(fundo))
        painter.drawRoundedRect(rect, 3, 3)

        if self.isChecked():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(p["accent"])))
            painter.drawRoundedRect(rect, 3, 3)
            check = QPainterPath()
            check.moveTo(x + 4.2, y + 8.2)
            check.lineTo(x + 7.0, y + 11.0)
            check.lineTo(x + 12.2, y + 5.2)
            painter.setPen(
                QPen(
                    QColor("#FFFFFF"),
                    2.0,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                )
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(check)

        painter.setPen(QColor(p["text"] if self.isEnabled() else p["faint"]))
        painter.setFont(self.font())
        painter.drawText(
            self.rect().adjusted(int(x + box + 7), 0, -2, 0),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            self.text(),
        )

        if self.hasFocus():
            painter.setPen(QPen(QColor(p["accent"]), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-2.5, -2.5, 2.5, 2.5), 5, 5)
        painter.end()

    def refresh_theme(self) -> None:
        """Repinta o indicador após a troca de tema."""
        self.update()


# ---------------------------------------------------------------------------
# Seletor segmentado
# ---------------------------------------------------------------------------
class _SegmentButton(QPushButton):
    """Botão do seletor que desenha ícone, rótulo e ponto de estado ativo."""

    def __init__(
        self,
        label: str,
        icon_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("", parent)
        self._label = label
        self._icon_name = icon_name
        self._active = False
        self.setObjectName("segmentButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(label)

    def set_active(self, active: bool) -> None:
        """Atualiza o estado ativo (chamado pelo seletor)."""
        self._active = active
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        """Desenha o fundo do QSS e o conteúdo ícone + texto + ponto."""
        super().paintEvent(event)
        p = palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        cor_texto = p["seg_active_text"] if self._active else p["seg_text"]
        cor_icone = p["seg_active_icon"] if self._active else p["seg_icon"]
        if not self.isEnabled():
            cor_texto = p["faint"]
            cor_icone = p["faint"]

        fonte = QFont(self.font())
        fonte.setWeight(
            QFont.Weight.Bold if self._active else QFont.Weight.DemiBold
        )
        fonte.setPixelSize(13)
        painter.setFont(fonte)
        metrics = QFontMetrics(fonte)
        texto_w = metrics.horizontalAdvance(self._label)
        icone_w = 14
        dot_w = 12 if self._active else 0
        gap = 7
        total = icone_w + gap + texto_w + dot_w
        inicio = (self.width() - total) / 2.0
        centro_y = self.height() / 2.0

        pixmap = icon_pixmap(self._icon_name, icone_w, cor_icone, 1.8)
        painter.drawPixmap(
            QPointF(inicio, centro_y - icone_w / 2.0), pixmap
        )
        painter.setPen(QColor(cor_texto))
        painter.drawText(
            QRectF(
                inicio + icone_w + gap,
                0,
                texto_w + 2,
                self.height(),
            ),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            self._label,
        )
        if self._active:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(p["seg_active_icon"]))
            painter.drawEllipse(
                QPointF(
                    inicio + icone_w + gap + texto_w + 7,
                    centro_y,
                ),
                2.6,
                2.6,
            )

        if self.hasFocus():
            painter.setPen(QPen(QColor(p["accent"]), 1.6))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                QRectF(2.0, 2.0, self.width() - 4.0, self.height() - 4.0),
                4,
                4,
            )
        painter.end()


class SegmentedSelector(QWidget):
    """Controle segmentado com dois estados mutuamente exclusivos."""

    changed = pyqtSignal(str)

    def __init__(
        self,
        options: list[tuple[str, str]],
        initial: str = "",
        parent: QWidget | None = None,
        icons: dict[str, str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._buttons: dict[str, _SegmentButton] = {}
        self._current = ""
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        mapa_icones = icons or {"motorista": "user", "transportador": "truck"}

        frame = QFrame(self)
        frame.setObjectName("segmentFrame")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        for key, label in options:
            button = _SegmentButton(label, mapa_icones.get(key, "dot"), frame)
            button.setAccessibleDescription("Tipo de relatório")
            button.clicked.connect(lambda _=False, k=key: self.set_current(k))
            self._group.addButton(button)
            layout.addWidget(button, 1)
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
            button.set_active(active)
            button.setChecked(active)
        if emit and changed:
            self.changed.emit(key)

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 (API Qt)
        """Habilita/desabilita todas as opções."""
        super().setEnabled(enabled)
        for button in self._buttons.values():
            button.setEnabled(enabled)

    def refresh_theme(self) -> None:
        """Repinta os botões do seletor após a troca de tema."""
        for button in self._buttons.values():
            button.update()


# ---------------------------------------------------------------------------
# Seletor de arquivo / pasta
# ---------------------------------------------------------------------------
class FileSelector(QWidget):
    """Campo que exibe um caminho e permite escolher/limpar via QFileDialog."""

    selectionChanged = pyqtSignal(str)

    def __init__(
        self,
        caption: str,
        button_text: str = "Procurar...",
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
        self._caption = caption

        caption_row = QHBoxLayout()
        caption_row.setContentsMargins(0, 0, 0, 0)
        caption_row.setSpacing(6)
        self._caption_icon = IconWidget(
            "file" if mode != "directory" else "folder",
            14,
            "accent",
        )
        caption_label = QLabel(caption, self)
        caption_label.setObjectName("fieldLabel")
        self._badge = Badge("PENDENTE", "idle")
        self._badge.setAccessibleName(f"Situação de {caption}")
        caption_row.addWidget(self._caption_icon)
        caption_row.addWidget(caption_label)
        caption_row.addStretch(1)
        caption_row.addWidget(self._badge)

        self._field = QFrame(self)
        self._field.setObjectName("fieldFrame")
        self._field.setMinimumHeight(40)
        field_layout = QHBoxLayout(self._field)
        field_layout.setContentsMargins(10, 3, 4, 3)
        field_layout.setSpacing(8)

        self._field_icon = IconWidget(
            "file" if mode != "directory" else "folder",
            15,
            "subtle",
        )

        self._path_label = QLabel("Nenhum arquivo selecionado", self._field)
        self._path_label.setObjectName("fieldPath")
        self._path_label.setProperty("empty", "true")
        self._path_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._path_label.setMinimumWidth(40)
        self._path_label.setAccessibleDescription(caption)

        self._clear_button = QToolButton(self._field)
        self._clear_button.setObjectName("clearButton")
        self._clear_button.setIcon(vector_icon("close", 12, tone("subtle")))
        self._clear_button.setIconSize(QSize(12, 12))
        self._clear_button.setToolTip("Limpar seleção")
        self._clear_button.setAccessibleName(f"Limpar seleção — {caption}")
        self._clear_button.setFixedSize(24, 24)
        self._clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_button.clicked.connect(self.clear)
        self._clear_button.setEnabled(False)

        self._browse_button = QPushButton(button_text, self._field)
        self._browse_button.setObjectName("miniButton")
        self._browse_button.setIcon(vector_icon("search", 12, tone("text")))
        self._browse_button.setIconSize(QSize(12, 12))
        self._browse_button.setAccessibleName(f"{button_text} — {caption}")
        self._browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_button.setMinimumHeight(30)
        self._browse_button.clicked.connect(self._open_dialog)
        caption_label.setBuddy(self._browse_button)

        field_layout.addWidget(self._field_icon)
        field_layout.addWidget(self._path_label, 1)
        field_layout.addWidget(self._clear_button)
        field_layout.addWidget(self._browse_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(caption_row)
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
        """Atualiza o texto exibido, a dica, o selo e o botão de limpar."""
        if self._path:
            self._path_label.setProperty("empty", "false")
            self._path_label.setToolTip(self._path)
            self._field.setToolTip(self._path)
            self._clear_button.setEnabled(self.isEnabled())
            self._badge.set_status("SELECIONADO", "ok")
            self._path_label.setText(self._path)
        else:
            placeholder = (
                "Nenhuma pasta selecionada"
                if self._mode == "directory"
                else "Nenhum arquivo selecionado"
            )
            self._path_label.setProperty("empty", "true")
            self._path_label.setToolTip("")
            self._path_label.setText(placeholder)
            self._field.setToolTip("")
            self._clear_button.setEnabled(False)
            self._badge.set_status("PENDENTE", "idle")
        self._path_label.style().unpolish(self._path_label)
        self._path_label.style().polish(self._path_label)
        self._elide()

    def _elide(self) -> None:
        """Elide o caminho no meio, conforme a largura disponível."""
        if not self._path:
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

    def refresh_theme(self) -> None:
        """Repinta ícones e selo após a troca de tema."""
        self._caption_icon.refresh_theme()
        self._field_icon.refresh_theme()
        cor = tone("text") if self.isEnabled() else tone("faint")
        self._browse_button.setIcon(vector_icon("search", 12, cor))
        self._clear_button.setIcon(
            vector_icon("close", 12, tone("subtle"))
        )
        self._badge.style().unpolish(self._badge)
        self._badge.style().polish(self._badge)


# ---------------------------------------------------------------------------
# Console de log
# ---------------------------------------------------------------------------
class LogView(QWidget):
    """Console escuro com cabeçalho e linhas coloridas por nível."""

    LEVEL_ICONS = {
        "info": "•",
        "success": "✔",
        "warning": "!",
        "error": "✖",
    }

    def __init__(
        self,
        parent: QWidget | None = None,
        title: str = "CONSOLE DE PROCESSAMENTO LOGÍSTICO • GRUPOSC",
        meta: str = "UTF-8 • xlsx-engine-v1.1",
    ) -> None:
        super().__init__(parent)

        frame = QFrame(self)
        frame.setObjectName("consoleFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        header = QFrame(frame)
        header.setObjectName("consoleHeader")
        header.setFixedHeight(32)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)
        header_layout.setSpacing(8)

        dots = QHBoxLayout()
        dots.setSpacing(5)
        for cor in ("#EF4444", "#F59E0B", "#10B981"):
            dot = QFrame(header)
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(
                f"background: {cor}; border: none; border-radius: 4px;"
            )
            dot.setAccessibleName("")
            dots.addWidget(dot)
        header_layout.addLayout(dots)

        self._title = QLabel(title, header)
        self._title.setObjectName("consoleTitle")
        self._title.setAccessibleName("Console de log")
        header_layout.addWidget(self._title)
        header_layout.addStretch(1)

        self._meta = QLabel(meta, header)
        self._meta.setObjectName("consoleMeta")
        header_layout.addWidget(self._meta)

        self._view = QPlainTextEdit(frame)
        self._view.setObjectName("logView")
        self._view.setReadOnly(True)
        self._view.setMaximumBlockCount(800)
        self._view.setFont(QFont("Cascadia Mono", 9))
        self._view.setAccessibleName("Log de mensagens")
        self._view.setAccessibleDescription(
            "Mensagens de status, sucesso, aviso e erro."
        )
        self._view.setPlaceholderText(
            "Console pronto • aguardando disparo do operador…"
        )
        paleta = self._view.palette()
        paleta.setColor(
            QPalette.ColorRole.PlaceholderText, QColor("#8FA5C7")
        )
        self._view.setPalette(paleta)

        frame_layout.addWidget(header)
        frame_layout.addWidget(self._view, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(frame)
        self.setMinimumHeight(150)

    def append_log(self, message: str, level: str = "info") -> None:
        """Adiciona uma linha colorida (hora, nível e mensagem) ao console."""
        color = LOG_COLORS.get(level, LOG_COLORS["info"])
        rotulo = LOG_LABELS.get(level, "INFO")
        safe = (
            str(message)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        hora = datetime.now().strftime("%H:%M:%S")
        self._view.appendHtml(
            f'<span style="color:#64748B;">{hora}</span>'
            f'&nbsp;&nbsp;<span style="color:{color}; font-weight:700;">'
            f"[{rotulo}]</span>&nbsp;&nbsp;"
            f'<span style="color:#CBD5E1;">{safe}</span>'
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
    """Ponto luminoso de status (parado / executando / ok / erro)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._state = "idle"
        self._pulse = 0.0
        self.setAccessibleName("Indicador visual de status")
        self.setAccessibleDescription(
            "Informativo. O texto de status ao lado descreve o estado atual."
        )
        self._animation = QPropertyAnimation(self, b"pulse", self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(1100)
        self._animation.setLoopCount(-1)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._animation.valueChanged.connect(self._on_pulse)
        self._animation.start()

    def set_state(self, state: str) -> None:
        """Define o estado visual: idle, running, ok, error ou cancelled."""
        self._state = state if state in ("idle", "running", "ok", "error", "cancelled") else "idle"
        rotulos = {
            "idle": "Parado",
            "running": "Em execução",
            "ok": "Concluído",
            "error": "Erro",
            "cancelled": "Cancelado",
        }
        self.setToolTip(rotulos[self._state])
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
        """Desenha o ponto com halo suave."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = QColor(led_color(self._state))

        centro = QPointF(self.width() / 2, self.height() / 2)
        if self._state == "running":
            halo = QRadialGradient(centro, 6)
            halo.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 110))
            halo.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(halo))
            painter.drawEllipse(centro, 6, 6)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(centro, 3.6, 3.6)
        painter.end()

    def refresh_theme(self) -> None:
        """Repinta o LED após a troca de tema."""
        self.update()


# ---------------------------------------------------------------------------
# Ícone do aplicativo
# ---------------------------------------------------------------------------
def create_app_icon(size: int = 64) -> QIcon:
    """Desenha o ícone institucional (SC sobre azul-marinho e filete laranja)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    margem = size * 0.03
    path = QPainterPath()
    path.addRoundedRect(
        QRectF(margem, margem, size - 2 * margem, size - 2 * margem),
        size * 0.18,
        size * 0.18,
    )
    painter.fillPath(path, QBrush(QColor("#1C2445")))
    painter.setPen(QPen(QColor("#33A6DE"), max(1.0, size * 0.012)))
    painter.drawPath(path)

    # Filete laranja superior.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#FF9F00"))
    painter.drawRoundedRect(
        QRectF(size * 0.16, size * 0.12, size * 0.68, size * 0.055),
        size * 0.03,
        size * 0.03,
    )

    # Monograma SC.
    fonte = QFont(APP_FONT, max(6, int(size * 0.30)))
    fonte.setWeight(QFont.Weight.Bold)
    painter.setFont(fonte)
    painter.setPen(QColor("#33A6DE"))
    painter.drawText(
        QRectF(0, size * 0.30, size, size * 0.52),
        int(Qt.AlignmentFlag.AlignCenter),
        "SC",
    )
    painter.end()
    return QIcon(pixmap)
