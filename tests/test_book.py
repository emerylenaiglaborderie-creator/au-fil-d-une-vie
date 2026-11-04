import re
import sqlite3
from pathlib import Path

import pytest
from pypdf import PdfReader

from au_fil_d_une_vie.repositories import (
    KeywordRepository,
    NoteRepository,
    ProfileRepository,
    StoryRepository,
    ThemeRepository,
    TranscriptRepository,
)
from au_fil_d_une_vie.services.book import BookService
from au_fil_d_une_vie.services.book_pdf import BookAssets, render_book
from au_fil_d_une_vie.services.demo import load_demo
from au_fil_d_une_vie.services.links import LinkService
from au_fil_d_une_vie.services.stories import StoryService
from au_fil_d_une_vie.ui import theme

ASSETS = BookAssets(theme.FONTS, theme.IMAGES / "logo.png")


@pytest.fixture
def ids(conn: sqlite3.Connection) -> dict[str, int]:
    ids = list(load_demo(conn))
    return dict(zip(["ecole", "papi", "premier_jour", "plat", "travail", "etes"], ids, strict=True))


@pytest.fixture
def stories(conn: sqlite3.Connection, tmp_path: Path) -> StoryService:
    keywords = KeywordRepository(conn)
    return StoryService(
        StoryRepository(conn),
        TranscriptRepository(conn),
        keywords,
        NoteRepository(conn),
        LinkService(keywords),
        tmp_path,
    )


@pytest.fixture
def service(conn: sqlite3.Connection, stories: StoryService) -> BookService:
    return BookService(stories, ProfileRepository(conn), ThemeRepository(conn))


def test_le_livre_range_les_recits_par_piste(service: BookService, ids: dict[str, int]) -> None:
    livre = service.gather()
    assert livre.author == "Camille"
    assert [c.theme_label for c in livre.chapters] == ["Enfance", "Rencontres", "Cuisine", "Métier"]
    enfance = livre.chapters[0]
    assert [s.id for s in enfance.stories] == [ids["etes"], ids["premier_jour"], ids["ecole"]]
    assert livre.story_count == 6


def test_seuls_les_recits_choisis_entrent_dans_le_livre(
    service: BookService, ids: dict[str, int]
) -> None:
    service.set_included(ids["papi"], False)
    livre = service.gather()
    toutes = [s.id for c in livre.chapters for s in c.stories]
    assert ids["papi"] not in toutes
    assert "Rencontres" not in [c.theme_label for c in livre.chapters]
    # Les renvois ne pointent que vers des récits présents dans le livre.
    renvois = {r.story_id for c in livre.chapters for s in c.stories for r in s.see_also}
    assert ids["papi"] not in renvois


def test_un_recit_masque_ou_sans_texte_n_y_entre_pas(
    service: BookService, conn: sqlite3.Connection, ids: dict[str, int]
) -> None:
    from au_fil_d_une_vie.models import StoryStatus

    StoryRepository(conn).set_hidden(ids["plat"], True)
    StoryRepository(conn).set_status(ids["travail"], StoryStatus.RECORDED)
    candidats = {c.id for c in service.candidates()}
    assert ids["plat"] not in candidats and ids["travail"] not in candidats


def test_le_pdf_contient_sommaire_recits_renvois_et_index(
    service: BookService, stories: StoryService, ids: dict[str, int], tmp_path: Path
) -> None:
    stories.save_note(ids["ecole"], "Demander le nom de l'école.")
    chemin = render_book(service.gather(), tmp_path / "livre.pdf", ASSETS)

    lecteur = PdfReader(chemin)
    texte = "\n".join(page.extract_text() for page in lecteur.pages)
    assert len(lecteur.pages) >= 6
    for attendu in (
        "Le livre de famille",
        "recueilli par Camille",
        "Sommaire",
        "Mamie Yvonne raconte",
        "CE QUE J'EN RETIENS",
        "Demander le nom de l'école.",
        "VOIR AUSSI",
        "Index des mots",
    ):
        assert attendu in texte, attendu
    # Le sommaire et l'index renvoient à de vrais numéros de page.
    assert re.search(r"institutrice\s*[ .]*\s*\d", texte)
    titres = [item.title for item in lecteur.outline if not isinstance(item, list)]
    assert "Enfance" in titres


def test_un_livre_vide_reste_valide(
    conn: sqlite3.Connection, stories: StoryService, tmp_path: Path
) -> None:
    service = BookService(stories, ProfileRepository(conn), ThemeRepository(conn))
    chemin = render_book(service.gather(), tmp_path / "vide.pdf", ASSETS)
    assert PdfReader(chemin).pages
