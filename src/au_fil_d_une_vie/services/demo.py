"""Chargement du jeu de démonstration fictif (data/demo.json, embarqué dans le paquet)."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from au_fil_d_une_vie.models import StoryStatus
from au_fil_d_une_vie.repositories import (
    KeywordRepository,
    PersonRepository,
    ProfileRepository,
    StoryRepository,
    ThemeRepository,
    TranscriptRepository,
)
from au_fil_d_une_vie.services.keywords import TextAnalyzer, lemma_of

DEMO_PATH = Path(__file__).resolve().parent.parent / "data" / "demo.json"
DEMO_CONSENT = "Consentement fictif (jeu de démonstration)."


def load_demo(
    conn: sqlite3.Connection, path: Path = DEMO_PATH, analyzer: TextAnalyzer | None = None
) -> dict[int, list[str]]:
    """Remplit une base vide avec le jeu de démo.

    Les mots-clés indiqués dans le fichier sont enregistrés comme validés. Avec un
    analyseur, ils sont lemmatisés comme ceux des vrais récits (« sabots » devient
    « sabot »), pour que les mots proposés plus tard s'y relient.
    Retourne, pour chaque récit créé, la liste de ses mots-clés.
    """
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    profile = data["profile"]
    ProfileRepository(conn).save(profile["first_name"], under_15=profile["under_15"])

    people_repo = PersonRepository(conn)
    people = {
        p["key"]: people_repo.add(p["display_name"], p["relationship"]).id for p in data["people"]
    }

    themes_repo = ThemeRepository(conn)
    questions: dict[str, int] = {}
    for position, theme in enumerate(data["themes"], start=1):
        theme_id = themes_repo.add_theme(theme["slug"], theme["label"], position).id
        for q_position, question in enumerate(theme["questions"], start=1):
            question_id = themes_repo.add_question(theme_id, question["text"], q_position).id
            questions[question["key"]] = question_id
            for f_position, text in enumerate(question.get("follow_ups", []), start=1):
                themes_repo.add_follow_up(question_id, text, f_position)

    stories_repo = StoryRepository(conn)
    transcripts_repo = TranscriptRepository(conn)
    keywords_repo = KeywordRepository(conn)
    created: dict[int, list[str]] = {}
    for index, story in enumerate(data["stories"], start=1):
        record = stories_repo.create(
            person_id=people[story["person"]],
            question_id=questions[story["question"]],
            duration_s=float(story["duration_s"]),
            audio_path=Path(f"demo/recit-{index}.wav"),
            consent_statement=DEMO_CONSENT,
            recorded_at=datetime.fromisoformat(story["recorded_at"]),
        )
        transcripts_repo.save_raw(record.id, story["text"])
        stories_repo.set_status(record.id, StoryStatus.TRANSCRIBED)
        for label in story["keywords"]:
            keywords_repo.add_validated(record.id, lemma_of(label, analyzer), label)
        created[record.id] = story["keywords"]
    return created
