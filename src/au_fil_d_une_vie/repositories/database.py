"""Connexion SQLite et migrations du schéma.

Une connexion ne se partage pas entre threads : chaque thread (interface, transcription)
ouvre la sienne avec `connect`.
"""

import re
import sqlite3
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

_MIGRATION_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


def connect(path: Path | str) -> sqlite3.Connection:
    """Ouvre la base, active les clés étrangères et applique les migrations en attente."""
    if isinstance(path, Path):
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if str(path) != ":memory:":
        # Lectures (interface) et écritures (transcription) en parallèle sans blocage.
        conn.execute("PRAGMA journal_mode = WAL")
    migrate(conn)
    return conn


def _migrations() -> list[tuple[int, str]]:
    """Liste triée des migrations embarquées : (version, script SQL)."""
    found: list[tuple[int, str]] = []
    for entry in resources.files(__package__ + ".migrations").iterdir():
        match = _MIGRATION_NAME.match(entry.name)
        if match:
            found.append((int(match.group(1)), entry.read_text(encoding="utf-8")))
    return sorted(found)


def schema_version(conn: sqlite3.Connection) -> int:
    """Version du schéma enregistrée dans la base."""
    version: int = conn.execute("PRAGMA user_version").fetchone()[0]
    return version


def migrate(conn: sqlite3.Connection) -> None:
    """Applique, dans une transaction chacune, les migrations plus récentes que la base."""
    current = schema_version(conn)
    for version, script in _migrations():
        if version <= current:
            continue
        try:
            conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {version};\nCOMMIT;")
        except sqlite3.Error:
            conn.rollback()
            raise


def now_iso() -> str:
    """Horodatage courant en UTC, au format stocké dans la base."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def parse_iso(value: str) -> datetime:
    """Relit un horodatage stocké dans la base."""
    return datetime.fromisoformat(value)
