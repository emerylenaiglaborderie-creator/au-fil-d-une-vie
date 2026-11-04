"""Écran « Au fil des mots » : le graphe des liens entre les récits."""

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QVBoxLayout, QWidget

from au_fil_d_une_vie.services.graph import GraphService, GraphView, StoryNode
from au_fil_d_une_vie.services.stories import StoryService
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.screens.story import RelatedThread
from au_fil_d_une_vie.ui.widgets import (
    eyebrow,
    label,
    link_button,
    paint_dot,
    section_title,
    soft_shadow,
)

BOARD = QSize(780, 580)
PLATE_WIDTH = 150
WORD_GREEN = "#CFE3A0"


def _curve(start: QPointF, end: QPointF, bend: float = 0.12) -> QPainterPath:
    """Fil légèrement courbé entre deux points (contrôle décalé sur la perpendiculaire)."""
    middle = (start + end) / 2
    dx, dy = end.x() - start.x(), end.y() - start.y()
    control = QPointF(middle.x() - dy * bend, middle.y() + dx * bend)
    path = QPainterPath(start)
    path.quadTo(control, end)
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
    """Plateau du graphe : arbre du logo en fond, fils, mots communs et récits."""

    story_selected = Signal(int)
    story_activated = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(BOARD)
        self.setMouseTracking(True)
        self.setAccessibleName("Graphe des liens entre les récits")
        self._view: GraphView | None = None
        self._selected: int | None = None
        self._show_words = True
        self._tree = QPixmap(str(theme.IMAGES / "arbre.png"))
        self._plate_font = theme.font(theme.SERIF, 15, italic=True)
        self._plate_font_bold = theme.font(theme.SERIF, 15, QFont.Weight.Medium, italic=True)
        self._person_font = theme.font(theme.SANS, 13)
        self._word_font = theme.font(theme.SANS, 14)
        self._word_centers: dict[int, QPointF] = {}

    def set_view(self, view: GraphView, selected: int | None) -> None:
        self._view = view
        self._selected = selected
        self._word_centers = self._place_words()
        self.update()

    def _word_rect(self, label_text: str, center: QPointF) -> QRectF:
        width = QFontMetrics(self._word_font).horizontalAdvance(label_text) + 24
        return QRectF(center.x() - width / 2, center.y() - 14, width, 28)

    def _place_words(self) -> dict[int, QPointF]:
        """Écarte les étiquettes de mots des plaques, des points et des autres étiquettes.

        Quelques passes de répulsion simple : chaque étiquette qui chevauche un obstacle
        est poussée à l'opposé de celui-ci, sans sortir du plateau.
        """
        if self._view is None:
            return {}
        obstacles = [self._plate_rect(s).adjusted(-4, -4, 4, 4) for s in self._view.stories]
        obstacles += [
            QRectF(self._point(s.x, s.y) - QPointF(16, 16), QSize(32, 32))
            for s in self._view.stories
        ]
        centers = {w.keyword_id: self._point(w.x, w.y) for w in self._view.words}
        labels = {w.keyword_id: w.label for w in self._view.words}
        for _ in range(60):
            moved = False
            for keyword_id, center in centers.items():
                rect = self._word_rect(labels[keyword_id], center)
                others = [
                    self._word_rect(labels[k], c).adjusted(-4, -4, 4, 4)
                    for k, c in centers.items()
                    if k != keyword_id
                ]
                for obstacle in obstacles + others:
                    if not rect.intersects(obstacle):
                        continue
                    away = center - obstacle.center()
                    length = math.hypot(away.x(), away.y()) or 1.0
                    center = center + QPointF(away.x() / length * 6, away.y() / length * 6)
                    rect = self._word_rect(labels[keyword_id], center)
                    moved = True
                half = rect.width() / 2
                centers[keyword_id] = QPointF(
                    min(max(center.x(), half + 8), self.width() - half - 8),
                    min(max(center.y(), 22), self.height() - 22),
                )
            if not moved:
                break
        return centers

    def set_selected(self, story_id: int | None) -> None:
        self._selected = story_id
        self.update()

    def set_show_words(self, show: bool) -> None:
        self._show_words = show
        self.update()

    # Géométrie

    def _point(self, x: float, y: float) -> QPointF:
        return QPointF(x * self.width(), y * self.height())

    def _plate_rect(self, node: StoryNode) -> QRectF:
        center = self._point(node.x, node.y)
        height = self._plate_height(node)
        left = min(max(center.x() - PLATE_WIDTH / 2, 6), self.width() - PLATE_WIDTH - 6)
        return QRectF(left, center.y() + 16, PLATE_WIDTH, height)

    def _plate_height(self, node: StoryNode) -> float:
        metrics = QFontMetrics(self._plate_font_bold)
        lines = len(two_lines(node.question, metrics, PLATE_WIDTH - 16))
        return 8 + lines * metrics.lineSpacing() + QFontMetrics(self._person_font).lineSpacing()

    def node_at(self, position: QPointF) -> int | None:
        if self._view is None:
            return None
        for node in reversed(self._view.stories):
            center = self._point(node.x, node.y)
            near = math.dist((center.x(), center.y()), (position.x(), position.y())) <= 16
            if near or self._plate_rect(node).contains(position):
                return node.id
        return None

    # Souris

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        over = self.node_at(event.position()) is not None
        self.setCursor(Qt.CursorShape.PointingHandCursor if over else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
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
        frame = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(frame, 20, 20)
        painter.fillPath(clip, theme.color(theme.WHITE))
        painter.setClipPath(clip)
        if not self._tree.isNull():
            # Plus pâle que la maquette (0,5) : ses points rouges ressemblaient à des récits.
            painter.setOpacity(0.3)
            width = 560
            height = width * self._tree.height() / self._tree.width()
            painter.drawPixmap(
                QRectF((self.width() - width) / 2, 8, width, height),
                self._tree,
                QRectF(self._tree.rect()),
            )
            painter.setOpacity(1.0)
        if self._view is not None:
            if self._show_words:
                self._paint_word_threads(painter)
            else:
                self._paint_story_threads(painter)
            for node in self._view.stories:
                self._paint_story(painter, node)
            if self._show_words:
                for word in self._view.words:
                    center = self._word_centers.get(word.keyword_id, self._point(word.x, word.y))
                    self._paint_word(painter, word.label, center)
            self._paint_isolated_note(painter)
        painter.setClipping(False)
        painter.setPen(QPen(theme.color(theme.BORDER), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(frame, 20, 20)

    def _thread_pen(self, strong: bool, width: float = 2.0) -> QPen:
        color = QColor(theme.THREAD if strong else "#555555")
        if not strong:
            color.setAlphaF(0.6)
        pen = QPen(color, 2.8 if strong else width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        return pen

    def _paint_word_threads(self, painter: QPainter) -> None:
        assert self._view is not None
        words = {w.keyword_id: w for w in self._view.words}
        stories = {s.id: s for s in self._view.stories}
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for strong in (False, True):  # les fils du récit choisi par-dessus
            for story_id, keyword_id in self._view.word_edges:
                if (story_id == self._selected) != strong:
                    continue
                story, word = stories[story_id], words[keyword_id]
                painter.setPen(self._thread_pen(strong))
                painter.drawPath(_curve(self._point(story.x, story.y), self._point(word.x, word.y)))

    def _paint_story_threads(self, painter: QPainter) -> None:
        assert self._view is not None
        stories = {s.id: s for s in self._view.stories}
        heaviest = max((link.weight for link in self._view.story_links), default=1.0)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for link in self._view.story_links:
            strong = self._selected in (link.story_a, link.story_b)
            a, b = stories.get(link.story_a), stories.get(link.story_b)
            if a is None or b is None:
                continue
            painter.setPen(self._thread_pen(strong, 1.2 + 2.4 * link.weight / heaviest))
            painter.drawPath(_curve(self._point(a.x, a.y), self._point(b.x, b.y), 0.18))

    def _paint_story(self, painter: QPainter, node: StoryNode) -> None:
        center = self._point(node.x, node.y)
        selected = node.id == self._selected
        if selected:
            halo = QColor(theme.RED)
            halo.setAlphaF(0.2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(halo)
            painter.drawEllipse(center, 20, 20)
        paint_dot(painter, center, 26 if selected else 18, filled=node.linked)

        rect = self._plate_rect(node)
        plate = QColor(theme.WHITE)
        plate.setAlphaF(0.92)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(plate)
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(theme.color(theme.INK))
        painter.setFont(self._plate_font_bold if selected else self._plate_font)
        person_height = QFontMetrics(self._person_font).lineSpacing()
        text_rect = rect.adjusted(8, 4, -8, -person_height - 4)
        lines = two_lines(node.question, QFontMetrics(painter.font()), int(text_rect.width()))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter, "\n".join(lines))
        painter.setFont(self._person_font)
        painter.setPen(theme.color(theme.MUTED))
        painter.drawText(
            QRectF(rect.left(), rect.bottom() - person_height - 3, rect.width(), person_height),
            Qt.AlignmentFlag.AlignHCenter,
            node.person_name,
        )

    def _paint_word(self, painter: QPainter, text: str, center: QPointF) -> None:
        rect = self._word_rect(text, center)
        shadow = QColor(0, 0, 0, 46)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shadow)
        painter.drawPath(_leaf_path(rect.translated(0, 1)))
        painter.setBrush(theme.color(WORD_GREEN))
        painter.drawPath(_leaf_path(rect))
        painter.setFont(self._word_font)
        painter.setPen(theme.color(theme.LEAF_TEXT))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _paint_isolated_note(self, painter: QPainter) -> None:
        assert self._view is not None
        alone = [s for s in self._view.stories if not s.linked]
        if not alone:
            return
        lowest = max(alone, key=lambda s: s.y)
        rect = self._plate_rect(lowest)
        painter.setFont(theme.font(theme.SCRIPT, 30))
        painter.setPen(theme.color("#4A4A4A"))
        painter.drawText(
            QRectF(rect.left() - 20, rect.bottom() + 2, rect.width() + 40, 34),
            Qt.AlignmentFlag.AlignHCenter,
            "pas encore de lien",
        )


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
        titles.addWidget(eyebrow("Graphe des liens"))
        titles.addWidget(label("Au fil des mots", theme.SCRIPT, 96, color=theme.INK_SOFT))
        head.addLayout(titles)
        head.addStretch(1)
        self._words = QCheckBox("Afficher les mots communs")
        self._words.setFont(theme.font(theme.SANS, 15, QFont.Weight.Medium))
        self._words.setCursor(Qt.CursorShape.PointingHandCursor)
        self._words.setChecked(True)
        self._words.toggled.connect(self._toggle_words)
        head.addWidget(self._words, 0, Qt.AlignmentFlag.AlignBottom)
        root.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(40)
        board_box = QVBoxLayout()
        self._board = GraphBoard()
        soft_shadow(self._board)
        self._board.story_selected.connect(self.select)
        self._board.story_activated.connect(self.story_opened)
        board_box.addWidget(self._board)
        self._summary = label("", px=15, color=theme.MUTED)
        board_box.addWidget(self._summary)
        self._empty = label(
            "Le graphe apparaîtra quand tu auras recueilli et relié quelques récits.",
            theme.SERIF,
            19,
            color=theme.MUTED,
            italic=True,
            wrap=True,
        )
        board_box.addWidget(self._empty)
        board_box.addStretch(1)
        body.addLayout(board_box)

        aside = QVBoxLayout()
        aside.setSpacing(32)
        aside.setContentsMargins(0, 4, 0, 0)
        aside.addWidget(self._build_card())
        aside.addLayout(self._build_legend())
        aside.addStretch(1)
        aside_box = QWidget()
        aside_box.setLayout(aside)
        aside_box.setFixedWidth(380)
        body.addWidget(aside_box, 0, Qt.AlignmentFlag.AlignTop)
        body.addStretch(1)
        root.addLayout(body)
        root.addStretch(1)

    def _build_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("plainCard")
        soft_shadow(card)
        box = QVBoxLayout(card)
        box.setContentsMargins(26, 26, 26, 22)
        box.setSpacing(10)
        box.addWidget(eyebrow("Récit sélectionné"))
        self._card_question = label("", theme.SERIF, 26, QFont.Weight.Medium, wrap=True)
        box.addWidget(self._card_question)
        self._card_person = label("", theme.SCRIPT, 38, color=theme.RED_TEXT)
        box.addWidget(self._card_person)
        self._card_related = RelatedThread()
        self._card_related.opened.connect(self.story_opened)
        box.addWidget(self._card_related)
        self._card_alone = label(
            "Pas encore de mot en commun avec un autre récit.",
            theme.SERIF,
            16,
            color=theme.MUTED,
            italic=True,
            wrap=True,
        )
        box.addWidget(self._card_alone)
        self._open = link_button("Ouvrir la fiche")
        self._open.clicked.connect(self._open_selected)
        box.addWidget(self._open, 0, Qt.AlignmentFlag.AlignLeft)
        self._card = card
        return card

    def _build_legend(self) -> QVBoxLayout:
        legend = QVBoxLayout()
        legend.setSpacing(12)
        legend.addWidget(section_title("Légende"))
        for kind, text in (
            ("story", "Un récit"),
            ("alone", "Un récit sans lien pour l'instant"),
            ("word", "Un mot qu'on retrouve ailleurs"),
            ("thread", "Un fil entre un récit et un mot"),
        ):
            row = QHBoxLayout()
            row.setSpacing(14)
            row.addWidget(LegendMark(kind))
            row.addWidget(label(text, px=16), 1)
            legend.addLayout(row)
        return legend

    # Données

    def refresh(self) -> None:
        self._view = self._graph.build()
        known = {s.id for s in self._view.stories}
        if self._selected not in known:
            self._selected = self._view.busiest_story()
        self._board.set_view(self._view, self._selected)
        has_stories = bool(self._view.stories)
        self._board.setVisible(has_stories)
        self._card.setVisible(has_stories)
        self._empty.setVisible(not has_stories)
        linked = sum(1 for s in self._view.stories if s.linked)
        self._summary.setText(
            f"{len(self._view.stories)} récits, {linked} reliés par "
            f"{len(self._view.words)} mots communs. Double-clique sur un récit pour l'ouvrir."
            if has_stories
            else ""
        )
        self._fill_card()

    def select(self, story_id: int) -> None:
        self._selected = story_id
        self._board.set_selected(story_id)
        self._fill_card()

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
            painter.setBrush(theme.color(WORD_GREEN))
            painter.drawPath(_leaf_path(QRectF(0, 2, 28, 16), 12, 2))
        else:
            painter.setPen(QPen(theme.color(theme.THREAD), 2))
            painter.drawLine(QPointF(0, 10), QPointF(28, 10))
