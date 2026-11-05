"""État local de la synchronisation avec le serveur familial.

Le journal des modifications (`sync_outbox`) est tenu par les triggers de la
migration 0004 : les autres repositories n'ont rien à faire pour qu'une
modification soit envoyée. Ce repository le lit et l'acquitte.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from au_fil_d_une_vie.models import PendingChange, SyncEntity, SyncOperation
from au_fil_d_une_vie.repositories.database import parse_iso


class SyncRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def pending(self) -> list[PendingChange]:
        """Modifications à envoyer, de la plus ancienne à la plus récente."""
        rows = self._conn.execute(
            """
            SELECT revision, entity, entity_key, operation, changed_at
            FROM sync_outbox
            ORDER BY revision
            """
        ).fetchall()
        return [
            PendingChange(
                revision=row["revision"],
                entity=SyncEntity(row["entity"]),
                key=row["entity_key"],
                operation=SyncOperation(row["operation"]),
                changed_at=parse_iso(row["changed_at"]),
            )
            for row in rows
        ]

    def pending_count(self) -> int:
        count: int = self._conn.execute("SELECT COUNT(*) FROM sync_outbox").fetchone()[0]
        return count

    def acknowledge(self, change: PendingChange, server_version: int | None) -> None:
        """Le serveur a accepté une modification : elle quitte le journal.

        Pour un ajout ou une mise à jour, on retient la version donnée par le serveur.
        Pour une suppression, le serveur n'a plus rien à nous apprendre sur la donnée.
        Si la donnée a encore changé depuis la lecture du journal, sa nouvelle entrée
        est gardée pour un prochain envoi.
        """
        if change.operation is SyncOperation.UPSERT and (
            server_version is None or server_version < 1
        ):
            raise ValueError("Une version serveur positive est attendue.")
        with self._conn:
            self._conn.execute("DELETE FROM sync_outbox WHERE revision = ?", (change.revision,))
            if change.operation is SyncOperation.DELETE:
                self._forget(change.entity, change.key)
            else:
                assert server_version is not None
                self._remember(change.entity, change.key, server_version)

    def server_version(self, entity: SyncEntity, key: str) -> int | None:
        """Version connue du serveur pour une donnée, None si elle ne lui a jamais été envoyée."""
        row = self._conn.execute(
            "SELECT server_version FROM sync_known WHERE entity = ? AND entity_key = ?",
            (entity.value, key),
        ).fetchone()
        return row["server_version"] if row else None

    def last_pulled_seq(self) -> int:
        seq: int = self._conn.execute(
            "SELECT last_pulled_seq FROM sync_state WHERE id = 1"
        ).fetchone()[0]
        return seq

    def set_last_pulled_seq(self, seq: int) -> None:
        """Retient le numéro de la dernière modification reçue du serveur (jamais en arrière)."""
        if seq < self.last_pulled_seq():
            raise ValueError("Le numéro de réception ne peut pas reculer.")
        with self._conn:
            self._conn.execute("UPDATE sync_state SET last_pulled_seq = ? WHERE id = 1", (seq,))

    @contextmanager
    def applying_remote(self) -> Iterator[None]:
        """Transaction d'application des changements reçus du serveur.

        Le journal est coupé le temps de la transaction : ce qui vient du serveur
        n'est pas renvoyé au serveur. Tout est annulé en cas d'erreur.

        Les écritures faites dans ce bloc ne doivent pas valider elles-mêmes la
        transaction (pas de méthode de repository qui ouvre `with conn`).
        """
        with self._conn:
            self._conn.execute("UPDATE sync_state SET applying_remote = 1 WHERE id = 1")
            try:
                yield
            finally:
                self._conn.execute("UPDATE sync_state SET applying_remote = 0 WHERE id = 1")

    def _remember(self, entity: SyncEntity, key: str, server_version: int) -> None:
        self._conn.execute(
            """
            INSERT INTO sync_known (entity, entity_key, server_version) VALUES (?, ?, ?)
            ON CONFLICT (entity, entity_key) DO UPDATE SET
                server_version = excluded.server_version
            """,
            (entity.value, key, server_version),
        )

    def _forget(self, entity: SyncEntity, key: str) -> None:
        self._conn.execute(
            "DELETE FROM sync_known WHERE entity = ? AND entity_key = ?", (entity.value, key)
        )
