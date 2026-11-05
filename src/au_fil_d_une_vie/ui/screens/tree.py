"""Écran « Mon arbre » : l'accueil, point de départ de toutes les sections.

Planche d'herbier : l'aquarelle de l'arbre (image du logo) en fond, et par-dessus,
dessinés à l'encre, le sol, les racines portant le nom des proches, les fils et les
étiquettes numérotées qui ouvrent chaque section.

Tout est placé dans une scène de taille fixe (`SCENE`), mise à l'échelle de la
fenêtre. Le dessin est isolé ici : remplacer l'image par un arbre généré ne
toucherait à rien d'autre.
"""

import math
import random
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
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
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
TRUNK = QPointF(850, 586)  # pied du tronc, sur la ligne de sol
GROUND_Y = 588
MAX_ROOTS = 6
SEED = 1904  # même tracé d'encre à chaque lancement


def _ink_line(start: QPointF, end: QPointF, rng: random.Random, wobble: float) -> list[QPointF]:
    """Points d'un trait d'encre légèrement tremblé entre deux points."""
    steps = max(2, int(math.dist((start.x(), start.y()), (end.x(), end.y())) / 14))
    points = []
    for i in range(steps + 1):
        t = i / steps
        jitter = 0 if i in (0, steps) else rng.uniform(-wobble, wobble)
        normal = QPointF(-(end.y() - start.y()), end.x() - start.x())
        length = math.hypot(normal.x(), normal.y()) or 1
        points.append(start + (end - start) * t + normal * (jitter / length))
    return points


def ink_polygon(corners: list[QPointF], seed: int, wobble: float = 0.7) -> QPainterPath:
    """Contour fermé au trait tremblé, comme tracé à la plume."""
    rng = random.Random(seed)
    path = QPainterPath(corners[0])
    for start, end in zip(corners, corners[1:] + corners[:1], strict=True):
        for point in _ink_line(start, end, rng, wobble)[1:]:
            path.lineTo(point)
    path.closeSubpath()
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


class HerbariumTag(QGraphicsObject):
    """Étiquette numérotée, coins supérieurs coupés, œillet percé.

    Elle se balance autour de son œillet au survol et au focus clavier, et
    s'active au clic, avec Entrée ou Espace.
    """

    activated = Signal(int)

    WIDTH = 252.0
    HEIGHT = 148.0
    CUT = 22.0
    EYELET_Y = 20.0
    SHADOW = QPointF(5, 6)

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
        self._swing.setDuration(900)
        self._swing.setEasingCurve(QEasingCurve.Type.OutSine)
        a = spec.angle
        for step, value in ((0.0, a), (0.25, a + 4), (0.5, a - 3), (0.75, a + 1.5), (1.0, a)):
            self._swing.setKeyValueAt(step, value)
        self._outline = ink_polygon(self._corners(), seed=SEED + spec.number)
        self._title_font = self._fitted_title_font(spec.title)

    def _fitted_title_font(self, title: str) -> QFont:
        """Titre manuscrit le plus grand possible (48 px au plus) qui tient sur une ligne."""
        available = self.WIDTH - 40
        for px in range(48, 31, -2):
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

    def _corners(self) -> list[QPointF]:
        w, h, c = self.WIDTH, self.HEIGHT, self.CUT
        left, top = -w / 2, -self.EYELET_Y
        return [
            QPointF(left + c, top),
            QPointF(left + w - c, top),
            QPointF(left + w, top + c),
            QPointF(left + w, top + h),
            QPointF(left, top + h),
            QPointF(left, top + c),
        ]

    def boundingRect(self) -> QRectF:
        w, h = self.WIDTH, self.HEIGHT
        return QRectF(-w / 2 - 4, -self.EYELET_Y - 4, w + 16, h + 16)

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
        painter.setBrush(theme.color(theme.WASH))
        painter.drawPath(self._outline.translated(self.SHADOW))
        # Corps de l'étiquette, bord d'encre.
        ink = theme.color(theme.RED_SHADOW if red else theme.INK_SOFT)
        painter.setBrush(theme.color(theme.RED if red else theme.PAPER))
        painter.setPen(QPen(ink, 1.5))
        painter.drawPath(self._outline)
        if red:  # couture pointillée blanche
            seam = QPen(theme.color(theme.ON_RED), 1.2, Qt.PenStyle.DashLine)
            painter.setPen(seam)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            w, h = self.WIDTH - 16, self.HEIGHT - 16
            painter.drawPath(
                ink_polygon(
                    [
                        QPointF(-w / 2 + self.CUT - 4, -self.EYELET_Y + 8),
                        QPointF(w / 2 - self.CUT + 4, -self.EYELET_Y + 8),
                        QPointF(w / 2, -self.EYELET_Y + self.CUT + 4),
                        QPointF(w / 2, -self.EYELET_Y + 8 + h),
                        QPointF(-w / 2, -self.EYELET_Y + 8 + h),
                        QPointF(-w / 2, -self.EYELET_Y + self.CUT + 4),
                    ],
                    seed=SEED,
                    wobble=0.4,
                )
            )
        # Œillet percé (le fil passe dedans).
        painter.setPen(QPen(ink, 1.4))
        painter.setBrush(theme.color(theme.CREAM))
        painter.drawEllipse(QPointF(0, 0), 5.5, 5.5)

        text = theme.color(theme.ON_RED if red else theme.INK_SOFT)
        soft = theme.color(theme.ON_RED if red else theme.MUTED)
        left = -self.WIDTH / 2 + 22
        painter.setPen(soft)
        painter.setFont(theme.font(theme.SANS, 12, QFont.Weight.Medium, spacing_em=0.18))
        painter.drawText(QPointF(left, 30), _("N° {number}").format(number=self.spec.number))
        if red:
            mic = icon_pixmap("mic", 18, theme.ON_RED)
            painter.drawPixmap(QPointF(self.WIDTH / 2 - 40, 16), mic)
        painter.setPen(text)
        painter.setFont(self._title_font)
        painter.drawText(
            QRectF(left - 4, 30, self.WIDTH - 36, 60),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.spec.title,
        )
        painter.setPen(soft)
        painter.setFont(theme.font(theme.SERIF, 15, italic=True))
        painter.drawText(
            QRectF(left, 92, self.WIDTH - 40, 30),
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

    def __init__(self, center: QPointF, diameter: float = 12) -> None:
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


def string_path(anchor: QPointF, eyelet: QPointF) -> QPainterPath:
    """Fil qui pend du nœud à l'œillet, avec un léger affaissement."""
    middle = (anchor + eyelet) / 2 + QPointF(0, 10)
    path = QPainterPath(anchor)
    path.quadTo(middle, eyelet)
    return path


# Sol et racines


class Ground(QGraphicsItem):
    """Ligne de sol à l'encre, avec ses petites hachures."""

    def __init__(self, left: float, right: float, y: float) -> None:
        super().__init__()
        self._left, self._right, self._y = left, right, y
        rng = random.Random(SEED)
        self._line = QPainterPath()
        points = _ink_line(QPointF(left, y), QPointF(right, y), rng, 1.2)
        self._line.moveTo(points[0])
        for point in points[1:]:
            self._line.lineTo(point)
        self._hatches = [
            (x, rng.uniform(4, 9), rng.uniform(-0.5, -0.2))
            for x in (left + 10 + i * rng.uniform(18, 30) for i in range(40))
            if x < right - 10
        ]

    def boundingRect(self) -> QRectF:
        return QRectF(self._left - 4, self._y - 6, self._right - self._left + 8, 22)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(theme.color(theme.INK_SOFT), 1.6))
        painter.drawPath(self._line)
        painter.setPen(QPen(theme.color(theme.INK_SOFT), 1.0))
        for x, length, slope in self._hatches:
            painter.drawLine(
                QPointF(x, self._y + 3), QPointF(x + length * slope, self._y + 3 + length)
            )


