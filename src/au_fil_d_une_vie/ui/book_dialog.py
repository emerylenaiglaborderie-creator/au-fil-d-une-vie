"""Fenêtre « Livre de famille » : choisir les récits et créer le PDF."""

from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFontMetrics
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from au_fil_d_une_vie.services.book import BookService
from au_fil_d_une_vie.services.book_pdf import BookAssets, render_book
from au_fil_d_une_vie.services.stories import StoryCard
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.bridge import BackgroundTask
from au_fil_d_une_vie.ui.text import plural
from au_fil_d_une_vie.ui.widgets import (
    PrimaryButton,
    ThreadProgress,
    eyebrow,
    label,
    link_button,
)

DEFAULT_NAME = "Livre de famille.pdf"
CHECK_TEXT_WIDTH = 460


def default_book_path() -> Path:
    documents = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    return Path(documents or Path.home()) / DEFAULT_NAME


class BookDialog(QDialog):
    """Choix des récits (case par récit, rangés par piste) puis création du PDF."""

    created = Signal(Path)

    def __init__(self, service: BookService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._boxes: dict[int, QCheckBox] = {}
        self._path: Path | None = None
        self.setWindowTitle("Livre de famille")
        self.setModal(True)
        self.setFixedWidth(620)
        self.setStyleSheet(f"QDialog {{ background: {theme.CREAM}; }}")

        box = QVBoxLayout(self)
        box.setContentsMargins(40, 30, 40, 30)
        box.setSpacing(12)
        box.addWidget(label("Le livre de famille", theme.SCRIPT, 56, color=theme.RED_TEXT))
        box.addWidget(
            label(
                "Choisis les récits à mettre dans ton livre. Il est créé en PDF sur cet "
                "ordinateur, avec un sommaire, les liens entre les récits et un index des mots.",
                theme.SERIF,
                17,
                wrap=True,
            )
        )

        tools = QHBoxLayout()
        self._count = label("", px=15, color=theme.MUTED)
        tools.addWidget(self._count)
        tools.addStretch(1)
        everything = link_button("Tout choisir")
        everything.clicked.connect(lambda: self._check_all(True))
        tools.addWidget(everything)
        tools.addSpacing(16)
        nothing = link_button("Aucun")
        nothing.clicked.connect(lambda: self._check_all(False))
        tools.addWidget(nothing)
        box.addLayout(tools)

        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setFixedHeight(320)
        area.setStyleSheet(
            f"QScrollArea {{ background: {theme.SURFACE}; border: 1px solid {theme.BORDER};"
            " border-radius: 14px; }"
        )
        inner = QWidget()
        inner.setStyleSheet(f"background: {theme.SURFACE};")
        self._list = QVBoxLayout(inner)
        self._list.setContentsMargins(18, 14, 18, 14)
        self._list.setSpacing(6)
        area.setWidget(inner)
        box.addWidget(area)
        self._missing = label("", px=14, color=theme.MUTED, wrap=True)
        box.addWidget(self._missing)

        self._progress_row = QWidget()
        progress = QHBoxLayout(self._progress_row)
        progress.setContentsMargins(0, 0, 0, 0)
        progress.setSpacing(12)
        self._progress = ThreadProgress(200)
        progress.addWidget(self._progress)
        self._status = label("Mise en page du livre...", px=15, color=theme.MUTED)
        progress.addWidget(self._status, 1)
        self._progress_row.hide()
        box.addWidget(self._progress_row)

        self._done = QWidget()
        done = QHBoxLayout(self._done)
        done.setContentsMargins(0, 0, 0, 0)
        done.setSpacing(20)
        done.addWidget(label("Ton livre est prêt.", theme.SERIF, 17, color=theme.LEAF_TEXT))
        open_book = link_button("Ouvrir le livre")
        open_book.clicked.connect(self._open_book)
        done.addWidget(open_book)
        open_folder = link_button("Afficher le dossier")
        open_folder.clicked.connect(self._open_folder)
        done.addWidget(open_folder)
        done.addStretch(1)
        self._done.hide()
        box.addWidget(self._done)

        self._error = label("", px=15, color=theme.RED_TEXT, wrap=True)
        self._error.hide()
        box.addWidget(self._error)

        actions = QHBoxLayout()
        actions.setSpacing(24)
        self._create = PrimaryButton("Créer le PDF")
        self._create.clicked.connect(self._choose_path)
        actions.addWidget(self._create)
        close = link_button("Fermer")
        close.clicked.connect(self.accept)
        actions.addWidget(close)
        actions.addStretch(1)
        box.addLayout(actions)

        self._fill()

    # Liste

    def _fill(self) -> None:
        cards = self._service.candidates()
        current_theme = None
        for card in sorted(cards, key=lambda c: (c.theme_id, c.recorded_at)):
            if card.theme_label != current_theme:
                current_theme = card.theme_label
                self._list.addSpacing(6)
                self._list.addWidget(eyebrow(card.theme_label))
            self._list.addWidget(self._checkbox(card))
        self._list.addStretch(1)
        if not cards:
            self._list.insertWidget(
                0,
                label(
                    "Aucun récit n'a encore son texte. Enregistre une interview : elle pourra "
                    "entrer dans le livre une fois transcrite.",
                    theme.SERIF,
                    16,
                    color=theme.MUTED,
                    italic=True,
                    wrap=True,
                ),
            )
        self._update_count()

    def _checkbox(self, card: StoryCard) -> QCheckBox:
        full = f"{card.question}  ·  {card.person_name}"
        font = theme.font(theme.SERIF, 16)
        text = QFontMetrics(font).elidedText(full, Qt.TextElideMode.ElideRight, CHECK_TEXT_WIDTH)
        box = QCheckBox(text)
        box.setFont(font)
        box.setToolTip(full)
        box.setCursor(Qt.CursorShape.PointingHandCursor)
        box.setChecked(card.in_book)
        box.toggled.connect(lambda checked, story_id=card.id: self._toggle(story_id, checked))
        self._boxes[card.id] = box
        return box

    def _toggle(self, story_id: int, checked: bool) -> None:
        self._service.set_included(story_id, checked)
        self._update_count()

    def _check_all(self, checked: bool) -> None:
        for box in self._boxes.values():
            box.setChecked(checked)

    def _update_count(self) -> None:
        chosen = sum(1 for b in self._boxes.values() if b.isChecked())
        self._count.setText(plural(chosen, "récit choisi", "récits choisis"))
        self._create.setEnabled(chosen > 0)

    # Création

    def _choose_path(self) -> None:
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer le livre", str(default_book_path()), "PDF (*.pdf)"
        )
        if chosen:
            path = Path(chosen)
            self.export_to(path if path.suffix.lower() == ".pdf" else path.with_suffix(".pdf"))

    def export_to(self, path: Path) -> None:
        """Rassemble le livre puis le met en page dans un thread (l'écran reste utilisable)."""
        book = self._service.gather()
        self._path = path
        self._error.hide()
        self._done.hide()
        self._create.setEnabled(False)
        self._progress_row.show()
        self._progress.set_value(None)
        assets = BookAssets(theme.FONTS, theme.IMAGES / "logo.png")
        self._task = BackgroundTask(lambda: render_book(book, path, assets), self)
        self._task.succeeded.connect(self._finished, Qt.ConnectionType.QueuedConnection)
        self._task.failed.connect(self._failed, Qt.ConnectionType.QueuedConnection)
        self._task.start()

    def _finished(self) -> None:
        self._progress_row.hide()
        self._done.show()
        self._update_count()
        if self._path is not None:
            self.created.emit(self._path)

    def _failed(self, message: str) -> None:
        self._progress_row.hide()
        self._error.setText(f"Le livre n'a pas pu être créé. ({message})")
        self._error.show()
        self._update_count()

    def _open_book(self) -> None:
        if self._path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._path)))

    def _open_folder(self) -> None:
        if self._path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._path.parent)))
