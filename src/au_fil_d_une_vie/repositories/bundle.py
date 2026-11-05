"""Ensemble des repositories d'une même connexion.

Les services et l'assemblage de l'application manipulent cet ensemble plutôt
qu'une connexion SQLite : seuls les repositories connaissent la base.
"""

import sqlite3
from pathlib import Path

from au_fil_d_une_vie.repositories.database import connect
from au_fil_d_une_vie.repositories.keywords import KeywordRepository
from au_fil_d_une_vie.repositories.notes import NoteRepository
from au_fil_d_une_vie.repositories.people import PersonRepository
from au_fil_d_une_vie.repositories.profile import ProfileRepository
from au_fil_d_une_vie.repositories.stories import StoryRepository
from au_fil_d_une_vie.repositories.sync import SyncRepository
from au_fil_d_une_vie.repositories.themes import ThemeRepository
from au_fil_d_une_vie.repositories.transcripts import TranscriptRepository


class Repositories:
    """Les repositories partageant une connexion (une connexion par thread)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.keywords = KeywordRepository(conn)
        self.notes = NoteRepository(conn)
        self.people = PersonRepository(conn)
        self.profile = ProfileRepository(conn)
        self.stories = StoryRepository(conn)
        self.sync = SyncRepository(conn)
        self.themes = ThemeRepository(conn)
        self.transcripts = TranscriptRepository(conn)

    @classmethod
    def open(cls, path: Path | str) -> "Repositories":
        """Ouvre la base (migrations comprises) et prépare les repositories."""
        return cls(connect(path))

    def close(self) -> None:
        self._conn.close()
