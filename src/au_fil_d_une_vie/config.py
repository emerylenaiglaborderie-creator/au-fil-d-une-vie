"""Chemins des données locales, propres à chaque système (jamais en dur)."""

from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "AuFilDuneVie"

_dirs = PlatformDirs(appname=APP_NAME, appauthor=False)


def data_dir() -> Path:
    """Dossier racine des données de l'utilisateur."""
    return Path(_dirs.user_data_dir)


def db_path() -> Path:
    """Fichier de la base SQLite."""
    return data_dir() / "au-fil-d-une-vie.db"


def audio_dir() -> Path:
    """Dossier des enregistrements WAV."""
    return data_dir() / "audio"


def models_dir() -> Path:
    """Dossier des modèles téléchargés au premier lancement (Whisper, spaCy)."""
    return data_dir() / "models"
