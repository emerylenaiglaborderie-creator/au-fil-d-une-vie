"""Accès aux mots-clés et à leur rattachement aux récits."""

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass

from au_fil_d_une_vie.models import Keyword, StoryKeyword


@dataclass(frozen=True, slots=True)
class KeywordCandidate:
    """Mot-clé proposé par l'analyse d'un texte."""

    lemma: str
    label: str
    weight: float


class KeywordRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def propose(self, story_id: int, candidates: Iterable[KeywordCandidate]) -> None:
        """Rattache des mots-clés proposés à un récit.

        Le poids est mis à jour, la validation déjà donnée par l'utilisateur est conservée.
        """
        with self._conn:
            self._upsert(story_id, candidates)

    def replace_suggestions(self, story_id: int, candidates: Iterable[KeywordCandidate]) -> None:
        """Remplace les propositions non validées d'un récit par une nouvelle analyse.

        Les mots déjà validés sont conservés (et leur poids mis à jour s'ils sont reproposés).
        """
        with self._conn:
            self._conn.execute(
                "DELETE FROM story_keyword WHERE story_id = ? AND is_validated = 0", (story_id,)
            )
            self._upsert(story_id, candidates)

    def add_validated(self, story_id: int, lemma: str, label: str, weight: float = 1.0) -> None:
        """Ajoute un mot choisi par l'utilisateur, validé d'office."""
        with self._conn:
            self._upsert(story_id, [KeywordCandidate(lemma, label, weight)])
            self._conn.execute(
                """
                UPDATE story_keyword SET is_validated = 1
                WHERE story_id = ? AND keyword_id = (SELECT id FROM keyword WHERE lemma = ?)
                """,
                (story_id, lemma),
            )

    def _upsert(self, story_id: int, candidates: Iterable[KeywordCandidate]) -> None:
        """Insère ou met à jour les mots-clés. À appeler dans une transaction ouverte."""
        for candidate in candidates:
            keyword_id = self._conn.execute(
                """
                INSERT INTO keyword (lemma, label) VALUES (?, ?)
                ON CONFLICT (lemma) DO UPDATE SET label = keyword.label
                RETURNING id
                """,
                (candidate.lemma, candidate.label),
            ).fetchone()[0]
            self._conn.execute(
                """
                INSERT INTO story_keyword (story_id, keyword_id, weight)
                VALUES (?, ?, ?)
                ON CONFLICT (story_id, keyword_id) DO UPDATE SET weight = excluded.weight
                """,
                (story_id, keyword_id, candidate.weight),
            )

    def set_validated(self, story_id: int, keyword_id: int, validated: bool) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE story_keyword SET is_validated = ? WHERE story_id = ? AND keyword_id = ?",
                (int(validated), story_id, keyword_id),
            )

    def remove(self, story_id: int, keyword_id: int) -> None:
        """Retire un mot-clé d'un récit (le mot disparaît s'il n'est plus utilisé)."""
        with self._conn:
            self._conn.execute(
                "DELETE FROM story_keyword WHERE story_id = ? AND keyword_id = ?",
                (story_id, keyword_id),
            )

    def for_story(self, story_id: int, validated_only: bool = False) -> list[StoryKeyword]:
        rows = self._conn.execute(
            """
            SELECT sk.story_id, sk.weight, sk.is_validated, k.id, k.lemma, k.label
            FROM story_keyword AS sk
            JOIN keyword AS k ON k.id = sk.keyword_id
            WHERE sk.story_id = ? AND (? = 0 OR sk.is_validated = 1)
            ORDER BY sk.weight DESC, k.label
            """,
            (story_id, int(validated_only)),
        ).fetchall()
        return [
            StoryKeyword(
                story_id=row["story_id"],
                keyword=Keyword(id=row["id"], lemma=row["lemma"], label=row["label"]),
                weight=row["weight"],
                is_validated=bool(row["is_validated"]),
            )
            for row in rows
        ]

    def get_many(self, keyword_ids: Iterable[int]) -> dict[int, Keyword]:
        """Mots-clés par identifiant (pour afficher les mots communs d'un lien)."""
        ids = list(keyword_ids)
        if not ids:
            return {}
        placeholders = ", ".join("?" for _id in ids)
        rows = self._conn.execute(
            f"SELECT id, lemma, label FROM keyword WHERE id IN ({placeholders})", ids
        ).fetchall()
        return {row["id"]: Keyword(row["id"], row["lemma"], row["label"]) for row in rows}

    def validated_by_story(self) -> dict[int, list[Keyword]]:
        """Mots validés de chaque récit, les plus forts d'abord."""
        rows = self._conn.execute(
            """
            SELECT sk.story_id, k.id, k.lemma, k.label
            FROM story_keyword AS sk
            JOIN keyword AS k ON k.id = sk.keyword_id
            WHERE sk.is_validated = 1
            ORDER BY sk.story_id, sk.weight DESC, k.label
            """
        ).fetchall()
        result: dict[int, list[Keyword]] = {}
        for row in rows:
            result.setdefault(row["story_id"], []).append(
                Keyword(row["id"], row["lemma"], row["label"])
            )
        return result

    def validated_pairs(self) -> list[tuple[int, int]]:
        """Couples (récit, mot-clé) validés, récits masqués exclus. Base du calcul des liens."""
        rows = self._conn.execute(
            """
            SELECT sk.story_id, sk.keyword_id
            FROM story_keyword AS sk
            JOIN story AS s ON s.id = sk.story_id
            WHERE sk.is_validated = 1 AND s.is_hidden = 0
            ORDER BY sk.story_id, sk.keyword_id
            """
        ).fetchall()
        return [(row["story_id"], row["keyword_id"]) for row in rows]
