"""Composants maison de la DA : points rouges, fil, boutons, étiquettes feuilles, cartes."""

from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QEnterEvent,
    QFont,
    QFontMetrics,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from au_fil_d_une_vie.ui import theme

# Points rouges


def paint_dot(painter: QPainter, center: QPointF, diameter: float, filled: bool) -> None:
    """Point rouge plein (fait, avec ombre portée) ou vide (à faire, contour rouge)."""
    r = diameter / 2
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if filled:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.color(theme.RED_SHADOW))
        painter.drawEllipse(QPointF(center.x(), center.y() + diameter / 6), r, r)
        painter.setBrush(theme.color(theme.RED))
        painter.drawEllipse(center, r, r)
    else:
        width = max(1.5, diameter * 0.2)
        painter.setPen(QPen(theme.color(theme.RED), width))
        painter.setBrush(theme.color(theme.WHITE))
        painter.drawEllipse(center, r - width / 2, r - width / 2)
    painter.restore()


class DotRow(QWidget):
    """Rangée de points : `done` pleins puis `total - done` vides."""

    def __init__(
        self, done: int, total: int, diameter: int = 12, gap: int = 8, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._done = done
        self._total = total
        self._diameter = diameter
        self._gap = gap
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAccessibleName(f"{done} sur {total}")

    def sizeHint(self) -> QSize:
        n = max(self._total, 1)
        return QSize(n * self._diameter + (n - 1) * self._gap, self._diameter + 3)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        r = self._diameter / 2
        for i in range(self._total):
            x = r + i * (self._diameter + self._gap)
            paint_dot(painter, QPointF(x, r), self._diameter, filled=i < self._done)


# Boutons


_MIC_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z"/>'
    '<path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>'
)

ICONS = {"mic": _MIC_SVG}


