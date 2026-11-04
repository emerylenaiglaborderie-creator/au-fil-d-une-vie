import sqlite3

import pytest

from au_fil_d_une_vie.repositories import KeywordRepository, StoryRepository
from au_fil_d_une_vie.services.demo import load_demo
from au_fil_d_une_vie.services.graph import GraphService


@pytest.fixture
def ids(conn: sqlite3.Connection) -> dict[str, int]:
    ids = list(load_demo(conn))
    return dict(zip(["ecole", "papi", "premier_jour", "plat", "travail", "etes"], ids, strict=True))


def _service(conn: sqlite3.Connection) -> GraphService:
    return GraphService(StoryRepository(conn), KeywordRepository(conn))


def test_les_mots_communs_sont_des_noeuds(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    vue = _service(conn).build()
    assert {w.label for w in vue.words} == {
        "bourg",
        "sabots",
        "ferme",
        "école",
        "institutrice",
        "craie",
    }
    bourg = next(w for w in vue.words if w.label == "bourg")
    assert set(bourg.story_ids) == {ids["ecole"], ids["papi"], ids["etes"]}
    assert (ids["ecole"], bourg.keyword_id) in vue.word_edges


def test_les_positions_restent_sur_le_plateau(
    conn: sqlite3.Connection, ids: dict[str, int]
) -> None:
    vue = _service(conn).build()
    for node in [*vue.stories, *vue.words]:
        assert 0.0 <= node.x <= 1.0 and 0.0 <= node.y <= 1.0


def test_le_dessin_est_stable(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    premier = _service(conn).build()
    second = _service(conn).build()
    assert [(s.x, s.y) for s in premier.stories] == [(s.x, s.y) for s in second.stories]


def test_le_recit_sans_lien_est_range_a_part(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    vue = _service(conn).build()
    garage = vue.story(ids["travail"])
    assert garage is not None and not garage.linked
    assert all(s.linked for s in vue.stories if s.id != ids["travail"])
    assert garage.x > max(s.x for s in vue.stories if s.linked)


def test_selection_par_defaut_et_groupes(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    vue = _service(conn).build()
    assert vue.busiest_story() == ids["ecole"]
    assert vue.groups == 1
    assert len(vue.story_links) == 5


def test_un_recit_masque_disparait_du_graphe(conn: sqlite3.Connection, ids: dict[str, int]) -> None:
    StoryRepository(conn).set_hidden(ids["plat"], True)
    vue = _service(conn).build()
    assert vue.story(ids["plat"]) is None
    assert "ferme" not in {w.label for w in vue.words}


def test_graphe_vide(conn: sqlite3.Connection) -> None:
    vue = _service(conn).build()
    assert vue.stories == [] and vue.words == [] and vue.busiest_story() is None
