"""Catalogue des pistes et questions, chargé dans toute nouvelle base."""

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from au_fil_d_une_vie.models import Question, Theme
from au_fil_d_une_vie.repositories import ThemeRepository
from au_fil_d_une_vie.services.stories import fold

MAX_THEME_LENGTH = 30
MAX_QUESTION_LENGTH = 160


class TrackError(ValueError):
    """Nom vide ou déjà pris, ou piste et question qui ont déjà des récits."""


@dataclass(frozen=True, slots=True)
class QuestionInfo:
    question: Question
    story_count: int


@dataclass(frozen=True, slots=True)
class TrackInfo:
    theme: Theme
    questions: list[QuestionInfo]

    @property
    def story_count(self) -> int:
        return sum(q.story_count for q in self.questions)


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


def slugify(label: str) -> str:
    """Identifiant lisible d'une piste : « Fêtes de famille » devient « fetes-de-famille »."""
    return re.sub(r"[^a-z0-9]+", "-", fold(label)).strip("-") or "piste"


class TrackService:
    """Personnalisation des pistes et de leurs questions."""

    def __init__(self, themes: ThemeRepository) -> None:
        self._themes = themes

    def all(self) -> list[TrackInfo]:
        counts = self._themes.story_counts_by_question()
        return [
            TrackInfo(
                theme,
                [
                    QuestionInfo(q, counts.get(q.id, 0))
                    for q in self._themes.questions_for(theme.id)
                ],
            )
            for theme in self._themes.list_themes()
        ]

    # Pistes

    def add_theme(self, label: str) -> Theme:
        clean = self._check_theme(label)
        slug = base = slugify(clean)
        suffix = 2
        while self._themes.slug_exists(slug):
            slug = f"{base}-{suffix}"
            suffix += 1
        position = len(self._themes.list_themes()) + 1
        return self._themes.add_theme(slug, clean, position)

    def rename_theme(self, theme_id: int, label: str) -> None:
        self._themes.rename_theme(theme_id, self._check_theme(label, theme_id))

    def delete_theme(self, theme_id: int) -> None:
        track = self._track(theme_id)
        if track.story_count:
            raise TrackError(
                "Cette piste a déjà des récits : elle ne peut pas être supprimée. "
                "Tu peux la renommer."
            )
        self._themes.delete_theme(theme_id)

    def move_theme(self, theme_id: int, step: int) -> None:
        """Monte (step = -1) ou descend (step = +1) une piste dans la liste."""
        ids = [t.id for t in self._themes.list_themes()]
        index = ids.index(theme_id)
        target = index + step
        if 0 <= target < len(ids):
            ids[index], ids[target] = ids[target], ids[index]
            self._themes.set_theme_positions(ids)

    # Questions

    def add_question(self, theme_id: int, text: str) -> Question:
        clean = self._check_question(text, theme_id)
        position = len(self._themes.questions_for(theme_id)) + 1
        return self._themes.add_question(theme_id, clean, position)

    def edit_question(self, question_id: int, text: str) -> None:
        question = self._themes.get_question(question_id)
        if question is None:
            raise TrackError("Cette question n'existe plus.")
        self._themes.update_question(
            question_id, self._check_question(text, question.theme_id, question_id)
        )

    def delete_question(self, question_id: int) -> None:
        if self._themes.story_counts_by_question().get(question_id, 0):
            raise TrackError(
                "Cette question a déjà des récits : elle ne peut pas être supprimée. "
                "Tu peux corriger son texte."
            )
        self._themes.delete_question(question_id)

    # Vérifications

    def _track(self, theme_id: int) -> TrackInfo:
        for track in self.all():
            if track.theme.id == theme_id:
                return track
        raise TrackError("Cette piste n'existe plus.")

    def _check_theme(self, label: str, theme_id: int | None = None) -> str:
        clean = " ".join(label.split())
        if not clean:
            raise TrackError("Donne un nom à la piste.")
        if len(clean) > MAX_THEME_LENGTH:
            raise TrackError("Ce nom de piste est trop long.")
        taken = {fold(t.label) for t in self._themes.list_themes() if t.id != theme_id}
        if fold(clean) in taken:
            raise TrackError(f"La piste « {clean} » existe déjà.")
        return clean

    def _check_question(self, text: str, theme_id: int, question_id: int | None = None) -> str:
        clean = " ".join(text.split())
        if not clean:
            raise TrackError("Écris la question.")
        if len(clean) > MAX_QUESTION_LENGTH:
            raise TrackError("Cette question est trop longue.")
        taken = {fold(q.text) for q in self._themes.questions_for(theme_id) if q.id != question_id}
        if fold(clean) in taken:
            raise TrackError("Cette question est déjà dans la piste.")
        return clean
