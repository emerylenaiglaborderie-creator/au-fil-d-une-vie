import sqlite3

from au_fil_d_une_vie.repositories import ThemeRepository
from au_fil_d_une_vie.services.tracks import seed_tracks


def test_une_nouvelle_base_recoit_les_pistes(conn: sqlite3.Connection) -> None:
    questions = seed_tracks(conn)
    themes = ThemeRepository(conn)
    assert [t.label for t in themes.list_themes()] == [
        "Enfance", "Rencontres", "Cuisine", "Métier", "Musique", "Fêtes",
    ]  # fmt: skip
    assert len(questions) == 25
    assert themes.follow_ups_for(questions["ecole"])[0] == "Comment s'appelait ton institutrice ?"


def test_les_pistes_ne_sont_chargees_qu_une_fois(conn: sqlite3.Connection) -> None:
    premieres = seed_tracks(conn)
    secondes = seed_tracks(conn)
    assert premieres == secondes
    assert len(ThemeRepository(conn).list_themes()) == 6
