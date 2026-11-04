"""Objets métier partagés par les services et les repositories."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class StoryStatus(StrEnum):
    """Avancement du traitement d'un récit."""

    RECORDED = "recorded"
    TRANSCRIBING = "transcribing"
    TRANSCRIBED = "transcribed"


@dataclass(frozen=True, slots=True)
class Profile:
    """Le jeune qui mène la quête."""

    first_name: str
    under_15: bool
    parental_consent_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Person:
    """Proche interrogé."""

    id: int
    display_name: str
    relationship: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Theme:
    """Piste à explorer."""

    id: int
    slug: str
    label: str
    position: int


@dataclass(frozen=True, slots=True)
class Question:
    """Question rattachée à une piste."""

    id: int
    theme_id: int
    text: str
    position: int


@dataclass(frozen=True, slots=True)
class Story:
    """Un récit enregistré."""

    id: int
    person_id: int
    question_id: int
    recorded_at: datetime
    duration_s: float
    audio_path: Path
    is_hidden: bool
    status: StoryStatus


@dataclass(frozen=True, slots=True)
class Consent:
    """Accord du proche pour un enregistrement."""

    id: int
    story_id: int
    given_at: datetime
    statement: str


@dataclass(frozen=True, slots=True)
class Transcript:
    """Texte brut et version livre d'un récit."""

    story_id: int
    raw_text: str
    book_text: str | None
    language: str
    updated_at: datetime

    @property
    def display_text(self) -> str:
        """Version livre si elle existe, sinon texte brut."""
        return self.book_text if self.book_text is not None else self.raw_text


@dataclass(frozen=True, slots=True)
class Keyword:
    """Mot-clé identifié par son lemme."""

    id: int
    lemma: str
    label: str


@dataclass(frozen=True, slots=True)
class StoryKeyword:
    """Mot-clé rattaché à un récit."""

    story_id: int
    keyword: Keyword
    weight: float
    is_validated: bool


@dataclass(frozen=True, slots=True)
class Note:
    """« Mon carnet » : ce que l'utilisateur retient d'un récit."""

    story_id: int
    content: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StoryRow:
    """Un récit avec ce qu'il faut pour l'afficher dans une liste (une seule requête)."""

    story: Story
    person_name: str
    question_text: str
    theme_id: int
    theme_label: str
    text: str | None
