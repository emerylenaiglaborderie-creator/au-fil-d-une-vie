"""Lancement de l'interface Qt."""

import sys

from PySide6.QtWidgets import QApplication

from au_fil_d_une_vie.bootstrap import Services
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.main_window import MainWindow


def create_application(argv: list[str] | None = None) -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        app = existing
    else:
        app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Au fil d'une vie")
    theme.load_fonts()
    app.setFont(theme.default_font())
    app.setStyleSheet(theme.STYLESHEET)
    return app


def run(services: Services) -> int:
    app = create_application()
    window = MainWindow(services)
    window.show()
    window.start_background_work()
    return app.exec()
