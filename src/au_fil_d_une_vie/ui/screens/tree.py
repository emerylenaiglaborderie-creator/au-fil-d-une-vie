"""Écran « Mon arbre » : l'accueil, point de départ de toutes les sections.

Planche d'herbier : l'aquarelle de l'arbre (image du logo) en fond, et par-dessus
une ombre de sol, des racines effilées portant le nom des proches, des fils souples
et les étiquettes numérotées qui ouvrent chaque section.

Tout est placé dans une scène de taille fixe (`SCENE`), mise à l'échelle de la
fenêtre. Le dessin est isolé ici : remplacer l'image par un arbre généré ne
toucherait à rien d'autre.
"""

import math
from dataclasses import dataclass

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFocusEvent,
    QFont,
    QFontMetricsF,
    QKeyEvent,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
    QGraphicsSimpleTextItem,
    QGraphicsTextItem,
    QGraphicsView,
    QSizePolicy,
    QStyleOptionGraphicsItem,
    QVBoxLayout,
    QWidget,
)

from au_fil_d_une_vie.i18n import _
from au_fil_d_une_vie.services.quest import PersonProgress, QuestService
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.text import plural
from au_fil_d_une_vie.ui.widgets import icon_pixmap, paint_dot

SCENE = QRectF(0, 0, 1360, 820)
TREE_IMAGE = "arbre-accueil.png"
TREE_RECT = QRectF(632, 22, 474, 632)  # l'image garde ses proportions dans ce cadre
TRUNK = QPointF(850, 590)  # pied du tronc
GROUND_Y = 592
MAX_ROOTS = 6


def with_alpha(color: QColor, alpha: int) -> QColor:
    result = QColor(color)
    result.setAlpha(alpha)
    return result


# Courbes


def bezier(p0: QPointF, c1: QPointF, c2: QPointF, p3: QPointF, t: float) -> QPointF:
    u = 1 - t
    return p0 * (u**3) + c1 * (3 * u * u * t) + c2 * (3 * u * t * t) + p3 * (t**3)


def tapered_stroke(
    p0: QPointF, c1: QPointF, c2: QPointF, p3: QPointF, start_width: float, end_width: float
) -> QPainterPath:
    """Trait plein qui s'affine le long d'une courbe, comme une racine ou un pinceau."""
    steps = 48
    left: list[QPointF] = []
    right: list[QPointF] = []
    for i in range(steps + 1):
        t = i / steps
        point = bezier(p0, c1, c2, p3, t)
        ahead = bezier(p0, c1, c2, p3, min(1.0, t + 0.01))
        behind = bezier(p0, c1, c2, p3, max(0.0, t - 0.01))
        dx, dy = ahead.x() - behind.x(), ahead.y() - behind.y()
        length = math.hypot(dx, dy) or 1.0
        normal = QPointF(-dy / length, dx / length)
        # Affinement rapide au départ puis plus lent : le profil d'une vraie racine.
        width = end_width + (start_width - end_width) * (1 - t) ** 1.6
        left.append(point + normal * (width / 2))
        right.append(point - normal * (width / 2))
    path = QPainterPath(left[0])
    for point in left[1:]:
        path.lineTo(point)
    tip = p3
    path.quadTo(tip, right[-1])
    for point in reversed(right[:-1]):
        path.lineTo(point)
    path.closeSubpath()
    return path


def string_path(anchor: QPointF, eyelet: QPointF) -> QPainterPath:
    """Fil souple qui pend du nœud à l'œillet : il s'affaisse selon sa longueur."""
    length = math.dist((anchor.x(), anchor.y()), (eyelet.x(), eyelet.y()))
    sag = QPointF(0, 0.16 * length)
    path = QPainterPath(anchor)
    path.cubicTo(
        anchor + (eyelet - anchor) * 0.3 + sag,
        eyelet - (eyelet - anchor) * 0.25 + sag * 0.6,
        eyelet,
    )
    return path


# Étiquettes d'herbier


