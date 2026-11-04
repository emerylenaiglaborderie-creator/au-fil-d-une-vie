"""Catalogue des pistes et questions, chargé dans toute nouvelle base."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from au_fil_d_une_vie.repositories import ThemeRepository

TRACKS_PATH = Path(__file__).resolve().parent.parent / "data" / "pistes.json"


def seed_tracks(conn: sqlite3.Connection, path: Path = TRACKS_PATH) -> dict[str, int]:
    """Ajoute les pistes, questions et relances si la base n'en a pas encore.

    Retourne l'identifiant de chaque question selon sa clé (utile au jeu de démo).
    """
    themes_repo = ThemeRepository(conn)
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    questions: dict[str, int] = {}
    if themes_repo.list_themes():
        by_text = {
            q.text: q.id for t in themes_repo.list_themes() for q in themes_repo.questions_for(t.id)
        }
        for theme in data["themes"]:
            for question in theme["questions"]:
                if question["text"] in by_text:
                    questions[question["key"]] = by_text[question["text"]]
        return questions
    for position, theme in enumerate(data["themes"], start=1):
        theme_id = themes_repo.add_theme(theme["slug"], theme["label"], position).id
        for q_position, question in enumerate(theme["questions"], start=1):
            question_id = themes_repo.add_question(theme_id, question["text"], q_position).id
            questions[question["key"]] = question_id
            for f_position, text in enumerate(question.get("follow_ups", []), start=1):
                themes_repo.add_follow_up(question_id, text, f_position)
    return questions
