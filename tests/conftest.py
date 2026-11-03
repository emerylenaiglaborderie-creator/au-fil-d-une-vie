import os
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

# Tests d'interface sans fenêtre à l'écran, en local comme en CI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from au_fil_d_une_vie.models import Person, Question, Story
from au_fil_d_une_vie.repositories import (
    PersonRepository,
    StoryRepository,
    ThemeRepository,
    connect,
)
from au_fil_d_une_vie.services.demo import DEMO_PATH

CONSENT = "Mamie Yvonne sait qu'elle est enregistrée et est d'accord."


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    connection = connect(":memory:")
    yield connection
    connection.close()


@dataclass
class Scene:
    """Petit jeu de données fictif : une piste, deux questions, deux proches."""

    yvonne: Person
    papa: Person
    q_ecole: Question
    q_jeux: Question

    def story(self, conn: sqlite3.Connection, person: Person, question: Question) -> Story:
        return StoryRepository(conn).create(
            person_id=person.id,
            question_id=question.id,
            duration_s=252.0,
            audio_path=Path("2026/recit.wav"),
            consent_statement=CONSENT,
        )


@pytest.fixture
def scene(conn: sqlite3.Connection) -> Scene:
    themes = ThemeRepository(conn)
    enfance = themes.add_theme("enfance", "Enfance", 1)
    people = PersonRepository(conn)
    return Scene(
        yvonne=people.add("Mamie Yvonne", "grand-mère"),
        papa=people.add("Papa", "père"),
        q_ecole=themes.add_question(enfance.id, "Comment était ton école ?", 1),
        q_jeux=themes.add_question(enfance.id, "À quoi jouais-tu ?", 2),
    )


@pytest.fixture
def demo_path() -> Path:
    return DEMO_PATH
