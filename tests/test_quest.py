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


def test_relances_propres_a_la_question_ou_generales(
    conn: sqlite3.Connection, demo_path: Path
) -> None:
    from au_fil_d_une_vie.services.quest import DEFAULT_FOLLOW_UPS

    load_demo(conn, demo_path)
    service = _service(conn)
    piste = service.next_track()
    assert piste is not None
    assert service.follow_ups(piste.question.id) == [
        "Où l'entendais-tu ?",
        "Avec qui l'écoutais-tu ?",
        "Peux-tu m'en chanter un bout ?",
    ]
    sans = next(
        q for q in ThemeRepository(conn).open_questions() if q.text == "Où allais-tu danser ?"
    )
    assert service.follow_ups(sans.id) == list(DEFAULT_FOLLOW_UPS)


def test_d_autres_pistes_une_par_theme(conn: sqlite3.Connection, demo_path: Path) -> None:
    load_demo(conn, demo_path)
    service = _service(conn)
    actuelle = service.next_track()
    assert actuelle is not None
    autres = service.other_tracks(actuelle.question.id)
    assert len(autres) == 4
    assert len({p.theme.id for p in autres}) == 4
    assert actuelle.question.id not in {p.question.id for p in autres}


def test_retrouver_une_piste(conn: sqlite3.Connection, scene: Scene) -> None:
    piste = _service(conn).track(scene.q_jeux.id)
    assert piste is not None and piste.theme.slug == "enfance"
    assert _service(conn).track(9999) is None
