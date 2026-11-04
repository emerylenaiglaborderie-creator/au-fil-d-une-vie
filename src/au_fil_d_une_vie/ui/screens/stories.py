"""Écran « Mes récits » : les récits sur un fil vertical, recherche et filtre par piste."""

from html import escape

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from au_fil_d_une_vie.i18n import _
from au_fil_d_une_vie.models import StoryStatus
from au_fil_d_une_vie.services.stories import StoryCard, StoryService
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.leaves import ElidedLabel, LeafChip, SearchField, UnderlineTab
from au_fil_d_une_vie.ui.text import duration, links_label, short_date
from au_fil_d_une_vie.ui.widgets import (
    ClickableFrame,
    Picture,
    PrimaryButton,
    clear_layout,
    eyebrow,
    label,
    paint_dot,
)

ROW_HEIGHT = 156
THREAD_X = 40.0
FIRST_DOT = 28.0
MAX_TAGS = 3


def status_text(card: StoryCard) -> str:
    if card.status is StoryStatus.TRANSCRIBING:
        return _("Le texte de ce récit est en préparation…")
    return _("Le texte de ce récit n'est pas encore prêt.")


class StoryEntry(ClickableFrame):
    """Une entrée du fil : question, métadonnées, extrait et mots-clés."""

    def __init__(self, card: StoryCard, parent: QWidget | None = None) -> None:
        super().__init__("storyRow", parent)
        self.card = card
        self.setFixedHeight(ROW_HEIGHT)
        self.setAccessibleName(f"{card.question}, {card.person_name}")
        dim = card.is_hidden

        box = QVBoxLayout(self)
        box.setContentsMargins(18, 14, 18, 0)
        box.setSpacing(5)

        head = QHBoxLayout()
        head.setSpacing(14)
        title = ElidedLabel(card.question)
        title.setFont(theme.font(theme.SERIF, 22, QFont.Weight.Medium))
        title.setStyleSheet(f"color: {theme.MUTED if dim else theme.INK};")
        head.addWidget(title, 1)
        head.addWidget(eyebrow(card.theme_label, spacing_em=0.12))
        box.addLayout(head)

        links = links_label(card.link_count)
        links_html = (
            f'<span style="color:{theme.RED_TEXT}; font-weight:500">{links}</span>'
            if card.link_count
            else links
        )
        parts = [card.person_name, short_date(card.recorded_at), duration(card.duration_s)]
        hidden = _(" · masqué") if dim else ""
        meta = QLabel(" · ".join(escape(p) for p in parts) + " · " + links_html + hidden)
        meta.setTextFormat(Qt.TextFormat.RichText)
        meta.setFont(theme.font(theme.SANS, 15))
        meta.setStyleSheet(f"color: {theme.MUTED};")
        box.addWidget(meta)

        text = f"« {card.excerpt} »" if card.excerpt else status_text(card)
        quote = label(text, theme.SERIF, 16, color=theme.QUOTE, italic=True, wrap=True)
        quote.setFixedHeight(46)
        quote.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        box.addWidget(quote)

        tags = QHBoxLayout()
        tags.setSpacing(6)
        for tag in card.tags[:MAX_TAGS]:
            tags.addWidget(LeafChip(tag.label, "filled" if tag.shared else "outline", small=True))
        if len(card.tags) > MAX_TAGS:
            tags.addWidget(label(f"+{len(card.tags) - MAX_TAGS}", px=13, color=theme.MUTED))
        tags.addStretch(1)
        box.addLayout(tags)
        box.addStretch(1)


