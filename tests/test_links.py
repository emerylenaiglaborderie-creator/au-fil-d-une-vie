import math
import sqlite3
from pathlib import Path

import pytest

from au_fil_d_une_vie.repositories import KeywordRepository, StoryRepository
from au_fil_d_une_vie.services.demo import load_demo
from au_fil_d_une_vie.services.links import LinkService, compute_links, keyword_weights

# Calcul pur, sur des couples (récit, mot-clé)


def test_le_poids_d_un_mot_depend_de_sa_rarete() -> None:
    pairs = [(1, 10), (2, 10), (3, 10), (1, 20), (2, 20)]
    poids = keyword_weights(pairs)
    assert poids[20] == pytest.approx(math.log(1 + 3 / 2))
    assert poids[10] == pytest.approx(math.log(2))
    assert poids[20] > poids[10]


def test_deux_recits_sans_mot_commun_ne_sont_pas_lies() -> None:
    assert compute_links([(1, 10), (2, 20)]) == []


def test_un_lien_somme_les_mots_communs() -> None:
    liens = compute_links([(1, 10), (2, 10), (1, 20), (2, 20), (3, 30)])
    assert len(liens) == 1
    lien = liens[0]
    assert (lien.story_a, lien.story_b, lien.shared_keyword_ids) == (1, 2, (10, 20))
    assert lien.weight == pytest.approx(2 * math.log(1 + 3 / 2))
    assert lien.other(1) == 2 and lien.other(2) == 1


def test_un_mot_rare_cree_un_lien_plus_fort_qu_un_mot_commun() -> None:
    # Le mot 10 est partout, le mot 20 n'est partagé que par 1 et 2.
    pairs = [(1, 10), (2, 10), (3, 10), (1, 20), (2, 20)]
    liens = compute_links(pairs)
    assert (liens[0].story_a, liens[0].story_b) == (1, 2)


# Sur le jeu de démo


@pytest.fixture
def demo(conn: sqlite3.Connection, demo_path: Path) -> dict[str, int]:
    """Identifiants des six récits de démo, par mot repère."""
    ids = list(load_demo(conn, demo_path))
    return dict(zip(["ecole", "papi", "premier_jour", "plat", "travail", "etes"], ids, strict=True))


def _libelles(conn: sqlite3.Connection, keyword_ids: tuple[int, ...]) -> set[str]:
    return {k.label for k in KeywordRepository(conn).get_many(keyword_ids).values()}


def test_le_lien_le_plus_fort_relie_les_deux_recits_d_ecole(
    conn: sqlite3.Connection, demo: dict[str, int]
) -> None:
    lien = LinkService(KeywordRepository(conn)).links()[0]
    assert {lien.story_a, lien.story_b} == {demo["ecole"], demo["premier_jour"]}
    assert _libelles(conn, lien.shared_keyword_ids) == {"école", "institutrice", "craie"}


def test_voir_aussi(conn: sqlite3.Connection, demo: dict[str, int]) -> None:
    lies = [
        lien.other(demo["ecole"])
        for lien in LinkService(KeywordRepository(conn)).related(demo["ecole"])
    ]
    assert lies == [demo["premier_jour"], demo["etes"], demo["papi"]]


def test_le_recit_du_garage_est_isole(conn: sqlite3.Connection, demo: dict[str, int]) -> None:
    service = LinkService(KeywordRepository(conn))
    assert service.isolated(demo.values()) == [demo["travail"]]


def test_les_mots_communs_de_la_demo(conn: sqlite3.Connection, demo: dict[str, int]) -> None:
    communs = LinkService(KeywordRepository(conn)).shared_keyword_ids()
    assert _libelles(conn, tuple(communs)) == {
        "bourg", "sabots", "ferme", "école", "institutrice", "craie"
    }  # fmt: skip


def test_masquer_un_recit_coupe_ses_liens(conn: sqlite3.Connection, demo: dict[str, int]) -> None:
    StoryRepository(conn).set_hidden(demo["plat"], True)
    service = LinkService(KeywordRepository(conn))
    assert all(demo["plat"] not in (lien.story_a, lien.story_b) for lien in service.links())
    # « ferme » n'était partagé qu'avec le récit masqué : ce n'est plus un mot commun.
    assert "ferme" not in _libelles(conn, tuple(service.shared_keyword_ids()))
