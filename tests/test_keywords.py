import sqlite3
from pathlib import Path

import pytest

from au_fil_d_une_vie.repositories import KeywordRepository, TranscriptRepository
from au_fil_d_une_vie.services.keywords import KeywordService, Term, rank_candidates, tf_idf
from tests.conftest import Scene

MOTS_VIDES = {"le", "la", "les", "de", "du", "et", "on", "un", "une", "au", "à", "en", "y"}


class AnalyseurSimple:
    """Remplace spaCy dans les tests : découpe sur les espaces, sans lemmatisation."""

    def terms(self, text: str) -> list[Term]:
        mots = [m.strip(".,;:!?'").lower() for m in text.split()]
        return [
            Term(lemma=m, label=m, is_entity=m[:1].isupper())
            for m in mots
            if m and m not in MOTS_VIDES
        ]


def _termes(*lemmes: str) -> list[Term]:
    return [Term(lemma=lemme, label=lemme) for lemme in lemmes]


# Calcul pur


def test_un_mot_rare_pese_plus_qu_un_mot_partout() -> None:
    corpus = [["école", "ferme"], ["ferme", "bal"], ["ferme", "garage"]]
    scores = tf_idf(corpus[0], corpus)
    assert scores["école"] > scores["ferme"] > 0


def test_un_document_vide_n_a_pas_de_score() -> None:
    assert tf_idf([], [[]]) == {}


def test_un_corpus_d_un_seul_recit_reste_exploitable() -> None:
    scores = tf_idf(["sabot", "sabot", "craie"], [["sabot", "sabot", "craie"]])
    assert scores["sabot"] > scores["craie"] > 0


def test_les_candidats_sont_classes_et_normalises() -> None:
    doc = _termes("école", "école", "craie", "ferme")
    corpus = [doc, _termes("ferme", "bal")]
    candidats = rank_candidates(doc, corpus, limit=2)
    assert [c.lemma for c in candidats] == ["école", "craie"]
    assert candidats[0].weight == 1.0
    assert 0 < candidats[1].weight < 1


def test_les_entites_sont_favorisees() -> None:
    doc = [Term("bourg", "bourg"), Term("quimper", "Quimper", is_entity=True)]
    candidats = rank_candidates(doc, [doc])
    assert candidats[0].label == "Quimper"


def test_le_libelle_le_plus_frequent_est_garde() -> None:
    doc = [Term("sabot", "sabots"), Term("sabot", "sabots"), Term("sabot", "sabot")]
    assert rank_candidates(doc, [doc])[0].label == "sabots"


# Service


@pytest.fixture
def service(conn: sqlite3.Connection) -> KeywordService:
    return KeywordService(
        AnalyseurSimple(), TranscriptRepository(conn), KeywordRepository(conn), max_suggestions=3
    )


def test_proposer_des_mots_cles_pour_un_recit(
    conn: sqlite3.Connection, scene: Scene, service: KeywordService
) -> None:
    r1 = scene.story(conn, scene.yvonne, scene.q_ecole)
    r2 = scene.story(conn, scene.papa, scene.q_ecole)
    textes = TranscriptRepository(conn)
    textes.save_raw(r1.id, "sabots sabots craie ferme")
    textes.save_raw(r2.id, "ferme cartable")

    mots = service.suggest(r1.id)

    assert [m.keyword.lemma for m in mots] == ["sabots", "craie", "ferme"]
    assert not any(m.is_validated for m in mots)


def test_une_nouvelle_analyse_garde_les_mots_valides(
    conn: sqlite3.Connection, scene: Scene, service: KeywordService
) -> None:
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    textes = TranscriptRepository(conn)
    textes.save_raw(recit.id, "sabots craie")
    mots = {m.keyword.lemma: m.keyword.id for m in service.suggest(recit.id)}
    service.validate(recit.id, mots["craie"])

    textes.save_book_text(recit.id, "institutrice bourg")
    apres = {m.keyword.lemma: m.is_validated for m in service.suggest(recit.id)}

    assert apres == {"craie": True, "institutrice": False, "bourg": False}


def test_rejeter_et_ajouter_un_mot(
    conn: sqlite3.Connection, scene: Scene, service: KeywordService
) -> None:
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    TranscriptRepository(conn).save_raw(recit.id, "sabots craie")
    mots = {m.keyword.lemma: m.keyword.id for m in service.suggest(recit.id)}

    service.reject(recit.id, mots["craie"])
    service.add(recit.id, "  Le   Gall ")

    restants = {
        (m.keyword.label, m.is_validated) for m in KeywordRepository(conn).for_story(recit.id)
    }
    assert restants == {("sabots", False), ("Le Gall", True)}


def test_pas_de_proposition_sans_texte(
    conn: sqlite3.Connection, scene: Scene, service: KeywordService
) -> None:
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    with pytest.raises(LookupError):
        service.suggest(recit.id)


def test_un_mot_vide_est_refuse(
    conn: sqlite3.Connection, scene: Scene, service: KeywordService
) -> None:
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    with pytest.raises(ValueError):
        service.add(recit.id, "   ")


def test_suggestions_sur_le_jeu_de_demo(conn: sqlite3.Connection, demo_path: Path) -> None:
    from au_fil_d_une_vie.services.demo import load_demo

    ids = list(load_demo(conn, demo_path))
    service = KeywordService(AnalyseurSimple(), TranscriptRepository(conn), KeywordRepository(conn))
    proposes = {m.keyword.lemma for m in service.suggest(ids[0])}
    assert "institutrice" in proposes