@dataclass(frozen=True, slots=True)
class TagSpec:
    """Une étiquette de l'arbre : ce qu'elle ouvre, son texte, où elle pend."""

    section: int
    number: int
    title: str
    subtitle: str
    anchor: QPointF  # nœud sur le feuillage (point rouge)
    eyelet: QPointF  # œillet de l'étiquette, au bout du fil
    angle: float
    red: bool = False


def tag_outline(width: float, height: float, cut: float, top: float) -> QPainterPath:
    """Étiquette aux deux coins supérieurs coupés, angles légèrement adoucis."""
    left, right, bottom = -width / 2, width / 2, top + height
    r = 4.0
    path = QPainterPath(QPointF(left + cut, top))
    path.lineTo(right - cut, top)
    path.lineTo(right, top + cut)
    path.lineTo(right, bottom - r)
    path.quadTo(right, bottom, right - r, bottom)
    path.lineTo(left + r, bottom)
    path.quadTo(left, bottom, left, bottom - r)
    path.lineTo(left, top + cut)
    path.closeSubpath()
    return path


class HerbariumTag(QGraphicsObject):
    """Étiquette numérotée, coins supérieurs coupés, œillet cerclé.

    Elle se balance autour de son œillet au survol et au focus clavier, et
    s'active au clic, avec Entrée ou Espace.
    """

    activated = Signal(int)

    WIDTH = 252.0
    HEIGHT = 144.0
    CUT = 18.0
    EYELET_Y = 20.0
    SHADOW = QPointF(4, 5)

    def __init__(self, spec: TagSpec) -> None:
        super().__init__()
        self.spec = spec
        self._subtitle = spec.subtitle
        self._focused = False
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable)
        self.setToolTip(f"{spec.title} · {spec.subtitle}")
        # L'origine de l'étiquette est son œillet : elle pivote autour de lui.
        self.setPos(spec.eyelet)
        self.setRotation(spec.angle)
        self._swing = QPropertyAnimation(self, b"rotation", self)
        self._swing.setDuration(1100)
        self._swing.setEasingCurve(QEasingCurve.Type.InOutSine)
        a = spec.angle
        for step, value in ((0.0, a), (0.22, a + 3.5), (0.5, a - 2.5), (0.78, a + 1), (1.0, a)):
            self._swing.setKeyValueAt(step, value)
        self._outline = tag_outline(self.WIDTH, self.HEIGHT, self.CUT, -self.EYELET_Y)
        self._title_font = self._fitted_title_font(spec.title)

    def _fitted_title_font(self, title: str) -> QFont:
        """Titre manuscrit le plus grand possible (46 px au plus) qui tient sur une ligne."""
        available = self.WIDTH - 44
        for px in range(46, 31, -2):
            font = theme.font(theme.SCRIPT, px)
            if QFontMetricsF(font).horizontalAdvance(title) <= available:
                return font
        return theme.font(theme.SCRIPT, 32)

    def set_subtitle(self, text: str) -> None:
        self._subtitle = text
        self.setToolTip(f"{self.spec.title} · {text}")
        self.update()

    def subtitle(self) -> str:
        return self._subtitle

    def boundingRect(self) -> QRectF:
        return self._outline.boundingRect().adjusted(
            -3, -3, self.SHADOW.x() + 3, self.SHADOW.y() + 3
        )

    def shape(self) -> QPainterPath:
        return self._outline

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        red = self.spec.red
        # Ombre pleine décalée, lavis vert.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(with_alpha(theme.color(theme.WASH), 230))
        painter.drawPath(self._outline.translated(self.SHADOW))
        # Corps : papier et trait d'encre fin.
        ink = theme.color(theme.RED_SHADOW if red else theme.INK_SOFT)
        border = QPen(with_alpha(ink, 200), 1.2)
        border.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(border)
        painter.setBrush(theme.color(theme.RED if red else theme.PAPER))
        painter.drawPath(self._outline)
        if red:  # couture pointillée
            seam = QPen(with_alpha(theme.color(theme.ON_RED), 170), 1.0)
            seam.setDashPattern([3.0, 3.0])
            seam.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(seam)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            inset = tag_outline(self.WIDTH - 14, self.HEIGHT - 14, self.CUT - 3, -self.EYELET_Y + 7)
            painter.drawPath(inset)
        # Œillet : un anneau, le papier percé au centre.
        painter.setPen(QPen(with_alpha(ink, 210), 1.6))
        painter.setBrush(theme.color(theme.CREAM))
        painter.drawEllipse(QPointF(0, 0), 5.0, 5.0)

        text = theme.color(theme.ON_RED if red else theme.INK_SOFT)
        soft = with_alpha(theme.color(theme.ON_RED if red else theme.MUTED), 220)
        left = -self.WIDTH / 2 + 22
        painter.setPen(soft)
        painter.setFont(theme.font(theme.SANS, 11, QFont.Weight.Medium, spacing_em=0.12))
        painter.drawText(QPointF(left, 28), _("N° {number}").format(number=self.spec.number))
        if red:
            painter.drawPixmap(
                QPointF(self.WIDTH / 2 - 40, 14), icon_pixmap("mic", 16, theme.ON_RED)
            )
        painter.setPen(text)
        painter.setFont(self._title_font)
        painter.drawText(
            QRectF(left - 2, 30, self.WIDTH - 40, 56),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.spec.title,
        )
        painter.setPen(soft)
        painter.setFont(theme.font(theme.SERIF, 15, italic=True))
        painter.drawText(
            QRectF(left, 88, self.WIDTH - 40, 28),
            Qt.TextFlag.TextSingleLine,
            self._subtitle,
        )
        if self._focused:  # repère du focus clavier
            painter.setPen(QPen(theme.color(theme.RED), 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(self._outline)

    def swing(self) -> None:
        if self._swing.state() != QPropertyAnimation.State.Running:
            self._swing.start()

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.swing()
        super().hoverEnterEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()  # nécessaire pour recevoir le relâchement

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.shape().contains(event.pos()):
            self.activated.emit(self.spec.section)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activated.emit(self.spec.section)
        else:
            super().keyPressEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        self._focused = True
        self.swing()
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        self._focused = False
        self.update()
        super().focusOutEvent(event)


class Knot(QGraphicsItem):
    """Point rouge où le fil est noué sur le feuillage."""

    def __init__(self, center: QPointF, diameter: float = 10) -> None:
        super().__init__()
        self._d = diameter
        self.setPos(center)

    def boundingRect(self) -> QRectF:
        d = self._d
        return QRectF(-d, -d, 2 * d, 2 * d)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        paint_dot(painter, QPointF(0, 0), self._d, True)


# Sol et racines


class Ground(QGraphicsItem):
    """Sol suggéré : une ombre de lavis sous le tronc et un trait qui s'efface aux bords."""

    RX, RY = 330.0, 30.0

    def boundingRect(self) -> QRectF:
        return QRectF(TRUNK.x() - self.RX, GROUND_Y - self.RY, 2 * self.RX, 2 * self.RY)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        wash = theme.color(theme.WASH)
        shadow = QRadialGradient(QPointF(TRUNK.x(), GROUND_Y), self.RX)
        shadow.setColorAt(0.0, with_alpha(wash, 150))
        shadow.setColorAt(0.6, with_alpha(wash, 60))
        shadow.setColorAt(1.0, with_alpha(wash, 0))
        painter.save()
        painter.translate(TRUNK.x(), GROUND_Y)
        painter.scale(1.0, self.RY / self.RX)
        painter.translate(-TRUNK.x(), -GROUND_Y)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(shadow))
        painter.drawEllipse(QPointF(TRUNK.x(), GROUND_Y), self.RX, self.RX)
        painter.restore()
        line = QLinearGradient(TRUNK.x() - self.RX, 0, TRUNK.x() + self.RX, 0)
        ink = theme.color(theme.INK_SOFT)
        line.setColorAt(0.0, with_alpha(ink, 0))
        line.setColorAt(0.5, with_alpha(ink, 120))
        line.setColorAt(1.0, with_alpha(ink, 0))
        painter.setPen(QPen(QBrush(line), 1.1))
        painter.drawLine(
            QPointF(TRUNK.x() - self.RX, GROUND_Y), QPointF(TRUNK.x() + self.RX, GROUND_Y)
        )


class Root(QGraphicsObject):
    """Racine effilée portant, à son extrémité, le nom d'un proche et ses récits."""

    activated = Signal(int)

    def __init__(
        self, person_id: int, name: str, story_count: int, end: QPointF, index: int
    ) -> None:
        super().__init__()
        self.person_id = person_id
        self._name = name
        self._count = story_count
        self._hover = False
        self._end = end
        self._direction = 1 if end.x() >= TRUNK.x() else -1
        d = self._direction
        start = QPointF(TRUNK.x() + d * (3 + index % 3), TRUNK.y() - 2)
        drop = end.y() - start.y()
        # Elle plonge d'abord, puis s'étire vers l'extérieur en s'affinant.
        c1 = QPointF(start.x() + d * 8, start.y() + drop * 0.75)
        c2 = QPointF(end.x() - d * abs(end.x() - start.x()) * 0.55, end.y() + 4)
        self._stroke = tapered_stroke(start, c1, c2, end, 10 - index * 0.6, 1.8)
        # Une radicelle, qui part du premier tiers de la racine.
        fork = bezier(start, c1, c2, end, 0.42)
        tip = fork + QPointF(d * 36, 26 + (index % 2) * 10)
        self._rootlet = tapered_stroke(
            fork, fork + QPointF(d * 6, 12), tip - QPointF(d * 14, 2), tip, 3.0, 0.6
        )
        self._gradient_end = end
        self._start = start
        self._font = theme.font(theme.SCRIPT, 38)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable)
        self.setToolTip(_("Voir les récits de {name}").format(name=name))

    def name(self) -> str:
        return self._name

    def _label_rect(self) -> QRectF:
        width = 260.0
        x = self._end.x() + 12 if self._direction > 0 else self._end.x() - 12 - width
        return QRectF(x, self._end.y() - 30, width, 64)

    def boundingRect(self) -> QRectF:
        return (
            self._stroke.boundingRect()
            .united(self._rootlet.boundingRect())
            .united(self._label_rect())
            .adjusted(-4, -4, 4, 4)
        )

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addRect(self._label_rect())
        return path

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bark = theme.color(theme.BARK)
        fade = QLinearGradient(self._start, self._gradient_end)
        fade.setColorAt(0.0, with_alpha(bark, 240))
        fade.setColorAt(1.0, with_alpha(bark, 200))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(fade))
        painter.drawPath(self._stroke)
        painter.setBrush(with_alpha(bark, 150))
        painter.drawPath(self._rootlet)

        rect = self._label_rect()
        painter.setFont(self._font)
        painter.setPen(theme.color(theme.RED_TEXT if self._hover else theme.INK_SOFT))
        align = Qt.AlignmentFlag.AlignVCenter | (
            Qt.AlignmentFlag.AlignLeft if self._direction > 0 else Qt.AlignmentFlag.AlignRight
        )
        painter.drawText(QRectF(rect.x(), rect.y(), rect.width(), 44), align, self._name)
        # Un point par récit (cinq au plus), un point vide si aucun.
        dots = max(1, min(self._count, 5))
        width = painter.fontMetrics().horizontalAdvance(self._name)
        start = rect.x() + (0 if self._direction > 0 else rect.width() - width)
        for i in range(dots):
            paint_dot(painter, QPointF(start + 6 + i * 15, rect.y() + 52), 9, self._count > 0)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._hover = True
        self.update()

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._hover = False
        self.update()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.shape().contains(event.pos()):
            self.activated.emit(self.person_id)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activated.emit(self.person_id)
        else:
            super().keyPressEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        self._hover = True
        self.update()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        self._hover = False
        self.update()


