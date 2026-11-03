"""Couche d'accès aux données : SQLite uniquement."""

from au_fil_d_une_vie.repositories.database import connect
from au_fil_d_une_vie.repositories.keywords import KeywordCandidate, KeywordRepository
from au_fil_d_une_vie.repositories.notes import NoteRepository
from au_fil_d_une_vie.repositories.people import PersonRepository
from au_fil_d_une_vie.repositories.profile import ProfileRepository
from au_fil_d_une_vie.repositories.stories import StoryRepository
from au_fil_d_une_vie.repositories.themes import ThemeRepository
from au_fil_d_une_vie.repositories.transcripts import TranscriptRepository

__all__ = [
    "KeywordCandidate",
    "KeywordRepository",
    "NoteRepository",
    "PersonRepository",
    "ProfileRepository",
    "StoryRepository",
    "ThemeRepository",
    "TranscriptRepository",
    "connect",
]
