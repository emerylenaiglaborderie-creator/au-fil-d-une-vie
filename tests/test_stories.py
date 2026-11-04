import sqlite3
from pathlib import Path

import pytest

from au_fil_d_une_vie.repositories import (
    KeywordRepository,
    NoteRepository,
    StoryRepository,
    TranscriptRepository,
)
from au_fil_d_une_vie.services.demo import load_demo
from au_fil_d_une_vie.services.links import LinkService
from au_fil_d_une_vie.services.stories import StoryService, Tag, excerpt, fold, keyword_spans
from tests.test_keywords import AnalyseurSimple


@pytest.fixture
def ids(conn: sqlite3.Connection) -> dict[str, int]:
    ids = list(load_demo(conn))
    return dict(zip(["ecole", "papi", "premier_jour", "plat", "travail", "etes"], ids, strict=True))


@pytest.fixture
def service(conn: sqlite3.Connection, tmp_path: Path) -> StoryService:
    keywords = KeywordRepository(conn)
    return StoryService(
        StoryRepository(conn),
        TranscriptRepository(conn),
        keywords,
        NoteRepository(conn),
        LinkService(keywords),
        tmp_path,
        AnalyseurSimple(),
    )


# Outils de texte


def test_recherche_sans_accents_ni_majuscules() -> None:
    assert fold("École du Bourg") == "ecole du bourg"


def test_extrait_coupe_sur_un_mot() -> None:
    texte = "mot " * 100
    court = excerpt(texte, 20)
    assert court.endswith("…") and len(court) <= 21
    assert excerpt("Court.") == "Court."


def test_surlignage_des_mots_cles() -> None:
    texte = "On allait à l'École en sabots."
    tags = [Tag(1, "école", "école", True), Tag(2, "sabots", "sabot", True)]
    spans = keyword_spans(texte, tags)
    assert [texte[a:b] for a, b in spans] == ["École", "sabots"]


def test_pas_de_surlignage_au_milieu_d_un_mot() -> None:
    texte = "Les bourgeois du bourg"
    spans = keyword_spans(texte, [Tag(1, "bourg", "bourg", True)])
    assert [texte[a:b] for a, b in spans] == ["bourg"] and spans[0][0] == 17


# Liste


def test_la_liste_va_du_plus_recent_au_plus_ancien(
    service: StoryService, ids: dict[str, int]
) -> None:
    cartes = service.cards()
    assert [c.id for c in cartes] == list(ids.values())
    ecole = cartes[0]
    assert ecole.person_name == "Mamie Yvonne"
    assert ecole.theme_label == "Enfance"
    assert ecole.link_count == 3
    assert ecole.excerpt is not None and ecole.excerpt.startswith("L'école")


def test_les_etiquettes_partagees_sont_pleines(service: StoryService, ids: dict[str, int]) -> None:
    papi = next(c for c in service.cards() if c.id == ids["papi"])
    etat = {t.label: t.shared for t in papi.tags}
    assert etat == {"bal": False, "bourg": True, "vélo": False, "danse": False}


def test_recherche_dans_le_texte_la_personne_et_les_mots(
    service: StoryService, ids: dict[str, int]
) -> None:
    assert [c.id for c in service.cards("mobylette")] == [ids["travail"]]
    assert {c.id for c in service.cards("tonton")} == {ids["travail"]}
    assert {c.id for c in service.cards("ecole")} == {ids["ecole"], ids["premier_jour"]}


def test_filtre_par_piste(service: StoryService, ids: dict[str, int]) -> None:
    enfance = next(tid for tid, label in service.themes_with_stories() if label == "Enfance")
    assert {c.id for c in service.cards(theme_id=enfance)} == {
        ids["ecole"],
        ids["premier_jour"],
        ids["etes"],
    }


# Fiche


def test_voir_aussi_avec_les_mots_partages(service: StoryService, ids: dict[str, int]) -> None:
    fiche = service.detail(ids["ecole"])
    assert fiche is not None
    premier = fiche.related[0]
    assert premier.id == ids["premier_jour"]
    assert premier.person_name == "Papa"
    assert set(premier.shared_labels) == {"école", "institutrice", "craie"}


