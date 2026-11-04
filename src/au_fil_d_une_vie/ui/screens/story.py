"""Écran « Fiche récit » : écoute, texte, correction, mots-clés, liens et carnet."""

from html import escape

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from au_fil_d_une_vie.models import StoryStatus
from au_fil_d_une_vie.services.stories import StoryDetail, StoryService, Tag, keyword_spans
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.leaves import FlowLayout, LeafChip, SearchField, UnderlineTab
from au_fil_d_une_vie.ui.player import AudioPlayer
from au_fil_d_une_vie.ui.text import duration, short_date
from au_fil_d_une_vie.ui.widgets import (
    ClickableFrame,
    PrimaryButton,
    ThreadDivider,
    clear_layout,
    eyebrow,
    label,
    link_button,
    outline_button,
    paint_dot,
    section_title,
    soft_shadow,
)

NOTE_SAVE_MS = 600


def highlighted_html(text: str, tags: list[Tag]) -> str:
    """Texte en paragraphes, mots-clés surlignés en vert « marqueur »."""
    spans = keyword_spans(text, tags)
    pieces: list[str] = []
    cursor = 0
    for start, end in spans:
        pieces.append(escape(text[cursor:start]))
        pieces.append(
            f'<span style="background-color:{theme.LEAF}">{escape(text[start:end])}</span>'
        )
        cursor = end
    pieces.append(escape(text[cursor:]))
    marked = "".join(pieces)
    paragraphs = [p.strip() for p in marked.replace("\r", "").split("\n") if p.strip()]
    return "".join(f'<p style="margin:0 0 20px 0; line-height:190%">{p}</p>' for p in paragraphs)


class RelatedThread(QWidget):
    """Liste « Voir aussi » posée sur un fil vertical, un point rouge par récit."""

    opened = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._box = QVBoxLayout(self)
        self._box.setContentsMargins(0, 4, 0, 0)
        self._box.setSpacing(0)

    def set_items(self, items: list[tuple[int, str, str]]) -> None:
        clear_layout(self._box)
        for story_id, title, subtitle in items:
            row = ClickableFrame("relatedRow")
            row.setMinimumHeight(68)
            cell = QVBoxLayout(row)
            cell.setContentsMargins(36, 10, 8, 10)
            cell.setSpacing(3)
            cell.addWidget(label(title, theme.SERIF, 19, wrap=True))
            cell.addWidget(label(subtitle, px=13, color=theme.LEAF_TEXT, wrap=True))
            row.clicked.connect(lambda story_id=story_id: self.opened.emit(story_id))
            self._box.addWidget(row)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        rows: list[QWidget] = []
        for i in range(self._box.count()):
            item = self._box.itemAt(i)
            widget = item.widget() if item is not None else None
            if widget is not None:
                rows.append(widget)
        if not rows:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tops = [r.y() + 22 for r in rows]
        if len(tops) > 1:
            painter.setPen(QPen(theme.color(theme.THREAD), 2))
            painter.drawLine(QPointF(9, tops[0]), QPointF(9, tops[-1]))
        for y in tops:
            paint_dot(painter, QPointF(9, y), 16, filled=True)


