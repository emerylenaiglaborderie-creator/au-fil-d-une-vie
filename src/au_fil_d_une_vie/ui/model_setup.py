"""Fenêtre de premier lancement : télécharger le modèle de transcription (refusable)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QWidget

from au_fil_d_une_vie.services.whisper import APPROX_SIZE_MB, WhisperModels
from au_fil_d_une_vie.ui import theme
from au_fil_d_une_vie.ui.bridge import BackgroundTask
from au_fil_d_une_vie.ui.widgets import PrimaryButton, ThreadProgress, label, link_button


class ModelSetupDialog(QDialog):
    """Explique pourquoi un téléchargement est nécessaire et laisse le choix."""

    installed = Signal()

    def __init__(self, models: WhisperModels, size: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._models = models
        self._size = size
        self.setWindowTitle("Au fil d'une vie")
        self.setModal(True)
        self.setFixedWidth(560)
        self.setStyleSheet(f"QDialog {{ background: {theme.CREAM}; }}")

        box = QVBoxLayout(self)
        box.setContentsMargins(40, 32, 40, 32)
        box.setSpacing(14)
        box.addWidget(label("Une dernière étape", theme.SCRIPT, 56, color=theme.RED_TEXT))
        mb = APPROX_SIZE_MB.get(size, 500)
        box.addWidget(
            label(
                "Pour transformer tes enregistrements en texte, l'application a besoin d'un "
                f"modèle de reconnaissance de la voix (environ {mb} Mo).",
                theme.SERIF,
                18,
                wrap=True,
            )
        )
        box.addWidget(
            label(
                "Il est téléchargé une seule fois. C'est le seul moment où l'application utilise "
                "internet : ensuite, tout se fait sur cet ordinateur, même sans connexion.",
                px=15,
                color=theme.MUTED,
                wrap=True,
            )
        )
        box.addSpacing(8)

        self._progress_row = QWidget()
        row = QHBoxLayout(self._progress_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        self._progress = ThreadProgress(220)
        row.addWidget(self._progress)
        self._status = label("Téléchargement en cours...", px=15, color=theme.MUTED)
        row.addWidget(self._status, 1)
        self._progress_row.hide()
        box.addWidget(self._progress_row)

        self._error = label("", px=15, color=theme.RED_TEXT, wrap=True)
        self._error.hide()
        box.addWidget(self._error)

        actions = QHBoxLayout()
        actions.setSpacing(24)
        self._download = PrimaryButton("Télécharger le modèle")
        self._download.clicked.connect(self._start)
        actions.addWidget(self._download)
        self._later = link_button("Plus tard")
        self._later.clicked.connect(self.reject)
        actions.addWidget(self._later)
        actions.addStretch(1)
        box.addLayout(actions)
        box.addWidget(
            label(
                "Sans ce modèle, tu peux quand même enregistrer : les textes seront préparés "
                "dès qu'il sera installé.",
                theme.SERIF,
                14,
                color=theme.MUTED,
                italic=True,
                wrap=True,
            )
        )

    def _start(self) -> None:
        self._download.setEnabled(False)
        self._later.setEnabled(False)
        self._error.hide()
        self._progress_row.show()
        self._progress.set_value(None)
        self._task = BackgroundTask(lambda: self._models.download(self._size), self)
        self._task.succeeded.connect(self._done, Qt.ConnectionType.QueuedConnection)
        self._task.failed.connect(self._fail, Qt.ConnectionType.QueuedConnection)
        self._task.start()

    def _done(self) -> None:
        self._progress.set_value(1.0)
        self.installed.emit()
        self.accept()

    def _fail(self, message: str) -> None:
        self._progress_row.hide()
        self._error.setText(
            f"Le téléchargement n'a pas abouti. Vérifie ta connexion et réessaie. ({message})"
        )
        self._error.show()
        self._download.setEnabled(True)
        self._later.setEnabled(True)
