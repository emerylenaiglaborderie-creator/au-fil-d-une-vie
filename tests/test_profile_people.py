import sqlite3
from pathlib import Path

import pytest

from au_fil_d_une_vie.repositories import PersonRepository, ProfileRepository, StoryRepository
from au_fil_d_une_vie.services.people import PeopleService, PersonError
from au_fil_d_une_vie.services.profile import ProfileError, ProfileService
from tests.conftest import Scene

# Profil


def test_creer_un_profil(conn: sqlite3.Connection) -> None:
    profil = ProfileService(ProfileRepository(conn)).save("  Camille ", under_15=False)
    assert profil.first_name == "Camille" and profil.parental_consent_at is None


def test_sous_15_ans_il_faut_l_accord_d_un_parent(conn: sqlite3.Connection) -> None:
    service = ProfileService(ProfileRepository(conn))
    with pytest.raises(ProfileError):
        service.save("Léo", under_15=True)
    profil = service.save("Léo", under_15=True, parental_consent=True)
    assert profil.parental_consent_at is not None


def test_l_accord_parental_garde_sa_date(conn: sqlite3.Connection) -> None:
    service = ProfileService(ProfileRepository(conn))
    premier = service.save("Léo", under_15=True, parental_consent=True)
    second = service.save("Léon", under_15=True, parental_consent=True)
    assert second.parental_consent_at == premier.parental_consent_at


def test_un_prenom_est_obligatoire(conn: sqlite3.Connection) -> None:
    with pytest.raises(ProfileError):
        ProfileService(ProfileRepository(conn)).save("   ", under_15=False)


# Proches


@pytest.fixture
def people(conn: sqlite3.Connection, tmp_path: Path) -> PeopleService:
    return PeopleService(PersonRepository(conn), StoryRepository(conn), tmp_path)


def test_ajouter_un_proche(people: PeopleService) -> None:
    mamie = people.add(" Mamie  Jeanne ", "Grand-mère")
    assert (mamie.display_name, mamie.relationship) == ("Mamie Jeanne", "grand-mère")
    assert people.add("Tonton", "").relationship == "autre"


def test_pas_de_proche_en_double(people: PeopleService) -> None:
    people.add("Mamie Jeanne", "grand-mère")
    with pytest.raises(PersonError):
        people.add("mamie jéanne", "grand-mère")
    with pytest.raises(PersonError):
        people.add("  ", "oncle")


def test_renommer_un_proche(people: PeopleService) -> None:
    papa = people.add("Papa", "père")
    people.rename(papa.id, "Papa", "beau-père")  # même nom : autorisé pour lui-même
    assert people.all()[0][0].relationship == "beau-père"


def test_supprimer_un_proche_efface_ses_recits_et_audios(
    people: PeopleService, conn: sqlite3.Connection, scene: Scene, tmp_path: Path
) -> None:
    recit = scene.story(conn, scene.yvonne, scene.q_ecole)
    fichier = tmp_path / recit.audio_path
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_bytes(b"RIFF")
    assert people.delete(scene.yvonne.id) == 1
    assert not fichier.exists()
    assert StoryRepository(conn).list_all(include_hidden=True) == []
    assert [p.display_name for p, _ in people.all()] == ["Papa"]
