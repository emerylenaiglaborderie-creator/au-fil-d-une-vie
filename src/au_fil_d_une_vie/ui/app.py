"""Lancement de l'interface Qt et application des préférences (thème)."""

import sys

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication

from au_fil_d_une_vie.bootstrap import Services
from au_fil_d_une_vie.services.settings import Settings
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.main_window import MainWindow


def create_application(argv: list[str] | None = None) -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        app = existing
    else:
        app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Au fil d'une vie")
    app.setWindowIcon(QIcon(str(theme.IMAGES / "icone.png")))
    theme.load_fonts()
    app.setFont(theme.default_font())
    app.setStyleSheet(theme.stylesheet())
    return app


def system_is_dark() -> bool:
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def apply_preferences(app: QApplication, settings: Settings) -> None:
    """Palette et feuille de style selon les préférences (avant de créer les widgets)."""
    dark = settings.theme == "dark" or (settings.theme == "auto" and system_is_dark())
    theme.apply(dark)
    app.setStyleSheet(theme.stylesheet())


class Controller(QObject):
    """Garde la fenêtre et la reconstruit quand le thème change.

    Les couleurs sont lues à la construction des widgets : plutôt que de repeindre
    chaque élément, on recrée la fenêtre, au même écran, avec les mêmes services.
    """

    def __init__(self, app: QApplication, services: Services) -> None:
        super().__init__(app)
        self._app = app
        self._services = services
        apply_preferences(app, services.settings.load())
        self.window = self._create()
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_changed)

    def _create(self) -> MainWindow:
        window = MainWindow(self._services)
        window.preferences_changed.connect(self.rebuild)
        return window

    def rebuild(self) -> None:
        old = self.window
        apply_preferences(self._app, self._services.settings.load())
        self.window = self._create()
        self.window.setGeometry(old.geometry())
        if old.current_screen() != MainWindow.WELCOME:
            self.window.show_screen(old.current_screen())
        self.window.show()
        old.dispose()
        old.deleteLater()

    def _system_changed(self) -> None:
        if (
            self._services.settings.load().theme == "auto"
            and not self.window.interview.is_recording()
        ):
            self.rebuild()


def run(services: Services) -> int:
    app = create_application()
    controller = Controller(app, services)
    controller.window.show()
    controller.window.start_background_work()
    return app.exec()
