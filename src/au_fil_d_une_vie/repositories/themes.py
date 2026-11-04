"""Accès aux pistes et à leurs questions."""

import sqlite3

from au_fil_d_une_vie.models import Question, Theme


def _to_theme(row: sqlite3.Row) -> Theme:
    return Theme(id=row["id"], slug=row["slug"], label=row["label"], position=row["position"])


def _to_question(row: sqlite3.Row) -> Question:
    return Question(
        id=row["id"], theme_id=row["theme_id"], text=row["text"], position=row["position"]
    )


class ThemeRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add_theme(self, slug: str, label: str, position: int = 0) -> Theme:
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO theme (slug, label, position) VALUES (?, ?, ?)",
                (slug, label, position),
            )
        return Theme(id=cursor.lastrowid or 0, slug=slug, label=label, position=position)

    def add_question(self, theme_id: int, text: str, position: int = 0) -> Question:
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO question (theme_id, text, position) VALUES (?, ?, ?)",
                (theme_id, text, position),
            )
        return Question(id=cursor.lastrowid or 0, theme_id=theme_id, text=text, position=position)

    def list_themes(self) -> list[Theme]:
        rows = self._conn.execute("SELECT * FROM theme ORDER BY position, id").fetchall()
        return [_to_theme(row) for row in rows]

    def get_question(self, question_id: int) -> Question | None:
        row = self._conn.execute("SELECT * FROM question WHERE id = ?", (question_id,)).fetchone()
        return _to_question(row) if row else None

    def questions_for(self, theme_id: int) -> list[Question]:
        rows = self._conn.execute(
            "SELECT * FROM question WHERE theme_id = ? ORDER BY position, id", (theme_id,)
        ).fetchall()
        return [_to_question(row) for row in rows]

    def progress(self) -> dict[int, tuple[int, int]]:
        """Par piste : (questions ayant au moins un récit visible, total des questions)."""
        rows = self._conn.execute(
            """
            SELECT t.id AS theme_id,
                   COUNT(DISTINCT s.question_id) AS done,
                   COUNT(DISTINCT q.id) AS total
            FROM theme AS t
            LEFT JOIN question AS q ON q.theme_id = t.id
            LEFT JOIN story AS s ON s.question_id = q.id AND s.is_hidden = 0
            GROUP BY t.id
            """
        ).fetchall()
        return {row["theme_id"]: (row["done"], row["total"]) for row in rows}

    def open_questions(self) -> list[Question]:
        """Questions sans aucun récit visible, dans l'ordre des pistes."""
        rows = self._conn.execute(
            """
            SELECT q.*
            FROM question AS q
            JOIN theme AS t ON t.id = q.theme_id
            WHERE NOT EXISTS (
                SELECT 1 FROM story AS s WHERE s.question_id = q.id AND s.is_hidden = 0
            )
            ORDER BY t.position, t.id, q.position, q.id
            """
        ).fetchall()
        return [_to_question(row) for row in rows]

    def add_follow_up(self, question_id: int, text: str, position: int = 0) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO follow_up (question_id, text, position) VALUES (?, ?, ?)",
                (question_id, text, position),
            )

    def follow_ups_for(self, question_id: int) -> list[str]:
        """Relances « Pour creuser » d'une question, dans l'ordre."""
        rows = self._conn.execute(
            "SELECT text FROM follow_up WHERE question_id = ? ORDER BY position, id",
            (question_id,),
        ).fetchall()
        return [row["text"] for row in rows]

    def get_theme(self, theme_id: int) -> Theme | None:
        row = self._conn.execute("SELECT * FROM theme WHERE id = ?", (theme_id,)).fetchone()
        return _to_theme(row) if row else None
