"""Assemblage de l'application : connexion, repositories et services.

C'est le seul endroit où les trois couches se rencontrent. L'interface reçoit
uniquement l'objet `Services`.
"""

import sqlite3
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from au_fil_d_une_vie import config
from au_fil_d_une_vie.repositories import (
    KeywordRepository,
    PersonRepository,
    ProfileRepository,
    StoryRepository,
    ThemeRepository,
    connect,
)
from au_fil_d_une_vie.services.demo import load_demo
from au_fil_d_une_vie.services.links import LinkService
from au_fil_d_une_vie.services.quest import QuestService
from au_fil_d_une_vie.services.recording import AudioInput, RecordingService


def _qt_microphone() -> AudioInput:
    # Import tardif : QtMultimedia n'est chargé que si l'on enregistre vraiment.
    from au_fil_d_une_vie.services.qt_audio import QtAudioInput

    return QtAudioInput()


@dataclass
class Services:
    quest: QuestService
    links: LinkService
    recording: RecordingService
    db_path: Path
    audio_dir: Path


def build_services(
    conn: sqlite3.Connection,
    db_path: Path,
    audio_dir: Path,
    microphone: Callable[[], AudioInput] = _qt_microphone,
) -> Services:
    keywords = KeywordRepository(conn)
    return Services(
        quest=QuestService(ProfileRepository(conn), PersonRepository(conn), ThemeRepository(conn)),
        links=LinkService(keywords),
        recording=RecordingService(StoryRepository(conn), audio_dir, microphone),
        db_path=db_path,
        audio_dir=audio_dir,
    )


def open_services(
    demo: bool = False, microphone: Callable[[], AudioInput] = _qt_microphone
) -> Services:
    """Base de l'utilisateur, ou base temporaire remplie avec le jeu de démo."""
    if demo:
        folder = Path(tempfile.mkdtemp(prefix="au-fil-demo-"))
        db_path, audio_dir = folder / "demo.db", folder / "audio"
        conn = connect(db_path)
        load_demo(conn)
    else:
        db_path, audio_dir = config.db_path(), config.audio_dir()
        conn = connect(db_path)
    return build_services(conn, db_path, audio_dir, microphone)
