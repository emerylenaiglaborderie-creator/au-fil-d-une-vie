"""Accès au profil du jeune qui mène la quête."""

import sqlite3
from datetime import datetime

from au_fil_d_une_vie.models import Profile
from au_fil_d_une_vie.repositories.database import now_iso, parse_iso


class ProfileRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self) -> Profile | None:
        row = self._conn.execute(
            "SELECT first_name, under_15, parental_consent_at, created_at FROM profile WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        consent = row["parental_consent_at"]
        return Profile(
            first_name=row["first_name"],
            under_15=bool(row["under_15"]),
            parental_consent_at=parse_iso(consent) if consent else None,
            created_at=parse_iso(row["created_at"]),
        )

    def save(
        self, first_name: str, under_15: bool, parental_consent_at: datetime | None = None
    ) -> Profile:
        """Crée ou met à jour le profil. Sous 15 ans, l'accord parental est exigé par la base."""
        consent = parental_consent_at.isoformat(timespec="seconds") if parental_consent_at else None
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO profile (id, first_name, under_15, parental_consent_at, created_at)
                VALUES (1, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    first_name = excluded.first_name,
                    under_15 = excluded.under_15,
                    parental_consent_at = excluded.parental_consent_at
                """,
                (first_name, int(under_15), consent, now_iso()),
            )
        profile = self.get()
        assert profile is not None
        return profile
