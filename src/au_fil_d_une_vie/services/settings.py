"""Préférences de l'application : langue et thème.

Ce ne sont pas des données personnelles : elles sont gardées dans un petit fichier
JSON du dossier de configuration, hors de la base (elles servent avant même de
l'ouvrir, et valent pour toutes les quêtes de l'ordinateur).
"""

import json
import logging
from dataclasses import asdict, dataclass, replace
from pathlib import Path

log = logging.getLogger(__name__)

LANGUAGES = ("fr", "en")
THEMES = ("auto", "light", "dark")


@dataclass(frozen=True, slots=True)
class Settings:
    language: str = "fr"
    theme: str = "auto"  # « auto » suit le réglage du système


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> Settings:
        """Préférences enregistrées ; valeurs par défaut si le fichier manque ou est abîmé."""
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return Settings()
        except (OSError, ValueError):
            log.warning("Préférences illisibles, valeurs par défaut utilisées : %s", self._path)
            return Settings()
        settings = Settings()
        if data.get("language") in LANGUAGES:
            settings = replace(settings, language=data["language"])
        if data.get("theme") in THEMES:
            settings = replace(settings, theme=data["theme"])
        return settings

    def save(self, settings: Settings) -> None:
        if settings.language not in LANGUAGES or settings.theme not in THEMES:
            raise ValueError("Préférence inconnue.")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(asdict(settings), indent=2) + "\n", encoding="utf-8")
