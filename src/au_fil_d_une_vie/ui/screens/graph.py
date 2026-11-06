"""Écran « Au fil des mots » : le graphe des liens entre les récits."""

import math

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from au_fil_d_une_vie.i18n import _
from au_fil_d_une_vie.services.graph import Arc, Density, GraphService, GraphView, StoryNode
from au_fil_d_une_vie.services.stories import StoryService
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.screens.story import RelatedThread
from au_fil_d_une_vie.ui.text import month_label, plural, short_date
from au_fil_d_une_vie.ui.widgets import (
    eyebrow,
    label,
    link_button,
    paint_dot,
    section_title,
    wash_shadow,
)

BOARD_HEIGHT = 470
MARGIN_X = 96  # place des titres du premier et du dernier récit, et de la fin du fil
THREAD_FROM_BOTTOM = 150  # sous le fil : titres, proches, repères de mois
TITLE_MAX_WIDTH = 160
WORD_LABELS_MAX = 5  # étiquettes de mots : les liens les plus forts du focus seulement
MIN_SPACING = 26  # écart minimal entre deux récits ; au-delà, le fil défile


def arc_path(start: QPointF, end: QPointF, height: float) -> QPainterPath:
    """Arc au-dessus du fil entre deux récits, presque en demi-cercle, de hauteur donnée."""
    span = end.x() - start.x()
    lift = height * 4 / 3  # contrôles d'une cubique dont le sommet atteint `height`
    path = QPainterPath(start)
    path.cubicTo(
        QPointF(start.x() + span * 0.04, start.y() - lift),
        QPointF(end.x() - span * 0.04, end.y() - lift),
        end,
    )
    return path


def _leaf_path(rect: QRectF, big: float = 14, small: float = 3) -> QPainterPath:
    """Rectangle aux coins « feuille » : deux arrondis, deux presque droits."""
    r = rect
    path = QPainterPath()
    path.moveTo(r.left() + big, r.top())
    path.lineTo(r.right() - small, r.top())
    path.quadTo(r.right(), r.top(), r.right(), r.top() + small)
    path.lineTo(r.right(), r.bottom() - big)
    path.quadTo(r.right(), r.bottom(), r.right() - big, r.bottom())
    path.lineTo(r.left() + small, r.bottom())
    path.quadTo(r.left(), r.bottom(), r.left(), r.bottom() - small)
    path.lineTo(r.left(), r.top() + big)
    path.quadTo(r.left(), r.top(), r.left() + big, r.top())
    return path


def two_lines(text: str, metrics: QFontMetrics, width: int) -> list[str]:
    """Coupe le texte en deux lignes au plus, sur des mots, avec « … » si besoin."""
    words = text.split()
    first = ""
    index = 0
    while index < len(words):
        candidate = f"{first} {words[index]}".strip()
        if first and metrics.horizontalAdvance(candidate) > width:
            break
        first = candidate
        index += 1
    if index >= len(words):
        return [first]
    rest = " ".join(words[index:])
    return [first, metrics.elidedText(rest, Qt.TextElideMode.ElideRight, width)]


