"""Accès à « Mon carnet »."""

import sqlite3

from au_fil_d_une_vie.models import Note
from au_fil_d_une_vie.repositories.database import now_iso, parse_iso


class NoteRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, story_id: int) -> Note | None:
        row = self._conn.execute("SELECT * FROM note WHERE story_id = ?", (story_id,)).fetchone()
        if row is None:
            return None
        return Note(
            story_id=row["story_id"],
            content=row["content"],
            updated_at=parse_iso(row["updated_at"]),
        )

    def save(self, story_id: int, content: str) -> None:
        """Enregistre la note. Une note vide est supprimée."""
        with self._conn:
            if not content.strip():
                self._conn.execute("DELETE FROM note WHERE story_id = ?", (story_id,))
                return
            self._conn.execute(
                """
                INSERT INTO note (story_id, content, updated_at) VALUES (?, ?, ?)
                ON CONFLICT (story_id) DO UPDATE SET
                    content = excluded.content,
                    updated_at = excluded.updated_at
                """,
                (story_id, content, now_iso()),
            )
