"""Tests sur le vrai modèle spaCy, ignorés tant qu'il n'est pas installé."""

import pytest

from au_fil_d_une_vie.services.spacy_analyzer import DEFAULT_MODEL, SpacyAnalyzer

spacy = pytest.importorskip("spacy")
if not spacy.util.is_package(DEFAULT_MODEL):
    pytest.skip(f"Modèle {DEFAULT_MODEL} absent", allow_module_level=True)


@pytest.fixture(scope="module")
def analyseur() -> SpacyAnalyzer:
    return SpacyAnalyzer()


def test_les_noms_sont_lemmatises(analyseur: SpacyAnalyzer) -> None:
    lemmes = {t.lemma for t in analyseur.terms("On allait à l'école en sabots avec nos ardoises.")}
    assert {"école", "sabot", "ardoise"} <= lemmes


def test_les_mots_vides_et_verbes_sont_ecartes(analyseur: SpacyAnalyzer) -> None:
    lemmes = {t.lemma for t in analyseur.terms("Alors on y allait, et puis voilà, une fois.")}
    assert lemmes == set()


def test_les_lieux_sont_des_entites(analyseur: SpacyAnalyzer) -> None:
    termes = analyseur.terms("Nous sommes partis vivre à Quimper après la guerre.")
    assert any(t.is_entity and t.label == "Quimper" for t in termes)
