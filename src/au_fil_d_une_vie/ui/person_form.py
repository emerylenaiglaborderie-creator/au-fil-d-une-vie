"""Petit formulaire pour ajouter ou modifier un proche (nom et lien)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QWidget

from au_fil_d_une_vie.services.people import RELATIONSHIPS
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.leaves import SearchField


class PersonForm(QWidget):
    """Nom (« Mamie Jeanne ») et lien (liste modifiable), validé par Entrée ou le bouton."""

    submitted = Signal(str, str)

    def __init__(self, button_text: str = "Ajouter", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        self.name = SearchField("Comment tu l'appelles (Mamie Jeanne, Papa...)")
        self.name.setClearButtonEnabled(False)
        self.name.setFont(theme.font(theme.SERIF, 17, italic=True))
        self.name.returnPressed.connect(self._submit)
        row.addWidget(self.name, 1)
        self.relationship = QComboBox()
        self.relationship.setObjectName("personPicker")
        self.relationship.setEditable(True)
        self.relationship.addItems(RELATIONSHIPS)
        self.relationship.setFont(theme.font(theme.SERIF, 17, italic=True))
        self.relationship.setMinimumWidth(150)
        self.relationship.setAccessibleName("Lien avec toi")
        row.addWidget(self.relationship)
        self.button = QPushButton(button_text)
        self.button.setObjectName("outline")
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.clicked.connect(self._submit)
        row.addWidget(self.button)

    def set_values(self, name: str, relationship: str) -> None:
        self.name.setText(name)
        self.relationship.setCurrentText(relationship)

    def clear(self) -> None:
        self.name.clear()
        self.relationship.setCurrentIndex(0)
        self.name.setFocus()

    def _submit(self) -> None:
        self.submitted.emit(self.name.text(), self.relationship.currentText())
