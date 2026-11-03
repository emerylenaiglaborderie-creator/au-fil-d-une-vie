"""Assemblage de l'application : connexion, repositories et services.

C'est le seul endroit où les trois couches se rencontrent. L'interface reçoit
uniquement l'objet `Services`.
"""

import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

from au_fil_d_une_vie import config
from au_fil_d_une_vie.repositories import (
    KeywordRepository,
    PersonRepository,
    ProfileRepository,
    ThemeRepository,
    connect,
)
from au_fil_d_une_vie.services.demo import load_demo
from au_fil_d_une_vie.services.links import LinkService
from au_fil_d_une_vie.services.quest import QuestService


@dataclass
class Services:
    quest: QuestService
    links: LinkService
    db_path: Path


def build_services(conn: sqlite3.Connection, db_path: Path) -> Services:
    keywords = KeywordRepository(conn)
    return Services(
        quest=QuestService(ProfileRepository(conn), PersonRepository(conn), ThemeRepository(conn)),
        links=LinkService(keywords),
        db_path=db_path,
    )


def open_services(demo: bool = False) -> Services:
    """Base de l'utilisateur, ou base temporaire remplie avec le jeu de démo."""
    if demo:
        db_path = Path(tempfile.mkdtemp(prefix="au-fil-demo-")) / "demo.db"
        conn = connect(db_path)
        load_demo(conn)
    else:
        db_path = config.db_path()
        conn = connect(db_path)
    return build_services(conn, db_path)
