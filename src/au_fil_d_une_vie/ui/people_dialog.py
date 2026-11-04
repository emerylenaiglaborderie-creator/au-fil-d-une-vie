"""Fenêtre « Mes proches » : ajouter, renommer ou supprimer les personnes interrogées."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QMessageBox, QVBoxLayout, QWidget

from au_fil_d_une_vie.models import Person
from au_fil_d_une_vie.services.people import PeopleService, PersonError
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.person_form import PersonForm
from au_fil_d_une_vie.ui.text import plural
from au_fil_d_une_vie.ui.widgets import clear_layout, label, link_button, section_title


class PeopleDialog(QDialog):
    def __init__(self, service: PeopleService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._editing: int | None = None
        self.setWindowTitle("Mes proches")
        self.setModal(True)
        self.setFixedWidth(640)
        self.setStyleSheet(f"QDialog {{ background: {theme.CREAM}; }}")

        box = QVBoxLayout(self)
        box.setContentsMargins(40, 30, 40, 30)
        box.setSpacing(12)
        box.addWidget(label("Mes proches", theme.SCRIPT, 56, color=theme.RED_TEXT))
        box.addWidget(section_title("Les personnes à interroger"))
        self._rows = QVBoxLayout()
        self._rows.setSpacing(0)
        box.addLayout(self._rows)
        box.addSpacing(12)
        self._form_title = label("Ajouter un proche", theme.SERIF, 17)
        box.addWidget(self._form_title)
        self.form = PersonForm()
        self.form.submitted.connect(self._submit)
        box.addWidget(self.form)
        self._error = label("", px=14, color=theme.RED_TEXT, wrap=True)
        self._error.hide()
        box.addWidget(self._error)
        close = link_button("Fermer")
        close.clicked.connect(self.accept)
        box.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
        self.refresh()

    def refresh(self) -> None:
        clear_layout(self._rows)
        people = self._service.all()
        if not people:
            self._rows.addWidget(
                label("Personne pour l'instant.", theme.SERIF, 16, color=theme.MUTED, italic=True)
            )
        for person, count in people:
            self._rows.addWidget(self._row(person, count))

    def _row(self, person: Person, count: int) -> QWidget:
        row = QWidget()
        row.setObjectName("row")
        line = QHBoxLayout(row)
        line.setContentsMargins(4, 8, 4, 8)
        line.setSpacing(16)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label(person.display_name, theme.SERIF, 19))
        relation = person.relationship
        stories = plural(count, "récit", "récits") if count else "pas encore de récit"
        detail = f"{relation[:1].upper()}{relation[1:]} · {stories}"
        names.addWidget(label(detail, px=13, color=theme.MUTED))
        line.addLayout(names, 1)
        edit = link_button("Modifier")
        edit.clicked.connect(lambda: self._start_edit(person))
        line.addWidget(edit)
        delete = link_button("Supprimer")
        delete.setStyleSheet(f"color: {theme.RED_TEXT};")
        delete.clicked.connect(lambda: self._delete(person, count))
        line.addWidget(delete)
        return row

    def _start_edit(self, person: Person) -> None:
        self._editing = person.id
        self._form_title.setText(f"Modifier {person.display_name}")
        self.form.button.setText("Enregistrer")
        self.form.set_values(person.display_name, person.relationship)
        self.form.name.setFocus()

    def _reset_form(self) -> None:
        self._editing = None
        self._form_title.setText("Ajouter un proche")
        self.form.button.setText("Ajouter")
        self.form.clear()

    def _submit(self, name: str, relationship: str) -> None:
        try:
            if self._editing is None:
                self._service.add(name, relationship)
            else:
                self._service.rename(self._editing, name, relationship)
        except PersonError as error:
            self._error.setText(str(error))
            self._error.show()
            return
        self._error.hide()
        self._reset_form()
        self.refresh()

    def _delete(self, person: Person, count: int) -> None:
        if count == 1:
            stories = " Son récit et son enregistrement seront aussi effacés."
        elif count > 1:
            stories = f" Ses {count} récits et leurs enregistrements seront aussi effacés."
        else:
            stories = ""
        if not self.confirm(f"Supprimer {person.display_name} ?{stories} Ce n'est pas réversible."):
            return
        self._service.delete(person.id)
        if self._editing == person.id:
            self._reset_form()
        self.refresh()

    def confirm(self, question: str) -> bool:
        """Demande une confirmation (remplacée dans les tests)."""
        answer = QMessageBox.question(self, "Au fil d'une vie", question)
        return answer == QMessageBox.StandardButton.Yes
