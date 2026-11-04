"""Profil du jeune qui mène la quête, et accord parental sous 15 ans.

En France, un mineur peut consentir seul au traitement de ses données à partir de
15 ans ; en dessous, l'accord d'un parent est nécessaire. On ne demande pas la date
de naissance (minimisation des données) : seulement « moins de 15 ans » ou non.
"""

from datetime import UTC, datetime

from au_fil_d_une_vie.models import Profile
from au_fil_d_une_vie.repositories import ProfileRepository

MAX_NAME_LENGTH = 40


class ProfileError(ValueError):
    """Profil incomplet ou accord parental manquant."""


class ProfileService:
    def __init__(self, profile: ProfileRepository) -> None:
        self._profile = profile

    def get(self) -> Profile | None:
        return self._profile.get()

    def save(self, first_name: str, under_15: bool, parental_consent: bool = False) -> Profile:
        name = " ".join(first_name.split())
        if not name:
            raise ProfileError("Indique ton prénom.")
        if len(name) > MAX_NAME_LENGTH:
            raise ProfileError("Ce prénom est trop long.")
        if under_15 and not parental_consent:
            raise ProfileError("Sous 15 ans, l'accord d'un parent est nécessaire.")
        existing = self._profile.get()
        consent_at = None
        if under_15:
            consent_at = (
                existing.parental_consent_at
                if existing and existing.parental_consent_at
                else datetime.now(UTC)
            )
        return self._profile.save(name, under_15, consent_at)
