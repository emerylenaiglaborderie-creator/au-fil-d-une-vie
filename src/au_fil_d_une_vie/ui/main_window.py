"""Fenêtre principale : en-tête de navigation, écrans, rappel de confidentialité."""

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from au_fil_d_une_vie.bootstrap import Services
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.book_dialog import BookDialog
from au_fil_d_une_vie.ui.bridge import TranscriptionBridge
from au_fil_d_une_vie.ui.model_setup import ModelSetupDialog
from au_fil_d_une_vie.ui.people_dialog import PeopleDialog
from au_fil_d_une_vie.ui.screens.graph import GraphScreen
from au_fil_d_une_vie.ui.screens.interview import InterviewScreen
from au_fil_d_une_vie.ui.screens.quest import QuestScreen
from au_fil_d_une_vie.ui.screens.settings import SettingsScreen
from au_fil_d_une_vie.ui.screens.stories import StoriesScreen
from au_fil_d_une_vie.ui.screens.story import StoryScreen
from au_fil_d_une_vie.ui.screens.welcome import WelcomeScreen
from au_fil_d_une_vie.ui.widgets import (
    NavLink,
    Picture,
    ThreadProgress,
    WashedPage,
    icon_pixmap,
    label,
    link_button,
    outline_button,
)

PRIVACY = "Tout reste sur cet ordinateur. Rien n'est envoyé en ligne."


