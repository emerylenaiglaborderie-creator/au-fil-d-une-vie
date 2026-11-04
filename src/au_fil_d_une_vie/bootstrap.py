"""Assemblage de l'application : connexion, repositories et services.

C'est le seul endroit où les trois couches se rencontrent. L'interface reçoit
uniquement l'objet `Services`.
"""

import functools
import sqlite3
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from au_fil_d_une_vie import config, i18n
from au_fil_d_une_vie.repositories import (
    KeywordRepository,
    NoteRepository,
    PersonRepository,
    ProfileRepository,
    StoryRepository,
    ThemeRepository,
    TranscriptRepository,
    connect,
)
from au_fil_d_une_vie.services.book import BookService
from au_fil_d_une_vie.services.demo import load_demo
from au_fil_d_une_vie.services.graph import GraphService
from au_fil_d_une_vie.services.keywords import Term, TextAnalyzer
from au_fil_d_une_vie.services.links import LinkService
from au_fil_d_une_vie.services.people import PeopleService
from au_fil_d_une_vie.services.profile import ProfileService
from au_fil_d_une_vie.services.quest import QuestService
from au_fil_d_une_vie.services.recording import AudioInput, RecordingService
from au_fil_d_une_vie.services.settings import SettingsStore
from au_fil_d_une_vie.services.stories import StoryService
from au_fil_d_une_vie.services.tracks import TrackService, seed_tracks
from au_fil_d_une_vie.services.transcription import Transcriber
from au_fil_d_une_vie.services.transcription_queue import TranscriptionQueue
from au_fil_d_une_vie.services.whisper import DEFAULT_SIZE, WhisperModels


@functools.cache
def _spacy(code: str) -> TextAnalyzer | None:
    """Analyseur spaCy de la langue, si son modèle est installé (chargé une seule fois)."""
    import importlib.util

    from au_fil_d_une_vie.services.spacy_analyzer import MODELS, SpacyAnalyzer

    model = MODELS.get(code)
    return SpacyAnalyzer(model, code) if model and importlib.util.find_spec(model) else None


class CurrentLanguageAnalyzer:
    """Analyseur qui suit la langue de l'interface (le français si l'anglais manque)."""

    def terms(self, text: str) -> list[Term]:
        analyzer = _spacy(i18n.language()) or _spacy("fr")
        return analyzer.terms(text) if analyzer else []


def _analyzer() -> TextAnalyzer | None:
    return CurrentLanguageAnalyzer() if _spacy("fr") or _spacy("en") else None


def _qt_microphone() -> AudioInput:
    # Import tardif : QtMultimedia n'est chargé que si l'on enregistre vraiment.
    from au_fil_d_une_vie.services.qt_audio import QtAudioInput

    return QtAudioInput()


@dataclass
class Services:
    quest: QuestService
    profile: ProfileService
    people: PeopleService
    tracks: TrackService
    links: LinkService
    stories: StoryService
    graph: GraphService
    book: BookService
    recording: RecordingService
    transcription: TranscriptionQueue
    models: WhisperModels
    model_size: str
    settings: SettingsStore
    db_path: Path
    audio_dir: Path

    def transcription_ready(self) -> bool:
        return self.models.is_installed(self.model_size)


def build_services(
    conn: sqlite3.Connection,
    db_path: Path,
    audio_dir: Path,
    microphone: Callable[[], AudioInput] = _qt_microphone,
    models_dir: Path | None = None,
    model_size: str = DEFAULT_SIZE,
    settings_path: Path | None = None,
) -> Services:
    keywords = KeywordRepository(conn)
    links = LinkService(keywords)
    stories = StoryService(
        StoryRepository(conn),
        TranscriptRepository(conn),
        keywords,
        NoteRepository(conn),
        links,
        audio_dir,
        _analyzer(),
    )
    models = WhisperModels(models_dir or config.models_dir())

    def transcriber() -> Transcriber:
        from au_fil_d_une_vie.services.whisper import FasterWhisperTranscriber

        return FasterWhisperTranscriber(models.path(model_size))

    return Services(
        quest=QuestService(ProfileRepository(conn), PersonRepository(conn), ThemeRepository(conn)),
        links=links,
        profile=ProfileService(ProfileRepository(conn)),
        people=PeopleService(PersonRepository(conn), StoryRepository(conn), audio_dir),
        tracks=TrackService(ThemeRepository(conn)),
        stories=stories,
        graph=GraphService(StoryRepository(conn), keywords),
        book=BookService(stories, ProfileRepository(conn), ThemeRepository(conn)),
        recording=RecordingService(StoryRepository(conn), audio_dir, microphone),
        transcription=TranscriptionQueue(
            lambda: connect(db_path), audio_dir, transcriber, _analyzer
        ),
        models=models,
        model_size=model_size,
        settings=SettingsStore(settings_path or config.settings_path()),
        db_path=db_path,
        audio_dir=audio_dir,
    )


def open_services(
    demo: bool = False,
    microphone: Callable[[], AudioInput] = _qt_microphone,
    model_size: str = DEFAULT_SIZE,
    models_dir: Path | None = None,
    settings_path: Path | None = None,
) -> Services:
    """Base de l'utilisateur, ou base temporaire remplie avec le jeu de démo."""
    if demo:
        folder = Path(tempfile.mkdtemp(prefix="au-fil-demo-"))
        db_path, audio_dir = folder / "demo.db", folder / "audio"
        conn = connect(db_path)
        load_demo(conn, analyzer=_spacy("fr"))  # le jeu de démo est en français
    else:
        db_path, audio_dir = config.db_path(), config.audio_dir()
        conn = connect(db_path)
        # Au tout premier lancement, les pistes sont chargées à la fin de l'accueil,
        # dans la langue choisie ; ici, seulement pour un profil qui n'en aurait pas.
        if ProfileRepository(conn).get() is not None:
            seed_tracks(conn)
    return build_services(
        conn, db_path, audio_dir, microphone, models_dir, model_size, settings_path
    )
