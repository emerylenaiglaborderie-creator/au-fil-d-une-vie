import sqlite3
from pathlib import Path

import pytest

from au_fil_d_une_vie.repositories import ProfileRepository
from au_fil_d_une_vie.services.profile import ProfileError, ProfileService
from au_fil_d_une_vie.services.settings import Settings, SettingsStore


def test_preferences_par_defaut(tmp_path: Path) -> None:
    assert SettingsStore(tmp_path / "absent.json").load() == Settings("fr", "auto")


def test_enregistrer_et_relire(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "config" / "settings.json")
    store.save(Settings("en", "dark"))
    assert store.load() == Settings("en", "dark")


def test_un_fichier_abime_ne_bloque_pas(tmp_path: Path) -> None:
    chemin = tmp_path / "settings.json"
    chemin.write_text("{pas du json")
    assert SettingsStore(chemin).load() == Settings()
    chemin.write_text('{"language": "klingon", "theme": "dark"}')
    assert SettingsStore(chemin).load() == Settings("fr", "dark")


def test_une_preference_inconnue_est_refusee(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        SettingsStore(tmp_path / "s.json").save(Settings("fr", "violet"))


def test_changer_son_prenom_garde_l_accord_parental(conn: sqlite3.Connection) -> None:
    service = ProfileService(ProfileRepository(conn))
    premier = service.save("Léo", under_15=True, parental_consent=True)
    renomme = service.rename("Léon")
    assert renomme.first_name == "Léon"
    assert renomme.under_15 and renomme.parental_consent_at == premier.parental_consent_at


def test_renommer_sans_profil(conn: sqlite3.Connection) -> None:
    with pytest.raises(ProfileError):
        ProfileService(ProfileRepository(conn)).rename("Léo")