class MainWindow(QMainWindow):
    QUEST, INTERVIEW, STORIES, GRAPH, STORY, WELCOME, SETTINGS = range(7)

    preferences_changed = Signal()

    def __init__(self, services: Services) -> None:
        super().__init__()
        self._services = services
        self.setWindowTitle("Au fil d'une vie")
        self.resize(1360, 900)
        self.setMinimumSize(1080, 700)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._header())

        self._stack = QStackedWidget()
        self.quest = QuestScreen(services.quest)
        self.quest.interview_requested.connect(self._open_interview)
        self.quest.theme_opened.connect(self._open_theme)
        self.quest.manage_people.connect(self.open_people)
        self.interview = InterviewScreen(services.quest, services.recording)
        self.interview.back_to_quest.connect(lambda: self.show_screen(self.QUEST))
        self.interview.story_saved.connect(self._story_saved)
        self.interview.manage_people.connect(self.open_people)
        self.welcome = WelcomeScreen(services.profile, services.people)
        self.welcome.finished.connect(self._welcome_done)
        self.settings = SettingsScreen(services)
        self.settings.preferences_changed.connect(self.preferences_changed)
        self.settings.manage_people.connect(self.open_people)
        self.settings.install_model.connect(self.offer_model_setup)
        self._disposed = False
        self.stories = StoriesScreen(services.stories)
        self.stories.story_opened.connect(self.show_story)
        self.stories.new_interview.connect(lambda: self.show_screen(self.INTERVIEW))
        self.story = StoryScreen(services.stories)
        self.story.back.connect(lambda: self.show_screen(self.STORIES))
        self.story.story_opened.connect(self.show_story)
        self.story.deleted.connect(lambda: self.show_screen(self.STORIES))
        self.graph = GraphScreen(services.graph, services.stories)
        self.graph.story_opened.connect(self.show_story)

        self._bridge = TranscriptionBridge(services.transcription, self)
        self._bridge.progress.connect(self._transcription_progress)
        self._bridge.finished.connect(self._transcription_finished)
        self._bridge.failed.connect(self._transcription_failed)
        self._model_offered = False
        for screen in (
            self.quest,
            self.interview,
            self.stories,
            self.graph,
            self.story,
            self.welcome,
            self.settings,
        ):
            self._stack.addWidget(self._scrollable(screen))
        layout.addWidget(self._stack, 1)
        layout.addWidget(self._footer())
        self.setCentralWidget(central)
        if services.profile.get() is None:
            self._show_welcome()
        else:
            self.show_screen(self.QUEST)

    def _open_interview(self, question_id: int, person_id: int) -> None:
        self.interview.open(question_id, person_id)
        self.show_screen(self.INTERVIEW)

    def _show_welcome(self) -> None:
        """Premier lancement : la navigation attend que le profil soit créé."""
        self._nav_box.hide()
        self._stack.setCurrentIndex(self.WELCOME)

    def _welcome_done(self) -> None:
        self._nav_box.show()
        self.show_screen(self.QUEST)

    def open_people(self) -> PeopleDialog:
        dialog = PeopleDialog(self._services.people, self)
        dialog.finished.connect(lambda _result: self._after_people())
        dialog.open()
        return dialog

    def _after_people(self) -> None:
        self.quest.refresh()
        if not self.interview.is_recording():
            self.interview.open()

    def open_book(self) -> BookDialog:
        dialog = BookDialog(self._services.book, self)
        dialog.finished.connect(lambda _result: self._after_book())
        dialog.open()
        return dialog

    def _after_book(self) -> None:
        if self._stack.currentIndex() == self.STORY:
            self.story.reload()

    def show_story(self, story_id: int) -> None:
        self.story.open(story_id)
        self.show_screen(self.STORY)

    def _open_theme(self, theme_id: int) -> None:
        self.stories.set_theme(theme_id)
        self.show_screen(self.STORIES)

    def _scroll_to_top(self, index: int) -> None:
        area = self._stack.widget(index)
        if isinstance(area, QScrollArea):
            area.verticalScrollBar().setValue(0)

    def _may_leave_interview(self) -> bool:
        """Quitter l'interview pendant un enregistrement : demander, puis effacer la prise."""
        if not self.interview.is_recording():
            return True
        if not self.interview.confirm("Un enregistrement est en cours. L'arrêter et l'effacer ?"):
            return False
        self.interview.abandon()
        return True

    def show_screen(self, index: int) -> None:
        current = self._stack.currentIndex()
        if current == self.INTERVIEW and index != current and not self._may_leave_interview():
            button = self._nav.button(current)
            if button is not None:
                button.setChecked(True)
            return
        if index == self.INTERVIEW and current != self.INTERVIEW:
            self.interview.open()
        if current == self.STORY and index != self.STORY:
            self.story.leave()
        if index == self.STORIES:
            self.stories.refresh()
        if index == self.GRAPH:
            self.graph.refresh()
        if index == self.SETTINGS:
            self.settings.refresh()
        self._stack.setCurrentIndex(index)
        self._scroll_to_top(index)
        button = self._nav.button(self.STORIES if index == self.STORY else index)
        if button is not None:
            button.setChecked(True)
        else:  # écran hors navigation (paramètres) : aucun lien actif
            self._nav.setExclusive(False)
            for link in self._nav.buttons():
                link.setChecked(False)
            self._nav.setExclusive(True)
        if index == self.QUEST:
            self.quest.refresh()

    def _scrollable(self, screen: QWidget) -> QScrollArea:
        page = WashedPage()
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(screen)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setWidget(page)
        return area

    def _header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("header")
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        row = QHBoxLayout(header)
        row.setContentsMargins(48, 0, 48, 0)
        row.setSpacing(12)

        tree = Picture(theme.IMAGES / "arbre.png", 46)
        tree.setFixedSize(46, 50)
        row.addWidget(tree)
        row.addWidget(label("Au fil d'une vie", theme.SCRIPT, 42, color=theme.INK_SOFT))
        row.addStretch(1)

        self._nav_box = QWidget()
        nav = QHBoxLayout(self._nav_box)
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(12)
        self._nav = QButtonGroup(self)
        for index, text in enumerate(("Ma quête", "Interview", "Récits", "Graphe")):
            link = NavLink(text)
            self._nav.addButton(link, index)
            nav.addWidget(link)
        self._nav.idClicked.connect(self.show_screen)
        nav.addSpacing(20)
        book = outline_button("Livre de famille")
        book.clicked.connect(self.open_book)
        nav.addWidget(book)
        gear = QPushButton()
        gear.setObjectName("outline")
        gear.setIcon(QIcon(icon_pixmap("gear", 20, theme.INK_SOFT)))
        gear.setIconSize(QSize(20, 20))
        gear.setFixedWidth(48)
        gear.setToolTip("Paramètres")
        gear.setAccessibleName("Paramètres")
        gear.setCursor(Qt.CursorShape.PointingHandCursor)
        gear.clicked.connect(lambda: self.show_screen(self.SETTINGS))
        nav.addWidget(gear)
        row.addWidget(self._nav_box)
        return header

    def _footer(self) -> QWidget:
        footer = QWidget()
        footer.setObjectName("footer")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        row = QHBoxLayout(footer)
        row.setContentsMargins(48, 10, 48, 10)
        row.setSpacing(12)
        text = label(PRIVACY, px=14, color=theme.MUTED)
        text.setObjectName("footerText")
        row.addWidget(text)
        row.addStretch(1)
        self._job_text = label("", px=14, color=theme.MUTED)
        row.addWidget(self._job_text)
        self._job_bar = ThreadProgress(140)
        self._job_bar.hide()
        row.addWidget(self._job_bar)
        self._install = link_button("Installer")
        self._install.setMinimumHeight(28)
        self._install.clicked.connect(self.offer_model_setup)
        self._install.hide()
        row.addWidget(self._install)
        self._clear_job = QTimer(self)
        self._clear_job.setSingleShot(True)
        self._clear_job.setInterval(6000)
        self._clear_job.timeout.connect(self._refresh_job_status)
        return footer

    # Transcription

    def start_background_work(self) -> None:
        """Au démarrage : reprendre les textes en attente, ou proposer le modèle."""
        if self._services.transcription_ready():
            self._services.transcription.resume_pending()
            self._refresh_job_status()
        else:
            self._refresh_job_status()
            if not self._model_offered:
                QTimer.singleShot(300, self.offer_model_setup)

    def offer_model_setup(self) -> None:
        self._model_offered = True
        dialog = ModelSetupDialog(self._services.models, self._services.model_size, self)
        dialog.installed.connect(self._model_installed)
        dialog.open()

    def _model_installed(self) -> None:
        self._services.transcription.resume_pending()
        self._refresh_job_status()

    def _story_saved(self, story_id: int) -> None:
        if self._services.transcription_ready():
            self._services.transcription.enqueue(story_id)
        self._refresh_job_status()

    def _transcription_progress(self, story_id: int, fraction: float) -> None:
        _current, waiting = self._services.transcription.snapshot()
        suffix = f" · {waiting} en attente" if waiting else ""
        self._job_text.setStyleSheet(f"color: {theme.MUTED};")
        self._job_text.setText(f"Texte du récit en préparation{suffix}")
        self._job_bar.set_value(fraction)
        self._job_bar.show()
        self._install.hide()

    def _transcription_finished(self, story_id: int) -> None:
        if self._stack.currentIndex() == self.STORIES:
            self.stories.refresh()
        if self._stack.currentIndex() == self.STORY and self.story.story_id == story_id:
            self.story.reload()
        current, waiting = self._services.transcription.snapshot()
        if current is None and not waiting:
            self._job_bar.hide()
            self._job_text.setStyleSheet(f"color: {theme.LEAF_TEXT};")
            self._job_text.setText("Le texte du récit est prêt.")
            self._clear_job.start()

    def _transcription_failed(self, story_id: int, message: str) -> None:
        self._job_bar.hide()
        self._job_text.setStyleSheet(f"color: {theme.RED_TEXT};")
        self._job_text.setText("Le texte d'un récit n'a pas pu être préparé.")
        self._job_text.setToolTip(message)
        self._clear_job.start()

    def _refresh_job_status(self) -> None:
        """État calme du pied de page : rien, ou un rappel si le modèle manque."""
        current, waiting = self._services.transcription.snapshot()
        if current is not None or waiting:
            return
        self._job_bar.hide()
        self._job_text.setToolTip("")
        if self._services.transcription_ready():
            self._job_text.setText("")
            self._install.hide()
        else:
            self._job_text.setStyleSheet(f"color: {theme.MUTED};")
            self._job_text.setText("Modèle de transcription non installé.")
            self._install.show()

    def current_screen(self) -> int:
        return self._stack.currentIndex()

    def dispose(self) -> None:
        """Ferme cette fenêtre pour la remplacer (thème ou langue changés)."""
        self._disposed = True
        self.story.leave()
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._disposed:
            event.accept()
            return
        if self._may_leave_interview():
            # Le récit en cours de transcription sera repris au prochain lancement.
            self._services.transcription.shutdown(timeout=0)
            self.story.leave()
            event.accept()
        else:
            event.ignore()
