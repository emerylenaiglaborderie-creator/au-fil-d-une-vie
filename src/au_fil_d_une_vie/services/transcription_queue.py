"""File d'attente des transcriptions, traitée dans un thread à part.

Le thread ouvre sa propre connexion SQLite (une connexion ne se partage pas entre
threads) et son propre moteur de transcription, chargé une seule fois.
Les rappels (`on_progress`, `on_finished`, `on_failed`) sont appelés depuis ce
thread : l'interface les relaie vers son propre thread (voir ui/bridge.py).
"""

import logging
import queue
import sqlite3
import threading
from collections.abc import Callable
from pathlib import Path

from au_fil_d_une_vie.models import StoryStatus
from au_fil_d_une_vie.repositories import (
    KeywordRepository,
    PersonRepository,
    StoryRepository,
    TranscriptRepository,
)
from au_fil_d_une_vie.services.keywords import KeywordService, TextAnalyzer
from au_fil_d_une_vie.services.transcription import Transcriber

log = logging.getLogger(__name__)

ProgressHandler = Callable[[int, float], None]
FinishedHandler = Callable[[int], None]
FailedHandler = Callable[[int, str], None]

_STOP = -1


class TranscriptionQueue:
    def __init__(
        self,
        connect: Callable[[], sqlite3.Connection],
        audio_dir: Path,
        transcriber_factory: Callable[[], Transcriber],
        analyzer_factory: Callable[[], TextAnalyzer | None] = lambda: None,
    ) -> None:
        self._connect = connect
        self._audio_dir = audio_dir
        self._transcriber_factory = transcriber_factory
        self._analyzer_factory = analyzer_factory
        self._queue: queue.Queue[int] = queue.Queue()
        self._lock = threading.Lock()
        self._waiting: list[int] = []
        self._current: int | None = None
        self._thread: threading.Thread | None = None
        self.on_progress: ProgressHandler | None = None
        self.on_finished: FinishedHandler | None = None
        self.on_failed: FailedHandler | None = None

    # Commandes (thread de l'interface)

    def enqueue(self, story_id: int) -> None:
        with self._lock:
            if story_id in self._waiting or story_id == self._current:
                return
            self._waiting.append(story_id)
        self._queue.put(story_id)
        self._ensure_worker()

    def resume_pending(self) -> list[int]:
        """Remet en file les récits pas encore transcrits (y compris ceux interrompus)."""
        conn = self._connect()
        try:
            ids = StoryRepository(conn).ids_with_status(
                StoryStatus.RECORDED, StoryStatus.TRANSCRIBING
            )
        finally:
            conn.close()
        for story_id in ids:
            self.enqueue(story_id)
        return ids

    def snapshot(self) -> tuple[int | None, int]:
        """(récit en cours, nombre de récits en attente derrière lui)."""
        with self._lock:
            return self._current, len(self._waiting)

    def shutdown(self, timeout: float | None = None) -> None:
        """Arrête le thread après le récit en cours."""
        if self._thread is not None and self._thread.is_alive():
            self._queue.put(_STOP)
            self._thread.join(timeout)

    # Thread de travail

    def _ensure_worker(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, name="transcription", daemon=True)
            self._thread.start()

    def _run(self) -> None:
        conn = self._connect()
        transcriber: Transcriber | None = None
        analyzer: TextAnalyzer | None = None
        analyzer_loaded = False
        try:
            while True:
                story_id = self._queue.get()
                if story_id == _STOP:
                    return
                with self._lock:
                    if story_id in self._waiting:
                        self._waiting.remove(story_id)
                    self._current = story_id
                try:
                    if transcriber is None:
                        transcriber = self._transcriber_factory()
                    if not analyzer_loaded:
                        analyzer = self._load_analyzer()
                        analyzer_loaded = True
                    self._process(conn, transcriber, analyzer, story_id)
                except Exception as error:  # noqa: BLE001 (on signale, la file continue)
                    log.exception("Transcription du récit %s impossible", story_id)
                    StoryRepository(conn).set_status(story_id, StoryStatus.RECORDED)
                    if self.on_failed is not None:
                        self.on_failed(story_id, str(error) or type(error).__name__)
                else:
                    if self.on_finished is not None:
                        self.on_finished(story_id)
                finally:
                    with self._lock:
                        self._current = None
        finally:
            conn.close()

    def _load_analyzer(self) -> TextAnalyzer | None:
        try:
            return self._analyzer_factory()
        except Exception:  # noqa: BLE001 (sans analyseur, pas de mots-clés proposés)
            log.exception("Analyseur de mots-clés indisponible")
            return None

    def _process(
        self,
        conn: sqlite3.Connection,
        transcriber: Transcriber,
        analyzer: TextAnalyzer | None,
        story_id: int,
    ) -> None:
        stories = StoryRepository(conn)
        story = stories.get(story_id)
        if story is None:
            return  # supprimé entre-temps
        stories.set_status(story_id, StoryStatus.TRANSCRIBING)

        # Les noms des proches aident à les écrire correctement dans le texte.
        names = " ".join(p.display_name for p in PersonRepository(conn).list_all())

        def progress(fraction: float) -> None:
            if self.on_progress is not None:
                self.on_progress(story_id, fraction)

        result = transcriber.transcribe(self._audio_dir / story.audio_path, progress, names or None)
        transcripts = TranscriptRepository(conn)
        transcripts.save_raw(story_id, result.text, result.language)
        stories.set_status(story_id, StoryStatus.TRANSCRIBED)

        if analyzer is not None and result.text.strip():
            try:
                KeywordService(analyzer, transcripts, KeywordRepository(conn)).suggest(story_id)
            except Exception:  # noqa: BLE001 (le texte est gardé même sans mots-clés)
                log.exception("Mots-clés du récit %s non proposés", story_id)