def test_corriger_le_texte_garde_le_brut_et_repropose_des_mots(
    service: StoryService, ids: dict[str, int]
) -> None:
    service.save_book_text(ids["travail"], "  Mon premier garage, chez Le Gall.  ")
    fiche = service.detail(ids["travail"])
    assert fiche is not None
    assert fiche.text == "Mon premier garage, chez Le Gall."
    assert fiche.raw_text is not None and fiche.raw_text.startswith("J'ai commencé")
    assert {"garage", "gall"} <= {t.lemma for t in fiche.suggestions} | {
        t.lemma for t in fiche.tags
    }
    assert {t.label for t in fiche.tags} == {"garage", "apprenti", "mobylette"}


def test_valider_retirer_et_ajouter_des_mots(service: StoryService, ids: dict[str, int]) -> None:
    story_id = ids["travail"]
    service.add_keyword(story_id, "  atelier ")
    fiche = service.detail(story_id)
    assert fiche is not None
    atelier = next(t for t in fiche.tags if t.label == "atelier")
    service.remove_keyword(story_id, atelier.keyword_id)
    service.save_book_text(story_id, "Le patron du garage montrait tout.")
    fiche = service.detail(story_id)
    assert fiche is not None and fiche.suggestions
    service.validate_keyword(story_id, fiche.suggestions[0].keyword_id)
    fiche = service.detail(story_id)
    assert fiche is not None
    assert "atelier" not in {t.label for t in fiche.tags}
    with pytest.raises(ValueError):
        service.add_keyword(story_id, "   ")


def test_carnet(service: StoryService, ids: dict[str, int]) -> None:
    service.save_note(ids["ecole"], "Demander le nom de l'école.")
    fiche = service.detail(ids["ecole"])
    assert fiche is not None and fiche.note == "Demander le nom de l'école."


def test_masquer_un_recit_coupe_ses_liens(service: StoryService, ids: dict[str, int]) -> None:
    service.set_hidden(ids["premier_jour"], True)
    cartes = {c.id: c for c in service.cards()}
    assert cartes[ids["premier_jour"]].is_hidden
    assert cartes[ids["ecole"]].link_count == 2


def test_supprimer_un_recit_efface_son_audio(
    service: StoryService, ids: dict[str, int], tmp_path: Path, conn: sqlite3.Connection
) -> None:
    story = StoryRepository(conn).get(ids["plat"])
    assert story is not None
    fichier = tmp_path / story.audio_path
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_bytes(b"RIFF")
    service.delete(ids["plat"])
    assert not fichier.exists()
    assert service.detail(ids["plat"]) is None
    service.delete(ids["plat"])  # déjà supprimé : sans erreur


def test_corriger_la_transcription_brute(service: StoryService, ids: dict[str, int]) -> None:
    story_id = ids["ecole"]
    service.save_raw_text(story_id, "L'école du bourg, avec Mademoiselle Le Gall.")
    fiche = service.detail(story_id)
    assert fiche is not None
    assert fiche.raw_text == "L'école du bourg, avec Mademoiselle Le Gall."
    assert fiche.book_text is None


def test_corriger_le_brut_ne_touche_pas_a_la_version_livre(
    service: StoryService, ids: dict[str, int]
) -> None:
    story_id = ids["ecole"]
    service.save_book_text(story_id, "Version pour le livre.")
    service.save_raw_text(story_id, "Transcription corrigée.")
    fiche = service.detail(story_id)
    assert fiche is not None
    assert (fiche.raw_text, fiche.book_text) == (
        "Transcription corrigée.",
        "Version pour le livre.",
    )


def test_un_texte_vide_est_refuse(service: StoryService, ids: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        service.save_raw_text(ids["ecole"], "   ")
    with pytest.raises(ValueError):
        service.save_book_text(ids["ecole"], "")
