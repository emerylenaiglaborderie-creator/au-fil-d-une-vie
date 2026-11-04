"""Écran « Paramètres » : profil, apparence, proches, données de l'application."""

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from au_fil_d_une_vie.bootstrap import Services
from au_fil_d_une_vie.i18n import LANGUAGES, _
from au_fil_d_une_vie.services.profile import ProfileError
from au_fil_d_une_vie.services.settings import Settings
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.leaves import SearchField
from au_fil_d_une_vie.ui.text import plural
from au_fil_d_une_vie.ui.widgets import (
    LeafToggle,
    eyebrow,
    label,
    link_button,
    outline_button,
    section_title,
    soft_shadow,
)

THEME_CHOICES = (("auto", "Comme l'ordinateur"), ("light", "Jour"), ("dark", "Nuit"))


class SettingsScreen(QWidget):
    preferences_changed = Signal()
    manage_people = Signal()
    manage_tracks = Signal()
    install_model = Signal()

    def __init__(self, services: Services, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._services = services
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 28)
        root.setSpacing(10)
        root.addWidget(eyebrow(_("Réglages")))
        root.addWidget(label(_("Paramètres"), theme.SCRIPT, 96, color=theme.INK_SOFT))
        root.addSpacing(18)

        columns = QHBoxLayout()
        columns.setSpacing(40)
        left = QVBoxLayout()
        left.setSpacing(28)
        left.addWidget(self._profile_card())
        left.addWidget(self._appearance_card())
        left.addWidget(self._language_card())
        left.addStretch(1)
        right = QVBoxLayout()
        right.setSpacing(28)
        right.addWidget(self._people_card())
        right.addWidget(self._tracks_card())
        right.addWidget(self._data_card())
        right.addStretch(1)
        columns.addLayout(left, 1)
        columns.addLayout(right, 1)
        root.addLayout(columns)
        root.addStretch(1)
        self.refresh()

    # Cartes

    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        soft_shadow(card)
        box = QVBoxLayout(card)
        box.setContentsMargins(30, 26, 30, 26)
        box.setSpacing(12)
        box.addWidget(section_title(title))
        return card, box

    def _profile_card(self) -> QFrame:
        card, box = self._card(_("Mon profil"))
        box.addWidget(eyebrow(_("Ton prénom"), color=theme.MUTED, spacing_em=0.14))
        row = QHBoxLayout()
        row.setSpacing(16)
        self._name = SearchField(_("Ton prénom"))
        self._name.setClearButtonEnabled(False)
        self._name.setFont(theme.font(theme.SERIF, 20, italic=True))
        self._name.returnPressed.connect(self._save_name)
        row.addWidget(self._name, 1)
        save = outline_button(_("Enregistrer"))
        save.clicked.connect(self._save_name)
        row.addWidget(save)
        box.addLayout(row)
        self._name_status = label("", px=14, color=theme.MUTED)
        box.addWidget(self._name_status)
        self._age = label("", px=15, color=theme.MUTED, wrap=True)
        box.addWidget(self._age)
        return card

    def _appearance_card(self) -> QFrame:
        card, box = self._card(_("Apparence"))
        box.addWidget(eyebrow(_("Thème"), color=theme.MUTED, spacing_em=0.14))
        row = QHBoxLayout()
        row.setSpacing(8)
        self._themes = QButtonGroup(self)
        for index, (_value, text) in enumerate(THEME_CHOICES):
            toggle = LeafToggle(_(text))
            self._themes.addButton(toggle, index)
            row.addWidget(toggle)
        row.addStretch(1)
        self._themes.idClicked.connect(self._choose_theme)
        box.addLayout(row)
        box.addWidget(
            label(
                _("« Comme l'ordinateur » suit le mode clair ou sombre de ton système."),
                px=14,
                color=theme.MUTED,
                wrap=True,
            )
        )
        return card

    def _language_card(self) -> QFrame:
        card, box = self._card(_("Langue"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self._languages = QButtonGroup(self)
        for index, (code, name) in enumerate(LANGUAGES.items()):
            toggle = LeafToggle(name)  # chaque langue écrite dans sa propre langue
            toggle.setProperty("code", code)
            self._languages.addButton(toggle, index)
            row.addWidget(toggle)
        row.addStretch(1)
        self._languages.idClicked.connect(self._choose_language)
        box.addLayout(row)
        box.addWidget(
            label(
                _(
                    "Change la langue de l'application et de la transcription. Tes récits et "
                    "tes pistes gardent la langue dans laquelle tu les as écrits."
                ),
                px=14,
                color=theme.MUTED,
                wrap=True,
            )
        )
        return card

    def _people_card(self) -> QFrame:
        card, box = self._card(_("Mes proches"))
        self._people_count = label("", theme.SERIF, 17, wrap=True)
        box.addWidget(self._people_count)
        manage = link_button(_("Ajouter, modifier ou supprimer un proche"))
        manage.clicked.connect(self.manage_people)
        box.addWidget(manage, 0, Qt.AlignmentFlag.AlignLeft)
        return card

    def _tracks_card(self) -> QFrame:
        card, box = self._card(_("Pistes et questions"))
        self._tracks_count = label("", theme.SERIF, 17, wrap=True)
        box.addWidget(self._tracks_count)
        manage = link_button(_("Créer, renommer ou réordonner les pistes"))
        manage.clicked.connect(self.manage_tracks)
        box.addWidget(manage, 0, Qt.AlignmentFlag.AlignLeft)
        return card

    def _data_card(self) -> QFrame:
        card, box = self._card(_("Mes données"))
        box.addWidget(
            label(
                _(
                    "Tout est rangé sur cet ordinateur, dans ce dossier. Rien n'est envoyé en ligne."
                ),
                theme.SERIF,
                16,
                wrap=True,
            )
        )
        self._folder = QLabel(str(self._services.db_path.parent))
        self._folder.setFont(theme.font(theme.SANS, 13))
        self._folder.setStyleSheet(f"color: {theme.MUTED};")
        self._folder.setWordWrap(True)
        self._folder.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box.addWidget(self._folder)
        open_folder = link_button(_("Ouvrir le dossier"))
        open_folder.clicked.connect(self._open_folder)
        box.addWidget(open_folder, 0, Qt.AlignmentFlag.AlignLeft)
        box.addSpacing(6)
        box.addWidget(eyebrow(_("Transcription"), color=theme.MUTED, spacing_em=0.14))
        self._model = label("", px=15, wrap=True)
        box.addWidget(self._model)
        self._install = link_button(_("Installer le modèle"))
        self._install.clicked.connect(self.install_model)
        box.addWidget(self._install, 0, Qt.AlignmentFlag.AlignLeft)
        return card

    # Données

    def refresh(self) -> None:
        profile = self._services.profile.get()
        self._name.setText(profile.first_name if profile else "")
        self._name_status.setText("")
        if profile is not None:
            self._age.setText(
                _("Moins de 15 ans, avec l'accord d'un parent.")
                if profile.under_15
                else _("15 ans ou plus.")
            )
        settings = self._services.settings.load()
        values = [value for value, _text in THEME_CHOICES]
        button = self._themes.button(values.index(settings.theme))
        if button is not None:
            button.setChecked(True)
        codes = list(LANGUAGES)
        language_button = self._languages.button(codes.index(settings.language))
        if language_button is not None:
            language_button.setChecked(True)
        count = len(self._services.people.all())
        self._people_count.setText(
            _("Personne pour l'instant.")
            if count == 0
            else _("{people} dans ta quête.").format(people=plural(count, "proche", "proches"))
        )
        tracks = self._services.tracks.all()
        questions = sum(len(t.questions) for t in tracks)
        self._tracks_count.setText(
            _("{tracks}, {questions}.").format(
                tracks=plural(len(tracks), "piste", "pistes"),
                questions=plural(questions, "question", "questions"),
            )
        )
        ready = self._services.transcription_ready()
        size = self._services.model_size
        self._model.setText(
            _("Modèle « {size} » installé : les textes se préparent sur cet ordinateur.").format(
                size=size
            )
            if ready
            else _("Le modèle n'est pas encore installé.")
        )
        self._install.setVisible(not ready)

    def _save_name(self) -> None:
        try:
            self._services.profile.rename(self._name.text())
        except ProfileError as error:
            self._name_status.setStyleSheet(f"color: {theme.RED_TEXT};")
            self._name_status.setText(str(error))
            return
        self._name_status.setStyleSheet(f"color: {theme.LEAF_TEXT};")
        self._name_status.setText(_("C'est enregistré."))

    def _choose_theme(self, index: int) -> None:
        current = self._services.settings.load()
        chosen = THEME_CHOICES[index][0]
        if chosen != current.theme:
            self._services.settings.save(Settings(language=current.language, theme=chosen))
            self.preferences_changed.emit()

    def _choose_language(self, index: int) -> None:
        current = self._services.settings.load()
        chosen = list(LANGUAGES)[index]
        if chosen != current.language:
            self._services.settings.save(Settings(language=chosen, theme=current.theme))
            self.preferences_changed.emit()

    def _open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._services.db_path.parent)))
