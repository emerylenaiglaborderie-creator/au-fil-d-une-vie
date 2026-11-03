"""Accès aux proches interrogés."""

import sqlite3

from au_fil_d_une_vie.models import Person
from au_fil_d_une_vie.repositories.database import now_iso, parse_iso


def _to_person(row: sqlite3.Row) -> Person:
    return Person(
        id=row["id"],
        display_name=row["display_name"],
        relationship=row["relationship"],
        created_at=parse_iso(row["created_at"]),
    )


class PersonRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, display_name: str, relationship: str) -> Person:
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO person (display_name, relationship, created_at) VALUES (?, ?, ?)",
                (display_name, relationship, now_iso()),
            )
        person = self.get(cursor.lastrowid or 0)
        assert person is not None
        return person

    def get(self, person_id: int) -> Person | None:
        row = self._conn.execute("SELECT * FROM person WHERE id = ?", (person_id,)).fetchone()
        return _to_person(row) if row else None

    def list_all(self) -> list[Person]:
        rows = self._conn.execute("SELECT * FROM person ORDER BY created_at, id").fetchall()
        return [_to_person(row) for row in rows]

    def list_with_story_count(self) -> list[tuple[Person, int]]:
        """Proches et nombre de récits visibles recueillis auprès de chacun."""
        rows = self._conn.execute(
            """
            SELECT p.*, COUNT(s.id) AS story_count
            FROM person AS p
            LEFT JOIN story AS s ON s.person_id = p.id AND s.is_hidden = 0
            GROUP BY p.id
            ORDER BY story_count DESC, p.created_at, p.id
            """
        ).fetchall()
        return [(_to_person(row), row["story_count"]) for row in rows]

    def rename(self, person_id: int, display_name: str, relationship: str) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE person SET display_name = ?, relationship = ? WHERE id = ?",
                (display_name, relationship, person_id),
            )

    def delete(self, person_id: int) -> None:
        """Supprime le proche et, en cascade, tous ses récits."""
        with self._conn:
            self._conn.execute("DELETE FROM person WHERE id = ?", (person_id,))
