"""Accès aux textes des récits (brut et version livre)."""

import sqlite3

from au_fil_d_une_vie.models import Transcript
from au_fil_d_une_vie.repositories.database import now_iso, parse_iso


class TranscriptRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, story_id: int) -> Transcript | None:
        row = self._conn.execute(
            "SELECT * FROM transcript WHERE story_id = ?", (story_id,)
        ).fetchone()
        if row is None:
            return None
        return Transcript(
            story_id=row["story_id"],
            raw_text=row["raw_text"],
            book_text=row["book_text"],
            language=row["language"],
            updated_at=parse_iso(row["updated_at"]),
        )

    def save_raw(self, story_id: int, raw_text: str, language: str = "fr") -> None:
        """Enregistre le texte brut. Une version livre déjà corrigée est conservée."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO transcript (story_id, raw_text, language, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (story_id) DO UPDATE SET
                    raw_text = excluded.raw_text,
                    language = excluded.language,
                    updated_at = excluded.updated_at
                """,
                (story_id, raw_text, language, now_iso()),
            )

    def save_book_text(self, story_id: int, book_text: str) -> None:
        """Enregistre la version corrigée par l'utilisateur."""
        with self._conn:
            cursor = self._conn.execute(
                "UPDATE transcript SET book_text = ?, updated_at = ? WHERE story_id = ?",
                (book_text, now_iso(), story_id),
            )
        if cursor.rowcount == 0:
            raise LookupError(f"Aucun texte brut pour le récit {story_id}.")
