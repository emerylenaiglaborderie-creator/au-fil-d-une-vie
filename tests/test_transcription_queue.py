import sqlite3
import threading
from pathlib import Path

import pytest

from au_fil_d_une_vie.models import StoryStatus
from au_fil_d_une_vie.repositories import (
    KeywordRepository,
    PersonRepository,
    StoryRepository,
    ThemeRepository,
    TranscriptRepository,
    connect,
)
from au_fil_d_une_vie.services.transcription import ProgressCallback, TranscriptionResult
from au_fil_d_une_vie.services.transcription_queue import TranscriptionQueue
from tests.test_keywords import AnalyseurSimple

TEXTE = "On allait à l'école en sabots, même l'hiver."


class FauxWhisper:
    """Transcrit toujours le même texte, en signalant sa progression."""

    def __init__(self, echec_pour: set[str] | None = None) -> None:
        self.indices: list[str | None] = []
        self.echec_pour = echec_pour or set()

    def transcribe(
        self,
        audio_path: Path,
        on_progress: ProgressCallback | None = None,
        hotwords: str | None = None,
    ) -> TranscriptionResult:
        self.indices.append(hotwords)
        if audio_path.name in self.echec_pour:
            raise RuntimeError("fichier illisible")
        for fraction in (0.25, 0.5, 1.0):
            if on_progress:
                on_progress(fraction)
        return TranscriptionResult(text=TEXTE, language="fr", duration_s=3.0)


@pytest.fixture
def base(tmp_path: Path) -> Path:
    chemin = tmp_path / "base.db"
    conn = connect(chemin)
    themes = ThemeRepository(conn)
    enfance = themes.add_theme("enfance", "Enfance")
    question = themes.add_question(enfance.id, "Comment était ton école ?")
    yvonne = PersonRepository(conn).add("Mamie Yvonne", "grand-mère")
    stories = StoryRepository(conn)
    for nom in ("a.wav", "b.wav"):
        stories.create(yvonne.id, question.id, 3.0, Path(nom), "accord")
    conn.close()
    return chemin


class Suivi:
    """Collecte les rappels de la file et attend la fin d'un nombre de récits."""

    def __init__(self, file: TranscriptionQueue, attendus: int) -> None:
        self.progression: list[tuple[int, float]] = []
        self.finis: list[int] = []
        self.echecs: list[tuple[int, str]] = []
        self._attendus = attendus
        self._fin = threading.Event()
        file.on_progress = lambda sid, f: self.progression.append((sid, f))
        file.on_finished = self._termine
        file.on_failed = lambda sid, msg: (self.echecs.append((sid, msg)), self._compte())

    def _termine(self, story_id: int) -> None:
        self.finis.append(story_id)
        self._compte()

    def _compte(self) -> None:
        if len(self.finis) + len(self.echecs) >= self._attendus:
            self._fin.set()

    def attendre(self) -> None:
        assert self._fin.wait(10), "la file ne s'est pas terminée"


def _file(base: Path, whisper: FauxWhisper, analyseur: bool = True) -> TranscriptionQueue:
    return TranscriptionQueue(
        lambda: connect(base),
        base.parent / "audio",
        lambda: whisper,
        (lambda: AnalyseurSimple()) if analyseur else (lambda: None),
    )


def _lire(base: Path) -> sqlite3.Connection:
    return connect(base)


def test_les_recits_en_attente_sont_transcrits(base: Path) -> None:
    whisper = FauxWhisper()
    file = _file(base, whisper)
    suivi = Suivi(file, attendus=2)

    assert file.resume_pending() == [1, 2]
    suivi.attendre()
    file.shutdown(5)

    assert sorted(suivi.finis) == [1, 2]
    assert (1, 1.0) in suivi.progression
    conn = _lire(base)
    texte = TranscriptRepository(conn).get(1)
    assert texte is not None and texte.raw_text == TEXTE
    assert StoryRepository(conn).ids_with_status(StoryStatus.TRANSCRIBED) == [1, 2]
    mots = {m.keyword.lemma for m in KeywordRepository(conn).for_story(1)}
    assert "sabots" in mots


def test_les_noms_des_proches_aident_la_transcription(base: Path) -> None:
    whisper = FauxWhisper()
    file = _file(base, whisper)
    suivi = Suivi(file, attendus=1)
    file.enqueue(1)
    suivi.attendre()
    file.shutdown(5)
    assert whisper.indices == ["Mamie Yvonne"]


def test_un_echec_n_arrete_pas_la_file(base: Path) -> None:
    file = _file(base, FauxWhisper(echec_pour={"a.wav"}))
    suivi = Suivi(file, attendus=2)
    file.resume_pending()
    suivi.attendre()
    file.shutdown(5)

    assert suivi.echecs == [(1, "fichier illisible")]
    assert suivi.finis == [2]
    conn = _lire(base)
    assert StoryRepository(conn).ids_with_status(StoryStatus.RECORDED) == [1]


def test_un_recit_interrompu_est_repris(base: Path) -> None:
    conn = _lire(base)
    StoryRepository(conn).set_status(1, StoryStatus.TRANSCRIBING)  # l'appli a été fermée
    StoryRepository(conn).set_status(2, StoryStatus.TRANSCRIBED)
    conn.close()
    file = _file(base, FauxWhisper())
    suivi = Suivi(file, attendus=1)
    assert file.resume_pending() == [1]
    suivi.attendre()
    file.shutdown(5)


def test_un_recit_n_est_mis_en_file_qu_une_fois(base: Path) -> None:
    file = _file(base, FauxWhisper())
    bloque = threading.Event()
    file._transcriber_factory = lambda: (bloque.wait(5), FauxWhisper())[1]  # type: ignore[method-assign]
    file.enqueue(1)
    file.enqueue(2)
    file.enqueue(2)
    assert file.snapshot()[1] <= 2
    suivi = Suivi(file, attendus=2)
    bloque.set()
    suivi.attendre()
    file.shutdown(5)
    assert sorted(suivi.finis) == [1, 2]


def test_sans_analyseur_le_texte_est_quand_meme_garde(base: Path) -> None:
    file = _file(base, FauxWhisper(), analyseur=False)
    suivi = Suivi(file, attendus=1)
    file.enqueue(1)
    suivi.attendre()
    file.shutdown(5)
    conn = _lire(base)
    assert TranscriptRepository(conn).get(1) is not None
    assert KeywordRepository(conn).for_story(1) == []
