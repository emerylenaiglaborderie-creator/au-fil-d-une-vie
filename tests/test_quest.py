import sqlite3
from pathlib import Path

from au_fil_d_une_vie.repositories import PersonRepository, ProfileRepository, ThemeRepository
from au_fil_d_une_vie.services.demo import load_demo
from au_fil_d_une_vie.services.quest import QuestService
from tests.conftest import Scene


def _service(conn: sqlite3.Connection) -> QuestService:
    return QuestService(ProfileRepository(conn), PersonRepository(conn), ThemeRepository(conn))


def test_vue_d_ensemble_de_la_demo(conn: sqlite3.Connection, demo_path: Path) -> None:
    load_demo(conn, demo_path)
    vue = _service(conn).overview()
    assert vue.first_name == "Camille"
    assert vue.story_count == 6
    assert vue.interviewed_count == 3
    assert [(t.theme.label, t.done, t.total) for t in vue.themes][:2] == [
        ("Enfance", 3, 6),
        ("Rencontres", 1, 4),
    ]
    assert vue.people[-1].person.display_name == "Tata Nadine"
    assert vue.people[-1].story_count == 0


def test_la_prochaine_piste_vient_d_un_theme_inexplore(
    conn: sqlite3.Connection, demo_path: Path
) -> None:
    load_demo(conn, demo_path)
    piste = _service(conn).next_track()
    assert piste is not None
    assert piste.theme.label == "Musique"
    assert piste.question.text == "Quelle chanson te rappelle ta jeunesse ?"


def test_une_autre_piste(conn: sqlite3.Connection, demo_path: Path) -> None:
    load_demo(conn, demo_path)
    service = _service(conn)
    premiere = service.next_track()
    assert premiere is not None
    autre = service.next_track(skip={premiere.question.id})
    assert autre is not None and autre.question.id != premiere.question.id


def test_sans_profil_ni_piste(conn: sqlite3.Connection) -> None:
    service = _service(conn)
    assert service.overview().first_name is None
    assert service.next_track() is None


def test_quand_tout_est_ecarte_on_repart_du_debut(conn: sqlite3.Connection, scene: Scene) -> None:
    service = _service(conn)
    toutes = {scene.q_ecole.id, scene.q_jeux.id}
    piste = service.next_track(skip=toutes)
    assert piste is not None and piste.question.id == scene.q_ecole.id
