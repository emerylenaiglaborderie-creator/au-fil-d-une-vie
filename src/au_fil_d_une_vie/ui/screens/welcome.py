"""Premier lancement : prénom, âge (accord parental sous 15 ans), premiers proches."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QVBoxLayout, QWidget

from au_fil_d_une_vie.services.people import PeopleService, PersonError
from au_fil_d_une_vie.services.profile import ProfileError, ProfileService
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.leaves import FlowLayout, LeafChip, SearchField
from au_fil_d_une_vie.ui.person_form import PersonForm
from au_fil_d_une_vie.ui.widgets import (
    ConsentBox,
    LeafToggle,
    Picture,
    PrimaryButton,
    clear_layout,
    eyebrow,
    label,
    soft_shadow,
)

PARENT_CONSENT = (
    "Je suis le parent ou le responsable légal, j'ai lu ce qui précède et je suis d'accord "
    "pour que mon enfant utilise Au fil d'une vie."
)


class WelcomeScreen(QWidget):
    finished = Signal()

    OLDER, YOUNGER = 0, 1

    def __init__(
        self, profile: ProfileService, people: PeopleService, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._profile = profile
        self._people = people

        root = QHBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 28)
        root.setSpacing(56)

        side = QVBoxLayout()
        side.setSpacing(4)
        side.addWidget(Picture(theme.IMAGES / "logo.png", 340))
        side.addStretch(1)
        side_box = QWidget()
        side_box.setLayout(side)
        side_box.setFixedWidth(340)
        root.addWidget(side_box, 0, Qt.AlignmentFlag.AlignTop)

        main = QVBoxLayout()
        main.setSpacing(10)
        main.addWidget(eyebrow("Ta quête commence"))
        main.addWidget(label("Bienvenue", theme.SCRIPT, 104, color=theme.INK_SOFT))
        main.addWidget(
            label(
                "Au fil d'une vie t'aide à recueillir les souvenirs de ta famille : tu poses "
                "une question à un proche, tu enregistres sa réponse, et les récits se relient "
                "entre eux au fil des mots.",
                theme.SERIF,
                19,
                color=theme.MUTED,
                italic=True,
                wrap=True,
            )
        )
        main.addSpacing(18)

        card = QFrame()
        card.setObjectName("card")
        soft_shadow(card)
        form = QVBoxLayout(card)
        form.setContentsMargins(34, 30, 34, 30)
        form.setSpacing(14)

        form.addWidget(eyebrow("Comment t'appelles-tu ?", color=theme.MUTED, spacing_em=0.14))
        self._name = SearchField("Ton prénom")
        self._name.setClearButtonEnabled(False)
        self._name.setFont(theme.font(theme.SERIF, 22, italic=True))
        self._name.setMaximumWidth(360)
        self._name.textChanged.connect(lambda _t: self._update())
        form.addWidget(self._name)
        form.addSpacing(8)

        form.addWidget(eyebrow("Quel âge as-tu ?", color=theme.MUTED, spacing_em=0.14))
        ages = QHBoxLayout()
        ages.setSpacing(8)
        self._age = QButtonGroup(self)
        for age_id, text in ((self.OLDER, "15 ans ou plus"), (self.YOUNGER, "Moins de 15 ans")):
            toggle = LeafToggle(text)
            self._age.addButton(toggle, age_id)
            ages.addWidget(toggle)
        ages.addStretch(1)
        self._age.idClicked.connect(lambda _id: self._update())
        form.addLayout(ages)

        self._parent = QFrame()
        self._parent.setObjectName("softCard")
        parent_box = QVBoxLayout(self._parent)
        parent_box.setContentsMargins(22, 18, 22, 18)
        parent_box.setSpacing(10)
        parent_box.addWidget(label("Pour ton parent", theme.SCRIPT, 40, color=theme.LEAF_TEXT))
        parent_box.addWidget(
            label(
                "Votre enfant va enregistrer la voix de proches qui acceptent de raconter leurs "
                "souvenirs. Tout reste sur cet ordinateur : pas de compte, rien n'est envoyé en "
                "ligne. Chaque proche donne son accord avant chaque enregistrement, et chaque "
                "récit peut être masqué ou supprimé à tout moment.",
                theme.SERIF,
                16,
                wrap=True,
            )
        )
        self._parent_consent = ConsentBox()
        self._parent_consent.set_text(PARENT_CONSENT)
        self._parent_consent.setStyleSheet(f"QFrame#consent {{ background: {theme.WHITE}; }}")
        self._parent_consent.toggled.connect(lambda _c: self._update())
        parent_box.addWidget(self._parent_consent)
        self._parent.hide()
        form.addWidget(self._parent)
        form.addSpacing(8)

        form.addWidget(eyebrow("Qui vas-tu interroger ?", color=theme.MUTED, spacing_em=0.14))
        form.addWidget(
            label(
                "Ajoute quelques proches maintenant, ou plus tard depuis ta quête.",
                px=15,
                color=theme.MUTED,
            )
        )
        self._person = PersonForm()
        self._person.submitted.connect(self._add_person)
        form.addWidget(self._person)
        self._added_box = QWidget()
        self._added = FlowLayout(self._added_box)
        form.addWidget(self._added_box)
        self._person_error = label("", px=14, color=theme.RED_TEXT)
        self._person_error.hide()
        form.addWidget(self._person_error)
        form.addSpacing(10)

        actions = QHBoxLayout()
        self._start = PrimaryButton("Commencer ma quête")
        self._start.clicked.connect(self._finish)
        actions.addWidget(self._start)
        actions.addStretch(1)
        form.addLayout(actions)
        self._error = label("", px=15, color=theme.RED_TEXT, wrap=True)
        self._error.hide()
        form.addWidget(self._error)
        main.addWidget(card)
        main.addStretch(1)
        root.addLayout(main, 1)

        self._refresh_people()
        self._update()

    def _under_15(self) -> bool:
        return self._age.checkedId() == self.YOUNGER

    def _update(self) -> None:
        self._parent.setVisible(self._under_15())
        ready = bool(self._name.text().strip()) and self._age.checkedId() >= 0
        if self._under_15():
            ready = ready and self._parent_consent.is_checked()
        self._start.setEnabled(ready)

    def _add_person(self, name: str, relationship: str) -> None:
        try:
            self._people.add(name, relationship)
        except PersonError as error:
            self._person_error.setText(str(error))
            self._person_error.show()
            return
        self._person_error.hide()
        self._person.clear()
        self._refresh_people()

    def _refresh_people(self) -> None:
        clear_layout(self._added)
        for person, _count in self._people.all():
            chip = LeafChip(
                f"{person.display_name} · {person.relationship}", "filled", closable=True
            )
            chip.closed.connect(lambda person_id=person.id: self._remove_person(person_id))
            self._added.addWidget(chip)
        self._added_box.updateGeometry()

    def _remove_person(self, person_id: int) -> None:
        self._people.delete(person_id)
        self._refresh_people()

    def _finish(self) -> None:
        try:
            self._profile.save(
                self._name.text(), self._under_15(), self._parent_consent.is_checked()
            )
        except ProfileError as error:
            self._error.setText(str(error))
            self._error.show()
            return
        self.finished.emit()