class Root(QGraphicsObject):
    """Racine à l'encre portant, à son extrémité, le nom d'un proche et ses récits."""

    activated = Signal(int)

    def __init__(
        self, person_id: int, name: str, story_count: int, end: QPointF, index: int
    ) -> None:
        super().__init__()
        self.person_id = person_id
        self._name = name
        self._count = story_count
        self._hover = False
        rng = random.Random(SEED + 100 + index)
        bend = rng.uniform(0.25, 0.45)
        direction = 1 if end.x() >= TRUNK.x() else -1
        c1 = QPointF(TRUNK.x() + direction * 10, TRUNK.y() + (end.y() - TRUNK.y()) * 0.7)
        c2 = QPointF(end.x() - (end.x() - TRUNK.x()) * bend, end.y() - 6)
        self._path = QPainterPath(QPointF(TRUNK.x() + direction * 6, TRUNK.y()))
        self._path.cubicTo(c1, c2, end)
        self._end = end
        self._direction = direction
        self._font = theme.font(theme.SCRIPT, 40)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable)
        self.setToolTip(_("Voir les récits de {name}").format(name=name))

    def name(self) -> str:
        return self._name

    def _label_rect(self) -> QRectF:
        width = 260.0
        x = self._end.x() + 10 if self._direction > 0 else self._end.x() - 10 - width
        return QRectF(x, self._end.y() - 34, width, 70)

    def boundingRect(self) -> QRectF:
        return self._path.boundingRect().adjusted(-6, -6, 6, 6).united(self._label_rect())

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
        ink = theme.color(theme.INK_SOFT)
        for width, alpha in ((3.2, 255), (1.4, 160)):
            pen = QPen(QColor(ink.red(), ink.green(), ink.blue(), alpha), width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(self._path)
        rect = self._label_rect()
        painter.setFont(self._font)
        painter.setPen(theme.color(theme.RED_TEXT if self._hover else theme.INK_SOFT))
        align = Qt.AlignmentFlag.AlignVCenter | (
            Qt.AlignmentFlag.AlignLeft if self._direction > 0 else Qt.AlignmentFlag.AlignRight
        )
        text_rect = QRectF(rect.x(), rect.y(), rect.width(), 46)
        painter.drawText(text_rect, align, self._name)
        # Un point par récit (cinq au plus), un point vide si aucun.
        dots = max(1, min(self._count, 5))
        width = painter.fontMetrics().horizontalAdvance(self._name)
        start = rect.x() + (0 if self._direction > 0 else rect.width() - width)
        for i in range(dots):
            center = QPointF(start + 6 + i * 16, rect.y() + 54)
            paint_dot(painter, center, 10, self._count > 0)

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
    """Extrémités des racines, réparties de part et d'autre du tronc, sous le sol."""
    slots = [
        QPointF(640, 668),
        QPointF(1060, 668),
        QPointF(470, 742),
        QPointF(1110, 742),
        QPointF(760, 776),
        QPointF(960, 790),
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
        self._scene.addItem(Ground(624, 1300, GROUND_Y))

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
        pen = QPen(theme.color(theme.THREAD), 2.2)
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
