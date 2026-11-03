"""Fenêtre principale : en-tête de navigation, écrans, rappel de confidentialité."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QMainWindow,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from au_fil_d_une_vie.bootstrap import Services
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.screens.placeholder import PlaceholderScreen
from au_fil_d_une_vie.ui.screens.quest import QuestScreen
from au_fil_d_une_vie.ui.widgets import NavLink, Picture, WashedPage, label, outline_button

PRIVACY = "Tout reste sur cet ordinateur. Rien n'est envoyé en ligne."


class MainWindow(QMainWindow):
    QUEST, INTERVIEW, STORIES, GRAPH = range(4)

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
        self.quest.interview_requested.connect(lambda *_: self.show_screen(self.INTERVIEW))
        self.quest.theme_opened.connect(lambda *_: self.show_screen(self.STORIES))
        for screen in (
            self.quest,
            PlaceholderScreen("Interview"),
            PlaceholderScreen("Mes récits"),
            PlaceholderScreen("Au fil des mots"),
        ):
            self._stack.addWidget(self._scrollable(screen))
        layout.addWidget(self._stack, 1)
        layout.addWidget(self._footer())
        self.setCentralWidget(central)
        self.show_screen(self.QUEST)

    def show_screen(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        button = self._nav.button(index)
        if button is not None:
            button.setChecked(True)
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

        self._nav = QButtonGroup(self)
        for index, text in enumerate(("Ma quête", "Interview", "Récits", "Graphe")):
            link = NavLink(text)
            self._nav.addButton(link, index)
            row.addWidget(link)
        self._nav.idClicked.connect(self.show_screen)
        row.addSpacing(20)
        row.addWidget(outline_button("Livre de famille"))
        return header

    def _footer(self) -> QWidget:
        footer = QWidget()
        footer.setObjectName("footer")
        footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        row = QHBoxLayout(footer)
        row.setContentsMargins(48, 14, 48, 14)
        text = label(PRIVACY, px=14, color=theme.MUTED)
        text.setObjectName("footerText")
        row.addWidget(text)
        row.addStretch(1)
        return footer
