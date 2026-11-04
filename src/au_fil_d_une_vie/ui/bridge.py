"""Relais entre les threads de travail et l'interface.

Les services appellent leurs rappels depuis un thread de travail ; ces signaux Qt
les ramènent dans le thread de l'interface (connexion en file automatique).
"""

import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal

from au_fil_d_une_vie.services.transcription_queue import TranscriptionQueue


class TranscriptionBridge(QObject):
    progress = Signal(int, float)
    finished = Signal(int)
    failed = Signal(int, str)

    def __init__(self, queue: TranscriptionQueue, parent: QObject | None = None) -> None:
        super().__init__(parent)
        queue.on_progress = self.progress.emit
        queue.on_finished = self.finished.emit
        queue.on_failed = self.failed.emit


class BackgroundTask(QObject):
    """Lance une fonction dans un thread et signale sa fin à l'interface."""

    succeeded = Signal()
    failed = Signal(str)

    def __init__(self, work: Callable[[], object], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._work = work

    def start(self) -> None:
        threading.Thread(target=self._run, name="tache", daemon=True).start()

    def _run(self) -> None:
        try:
            self._work()
        except Exception as error:  # noqa: BLE001 (affiché à l'utilisateur)
            self.failed.emit(str(error) or type(error).__name__)
        else:
            self.succeeded.emit()