def root_ends(count: int) -> list[QPointF]:
    """Extrémités des racines, en éventail de part et d'autre du tronc."""
    slots = [
        QPointF(700, 650),
        QPointF(1000, 650),
        QPointF(560, 724),
        QPointF(1130, 724),
        QPointF(770, 784),
        QPointF(940, 790),
    ]
    return slots[:count]


# Vue


class _FittedView(QGraphicsView):
    """Vue qui fait tenir la scène entière dans la place disponible."""

    def __init__(self, scene: QGraphicsScene) -> None:
        super().__init__(scene)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background: transparent;")
        self.viewport().setAutoFillBackground(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.fitInView(SCENE, Qt.AspectRatioMode.KeepAspectRatio)


class TreeScreen(QWidget):
    """Accueil : l'arbre et ses étiquettes, les racines et les proches."""

    INTERVIEW, TRACKS, STORIES, GRAPH, BOOK = range(5)

    section_requested = Signal(int)
    person_opened = Signal(int)
    manage_people = Signal()

    def __init__(self, service: QuestService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(560)

        self._scene = QGraphicsScene(SCENE, self)
        self._view = _FittedView(self._scene)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 8, 24, 8)
        layout.addWidget(self._view)

        self._build_static()
        self.tags: dict[int, HerbariumTag] = {}
        for spec in self._tag_specs():
            tag = HerbariumTag(spec)
            tag.activated.connect(self.section_requested)
            self._scene.addItem(tag)
            self.tags[spec.section] = tag
            # Le fil passe devant l'étiquette, jusque dans l'œillet.
            string = _StringItem(spec)
            string.setZValue(1)
            self._scene.addItem(string)
            knot = Knot(spec.anchor)
            knot.setZValue(2)
            self._scene.addItem(knot)
        self.roots: list[Root] = []
        self._roots_extra: QGraphicsSimpleTextItem | None = None
        self._add_person: _ClickableText | None = None
        self.refresh()

    def _build_static(self) -> None:
        pixmap = QPixmap(str(theme.IMAGES / TREE_IMAGE))
        if not pixmap.isNull():
            tree = QGraphicsPixmapItem(pixmap)
            tree.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            scale = min(TREE_RECT.width() / pixmap.width(), TREE_RECT.height() / pixmap.height())
            tree.setScale(scale)
            tree.setPos(TREE_RECT.topLeft())
            if theme.DARK_MODE:
                tree.setOpacity(0.85)
            self._scene.addItem(tree)
        ground = Ground()
        ground.setZValue(-1)  # sous l'arbre
        self._scene.addItem(ground)

        eyebrow = QGraphicsSimpleTextItem(_("Mon arbre").upper())
        eyebrow.setFont(theme.font(theme.SANS, 13, QFont.Weight.Medium, spacing_em=0.2))
        eyebrow.setBrush(QBrush(theme.color(theme.RED_TEXT)))
        eyebrow.setPos(56, 44)
        self._scene.addItem(eyebrow)
        self._hello = QGraphicsSimpleTextItem()
        self._hello.setFont(theme.font(theme.SCRIPT, 96))
        self._hello.setBrush(QBrush(theme.color(theme.INK_SOFT)))
        self._hello.setPos(48, 58)
        self._scene.addItem(self._hello)
        intro = QGraphicsTextItem(
            _(
                "Choisis une étiquette pour continuer ton enquête. "
                "Plus tu recueilles de récits, plus l'arbre grandit."
            )
        )
        intro.setFont(theme.font(theme.SERIF, 19, italic=True))
        intro.setDefaultTextColor(theme.color(theme.MUTED))
        intro.setTextWidth(420)
        intro.setPos(52, 186)
        self._scene.addItem(intro)

    def _tag_specs(self) -> list[TagSpec]:
        return [
            TagSpec(
                self.INTERVIEW,
                1,
                _("Interview"),
                "",
                anchor=QPointF(680, 228),
                eyelet=QPointF(560, 300),
                angle=-4,
                red=True,
            ),
            TagSpec(
                self.TRACKS,
                2,
                _("Les pistes"),
                "",
                anchor=QPointF(1040, 176),
                eyelet=QPointF(1172, 250),
                angle=3,
            ),
            TagSpec(
                self.STORIES,
                3,
                _("Mes récits"),
                "",
                anchor=QPointF(712, 446),
                eyelet=QPointF(484, 478),
                angle=2.5,
            ),
            TagSpec(
                self.GRAPH,
                4,
                _("Au fil des mots"),
                _("les liens entre tes récits"),
                anchor=QPointF(1036, 372),
                eyelet=QPointF(1186, 432),
                angle=-3,
            ),
            TagSpec(
                self.BOOK,
                5,
                _("Livre de famille"),
                _("le fruit de tes récits"),
                anchor=QPointF(936, 42),
                eyelet=QPointF(1182, 84),
                angle=-2,
            ),
        ]

    def refresh(self) -> None:
        overview = self._service.overview()
        name = overview.first_name
        self._hello.setText(_("Bonjour {name}").format(name=name) if name else _("Bonjour"))
        track = self._service.next_track()
        self.tags[self.INTERVIEW].set_subtitle(
            _("prochaine piste : {theme}").format(theme=track.theme.label)
            if track
            else _("pose une question à un proche")
        )
        self.tags[self.TRACKS].set_subtitle(
            _("{tracks} à explorer").format(tracks=plural(len(overview.themes), "thème", "thèmes"))
        )
        self.tags[self.STORIES].set_subtitle(
            _("{stories} recueillis").format(
                stories=plural(overview.story_count, "récit", "récits")
            )
            if overview.story_count
            else _("ton premier récit t'attend")
        )
        self._refresh_roots(overview.people)

    def _refresh_roots(self, people: list[PersonProgress]) -> None:
        for root in self.roots:
            self._scene.removeItem(root)
        self.roots = []
        for item in (self._roots_extra, self._add_person):
            if item is not None:
                self._scene.removeItem(item)
        self._roots_extra = self._add_person = None

        shown = people[:MAX_ROOTS]
        for index, (progress, end) in enumerate(zip(shown, root_ends(len(shown)), strict=True)):
            root = Root(
                progress.person.id,
                progress.person.display_name,
                progress.story_count,
                end,
                index,
            )
            root.activated.connect(self.person_opened)
            self._scene.addItem(root)
            self.roots.append(root)
        if len(people) > MAX_ROOTS:
            extra = QGraphicsSimpleTextItem(
                _("et {count} autres").format(count=len(people) - MAX_ROOTS)
            )
            extra.setFont(theme.font(theme.SERIF, 15, italic=True))
            extra.setBrush(QBrush(theme.color(theme.MUTED)))
            extra.setPos(TRUNK.x() + 30, GROUND_Y + 200)
            self._scene.addItem(extra)
            self._roots_extra = extra
        if not people:
            hint = _ClickableText(_("Ajoute un proche pour faire pousser les racines"))
            hint.setFont(theme.font(theme.SERIF, 17, italic=True))
            hint.setBrush(QBrush(theme.color(theme.RED_TEXT)))
            hint.setPos(TRUNK.x() - 200, GROUND_Y + 40)
            hint.activated.connect(self.manage_people)
            self._scene.addItem(hint)
            self._add_person = hint


class _StringItem(QGraphicsPathItem):
    """Fil gris entre le nœud et l'œillet d'une étiquette."""

    def __init__(self, spec: TagSpec) -> None:
        super().__init__(string_path(spec.anchor, spec.eyelet))
        pen = QPen(with_alpha(theme.color(theme.THREAD), 215), 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)


class _ClickableText(QGraphicsObject):
    """Texte cliquable de la scène (invitation à ajouter un proche)."""

    activated = Signal()

    def __init__(self, text: str) -> None:
        super().__init__()
        self._text = QGraphicsSimpleTextItem(text, self)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def setFont(self, font: QFont) -> None:  # noqa: N802 (même nom que Qt)
        self._text.setFont(font)

    def setBrush(self, brush: QBrush) -> None:  # noqa: N802
        self._text.setBrush(brush)

    def text(self) -> str:
        return self._text.text()

    def boundingRect(self) -> QRectF:
        return self._text.boundingRect()

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        pass

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.activated.emit()
