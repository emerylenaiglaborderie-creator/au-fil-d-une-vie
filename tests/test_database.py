import sqlite3
from pathlib import Path

import pytest

from au_fil_d_une_vie.repositories import connect
from au_fil_d_une_vie.repositories.database import _migrations, schema_version


def test_la_base_est_migree_a_la_derniere_version(conn: sqlite3.Connection) -> None:
    assert schema_version(conn) == _migrations()[-1][0]


def test_les_cles_etrangeres_sont_actives(conn: sqlite3.Connection) -> None:
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_reouvrir_une_base_ne_rejoue_pas_les_migrations(tmp_path: Path) -> None:
    chemin = tmp_path / "sous-dossier" / "base.db"
    connect(chemin).close()
    conn = connect(chemin)
    assert schema_version(conn) == _migrations()[-1][0]
    conn.close()


def test_une_cle_etrangere_invalide_est_refusee(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO question (theme_id, text) VALUES (999, 'Orpheline ?')")
