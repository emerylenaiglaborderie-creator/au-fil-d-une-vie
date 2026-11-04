"""Accès aux récits et aux consentements associés."""

import sqlite3
from datetime import datetime
from pathlib import Path

from au_fil_d_une_vie.models import Consent, Story, StoryRow, StoryStatus
from au_fil_d_une_vie.repositories.database import now_iso, parse_iso


def _to_story(row: sqlite3.Row) -> Story:
    return Story(
        id=row["id"],
        person_id=row["person_id"],
        question_id=row["question_id"],
        recorded_at=parse_iso(row["recorded_at"]),
        duration_s=row["duration_s"],
        audio_path=Path(row["audio_path"]),
        is_hidden=bool(row["is_hidden"]),
        status=StoryStatus(row["status"]),
        in_book=bool(row["in_book"]),
    )


class StoryRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        person_id: int,
        question_id: int,
        duration_s: float,
        audio_path: Path,
        consent_statement: str,
        recorded_at: datetime | None = None,
    ) -> Story:
        """Enregistre un récit et le consentement du proche dans la même transaction.

        Un récit ne peut donc jamais exister sans consentement.
        """
        if not consent_statement.strip():
            raise ValueError("Le consentement du proche est obligatoire.")
        recorded = recorded_at.isoformat(timespec="seconds") if recorded_at else now_iso()
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO story (person_id, question_id, recorded_at, duration_s, audio_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (person_id, question_id, recorded, duration_s, audio_path.as_posix()),
            )
            story_id = cursor.lastrowid or 0
            self._conn.execute(
                "INSERT INTO consent (story_id, given_at, statement) VALUES (?, ?, ?)",
                (story_id, recorded, consent_statement),
            )
        story = self.get(story_id)
        assert story is not None
        return story

    def get(self, story_id: int) -> Story | None:
        row = self._conn.execute("SELECT * FROM story WHERE id = ?", (story_id,)).fetchone()
        return _to_story(row) if row else None

    def list_all(self, include_hidden: bool = False) -> list[Story]:
        """Récits du plus récent au plus ancien."""
        rows = self._conn.execute(
            """
            SELECT * FROM story
            WHERE ? OR is_hidden = 0
            ORDER BY recorded_at DESC, id DESC
            """,
            (int(include_hidden),),
        ).fetchall()
        return [_to_story(row) for row in rows]

    def consent_for(self, story_id: int) -> Consent | None:
        row = self._conn.execute("SELECT * FROM consent WHERE story_id = ?", (story_id,)).fetchone()
        if row is None:
            return None
        return Consent(
            id=row["id"],
            story_id=row["story_id"],
            given_at=parse_iso(row["given_at"]),
            statement=row["statement"],
        )

    def set_hidden(self, story_id: int, hidden: bool) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE story SET is_hidden = ? WHERE id = ?", (int(hidden), story_id)
            )

    def set_in_book(self, story_id: int, in_book: bool) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE story SET in_book = ? WHERE id = ?", (int(in_book), story_id)
            )

    def set_status(self, story_id: int, status: StoryStatus) -> None:
        with self._conn:
            self._conn.execute("UPDATE story SET status = ? WHERE id = ?", (status.value, story_id))

    def delete(self, story_id: int) -> None:
        """Supprime le récit et, en cascade, consentement, texte, mots-clés et note.

        Le fichier audio est supprimé par le service, pas ici.
        """
        with self._conn:
            self._conn.execute("DELETE FROM story WHERE id = ?", (story_id,))

    def ids_with_status(self, *statuses: StoryStatus) -> list[int]:
        """Récits dans l'un des statuts donnés, du plus ancien au plus récent."""
        placeholders = ", ".join("?" for _ in statuses)
        rows = self._conn.execute(
            f"SELECT id FROM story WHERE status IN ({placeholders}) ORDER BY recorded_at, id",
            [s.value for s in statuses],
        ).fetchall()
        return [row["id"] for row in rows]

    def list_rows(self, include_hidden: bool = True) -> list[StoryRow]:
        """Récits avec personne, question, piste et texte, du plus récent au plus ancien."""
        rows = self._conn.execute(
            """
            SELECT s.*, p.display_name, q.text AS question_text,
                   t.id AS theme_id, t.label AS theme_label,
                   COALESCE(tr.book_text, tr.raw_text) AS story_text
            FROM story AS s
            JOIN person AS p ON p.id = s.person_id
            JOIN question AS q ON q.id = s.question_id
            JOIN theme AS t ON t.id = q.theme_id
            LEFT JOIN transcript AS tr ON tr.story_id = s.id
            WHERE ? OR s.is_hidden = 0
            ORDER BY s.recorded_at DESC, s.id DESC
            """,
            (int(include_hidden),),
        ).fetchall()
        return [
            StoryRow(
                story=_to_story(row),
                person_name=row["display_name"],
                question_text=row["question_text"],
                theme_id=row["theme_id"],
                theme_label=row["theme_label"],
                text=row["story_text"],
            )
            for row in rows
        ]