class StoryScreen(QWidget):
    back = Signal()
    story_opened = Signal(int)
    changed = Signal()
    deleted = Signal()

    def __init__(self, service: StoryService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._detail: StoryDetail | None = None
        self._editing = False
        self._editing_raw = False
        self._show_raw = False
        self._note_timer = QTimer(self)
        self._note_timer.setSingleShot(True)
        self._note_timer.setInterval(NOTE_SAVE_MS)
        self._note_timer.timeout.connect(self._save_note)

        root = QVBoxLayout(self)
        root.setContentsMargins(48, 20, 48, 28)
        root.setSpacing(24)

        back = QPushButton("←  Récits")
        back.setObjectName("mutedLink")
        back.setStyleSheet("text-decoration: none; padding: 0;")
        back.setMinimumHeight(44)
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.clicked.connect(self.back)
        root.addWidget(back, 0, Qt.AlignmentFlag.AlignLeft)

        head = QVBoxLayout()
        head.setSpacing(4)
        self._eyebrow = eyebrow("")
        head.addWidget(self._eyebrow)
        self._teller = label("", theme.SCRIPT, 54, color=theme.RED_TEXT)
        head.addWidget(self._teller)
        self._question = label("", theme.SERIF, 48, QFont.Weight.Medium, wrap=True)
        head.addWidget(self._question)
        root.addLayout(head)

        self._player = AudioPlayer()
        root.addWidget(self._player)

        body = QHBoxLayout()
        body.setSpacing(40)
        body.addLayout(self._build_text(), 1)
        aside = QWidget()
        aside.setFixedWidth(380)
        self._aside = QVBoxLayout(aside)
        self._aside.setContentsMargins(0, 4, 0, 0)
        self._aside.setSpacing(34)
        self._build_aside()
        body.addWidget(aside, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(body)
        root.addStretch(1)

    # Construction

    def _build_text(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(14)
        bar = QHBoxLayout()
        self._tabs = QButtonGroup(self)
        self._tab_book = UnderlineTab("Version livre")
        self._tab_raw = UnderlineTab("Transcription brute")
        self._tab_book.setChecked(True)
        for index, tab in enumerate((self._tab_book, self._tab_raw)):
            self._tabs.addButton(tab, index)
            bar.addWidget(tab)
        self._tabs.idClicked.connect(self._switch_tab)
        bar.addStretch(1)
        self._correct = link_button("Corriger le texte")
        self._correct.clicked.connect(self._start_editing)
        bar.addWidget(self._correct)
        column.addLayout(bar)

        article = QFrame()
        article.setObjectName("article")
        soft_shadow(article)
        box = QVBoxLayout(article)
        box.setContentsMargins(56, 44, 56, 28)
        box.setSpacing(12)
        self._text = QLabel()
        self._text.setTextFormat(Qt.TextFormat.RichText)
        self._text.setWordWrap(True)
        self._text.setFont(theme.font(theme.SERIF, 21))
        self._text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        box.addWidget(self._text)

        self._edit_hint = label(
            "",
            theme.SERIF,
            15,
            color=theme.MUTED,
            italic=True,
            wrap=True,
        )
        self._editor = QPlainTextEdit()
        self._editor.setObjectName("editor")
        self._editor.setFont(theme.font(theme.SERIF, 19))
        self._editor.setMinimumHeight(360)
        self._editor.setAccessibleName("Texte du récit à corriger")
        box.addWidget(self._edit_hint)
        box.addWidget(self._editor)
        self._edit_actions = QWidget()
        actions = QHBoxLayout(self._edit_actions)
        actions.setContentsMargins(0, 8, 0, 0)
        actions.setSpacing(24)
        save = PrimaryButton("Enregistrer la correction")
        save.clicked.connect(self._save_text)
        actions.addWidget(save)
        cancel = link_button("Annuler")
        cancel.clicked.connect(self._stop_editing)
        actions.addWidget(cancel)
        actions.addStretch(1)
        box.addWidget(self._edit_actions)
        box.addWidget(ThreadDivider())
        column.addWidget(article)
        column.addStretch(1)
        return column

    def _build_aside(self) -> None:
        words = QVBoxLayout()
        words.setSpacing(12)
        words.addWidget(section_title("Mots-clés"))
        self._tags_box = QWidget()
        self._tags = FlowLayout(self._tags_box)
        words.addWidget(self._tags_box)
        self._new_word = SearchField("Un mot à ajouter")
        self._new_word.setFont(theme.font(theme.SANS, 15))
        self._new_word.setClearButtonEnabled(False)
        self._new_word.returnPressed.connect(self._add_word)
        self._new_word.hide()
        words.addWidget(self._new_word)
        words.addWidget(
            label(
                "Une feuille pleine est un mot qu'on retrouve dans un autre récit.",
                theme.SERIF,
                14,
                color=theme.MUTED,
                italic=True,
                wrap=True,
            )
        )
        self._suggest_title = eyebrow("Mots proposés", color=theme.MUTED, spacing_em=0.14)
        words.addWidget(self._suggest_title)
        self._suggest_box = QWidget()
        self._suggest = FlowLayout(self._suggest_box)
        words.addWidget(self._suggest_box)
        self._suggest_hint = label(
            "Clique sur un mot pour le garder, sur × pour l'écarter.",
            px=13,
            color=theme.MUTED,
            wrap=True,
        )
        words.addWidget(self._suggest_hint)
        self._aside.addLayout(words)

        related = QVBoxLayout()
        related.setSpacing(10)
        related.addWidget(section_title("Voir aussi"))
        self._related = RelatedThread()
        self._related.opened.connect(self.story_opened)
        related.addWidget(self._related)
        self._no_related = label(
            "Pas encore de lien avec un autre récit.",
            theme.SERIF,
            16,
            color=theme.MUTED,
            italic=True,
        )
        related.addWidget(self._no_related)
        self._aside.addLayout(related)

        notebook = QVBoxLayout()
        notebook.setSpacing(10)
        notebook.addWidget(section_title("Mon carnet"))
        notebook.addWidget(
            label("Ce que j'en retiens", theme.SERIF, 17, color=theme.MUTED, italic=True)
        )
        self._note = QPlainTextEdit()
        self._note.setObjectName("notebook")
        self._note.setFont(theme.font(theme.SERIF, 17))
        self._note.setPlaceholderText(
            "Une phrase, un détail, une question pour la prochaine fois..."
        )
        self._note.setFixedHeight(130)
        self._note.setAccessibleName("Ce que j'en retiens")
        self._note.textChanged.connect(self._note_timer.start)
        notebook.addWidget(self._note)
        self._note_status = label("", px=13, color=theme.MUTED)
        notebook.addWidget(self._note_status)
        self._aside.addLayout(notebook)

        self._book = outline_button("Ajouter au livre de famille", large=True)
        self._book.clicked.connect(self._toggle_book)
        self._aside.addWidget(self._book)

        privacy = QHBoxLayout()
        privacy.setSpacing(20)
        self._hide = link_button("Masquer ce récit")
        self._hide.clicked.connect(self._toggle_hidden)
        privacy.addWidget(self._hide)
        delete = link_button("Supprimer")
        delete.setStyleSheet(f"color: {theme.RED_TEXT};")
        delete.clicked.connect(self._delete)
        privacy.addWidget(delete)
        privacy.addStretch(1)
        self._aside.addLayout(privacy)
        self._aside.addStretch(1)

    # Données

    @property
    def story_id(self) -> int | None:
        return self._detail.card.id if self._detail else None

    def open(self, story_id: int) -> None:
        self._flush_note()
        self._editing = False
        self._show_raw = False
        self._tab_book.setChecked(True)
        self._detail = self._service.detail(story_id)
        if self._detail is None:
            self.back.emit()
            return
        self._player.set_source(self._detail.audio_path, self._detail.card.duration_s)
        self._note.blockSignals(True)
        self._note.setPlainText(self._detail.note)
        self._note.blockSignals(False)
        self._note_status.setText("")
        self._render()

    def reload(self) -> None:
        """Recharge la fiche ouverte (après une transcription, une modification)."""
        if self._detail is None:
            return
        detail = self._service.detail(self._detail.card.id)
        if detail is None:
            self.back.emit()
            return
        self._detail = detail
        self._render()

    def leave(self) -> None:
        self._player.stop()
        self._flush_note()

    def _render(self) -> None:
        detail = self._detail
        if detail is None:
            return
        card = detail.card
        parts = (card.theme_label, short_date(card.recorded_at), duration(card.duration_s))
        self._eyebrow.setText(" · ".join(parts).upper())
        self._teller.setText(f"{card.person_name} raconte")
        self._question.setText(card.question)
        self._hide.setText("Ne plus masquer" if card.is_hidden else "Masquer ce récit")
        ready = card.status is StoryStatus.TRANSCRIBED and not card.is_hidden
        self._book.setEnabled(ready)
        self._book.setText(
            "Retirer du livre de famille" if card.in_book else "Ajouter au livre de famille"
        )
        self._book.setToolTip(
            "" if ready else "Un récit entre dans le livre quand son texte est prêt et visible."
        )
        self._render_text()
        self._render_tags()
        self._related.set_items(
            [
                (r.id, r.question, f"{r.person_name} · {', '.join(r.shared_labels)}")
                for r in detail.related
            ]
        )
        self._related.setVisible(bool(detail.related))
        self._no_related.setVisible(not detail.related)

    def _render_text(self) -> None:
        detail = self._detail
        if detail is None:
            return
        has_text = detail.raw_text is not None
        self._tab_raw.setEnabled(has_text and not self._editing)
        self._tab_book.setEnabled(not self._editing)
        self._correct.setText(
            "Corriger la transcription" if self._show_raw else "Corriger le texte"
        )
        self._correct.setVisible(has_text and not self._editing)
        self._editor.setVisible(self._editing)
        self._edit_actions.setVisible(self._editing)
        self._edit_hint.setVisible(self._editing)
        self._text.setVisible(not self._editing)
        if self._editing:
            return
        if not has_text:
            waiting = detail.card.status is StoryStatus.TRANSCRIBING
            self._text.setText(
                f'<p style="color:{theme.MUTED}"><i>'
                + (
                    "Le texte de ce récit est en préparation, sur cet ordinateur…"
                    if waiting
                    else "Le texte de ce récit n'est pas encore prêt. Il sera préparé dès que "
                    "le modèle de transcription sera installé."
                )
                + "</i></p>"
            )
            return
        text = detail.raw_text if self._show_raw else detail.text
        self._text.setText(highlighted_html(text or "", detail.tags))

    def _render_tags(self) -> None:
        detail = self._detail
        if detail is None:
            return
        clear_layout(self._tags)
        for tag in detail.tags:
            chip = LeafChip(tag.label, "filled" if tag.shared else "outline", closable=True)
            chip.closed.connect(lambda keyword_id=tag.keyword_id: self._remove_word(keyword_id))
            self._tags.addWidget(chip)
        add = LeafChip("+ ajouter", "add", clickable=True)
        add.clicked.connect(self._show_new_word)
        self._tags.addWidget(add)

        clear_layout(self._suggest)
        for tag in detail.suggestions:
            chip = LeafChip(tag.label, "proposed", closable=True, clickable=True)
            chip.setToolTip("Garder ce mot")
            chip.clicked.connect(lambda keyword_id=tag.keyword_id: self._keep_word(keyword_id))
            chip.closed.connect(lambda keyword_id=tag.keyword_id: self._remove_word(keyword_id))
            self._suggest.addWidget(chip)
        has_suggestions = bool(detail.suggestions)
        for widget in (self._suggest_title, self._suggest_box, self._suggest_hint):
            widget.setVisible(has_suggestions)
        self._tags_box.updateGeometry()
        self._suggest_box.updateGeometry()

    # Texte

    def _switch_tab(self, index: int) -> None:
        self._show_raw = index == 1
        self._render_text()

    def _start_editing(self) -> None:
        """Corrige le texte de l'onglet affiché : la transcription brute ou la version livre."""
        if self._detail is None or self._detail.raw_text is None:
            return
        self._editing = True
        self._editing_raw = self._show_raw
        if self._editing_raw:
            self._editor.setPlainText(self._detail.raw_text)
            self._edit_hint.setText(
                "Corrige ce qui a été mal compris : un mot mal entendu, un nom mal écrit. "
                "Tu peux réécouter le passage avec le lecteur au-dessus."
                + (
                    " La version livre, déjà corrigée, ne change pas."
                    if self._detail.book_text is not None
                    else ""
                )
            )
        else:
            self._editor.setPlainText(self._detail.text or "")
            self._edit_hint.setText(
                "Version pour le livre de famille : tu peux aussi reformuler. "
                "La transcription brute est gardée à côté."
            )
        self._render_text()
        self._editor.setFocus()

    def _stop_editing(self) -> None:
        self._editing = False
        self._render_text()

    def _save_text(self) -> None:
        if self._detail is None:
            return
        text = self._editor.toPlainText()
        if not text.strip():
            self._edit_hint.setText("Le texte ne peut pas être vide.")
            return
        if self._editing_raw:
            self._service.save_raw_text(self._detail.card.id, text)
        else:
            self._service.save_book_text(self._detail.card.id, text)
        self._editing = False
        self.reload()
        self.changed.emit()

    # Mots-clés

    def _show_new_word(self) -> None:
        self._new_word.show()
        self._new_word.setFocus()

    def _add_word(self) -> None:
        if self._detail is None or not self._new_word.text().strip():
            return
        self._service.add_keyword(self._detail.card.id, self._new_word.text())
        self._new_word.clear()
        self._new_word.hide()
        self.reload()
        self.changed.emit()

    def _keep_word(self, keyword_id: int) -> None:
        if self._detail is not None:
            self._service.validate_keyword(self._detail.card.id, keyword_id)
            self.reload()
            self.changed.emit()

    def _remove_word(self, keyword_id: int) -> None:
        if self._detail is not None:
            self._service.remove_keyword(self._detail.card.id, keyword_id)
            self.reload()
            self.changed.emit()

    # Carnet

    def _save_note(self) -> None:
        if self._detail is not None:
            self._service.save_note(self._detail.card.id, self._note.toPlainText())
            self._note_status.setText("Gardé dans ton carnet.")

    def _flush_note(self) -> None:
        if self._note_timer.isActive():
            self._note_timer.stop()
            self._save_note()

    # Confidentialité

    def _toggle_book(self) -> None:
        if self._detail is None:
            return
        self._service.set_in_book(self._detail.card.id, not self._detail.card.in_book)
        self.reload()
        self.changed.emit()

    def _toggle_hidden(self) -> None:
        if self._detail is None:
            return
        self._service.set_hidden(self._detail.card.id, not self._detail.card.is_hidden)
        self.reload()
        self.changed.emit()

    def _delete(self) -> None:
        if self._detail is None:
            return
        if not self.confirm(
            "Supprimer ce récit ? L'enregistrement, son texte, ses mots-clés et ta note "
            "seront effacés de cet ordinateur. Ce n'est pas réversible."
        ):
            return
        self._player.stop()
        self._note_timer.stop()
        self._service.delete(self._detail.card.id)
        self._detail = None
        self.deleted.emit()

    def confirm(self, question: str) -> bool:
        """Demande une confirmation (remplacée dans les tests)."""
        answer = QMessageBox.question(self, "Au fil d'une vie", question)
        return answer == QMessageBox.StandardButton.Yes