class GraphBoard(QWidget):
    """Plateau du graphe : le fil, les récits en points rouges, les arcs et leurs mots.

    Focus : les arcs du récit sélectionné ou survolé passent à l'encre, les autres
    s'estompent. En palier compact, les titres n'apparaissent qu'au survol et seuls
    les liens forts sont tracés, sauf ceux du récit en focus.
    """

    story_selected = Signal(int)
    story_activated = Signal(int)
    reveal_requested = Signal(int)  # un récit hors de vue, à ramener à l'écran

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(BOARD_HEIGHT)
        self.setMinimumWidth(700)
        self._span = (0.0, float("inf"))  # partie visible quand le fil défile
        self._hints: list[tuple[QRectF, int]] = []  # étiquettes « liens hors de vue »
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self.setAccessibleName(_("Graphe des liens entre les récits"))
        self._view: GraphView | None = None
        self._selected: int | None = None
        self._hovered: int | None = None
        self._show_words = True
        self._title_font = theme.font(theme.SERIF, 14, italic=True)
        self._title_font_bold = theme.font(theme.SERIF, 14, QFont.Weight.Medium, italic=True)
        self._person_font = theme.font(theme.SANS, 12)
        self._word_font = theme.font(theme.SANS, 13)
        self._month_font = theme.font(theme.SANS, 11, QFont.Weight.Medium, spacing_em=0.14)

    def set_view(self, view: GraphView, selected: int | None) -> None:
        self._view = view
        self._selected = selected
        self.setMinimumWidth(max(700, self.needed_width()))
        self.update()

    def needed_width(self) -> int:
        """Largeur qu'il faut pour garder `MIN_SPACING` entre deux récits."""
        count = len(self._view.stories) if self._view else 0
        return int(2 * MARGIN_X + max(0, count - 1) * MIN_SPACING)

    def set_visible_span(self, left: float, right: float) -> None:
        """Partie du plateau affichée par la zone qui défile (pour les liens hors de vue)."""
        self._span = (left, right)
        self.update()

    def set_selected(self, story_id: int | None) -> None:
        self._selected = story_id
        self.update()

    def set_show_words(self, show: bool) -> None:
        self._show_words = show
        self.update()

    # Géométrie

    def _thread_y(self) -> float:
        return float(self.height() - THREAD_FROM_BOTTOM)

    def _x(self, position: float) -> float:
        return MARGIN_X + position * (self.width() - 2 * MARGIN_X)

    def dot_center(self, story_id: int) -> QPointF:
        """Centre du point d'un récit sur le fil."""
        assert self._view is not None
        node = self._view.story(story_id)
        assert node is not None
        return QPointF(self._x(node.position), self._thread_y())

    def _spacing(self) -> float:
        count = len(self._view.stories) if self._view else 1
        return (self.width() - 2 * MARGIN_X) / max(1, count - 1)

    def _title_width(self) -> int:
        return int(min(TITLE_MAX_WIDTH, max(70.0, self._spacing() - 10)))

    def _title_rect(self, node: StoryNode, width: int) -> QRectF:
        x = self._x(node.position)
        left = min(max(x - width / 2, 4), self.width() - width - 4)
        return QRectF(left, self._thread_y() + 20, width, 74)

    def _arc_height(self, arc: Arc) -> float:
        assert self._view is not None
        a, b = self._view.story(arc.story_a), self._view.story(arc.story_b)
        assert a is not None and b is not None
        span = self._x(b.position) - self._x(a.position)
        ceiling = self._thread_y() - 46  # les arcs restent sous le haut du plateau
        return min(ceiling, 26 + span * 0.42)

    def _focus(self) -> set[int]:
        return {sid for sid in (self._selected, self._hovered) if sid is not None}

    def node_at(self, position: QPointF) -> int | None:
        if self._view is None:
            return None
        full = self._view.density is Density.FULL
        for node in self._view.stories:
            center = QPointF(self._x(node.position), self._thread_y())
            if math.dist((center.x(), center.y()), (position.x(), position.y())) <= 15:
                return node.id
            if full and self._title_rect(node, self._title_width()).contains(position):
                return node.id
        return None

    # Souris

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        over = self.node_at(event.position())
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if over is not None else Qt.CursorShape.ArrowCursor
        )
        if over != self._hovered:
            self._hovered = over
            self.update()

    def leaveEvent(self, event: QEvent) -> None:
        if self._hovered is not None:
            self._hovered = None
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        for rect, target in self._hints:
            if rect.contains(event.position()):
                self.reveal_requested.emit(target)
                return
        story_id = self.node_at(event.position())
        if story_id is not None:
            self._selected = story_id
            self.update()
            self.story_selected.emit(story_id)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        story_id = self.node_at(event.position())
        if story_id is not None:
            self.story_activated.emit(story_id)

    # Dessin

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Le cadre d'encre est celui de la zone qui défile : ses bords restent visibles.
        painter.fillRect(self.rect(), theme.color(theme.PAPER))
        self._hints = []
        if self._view is None or not self._view.stories:
            return
        focus = self._focus()
        self._paint_months(painter)
        self._paint_thread(painter)
        labels = self._paint_arcs(painter, focus)
        for node in self._view.stories:
            self._paint_story(painter, node, focus)
        for rect, text in labels:
            self._paint_word(painter, rect, text)
        self._paint_offscreen_hints(painter)
        if self._view.density is Density.COMPACT:
            for story_id in (self._selected, self._hovered):
                focused = self._view.story(story_id) if story_id is not None else None
                if focused is not None:
                    self._paint_plate(painter, focused)

    def _paint_thread(self, painter: QPainter) -> None:
        """Le fil : un trait d'encre fin, terminé par une petite boucle et un point rouge."""
        y = self._thread_y()
        left, right = MARGIN_X - 40, self.width() - 30.0
        thread = QPainterPath(QPointF(left, y))
        thread.lineTo(right - 18, y)
        thread.cubicTo(
            QPointF(right + 2, y - 2), QPointF(right - 2, y - 16), QPointF(right - 10, y - 9)
        )
        thread.cubicTo(QPointF(right - 16, y - 3), QPointF(right - 6, y + 4), QPointF(right + 8, y))
        pen = QPen(theme.color(theme.THREAD), 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(thread)
        paint_dot(painter, QPointF(right + 12, y), 8, True)

    def _paint_arcs(self, painter: QPainter, focus: set[int]) -> list[tuple[QRectF, str]]:
        """Trace les arcs ; renvoie les étiquettes de mots à poser par-dessus."""
        assert self._view is not None
        arcs = self._view.visible_arcs(focus)
        heaviest = max((a.weight for a in self._view.arcs), default=1.0)
        full = self._view.density is Density.FULL
        labels: list[tuple[QRectF, str]] = []
        taken: list[QRectF] = []
        # Mots affichés : sur les liens les plus forts du focus (ou sur tous, sans focus).
        focused_arcs = [a for a in arcs if any(a.touches(f) for f in focus)]
        if not self._show_words:
            labelled: set[int] = set()
        elif focus:
            inside = [a for a in focused_arcs if self._within_span(a)]
            labelled = {id(a) for a in inside[:WORD_LABELS_MAX]}
        else:
            labelled = {id(a) for a in arcs} if full else set()
        # Hors focus, les arcs s'effacent d'autant plus que le fil est chargé.
        faded = 0.2 if full else 0.1
        resting = 0.45 if full else 0.28
        # Les arcs du focus par-dessus les autres.
        for arc in sorted(arcs, key=lambda a: (any(a.touches(f) for f in focus), a.weight)):
            focused = any(arc.touches(f) for f in focus)
            start = self.dot_center(arc.story_a)
            end = self.dot_center(arc.story_b)
            # Un lien du focus qui sort de la vue est résumé par l'étiquette de bord :
            # tracé léger et sans mots, pour ne pas former un faisceau sous le haut du plateau.
            leaving = focused and (start.x() < self._span[0] or end.x() > self._span[1])
            color = QColor(theme.THREAD if focused else theme.THREAD_SOFT)
            if leaving:
                color.setAlphaF(0.3)
            else:
                color.setAlphaF(0.95 if focused else (faded if focus else resting))
            strong_pen = focused and not leaving
            pen = QPen(color, (1.4 if strong_pen else 1.0) + 2.6 * arc.weight / heaviest)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            path = arc_path(start, end, self._arc_height(arc))
            painter.drawPath(path)
            if id(arc) in labelled and not leaving:
                text = self._words_text(arc)
                rect = self._word_rect(text, path.pointAtPercent(0.5))
                while any(rect.intersects(t) for t in taken) and rect.top() > 8:
                    rect.translate(0, -24)  # étiquettes empilées sans se chevaucher
                taken.append(rect.adjusted(-4, -2, 4, 2))
                labels.append((rect, text))
        return labels

    def _within_span(self, arc: Arc) -> bool:
        left, right = self._span
        return (
            self.dot_center(arc.story_a).x() >= left and self.dot_center(arc.story_b).x() <= right
        )

    def _paint_offscreen_hints(self, painter: QPainter) -> None:
        """Au bord de la vue : combien de liens du récit choisi mènent hors de l'écran."""
        if self._view is None or self._selected is None:
            return
        left, right = self._span
        if right == float("inf"):
            return
        before: list[tuple[float, int]] = []
        after: list[tuple[float, int]] = []
        for arc in self._view.arcs:
            if not arc.touches(self._selected):
                continue
            other = arc.story_b if arc.story_a == self._selected else arc.story_a
            x = self.dot_center(other).x()
            if x < left:
                before.append((left - x, other))
            elif x > right:
                after.append((x - right, other))
        painter.setFont(self._person_font)
        metrics = QFontMetrics(self._person_font)
        y = self._thread_y() - 40
        for side, links in (("left", before), ("right", after)):
            if not links:
                continue
            nearest = min(links)[1]
            count = plural(len(links), "lien", "liens")
            text = f"←  {count}" if side == "left" else f"{count}  →"
            width = metrics.horizontalAdvance(text) + 20
            x = left + 10 if side == "left" else right - 10 - width
            rect = QRectF(x, y, width, 24)
            painter.setPen(QPen(theme.color(theme.INK_SOFT), 1.0))
            painter.setBrush(theme.color(theme.PAPER))
            painter.drawRoundedRect(rect, 3, 3)
            painter.setPen(theme.color(theme.INK))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            self._hints.append((rect, nearest))

    @staticmethod
    def _words_text(arc: Arc) -> str:
        shown = arc.words[:2]
        more = len(arc.words) - len(shown)
        return " · ".join(shown) + (f" +{more}" if more else "")

    def _word_rect(self, text: str, center: QPointF) -> QRectF:
        width = QFontMetrics(self._word_font).horizontalAdvance(text) + 22
        left = min(max(center.x() - width / 2, 6), self.width() - width - 6)
        return QRectF(left, center.y() - 13, width, 26)

    def _paint_word(self, painter: QPainter, rect: QRectF, text: str) -> None:
        """Étiquette feuille du style herbier : ombre pleine décalée, bord fin."""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.color(theme.WASH))
        painter.drawPath(_leaf_path(rect.translated(3, 3), 12, 2))
        border = QColor(theme.LEAF_TEXT_SOFT)
        border.setAlphaF(0.55)
        painter.setPen(QPen(border, 1.0))
        painter.setBrush(theme.color(theme.WORD_GREEN))
        painter.drawPath(_leaf_path(rect, 12, 2))
        painter.setFont(self._word_font)
        painter.setPen(theme.color(theme.LEAF_TEXT))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _paint_story(self, painter: QPainter, node: StoryNode, focus: set[int]) -> None:
        center = QPointF(self._x(node.position), self._thread_y())
        selected = node.id == self._selected
        if selected:
            halo = QColor(theme.RED)
            halo.setAlphaF(0.18)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(halo)
            painter.drawEllipse(center, 19, 19)
        compact = self._view is not None and self._view.density is Density.COMPACT
        size = 24 if selected else (14 if compact else 18)
        paint_dot(painter, center, size, filled=node.linked)
        if compact:
            return
        width = self._title_width()
        rect = self._title_rect(node, width)
        painter.setFont(self._title_font_bold if selected else self._title_font)
        painter.setPen(theme.color(theme.INK if selected or not focus else theme.MUTED))
        lines = two_lines(node.question, QFontMetrics(painter.font()), width)
        painter.drawText(
            QRectF(rect.left(), rect.top(), rect.width(), 40),
            Qt.AlignmentFlag.AlignHCenter,
            "\n".join(lines),
        )
        painter.setFont(self._person_font)
        painter.setPen(theme.color(theme.MUTED))
        painter.drawText(
            QRectF(rect.left(), rect.top() + 42, rect.width(), 18),
            Qt.AlignmentFlag.AlignHCenter,
            node.person_name,
        )

    def _paint_plate(self, painter: QPainter, node: StoryNode) -> None:
        """Palier compact : le titre du récit en focus, sur une petite plaque de papier."""
        width = 230
        rect = self._title_rect(node, width).adjusted(0, -2, 0, -6)
        painter.setPen(QPen(theme.color(theme.INK_SOFT), 1.2))
        painter.setBrush(theme.color(theme.PAPER))
        painter.drawRoundedRect(rect, 3, 3)
        inner = rect.adjusted(10, 6, -10, -6)
        painter.setFont(self._title_font_bold)
        painter.setPen(theme.color(theme.INK))
        lines = two_lines(node.question, QFontMetrics(painter.font()), int(inner.width()))
        painter.drawText(inner, Qt.AlignmentFlag.AlignHCenter, "\n".join(lines))
        painter.setFont(self._person_font)
        painter.setPen(theme.color(theme.MUTED))
        painter.drawText(
            QRectF(inner.left(), inner.bottom() - 16, inner.width(), 16),
            Qt.AlignmentFlag.AlignHCenter,
            f"{node.person_name} · {short_date(node.recorded_at)}",
        )

    def _paint_months(self, painter: QPainter) -> None:
        """Repères de mois : un trait pointillé qui traverse le fil, le mois en dessous."""
        assert self._view is not None
        y = self._thread_y()
        half = self._spacing() / 2 if len(self._view.stories) > 1 else 0
        pen = QPen(theme.color(theme.DOTS), 1.0)
        pen.setDashPattern([2.0, 3.0])
        for index, mark in enumerate(self._view.months):
            x = self._x(mark.position) - (half if index else 0)
            if index:
                painter.setPen(pen)
                painter.drawLine(QPointF(x, y - 16), QPointF(x, self.height() - 34))
            painter.setFont(self._month_font)
            painter.setPen(theme.color(theme.LEAF_TEXT))
            painter.drawText(
                QRectF(x + (6 if index else -MARGIN_X + 20), self.height() - 30, 160, 18),
                Qt.AlignmentFlag.AlignLeft,
                month_label(mark.month).upper(),
            )