def svg_pixmap(svg: str, size: int, device_ratio: float = 2.0) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pixmap = QPixmap(int(size * device_ratio), int(size * device_ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(device_ratio)
    return pixmap


class PrimaryButton(QPushButton):
    """Bouton rouge en relief (ombre pleine en bas) qui s'enfonce au clic."""

    SHADOW = 3

    def __init__(self, text: str, icon: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._icon = svg_pixmap(ICONS[icon], 20) if icon else None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(theme.font(theme.SANS, 17, QFont.Weight.DemiBold))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:
        text_width = self.fontMetrics().horizontalAdvance(self.text())
        icon_width = 32 if self._icon else 0
        return QSize(text_width + icon_width + 60, 56 + self.SHADOW)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pressed = self.isDown()
        enabled = self.isEnabled()
        face = QRectF(0, 0, self.width(), self.height() - self.SHADOW)
        offset = self.SHADOW - 1 if pressed else 0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.color(theme.RED_SHADOW if enabled else theme.BORDER))
        painter.drawRoundedRect(face.translated(0, self.SHADOW), 12, 12)
        top = QColor(theme.RED if enabled else theme.LEAF_BORDER)
        if self.underMouse() and enabled and not pressed:
            top = top.lighter(106)
        painter.setBrush(top)
        painter.drawRoundedRect(face.translated(0, offset), 12, 12)

        content = face.translated(0, offset)
        painter.setPen(theme.color(theme.WHITE))
        painter.setFont(self.font())
        text_width = self.fontMetrics().horizontalAdvance(self.text())
        total = text_width + (32 if self._icon else 0)
        x = content.center().x() - total / 2
        if self._icon:
            painter.drawPixmap(QPointF(x, content.center().y() - 10), self._icon)
            x += 32
        painter.drawText(
            QRectF(x, content.top(), text_width + 2, content.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.text(),
        )


class NavLink(QAbstractButton):
    """Lien de navigation : le lien actif porte un petit point rouge."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = False

    def _font(self) -> QFont:
        weight = QFont.Weight.DemiBold if self.isChecked() else QFont.Weight.Medium
        return theme.font(theme.SANS, 16, weight)

    def sizeHint(self) -> QSize:
        width = self.fontMetrics().horizontalAdvance(self.text()) * 1.08 + 36 + 16
        return QSize(int(width), 76)

    def enterEvent(self, event: QEnterEvent) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, event: QEvent) -> None:
        self._hover = False
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        x = 18.0
        if self.isChecked():
            paint_dot(painter, QPointF(x + 4, self.height() / 2), 8, filled=True)
            x += 16
        active = self.isChecked() or self._hover
        painter.setPen(theme.color("#2B2B2B" if active else theme.NAV_MUTED))
        painter.setFont(self._font())
        painter.drawText(
            QRectF(x, 0, self.width() - x, self.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.text(),
        )


class LeafToggle(QPushButton):
    """Bouton à bascule en forme de feuille (choix d'une personne)."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("leafToggle")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Largeur réservée pour le texte en gras (état coché), sans saut à la bascule.
        bold = QFontMetrics(theme.font(theme.SANS, 16, QFont.Weight.DemiBold))
        self.setMinimumWidth(bold.horizontalAdvance(text) + 40)


def link_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("link")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def outline_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("outline")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


# Textes


def label(
    text: str,
    family: str = theme.SANS,
    px: int = 17,
    weight: QFont.Weight = QFont.Weight.Normal,
    color: str = theme.INK,
    italic: bool = False,
    wrap: bool = False,
    spacing_em: float = 0.0,
) -> QLabel:
    widget = QLabel(text)
    widget.setFont(theme.font(family, px, weight, italic, spacing_em))
    widget.setStyleSheet(f"color: {color};")
    widget.setWordWrap(wrap)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    return widget


def eyebrow(text: str, color: str = theme.LEAF_TEXT_SOFT, spacing_em: float = 0.16) -> QLabel:
    """Petit titre en capitales espacées."""
    return label(
        text.upper(), px=13, weight=QFont.Weight.DemiBold, color=color, spacing_em=spacing_em
    )


def section_title(text: str) -> QLabel:
    """Titre de section souligné d'un trait d'encre."""
    widget = eyebrow(text, color=theme.INK_SOFT)
    widget.setObjectName("sectionTitle")
    return widget


# Surfaces


def soft_shadow(widget: QWidget, blur: int = 36, dy: int = 14, alpha: int = 26) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, dy)
    effect.setColor(QColor(70, 90, 40, alpha))
    widget.setGraphicsEffect(effect)


class ClickableFrame(QFrame):
    """Cadre cliquable (tuile, ligne de liste), survol géré par la feuille de style."""

    clicked = Signal()

    def __init__(self, object_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Space,
        ):
            self.clicked.emit()
            return
        super().keyPressEvent(event)


class Picture(QWidget):
    """Image à largeur maximale, hauteur proportionnelle, lissée."""

    def __init__(self, path: Path, max_width: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap = QPixmap(str(path))
        self._max_width = max_width
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def _ratio(self) -> float:
        if self._pixmap.isNull() or self._pixmap.width() == 0:
            return 1.0
        return self._pixmap.height() / self._pixmap.width()

    def sizeHint(self) -> QSize:
        return QSize(self._max_width, int(self._max_width * self._ratio()))

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return int(min(width, self._max_width) * self._ratio())

    def paintEvent(self, event: QPaintEvent) -> None:
        if self._pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        width = min(self.width(), self._max_width)
        height = int(width * self._ratio())
        x = (self.width() - width) / 2
        painter.drawPixmap(QRectF(x, 0, width, height), self._pixmap, QRectF(self._pixmap.rect()))


class WashedPage(QWidget):
    """Fond crème de page avec le lavis aquarelle en haut à droite."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page")
        self._wash = QPixmap(str(theme.IMAGES / "lavis.png"))

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), theme.color(theme.CREAM))
        if not self._wash.isNull():
            painter.setOpacity(0.4)
            painter.drawPixmap(self.width() - self._wash.width() + 140, 60, self._wash)


class ThreadDivider(QWidget):
    """Fil horizontal qui fait une boucle et se termine par un point rouge."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(40)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, mid = float(self.width()), self.height() / 2
        end = w - 10
        path = QPainterPath(QPointF(0, mid))
        path.cubicTo(w * 0.3, mid - 6, w * 0.55, mid + 6, end - 70, mid)
        path.cubicTo(end - 30, mid - 2, end - 34, mid - 18, end - 50, mid - 12)
        path.cubicTo(end - 64, mid - 6, end - 44, mid + 10, end - 8, mid)
        pen = QPen(theme.color(theme.THREAD), 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPath(path)
        paint_dot(painter, QPointF(end, mid), 10, filled=True)
