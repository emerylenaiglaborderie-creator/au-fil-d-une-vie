"""Chargement du jeu de démonstration fictif (data/demo.json, embarqué dans le paquet)."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from au_fil_d_une_vie.models import StoryStatus
from au_fil_d_une_vie.repositories import Repositories
from au_fil_d_une_vie.services.keywords import TextAnalyzer, lemma_of
from au_fil_d_une_vie.services.tracks import seed_tracks

DEMO_PATH = Path(__file__).resolve().parent.parent / "data" / "demo.json"
DEMO_CONSENT = "Consentement fictif (jeu de démonstration)."


def load_demo(
    repos: Repositories, path: Path = DEMO_PATH, analyzer: TextAnalyzer | None = None
) -> dict[int, list[str]]:
    """Remplit une base vide avec le jeu de démo.

    Les mots-clés indiqués dans le fichier sont enregistrés comme validés. Avec un
    analyseur, ils sont lemmatisés comme ceux des vrais récits (« sabots » devient
    « sabot »), pour que les mots proposés plus tard s'y relient.
    Retourne, pour chaque récit créé, la liste de ses mots-clés.
    """
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    profile = data["profile"]
    repos.profile.save(profile["first_name"], under_15=profile["under_15"])

    people = {
        p["key"]: repos.people.add(p["display_name"], p["relationship"]).id for p in data["people"]
    }

    questions = seed_tracks(repos.themes)

    stories_repo = repos.stories
    transcripts_repo = repos.transcripts
    keywords_repo = repos.keywords
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
        stories_repo.set_in_book(record.id, story.get("in_book", True))
        for label in story["keywords"]:
            keywords_repo.add_validated(record.id, lemma_of(label, analyzer), label)
        created[record.id] = story["keywords"]
    return created
