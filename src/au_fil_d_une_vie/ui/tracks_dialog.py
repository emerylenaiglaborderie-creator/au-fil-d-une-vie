"""Fenêtre « Mes pistes » : créer, renommer, réordonner et supprimer pistes et questions."""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from au_fil_d_une_vie.i18n import _
from au_fil_d_une_vie.services.tracks import TrackError, TrackInfo, TrackService
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.leaves import SearchField
from au_fil_d_une_vie.ui.text import plural
from au_fil_d_une_vie.ui.widgets import (
    ClickableFrame,
    clear_layout,
    eyebrow,
    label,
    link_button,
    outline_button,
    section_title,
)


def _small_button(text: str, tooltip: str) -> QPushButton:
    button = outline_button(text)
    button.setFixedWidth(44)
    button.setToolTip(tooltip)
    button.setAccessibleName(tooltip)
    return button


class TracksDialog(QDialog):
    def __init__(self, service: TrackService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._selected: int | None = None
        self._editing_question: int | None = None
        self.setWindowTitle(_("Mes pistes"))
        self.setModal(True)
        self.setFixedSize(960, 760)
        self.setStyleSheet(f"QDialog {{ background: {theme.CREAM}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 28, 40, 28)
        root.setSpacing(10)
        root.addWidget(label(_("Mes pistes"), theme.SCRIPT, 56, color=theme.RED_TEXT))
        root.addWidget(
            label(
                _(
                    "Les pistes sont les thèmes de ta quête. Change-les comme tu veux : ajoute les "
                    "tiennes, renomme-les, écris tes propres questions."
                ),
                theme.SERIF,
                16,
                color=theme.MUTED,
                wrap=True,
            )
        )
        root.addSpacing(8)

        body = QHBoxLayout()
        body.setSpacing(32)

        left = QVBoxLayout()
        left.setSpacing(8)
        left.addWidget(section_title(_("Les pistes")))
        self._list = QVBoxLayout()
        self._list.setSpacing(0)
        list_box = QWidget()
        list_box.setLayout(self._list)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(list_box)
        area.setStyleSheet(
            f"QScrollArea {{ background: transparent; }} QWidget {{ background: {theme.CREAM}; }}"
        )
        left.addWidget(area, 1)
        new_row = QHBoxLayout()
        self._new_theme = SearchField(_("Nouvelle piste (Voyages, Sport...)"))
        self._new_theme.setClearButtonEnabled(False)
        self._new_theme.setFont(theme.font(theme.SERIF, 16, italic=True))
        self._new_theme.returnPressed.connect(self._add_theme)
        new_row.addWidget(self._new_theme, 1)
        add_theme = outline_button(_("Ajouter"))
        add_theme.clicked.connect(self._add_theme)
        new_row.addWidget(add_theme)
        left.addLayout(new_row)
        left_box = QWidget()
        left_box.setLayout(left)
        left_box.setFixedWidth(330)
        body.addWidget(left_box)

        right = QVBoxLayout()
        right.setSpacing(10)
        head = QHBoxLayout()
        head.setSpacing(8)
        self._theme_name = SearchField(_("Nom de la piste"))
        self._theme_name.setClearButtonEnabled(False)
        self._theme_name.setFont(theme.font(theme.SERIF, 22))
        self._theme_name.returnPressed.connect(self._rename_theme)
        head.addWidget(self._theme_name, 1)
        rename = outline_button(_("Renommer"))
        rename.clicked.connect(self._rename_theme)
        head.addWidget(rename)
        self._up = _small_button("↑", _("Monter la piste"))
        self._up.clicked.connect(lambda: self._move(-1))
        head.addWidget(self._up)
        self._down = _small_button("↓", _("Descendre la piste"))
        self._down.clicked.connect(lambda: self._move(1))
        head.addWidget(self._down)
        right.addLayout(head)
        self._theme_info = label("", px=14, color=theme.MUTED)
        right.addWidget(self._theme_info)
        right.addSpacing(6)
        right.addWidget(section_title(_("Ses questions")))
        self._questions = QVBoxLayout()
        self._questions.setSpacing(0)
        questions_box = QWidget()
        questions_box.setLayout(self._questions)
        q_area = QScrollArea()
        q_area.setWidgetResizable(True)
        q_area.setWidget(questions_box)
        q_area.setStyleSheet(
            f"QScrollArea {{ background: transparent; }} QWidget {{ background: {theme.CREAM}; }}"
        )
        right.addWidget(q_area, 1)
        q_row = QHBoxLayout()
        self._question = SearchField(_("Une nouvelle question à poser"))
        self._question.setClearButtonEnabled(False)
        self._question.setFont(theme.font(theme.SERIF, 16, italic=True))
        self._question.returnPressed.connect(self._submit_question)
        q_row.addWidget(self._question, 1)
        self._question_button = outline_button(_("Ajouter"))
        self._question_button.clicked.connect(self._submit_question)
        q_row.addWidget(self._question_button)
        right.addLayout(q_row)
        self._delete_theme = link_button(_("Supprimer cette piste"))
        self._delete_theme.setStyleSheet(f"color: {theme.RED_TEXT};")
        self._delete_theme.clicked.connect(self._remove_theme)
        right.addWidget(self._delete_theme, 0, Qt.AlignmentFlag.AlignLeft)
        body.addLayout(right, 1)
        root.addLayout(body, 1)

        bottom = QHBoxLayout()
        self._error = label("", px=14, color=theme.RED_TEXT, wrap=True)
        bottom.addWidget(self._error, 1)
        close = link_button(_("Fermer"))
        close.clicked.connect(self.accept)
        bottom.addWidget(close)
        root.addLayout(bottom)
        self.refresh()

    # Données

    def _tracks(self) -> list[TrackInfo]:
        return self._service.all()

    def refresh(self) -> None:
        tracks = self._tracks()
        ids = [t.theme.id for t in tracks]
        if self._selected not in ids:
            self._selected = ids[0] if ids else None
        clear_layout(self._list)
        for track in tracks:
            row = ClickableFrame("row")
            row.setMinimumHeight(56)
            cell = QVBoxLayout(row)
            cell.setContentsMargins(10, 8, 10, 8)
            cell.setSpacing(0)
            selected = track.theme.id == self._selected
            name = label(
                track.theme.label, theme.SERIF, 18, color=theme.RED_TEXT if selected else None
            )
            cell.addWidget(name)
            cell.addWidget(
                label(
                    plural(len(track.questions), _("question"), _("questions"))
                    + " · "
                    + (
                        plural(track.story_count, _("récit"), _("récits"))
                        if track.story_count
                        else _("aucun récit")
                    ),
                    px=13,
                    color=theme.MUTED,
                )
            )
            row.clicked.connect(lambda theme_id=track.theme.id: self._select(theme_id))
            self._list.addWidget(row)
        self._list.addStretch(1)
        self._fill_detail(next((t for t in tracks if t.theme.id == self._selected), None), ids)

    def _fill_detail(self, track: TrackInfo | None, ids: list[int]) -> None:
        clear_layout(self._questions)
        enabled = track is not None
        for widget in (self._theme_name, self._question, self._question_button, self._delete_theme):
            widget.setEnabled(enabled)
        if track is None:
            self._theme_name.clear()
            self._theme_info.setText(_("Crée une piste pour commencer."))
            self._up.setEnabled(False)
            self._down.setEnabled(False)
            return
        self._theme_name.setText(track.theme.label)
        position = ids.index(track.theme.id)
        self._up.setEnabled(position > 0)
        self._down.setEnabled(position < len(ids) - 1)
        self._theme_info.setText(
            _("Elle a des récits : on peut la renommer, pas la supprimer.")
            if track.story_count
            else _("Pas encore de récit dans cette piste.")
        )
        self._delete_theme.setVisible(track.story_count == 0)
        for info in track.questions:
            row = QWidget()
            line = QHBoxLayout(row)
            line.setContentsMargins(4, 8, 4, 8)
            line.setSpacing(14)
            line.addWidget(label(info.question.text, theme.SERIF, 17, wrap=True), 1)
            if info.story_count:
                line.addWidget(
                    eyebrow(plural(info.story_count, _("récit"), _("récits")), spacing_em=0.1)
                )
            edit = link_button(_("Modifier"))
            edit.clicked.connect(lambda _c=False, q=info.question: self._start_edit(q.id, q.text))
            line.addWidget(edit)
            if not info.story_count:
                remove = link_button(_("Supprimer"))
                remove.setStyleSheet(f"color: {theme.RED_TEXT};")
                remove.clicked.connect(
                    lambda _c=False, q=info.question: self._remove_question(q.id)
                )
                line.addWidget(remove)
            self._questions.addWidget(row)
        if not track.questions:
            self._questions.addWidget(
                label(_("Pas encore de question."), theme.SERIF, 16, color=theme.MUTED, italic=True)
            )
        self._questions.addStretch(1)

    # Actions

    def _run(self, action: Callable[[], object]) -> bool:
        """Exécute une modification ; affiche l'erreur métier s'il y en a une."""
        try:
            action()
        except TrackError as error:
            self._error.setText(str(error))
            return False
        self._error.setText("")
        return True

    def _select(self, theme_id: int) -> None:
        self._selected = theme_id
        self._reset_question()
        self.refresh()

    def _add_theme(self) -> None:
        created: list[int] = []
        if self._run(lambda: created.append(self._service.add_theme(self._new_theme.text()).id)):
            self._new_theme.clear()
            self._selected = created[0]
            self.refresh()

    def _rename_theme(self) -> None:
        if self._selected is not None and self._run(
            lambda: self._service.rename_theme(self._selected or 0, self._theme_name.text())
        ):
            self.refresh()

    def _move(self, step: int) -> None:
        if self._selected is not None:
            self._service.move_theme(self._selected, step)
            self.refresh()

    def _remove_theme(self) -> None:
        if self._selected is None:
            return
        if not self.confirm(_("Supprimer cette piste et ses questions ?")):
            return
        if self._run(lambda: self._service.delete_theme(self._selected or 0)):
            self._selected = None
            self.refresh()

    def _start_edit(self, question_id: int, text: str) -> None:
        self._editing_question = question_id
        self._question.setText(text)
        self._question_button.setText(_("Enregistrer"))
        self._question.setFocus()

    def _reset_question(self) -> None:
        self._editing_question = None
        self._question.clear()
        self._question_button.setText(_("Ajouter"))

    def _submit_question(self) -> None:
        if self._selected is None:
            return
        text = self._question.text()
        editing = self._editing_question
        if editing is None:
            ok = self._run(lambda: self._service.add_question(self._selected or 0, text))
        else:
            ok = self._run(lambda: self._service.edit_question(editing, text))
        if ok:
            self._reset_question()
            self.refresh()

    def _remove_question(self, question_id: int) -> None:
        if self._run(lambda: self._service.delete_question(question_id)):
            if self._editing_question == question_id:
                self._reset_question()
            self.refresh()

    def confirm(self, question: str) -> bool:
        """Demande une confirmation (remplacée dans les tests)."""
        answer = QMessageBox.question(self, "Au fil d'une vie", question)
        return answer == QMessageBox.StandardButton.Yes