class StoryThread(QWidget):
    """Les entrées, reliées par un fil qui boucle entre chaque point rouge."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows = QVBoxLayout(self)
        self._rows.setContentsMargins(124, 0, 0, 0)
        self._rows.setSpacing(0)
        self._count = 0

    def set_entries(self, entries: list[StoryEntry]) -> None:
        clear_layout(self._rows)
        for entry in entries:
            self._rows.addWidget(entry)
        self._count = len(entries)
        self.setMinimumHeight(self._count * ROW_HEIGHT)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        if self._count == 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        x = THREAD_X
        path = QPainterPath(QPointF(x, FIRST_DOT))
        for i in range(self._count - 1):
            y = FIRST_DOT + i * ROW_HEIGHT
            nxt = y + ROW_HEIGHT
            if i % 2 == 0:  # descente puis boucle vers la droite
                path.lineTo(x, y + 56)
                path.cubicTo(x + 120, y + 200, x + 120, y + 20, x, nxt)
            else:  # ondulation douce
                path.cubicTo(x + 40, y + 46, x - 40, y + 106, x, nxt)
        last = FIRST_DOT + (self._count - 1) * ROW_HEIGHT
        path.cubicTo(x + 10, last + 40, x - 10, last + 90, x + 4, last + 120)
        pen = QPen(theme.color(theme.THREAD), 2.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPath(path)
        for i in range(self._count):
            paint_dot(painter, QPointF(x, FIRST_DOT + i * ROW_HEIGHT), 18, filled=True)


class StoriesScreen(QWidget):
    story_opened = Signal(int)
    new_interview = Signal()

    def __init__(self, service: StoryService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._theme_id: int | None = None
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._fill_list)

        root = QHBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 28)
        root.setSpacing(56)

        main = QVBoxLayout()
        main.setSpacing(8)
        main.addWidget(eyebrow(_("Récits recueillis")))
        main.addWidget(label(_("Mes récits"), theme.SCRIPT, 104, color=theme.INK_SOFT))
        main.addWidget(
            label(
                _("Du plus récent au plus ancien, tout ce que ta famille t'a raconté."),
                theme.SERIF,
                18,
                color=theme.MUTED,
                italic=True,
            )
        )
        main.addSpacing(14)

        tools = QHBoxLayout()
        tools.setSpacing(24)
        self._search = SearchField(_("Un mot, une personne, un lieu"))
        self._search.setMinimumWidth(300)
        self._search.setMaximumWidth(340)
        self._search.textChanged.connect(lambda _text: self._search_timer.start())
        tools.addWidget(self._search, 1, Qt.AlignmentFlag.AlignBottom)
        tools.addStretch(1)
        self._tabs_box = QHBoxLayout()
        self._tabs_box.setSpacing(4)
        tools.addLayout(self._tabs_box)
        main.addLayout(tools)
        main.addSpacing(16)

        self._thread = StoryThread()
        main.addWidget(self._thread)
        self._empty = label("", theme.SERIF, 19, color=theme.MUTED, italic=True, wrap=True)
        self._empty.hide()
        main.addWidget(self._empty)
        main.addStretch(1)
        root.addLayout(main, 1)

        aside = QVBoxLayout()
        aside.setContentsMargins(0, 16, 0, 0)
        aside.setSpacing(32)
        new = PrimaryButton(_("Nouvelle interview"), icon="mic")
        new.setMinimumWidth(380)
        new.clicked.connect(self.new_interview)
        aside.addWidget(new)
        aside.addWidget(Picture(theme.logo_image(), 380))
        aside.addStretch(1)
        aside_box = QWidget()
        aside_box.setLayout(aside)
        aside_box.setFixedWidth(380)
        root.addWidget(aside_box, 0, Qt.AlignmentFlag.AlignTop)

        self._tabs = QButtonGroup(self)
        self._tabs.idClicked.connect(self._choose_theme)
        self.refresh()

    def set_theme(self, theme_id: int | None) -> None:
        self._theme_id = theme_id
        self.refresh()

    def refresh(self) -> None:
        self._fill_tabs()
        self._fill_list()

    def _fill_tabs(self) -> None:
        for button in self._tabs.buttons():
            self._tabs.removeButton(button)
        clear_layout(self._tabs_box)
        themes = self._service.themes_with_stories()
        if self._theme_id not in {tid for tid, _label in themes}:
            self._theme_id = None
        for theme_id, text in [(-1, _("Tous")), *themes]:
            tab = UnderlineTab(text)
            self._tabs.addButton(tab, theme_id)
            self._tabs_box.addWidget(tab)
            tab.setChecked(theme_id == (self._theme_id if self._theme_id is not None else -1))

    def _choose_theme(self, theme_id: int) -> None:
        self._theme_id = None if theme_id < 0 else theme_id
        self._fill_list()

    def _fill_list(self) -> None:
        cards = self._service.cards(self._search.text(), self._theme_id)
        entries = []
        for card in cards:
            entry = StoryEntry(card)
            entry.clicked.connect(lambda story_id=card.id: self.story_opened.emit(story_id))
            entries.append(entry)
        self._thread.set_entries(entries)
        self._thread.setVisible(bool(entries))
        if not entries:
            self._empty.setText(
                _("Aucun récit ne correspond à ta recherche.")
                if self._search.text().strip() or self._theme_id is not None
                else _("Pas encore de récit. Lance ta première interview : il apparaîtra ici.")
            )
        self._empty.setVisible(not entries)
