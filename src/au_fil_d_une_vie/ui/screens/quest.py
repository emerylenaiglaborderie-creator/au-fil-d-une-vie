"""Écran « Ma quête » : accueil, prochaine piste, avancement des pistes et des personnes."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLayout,
    QVBoxLayout,
    QWidget,
)

from au_fil_d_une_vie.services.quest import QuestOverview, QuestService, Track
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.text import plural
from au_fil_d_une_vie.ui.widgets import (
    ClickableFrame,
    DotRow,
    LeafToggle,
    Picture,
    PrimaryButton,
    eyebrow,
    label,
    link_button,
    section_title,
    soft_shadow,
)


def _clear(layout: QLayout) -> None:
    """Vide un layout et détruit les widgets qu'il contenait."""
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            continue
        widget = item.widget()
        child = item.layout()
        if widget is not None:
            # Détaché tout de suite : sinon il reste affiché jusqu'à sa destruction.
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
        elif child is not None:
            _clear(child)


class QuestScreen(QWidget):
    interview_requested = Signal(int, int)  # question_id, person_id
    theme_opened = Signal(int)  # theme_id

    TILE_COLUMNS = 3

    def __init__(self, service: QuestService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._skipped: set[int] = set()
        self._track: Track | None = None
        self._people = QButtonGroup(self)
        self._people.setExclusive(True)

        root = QHBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 28)
        root.setSpacing(56)

        main = QVBoxLayout()
        main.setSpacing(10)
        main.addWidget(eyebrow("Ma quête"))
        self._hello = label("", theme.SCRIPT, 104, color=theme.INK_SOFT)
        main.addWidget(self._hello)
        self._intro = label("", theme.SERIF, 19, color=theme.MUTED, italic=True, wrap=True)
        self._intro.setMaximumWidth(620)
        main.addWidget(self._intro)
        main.addSpacing(18)

        self._card = QFrame()
        self._card.setObjectName("card")
        soft_shadow(self._card)
        self._card_layout = QVBoxLayout(self._card)
        self._card_layout.setContentsMargins(34, 32, 34, 30)
        self._card_layout.setSpacing(18)
        main.addWidget(self._card)

        main.addSpacing(34)
        main.addWidget(section_title("Les pistes à explorer"))
        main.addSpacing(6)
        self._tiles = QGridLayout()
        self._tiles.setSpacing(16)
        main.addLayout(self._tiles)
        main.addStretch(1)
        root.addLayout(main, 1)

        aside = QVBoxLayout()
        aside.setSpacing(4)
        aside.setContentsMargins(0, 16, 0, 0)
        aside.addWidget(Picture(theme.IMAGES / "arbre.png", 340))
        grows = label("ton arbre pousse", theme.SCRIPT, 46, color=theme.LEAF_TEXT)
        grows.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        aside.addWidget(grows)
        self._summary = label("", px=15, color=theme.MUTED)
        self._summary.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        aside.addWidget(self._summary)
        aside.addSpacing(30)
        aside.addWidget(section_title("Les personnes à interroger"))
        aside.addSpacing(4)
        self._rows = QVBoxLayout()
        self._rows.setSpacing(0)
        aside.addLayout(self._rows)
        aside.addStretch(1)
        aside_box = QWidget()
        aside_box.setLayout(aside)
        aside_box.setFixedWidth(380)
        root.addWidget(aside_box, 0, Qt.AlignmentFlag.AlignTop)

        self.refresh()

    # Données

    def refresh(self) -> None:
        overview = self._service.overview()
        self._track = self._service.next_track(self._skipped)
        name = overview.first_name
        self._hello.setText(f"Bonjour {name}" if name else "Bonjour")
        self._intro.setText(
            "Ton enquête avance. Voici la prochaine piste à suivre."
            if overview.story_count
            else "Ta quête commence ici. Choisis une piste et pose ta première question."
        )
        self._fill_card(overview)
        self._fill_tiles(overview)
        self._fill_people(overview)

    def _other_track(self) -> None:
        if self._track is not None:
            self._skipped.add(self._track.question.id)
        self.refresh()

    def _launch(self) -> None:
        person_id = self._people.checkedId()
        if self._track is not None and person_id >= 0:
            self.interview_requested.emit(self._track.question.id, person_id)

    # Construction

    def _fill_card(self, overview: QuestOverview) -> None:
        _clear(self._card_layout)
        for button in self._people.buttons():
            self._people.removeButton(button)
        layout = self._card_layout

        if self._track is None:
            layout.addWidget(eyebrow("Bravo", color=theme.RED_TEXT))
            layout.addWidget(
                label("Toutes les pistes ont été explorées.", theme.SERIF, 32, QFont.Weight.Medium)
            )
            return

        head = QHBoxLayout()
        head.setSpacing(16)
        head.addWidget(eyebrow("Prochaine piste", color=theme.RED_TEXT))
        head.addWidget(eyebrow(self._track.theme.label, spacing_em=0.12))
        head.addStretch(1)
        layout.addLayout(head)

        question = label(self._track.question.text, theme.SERIF, 38, QFont.Weight.Medium, wrap=True)
        layout.addWidget(question)

        ask = QVBoxLayout()
        ask.setSpacing(10)
        ask.addWidget(eyebrow("À poser à", color=theme.MUTED, spacing_em=0.14))
        toggles = QHBoxLayout()
        toggles.setSpacing(8)
        for index, progress in enumerate(overview.people):
            toggle = LeafToggle(progress.person.display_name)
            toggle.setChecked(index == 0)
            self._people.addButton(toggle, progress.person.id)
            toggles.addWidget(toggle)
        toggles.addStretch(1)
        ask.addLayout(toggles)
        if not overview.people:
            ask.addWidget(label("Ajoute d'abord un proche à interroger.", px=15, color=theme.MUTED))
        layout.addLayout(ask)

        actions = QHBoxLayout()
        actions.setSpacing(24)
        launch = PrimaryButton("Lancer l'interview", icon="mic")
        launch.setEnabled(bool(overview.people))
        launch.clicked.connect(self._launch)
        actions.addWidget(launch)
        other = link_button("Une autre piste")
        other.clicked.connect(self._other_track)
        actions.addWidget(other)
        actions.addStretch(1)
        layout.addSpacing(4)
        layout.addLayout(actions)

        layout.addWidget(
            label(
                "Prévois une dizaine de minutes, un endroit calme et l'accord de la personne.",
                theme.SERIF,
                15,
                color=theme.MUTED,
                italic=True,
                wrap=True,
            )
        )

    def _fill_tiles(self, overview: QuestOverview) -> None:
        _clear(self._tiles)
        for index, progress in enumerate(overview.themes):
            tile = ClickableFrame("tile")
            tile.setAccessibleName(f"{progress.theme.label}, {progress.done} sur {progress.total}")
            box = QVBoxLayout(tile)
            box.setContentsMargins(22, 20, 22, 20)
            box.setSpacing(12)
            box.addWidget(label(progress.theme.label, theme.SERIF, 23, QFont.Weight.Medium))
            box.addWidget(DotRow(progress.done, progress.total))
            status = f"{progress.done} sur {progress.total}" if progress.done else "À commencer"
            box.addWidget(label(status, px=14, color=theme.MUTED))
            theme_id = progress.theme.id
            tile.clicked.connect(lambda theme_id=theme_id: self.theme_opened.emit(theme_id))
            row, column = divmod(index, self.TILE_COLUMNS)
            self._tiles.addWidget(tile, row, column)
        for column in range(self.TILE_COLUMNS):
            self._tiles.setColumnStretch(column, 1)

    def _fill_people(self, overview: QuestOverview) -> None:
        _clear(self._rows)
        self._summary.setText(
            f"{plural(overview.story_count, 'récit recueilli', 'récits recueillis')} auprès de "
            f"{plural(overview.interviewed_count, 'personne', 'personnes')}"
        )
        for progress in overview.people:
            row = ClickableFrame("row")
            row.setMinimumHeight(64)
            line = QHBoxLayout(row)
            line.setContentsMargins(8, 8, 8, 8)
            names = QVBoxLayout()
            names.setSpacing(0)
            names.addWidget(label(progress.person.display_name, theme.SERIF, 19))
            relation = progress.person.relationship
            names.addWidget(label(relation[:1].upper() + relation[1:], px=13, color=theme.MUTED))
            line.addLayout(names)
            line.addStretch(1)
            if progress.story_count:
                line.addWidget(DotRow(progress.story_count, progress.story_count, gap=6))
            else:
                line.addWidget(
                    label(
                        "Pas encore de récit",
                        px=14,
                        weight=QFont.Weight.DemiBold,
                        color=theme.LEAF_TEXT,
                    )
                )
            person_id = progress.person.id
            row.clicked.connect(lambda person_id=person_id: self._select_person(person_id))
            self._rows.addWidget(row)

    def _select_person(self, person_id: int) -> None:
        button = self._people.button(person_id)
        if button is not None:
            button.setChecked(True)