class ThreadOverview(QWidget):
    """Vue d'ensemble du fil, quand il défile : tout le fil en miniature, et un cadre
    qui montre la partie affichée. Un clic ou un glissé déplace la vue."""

    moved = Signal(float)  # centre demandé, en fraction de la longueur du fil

    HEIGHT = 44

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(_("Vue d'ensemble du fil"))
        self.setToolTip(_("Clique ou fais glisser pour te déplacer le long du fil."))
        self._view: GraphView | None = None
        self._selected: int | None = None
        self._window = (0.0, 1.0)

    def set_view(self, view: GraphView, selected: int | None) -> None:
        self._view, self._selected = view, selected
        self.update()

    def set_window(self, start: float, end: float) -> None:
        self._window = (start, end)
        self.update()

    def _x(self, fraction: float) -> float:
        return 8 + fraction * (self.width() - 16)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._move_to(event.position().x())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._move_to(event.position().x())

    def _move_to(self, x: float) -> None:
        self.moved.emit(min(1.0, max(0.0, (x - 8) / max(1.0, self.width() - 16))))

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._view is None or not self._view.stories:
            return
        y = self.height() - 12.0
        ink = QColor(theme.THREAD_SOFT)
        ink.setAlphaF(0.18)  # en miniature, les arcs ne sont qu'une trame légère
        painter.setPen(QPen(ink, 0.8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        positions = {s.id: s.position for s in self._view.stories}
        for arc in self._view.arcs:
            if not arc.strong:
                continue
            start = QPointF(self._x(positions[arc.story_a]), y)
            end = QPointF(self._x(positions[arc.story_b]), y)
            painter.drawPath(arc_path(start, end, min(20.0, (end.x() - start.x()) * 0.3)))
        painter.setPen(QPen(theme.color(theme.THREAD), 1.2))
        painter.drawLine(QPointF(4, y), QPointF(self.width() - 4, y))
        for story in self._view.stories:
            selected = story.id == self._selected
            paint_dot(painter, QPointF(self._x(story.position), y), 8 if selected else 4, True)
        shown_from, shown_to = self._window
        left, right = self._x(shown_from), self._x(shown_to)
        frame = QRectF(left, 2, max(10.0, right - left), y + 7)
        wash = QColor(theme.WASH)
        wash.setAlphaF(0.4)
        painter.setPen(QPen(theme.color(theme.INK_SOFT), 1.2))
        painter.setBrush(wash)
        painter.drawRoundedRect(frame, 3, 3)


class ThreadScroller(QScrollArea):
    """Zone qui défile horizontalement le long du fil ; la molette la fait défiler aussi."""

    def __init__(self, board: GraphBoard, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("boardFrame")
        self.setWidget(board)
        self.setWidgetResizable(True)  # le plateau occupe toute la largeur, au moins
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(BOARD_HEIGHT + 14)

    def wheelEvent(self, event: QWheelEvent) -> None:
        bar = self.horizontalScrollBar()
        if bar.maximum() == 0:  # rien à faire défiler : la page défile normalement
            event.ignore()
            return
        delta = event.angleDelta().y() or event.angleDelta().x()
        bar.setValue(bar.value() - delta)
        event.accept()


class GraphScreen(QWidget):
    story_opened = Signal(int)

    def __init__(
        self, graph: GraphService, stories: StoryService, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._graph = graph
        self._stories = stories
        self._view: GraphView | None = None
        self._selected: int | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(48, 36, 48, 28)
        root.setSpacing(28)

        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(4)
        titles.addWidget(eyebrow(_("Graphe des liens")))
        titles.addWidget(label(_("Au fil des mots"), theme.SCRIPT, 96, color=theme.INK_SOFT))
        head.addLayout(titles)
        head.addStretch(1)
        self._words = QCheckBox(_("Afficher les mots communs"))
        self._words.setFont(theme.font(theme.SANS, 15, QFont.Weight.Medium))
        self._words.setCursor(Qt.CursorShape.PointingHandCursor)
        self._words.setChecked(True)
        self._words.toggled.connect(self._toggle_words)
        head.addWidget(self._words, 0, Qt.AlignmentFlag.AlignBottom)
        root.addLayout(head)

        # Le fil prend toute la largeur ; la fiche du récit choisi et la légende dessous.
        self._overview = ThreadOverview()
        self._overview.hide()
        root.addWidget(self._overview)
        self._board = GraphBoard()
        self._board.story_selected.connect(self.select)
        self._board.story_activated.connect(self.story_opened)
        self._board.reveal_requested.connect(self.reveal)
        self._scroller = ThreadScroller(self._board)
        wash_shadow(self._scroller)
        bar = self._scroller.horizontalScrollBar()
        bar.valueChanged.connect(lambda _value: self._sync_overview())
        bar.rangeChanged.connect(lambda _low, _high: self._sync_overview())
        self._overview.moved.connect(self._scroll_to_fraction)
        root.addWidget(self._scroller)
        self._summary = label("", px=15, color=theme.MUTED)
        root.addWidget(self._summary)
        self._empty = label(
            _("Le graphe apparaîtra quand tu auras recueilli et relié quelques récits."),
            theme.SERIF,
            19,
            color=theme.MUTED,
            italic=True,
            wrap=True,
        )
        root.addWidget(self._empty)

        below = QHBoxLayout()
        below.setSpacing(48)
        card = self._build_card()
        card.setMaximumWidth(640)
        below.addWidget(card, 1, Qt.AlignmentFlag.AlignTop)
        legend_box = QWidget()
        legend_box.setLayout(self._build_legend())
        legend_box.setFixedWidth(380)
        below.addWidget(legend_box, 0, Qt.AlignmentFlag.AlignTop)
        below.addStretch(1)
        root.addLayout(below)
        root.addStretch(1)

    def _build_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("plainCard")
        wash_shadow(card)
        box = QVBoxLayout(card)
        box.setContentsMargins(26, 26, 26, 22)
        box.setSpacing(10)
        box.addWidget(eyebrow(_("Récit sélectionné")))
        self._card_question = label("", theme.SERIF, 26, QFont.Weight.Medium, wrap=True)
        box.addWidget(self._card_question)
        self._card_person = label("", theme.SCRIPT, 38, color=theme.RED_TEXT)
        box.addWidget(self._card_person)
        self._card_related = RelatedThread()
        self._card_related.opened.connect(self.story_opened)
        box.addWidget(self._card_related)
        self._card_alone = label(
            _("Pas encore de mot en commun avec un autre récit."),
            theme.SERIF,
            16,
            color=theme.MUTED,
            italic=True,
            wrap=True,
        )
        box.addWidget(self._card_alone)
        self._open = link_button(_("Ouvrir la fiche"))
        self._open.clicked.connect(self._open_selected)
        box.addWidget(self._open, 0, Qt.AlignmentFlag.AlignLeft)
        self._card = card
        return card

    def _build_legend(self) -> QVBoxLayout:
        legend = QVBoxLayout()
        legend.setSpacing(12)
        legend.addWidget(section_title(_("Légende")))
        for kind, text in (
            ("story", _("Un récit, dans l'ordre où tu l'as recueilli")),
            ("alone", _("Un récit sans lien pour l'instant")),
            ("thread", _("Un lien : plus il est épais, plus les mots sont rares")),
            ("word", _("Les mots que les deux récits partagent")),
        ):
            row = QHBoxLayout()
            row.setSpacing(14)
            row.addWidget(LegendMark(kind))
            row.addWidget(label(text, px=16, wrap=True), 1)
            legend.addLayout(row)
        return legend

    # Données

    def refresh(self) -> None:
        self._view = self._graph.build()
        known = {s.id for s in self._view.stories}
        if self._selected not in known:
            self._selected = self._view.busiest_story()
        self._board.set_view(self._view, self._selected)
        self._overview.set_view(self._view, self._selected)
        has_stories = bool(self._view.stories)
        self._scroller.setVisible(has_stories)
        if self._selected is not None:  # une fois la largeur du plateau connue
            selected = self._selected
            QTimer.singleShot(0, self, lambda: self._center_on(selected))
        self._card.setVisible(has_stories)
        self._empty.setVisible(not has_stories)
        linked = sum(1 for s in self._view.stories if s.linked)
        words = len({word for arc in self._view.arcs for word in arc.words})
        hint = (
            _("Passe sur un récit pour lire son titre et voir tous ses liens.")
            if self._view.density is Density.COMPACT
            else _("Double-clique sur un récit pour l'ouvrir.")
        )
        self._summary.setText(
            _("{stories} récits, {linked} reliés par {words} mots communs.").format(
                stories=len(self._view.stories), linked=linked, words=words
            )
            + " "
            + hint
            if has_stories
            else ""
        )
        self._fill_card()

    def select(self, story_id: int) -> None:
        self._selected = story_id
        self._board.set_selected(story_id)
        if self._view is not None:
            self._overview.set_view(self._view, story_id)
        self._fill_card()

    def reveal(self, story_id: int) -> None:
        """Un récit lié mais hors de vue : on le sélectionne et on le ramène au centre."""
        self.select(story_id)
        self._center_on(story_id)

    # Défilement du fil

    def _center_on(self, story_id: int | None) -> None:
        if story_id is None or self._view is None or self._view.story(story_id) is None:
            return
        bar = self._scroller.horizontalScrollBar()
        x = self._board.dot_center(story_id).x()
        bar.setValue(int(x - self._scroller.viewport().width() / 2))

    def _scroll_to_fraction(self, fraction: float) -> None:
        bar = self._scroller.horizontalScrollBar()
        center = fraction * self._board.width()
        bar.setValue(int(center - self._scroller.viewport().width() / 2))

    def _sync_overview(self) -> None:
        """La vue d'ensemble n'apparaît que si le fil défile ; elle suit la partie visible."""
        bar = self._scroller.horizontalScrollBar()
        width = max(1, self._board.width())
        visible = self._scroller.viewport().width()
        scrolling = bar.maximum() > 0
        self._overview.setVisible(scrolling and self._scroller.isVisible())
        self._overview.set_window(bar.value() / width, (bar.value() + visible) / width)
        self._board.set_visible_span(
            bar.value(), bar.value() + visible if scrolling else float("inf")
        )

    def _fill_card(self) -> None:
        if self._view is None or self._selected is None:
            return
        node = self._view.story(self._selected)
        detail = self._stories.detail(self._selected)
        if node is None or detail is None:
            return
        self._card_question.setText(node.question)
        self._card_person.setText(node.person_name)
        items = [(r.id, r.question, ", ".join(r.shared_labels)) for r in detail.related]
        self._card_related.set_items(items)
        self._card_related.setVisible(bool(items))
        self._card_alone.setVisible(not items)

    def _toggle_words(self, show: bool) -> None:
        self._board.set_show_words(show)

    def _open_selected(self) -> None:
        if self._selected is not None:
            self.story_opened.emit(self._selected)


class LegendMark(QWidget):
    """Petit symbole de la légende, dessiné comme dans le graphe."""

    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._kind = kind
        self.setFixedSize(30, 20)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._kind in ("story", "alone"):
            paint_dot(painter, QPointF(8, 9), 16, filled=self._kind == "story")
        elif self._kind == "word":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.color(theme.WORD_GREEN))
            painter.drawPath(_leaf_path(QRectF(0, 2, 28, 16), 12, 2))
        else:  # un petit arc, comme dans le graphe
            painter.setPen(QPen(theme.color(theme.THREAD), 2))
            painter.drawPath(arc_path(QPointF(2, 17), QPointF(26, 17), 12))
