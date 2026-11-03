"""Écran provisoire pour les parties pas encore construites."""

from PySide6.QtWidgets import QVBoxLayout, QWidget

from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.widgets import label


class PlaceholderScreen(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 40, 48, 28)
        layout.addWidget(label(title, theme.SCRIPT, 96, color=theme.INK_SOFT))
        layout.addWidget(
            label("Cet écran arrive bientôt.", theme.SERIF, 19, color=theme.MUTED, italic=True)
        )
        layout.addStretch(1)
