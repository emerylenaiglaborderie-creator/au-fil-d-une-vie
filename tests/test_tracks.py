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


# Personnalisation

import pytest  # noqa: E402

from au_fil_d_une_vie.services.tracks import TrackError, TrackService, slugify  # noqa: E402
from tests.conftest import Scene  # noqa: E402


@pytest.fixture
def tracks(conn: sqlite3.Connection) -> TrackService:
    return TrackService(ThemeRepository(conn))


def test_identifiant_lisible() -> None:
    assert slugify("Fêtes de famille !") == "fetes-de-famille"
    assert slugify("???") == "piste"


def test_ajouter_une_piste_et_ses_questions(tracks: TrackService) -> None:
    voyages = tracks.add_theme("  Voyages ")
    tracks.add_question(voyages.id, "Quel a été ton plus beau voyage ?")
    tracks.add_question(voyages.id, "Où rêvais-tu d'aller ?")
    info = next(t for t in tracks.all() if t.theme.id == voyages.id)
    assert info.theme.label == "Voyages" and info.theme.slug == "voyages"
    assert [q.question.text for q in info.questions][1] == "Où rêvais-tu d'aller ?"


def test_pas_de_doublon(tracks: TrackService) -> None:
    tracks.add_theme("Voyages")
    with pytest.raises(TrackError):
        tracks.add_theme("voyagés")
    with pytest.raises(TrackError):
        tracks.add_theme("   ")
    autre = tracks.add_theme("Sport")
    tracks.add_question(autre.id, "Quel sport faisais-tu ?")
    with pytest.raises(TrackError):
        tracks.add_question(autre.id, "quel sport faisais-tu ?")


def test_meme_nom_deux_fois_donne_deux_identifiants(conn: sqlite3.Connection) -> None:
    repo = ThemeRepository(conn)
    repo.add_theme("voyages", "Ancien nom", 1)
    nouvelle = TrackService(repo).add_theme("Voyages")
    assert nouvelle.slug == "voyages-2"


def test_renommer_et_reordonner(tracks: TrackService, scene: Scene) -> None:
    sport = tracks.add_theme("Sport")
    tracks.rename_theme(sport.id, "Sports")
    tracks.move_theme(sport.id, -1)
    labels = [t.theme.label for t in tracks.all()]
    assert labels == ["Sports", "Enfance"]
    tracks.move_theme(sport.id, -1)  # déjà en tête : rien ne change
    assert [t.theme.label for t in tracks.all()] == ["Sports", "Enfance"]


def test_une_piste_avec_des_recits_ne_se_supprime_pas(
    tracks: TrackService, scene: Scene, conn: sqlite3.Connection
) -> None:
    scene.story(conn, scene.yvonne, scene.q_ecole)
    with pytest.raises(TrackError):
        tracks.delete_theme(scene.q_ecole.theme_id)
    with pytest.raises(TrackError):
        tracks.delete_question(scene.q_ecole.id)
    tracks.delete_question(scene.q_jeux.id)  # sans récit : possible
    assert [q.question.id for q in tracks.all()[0].questions] == [scene.q_ecole.id]


def test_supprimer_une_piste_vide(tracks: TrackService) -> None:
    vide = tracks.add_theme("Vide")
    tracks.add_question(vide.id, "Une question ?")
    tracks.delete_theme(vide.id)
    assert "Vide" not in [t.theme.label for t in tracks.all()]


def test_corriger_une_question_qui_a_des_recits(
    tracks: TrackService, scene: Scene, conn: sqlite3.Connection
) -> None:
    scene.story(conn, scene.yvonne, scene.q_ecole)
    tracks.edit_question(scene.q_ecole.id, "Comment était ton école ?!")
    question = ThemeRepository(conn).get_question(scene.q_ecole.id)
    assert question is not None and question.text == "Comment était ton école ?!"
