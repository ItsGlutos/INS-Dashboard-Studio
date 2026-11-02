"""Ícones vetoriais desenhados em código (sem imagens externas).

Todos os ícones usam uma grade de 24×24 e são pintados com ``QPainter`` no
momento da criação.  A cor é um parâmetro: os componentes repintam os ícones
quando o tema claro/escuro muda.  Este módulo é puramente visual.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

__all__ = ["ICON_NAMES", "icon_pixmap", "icon"]

ICON_NAMES = (
    "grid",
    "mail",
    "sliders",
    "history",
    "file",
    "folder",
    "template",
    "user",
    "truck",
    "play",
    "bolt",
    "shield",
    "excel",
    "search",
    "close",
    "check",
    "info",
    "sun",
    "moon",
    "trash",
    "refresh",
    "terminal",
    "external",
    "arrow-right",
    "lock",
    "chart",
    "layers",
    "download",
    "alert",
    "dot",
)


def _rounded(p: QPainter, x: float, y: float, w: float, h: float, r: float) -> None:
    p.drawRoundedRect(QRectF(x, y, w, h), r, r)


def _draw(name: str, p: QPainter, color: QColor) -> None:
    """Desenha o ícone ``name`` em uma grade 24×24 com o traço atual."""
    if name == "grid":
        _rounded(p, 3, 3, 7, 7, 1.5)
        _rounded(p, 14, 3, 7, 7, 1.5)
        _rounded(p, 3, 14, 7, 7, 1.5)
        _rounded(p, 14, 14, 7, 7, 1.5)
    elif name == "mail":
        _rounded(p, 3, 5, 18, 14, 2)
        path = QPainterPath()
        path.moveTo(4.5, 7)
        path.lineTo(12, 13)
        path.lineTo(19.5, 7)
        p.drawPath(path)
    elif name == "sliders":
        for y, x in ((7, 9), (12, 15), (17, 7)):
            p.drawLine(QPointF(3, y), QPointF(21, y))
            p.setBrush(QColor(color))
            p.drawEllipse(QPointF(x, y), 2.1, 2.1)
            p.setBrush(Qt.BrushStyle.NoBrush)
    elif name == "history":
        p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
        p.drawLine(QPointF(12, 7.5), QPointF(12, 12.3))
        p.drawLine(QPointF(12, 12.3), QPointF(15.4, 14.2))
    elif name == "file":
        path = QPainterPath()
        path.moveTo(6, 3)
        path.lineTo(14, 3)
        path.lineTo(19, 8)
        path.lineTo(19, 21)
        path.lineTo(6, 21)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(14, 3), QPointF(14, 8))
        p.drawLine(QPointF(14, 8), QPointF(19, 8))
        p.drawLine(QPointF(9, 13), QPointF(16, 13))
        p.drawLine(QPointF(9, 17), QPointF(16, 17))
    elif name == "folder":
        path = QPainterPath()
        path.moveTo(3, 7)
        path.lineTo(9, 7)
        path.lineTo(11, 9.5)
        path.lineTo(21, 9.5)
        path.lineTo(21, 19)
        path.lineTo(3, 19)
        path.closeSubpath()
        p.drawPath(path)
    elif name in ("template", "layers"):
        p.drawRect(QRectF(6, 4, 12, 14))
        p.drawLine(QPointF(9, 8), QPointF(15, 8))
        p.drawLine(QPointF(9, 11.5), QPointF(15, 11.5))
        p.drawLine(QPointF(9, 15), QPointF(13, 15))
        p.drawLine(QPointF(3, 7), QPointF(4.5, 7))
        p.drawLine(QPointF(3, 12), QPointF(4.5, 12))
        p.drawLine(QPointF(3, 17), QPointF(4.5, 17))
    elif name == "user":
        p.drawEllipse(QPointF(12, 8), 3.6, 3.6)
        path = QPainterPath()
        path.moveTo(5.2, 20)
        path.cubicTo(5.8, 15.6, 8.4, 14.2, 12, 14.2)
        path.cubicTo(15.6, 14.2, 18.2, 15.6, 18.8, 20)
        p.drawPath(path)
    elif name == "truck":
        p.drawRect(QRectF(2.5, 7, 11, 9))
        path = QPainterPath()
        path.moveTo(13.5, 9.5)
        path.lineTo(17.5, 9.5)
        path.lineTo(21, 12.5)
        path.lineTo(21, 16)
        path.lineTo(13.5, 16)
        path.closeSubpath()
        p.drawPath(path)
        p.drawEllipse(QPointF(7, 18), 2.1, 2.1)
        p.drawEllipse(QPointF(17.5, 18), 2.1, 2.1)
    elif name == "play":
        p.drawEllipse(QPointF(12, 12), 9, 9)
        path = QPainterPath()
        path.moveTo(10, 8)
        path.lineTo(16.5, 12)
        path.lineTo(10, 16)
        path.closeSubpath()
        p.setBrush(QColor(color))
        p.drawPath(path)
        p.setBrush(Qt.BrushStyle.NoBrush)
    elif name == "bolt":
        path = QPainterPath()
        path.moveTo(13.5, 2.5)
        path.lineTo(5, 13.5)
        path.lineTo(11, 13.5)
        path.lineTo(10.2, 21.5)
        path.lineTo(19, 10)
        path.lineTo(12.6, 10)
        path.closeSubpath()
        p.setBrush(QColor(color))
        p.drawPath(path)
        p.setBrush(Qt.BrushStyle.NoBrush)
    elif name == "shield":
        path = QPainterPath()
        path.moveTo(12, 2.5)
        path.lineTo(20, 5.5)
        path.lineTo(20, 12)
        path.cubicTo(20, 17, 16.5, 20.2, 12, 21.5)
        path.cubicTo(7.5, 20.2, 4, 17, 4, 12)
        path.lineTo(4, 5.5)
        path.closeSubpath()
        p.drawPath(path)
        path2 = QPainterPath()
        path2.moveTo(8.5, 12)
        path2.lineTo(11.2, 14.6)
        path2.lineTo(15.6, 9.4)
        p.drawPath(path2)
    elif name in ("excel", "chart"):
        _rounded(p, 3, 4, 18, 16, 2)
        p.drawLine(QPointF(3, 9), QPointF(21, 9))
        p.drawLine(QPointF(9.5, 9), QPointF(9.5, 20))
        p.drawLine(QPointF(15, 9), QPointF(15, 20))
    elif name == "search":
        p.drawEllipse(QPointF(10.5, 10.5), 6.5, 6.5)
        p.drawLine(QPointF(15.4, 15.4), QPointF(20.5, 20.5))
    elif name == "close":
        p.drawLine(QPointF(6, 6), QPointF(18, 18))
        p.drawLine(QPointF(18, 6), QPointF(6, 18))
    elif name == "check":
        path = QPainterPath()
        path.moveTo(4.5, 12.5)
        path.lineTo(9.5, 17.5)
        path.lineTo(19.5, 6.5)
        p.drawPath(path)
    elif name == "info":
        p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
        p.drawLine(QPointF(12, 10.8), QPointF(12, 17))
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(12, 7.4), 1.1, 1.1)
        p.setBrush(Qt.BrushStyle.NoBrush)
    elif name == "sun":
        p.drawEllipse(QPointF(12, 12), 4.2, 4.2)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            p.drawLine(
                QPointF(12 + math.cos(rad) * 7.2, 12 + math.sin(rad) * 7.2),
                QPointF(12 + math.cos(rad) * 9.6, 12 + math.sin(rad) * 9.6),
            )
    elif name == "moon":
        path = QPainterPath()
        path.moveTo(15.5, 3.5)
        path.cubicTo(9.5, 5, 6.5, 9, 6.5, 13.5)
        path.cubicTo(6.5, 17.5, 9.5, 20.5, 14, 21)
        path.cubicTo(10.6, 18.6, 9.4, 15.6, 9.4, 12.4)
        path.cubicTo(9.4, 8.8, 11.5, 5.4, 15.5, 3.5)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "trash":
        p.drawLine(QPointF(4, 7), QPointF(20, 7))
        p.drawLine(QPointF(9, 7), QPointF(9.5, 3.5))
        p.drawLine(QPointF(15, 7), QPointF(14.5, 3.5))
        p.drawLine(QPointF(9.5, 3.5), QPointF(14.5, 3.5))
        path = QPainterPath()
        path.moveTo(6, 7)
        path.lineTo(7.2, 20.5)
        path.lineTo(16.8, 20.5)
        path.lineTo(18, 7)
        p.drawPath(path)
    elif name == "refresh":
        p.drawArc(QRectF(4, 4, 16, 16), 40 * 16, 285 * 16)
        path = QPainterPath()
        path.moveTo(18.5, 3.5)
        path.lineTo(19.5, 8.5)
        path.lineTo(14.5, 8)
        p.drawPath(path)
    elif name == "terminal":
        _rounded(p, 2.5, 4.5, 19, 15, 2)
        path = QPainterPath()
        path.moveTo(6.5, 9)
        path.lineTo(9.5, 12)
        path.lineTo(6.5, 15)
        p.drawPath(path)
        p.drawLine(QPointF(12, 15), QPointF(17, 15))
    elif name == "external":
        path = QPainterPath()
        path.moveTo(13, 4)
        path.lineTo(20, 4)
        path.lineTo(20, 11)
        p.drawPath(path)
        p.drawLine(QPointF(20, 4), QPointF(11, 13))
        path2 = QPainterPath()
        path2.moveTo(18, 14)
        path2.lineTo(18, 20)
        path2.lineTo(4, 20)
        path2.lineTo(4, 6)
        path2.lineTo(10, 6)
        p.drawPath(path2)
    elif name == "arrow-right":
        p.drawLine(QPointF(4, 12), QPointF(19, 12))
        path = QPainterPath()
        path.moveTo(13.5, 6.5)
        path.lineTo(19, 12)
        path.lineTo(13.5, 17.5)
        p.drawPath(path)
    elif name == "lock":
        _rounded(p, 5, 10, 14, 11, 2)
        path = QPainterPath()
        path.moveTo(8, 10)
        path.lineTo(8, 7.5)
        path.cubicTo(8, 3.5, 16, 3.5, 16, 7.5)
        path.lineTo(16, 10)
        p.drawPath(path)
    elif name == "download":
        p.drawLine(QPointF(12, 3.5), QPointF(12, 15))
        path = QPainterPath()
        path.moveTo(7, 10)
        path.lineTo(12, 15)
        path.lineTo(17, 10)
        p.drawPath(path)
        p.drawLine(QPointF(4, 20), QPointF(20, 20))
    elif name == "alert":
        path = QPainterPath()
        path.moveTo(12, 3)
        path.lineTo(21.5, 20)
        path.lineTo(2.5, 20)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(12, 9), QPointF(12, 14))
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(12, 17), 1.0, 1.0)
        p.setBrush(Qt.BrushStyle.NoBrush)
    elif name == "dot":
        p.setBrush(QColor(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(12, 12), 4.2, 4.2)
    else:  # fallback: pequeno quadrado
        _rounded(p, 6, 6, 12, 12, 2)


def icon_pixmap(
    name: str,
    size: int = 16,
    color: str = "#1C2445",
    stroke: float = 1.7,
) -> QPixmap:
    """Cria um ``QPixmap`` nítido (2×) do ícone pedido."""
    escala = 2
    pixmap = QPixmap(max(8, size) * escala, max(8, size) * escala)
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(escala)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(max(8, size) / 24.0, max(8, size) / 24.0)
    caneta = QPen(QColor(color), stroke)
    caneta.setCapStyle(Qt.PenCapStyle.RoundCap)
    caneta.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(caneta)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    _draw(name, painter, QColor(color))
    painter.end()
    return pixmap


def icon(name: str, size: int = 16, color: str = "#1C2445") -> QIcon:
    """Atalho que devolve um ``QIcon`` a partir de :func:`icon_pixmap`."""
    return QIcon(icon_pixmap(name, size, color))
