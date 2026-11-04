"""Les proches interrogés : ajouter, renommer, supprimer (avec leurs récits)."""

from pathlib import Path

from au_fil_d_une_vie.i18n import _, language
from au_fil_d_une_vie.models import Person
from au_fil_d_une_vie.repositories import PersonRepository, StoryRepository
from au_fil_d_une_vie.services.stories import fold

RELATIONSHIPS = {
    "fr": (
        "grand-mère", "grand-père", "mère", "père", "tante", "oncle", "sœur", "frère",
        "cousine", "cousin", "marraine", "parrain", "autre",
    ),
    "en": (
        "grandmother", "grandfather", "mother", "father", "aunt", "uncle", "sister", "brother",
        "cousin", "godmother", "godfather", "other",
    ),
}  # fmt: skip
"""Liens proposés dans l'interface, selon la langue (on peut aussi en écrire un autre)."""


def relationships() -> tuple[str, ...]:
    return RELATIONSHIPS.get(language(), RELATIONSHIPS["fr"])


MAX_NAME_LENGTH = 40


class PersonError(ValueError):
    """Nom vide, trop long ou déjà utilisé."""


class PeopleService:
    def __init__(self, people: PersonRepository, stories: StoryRepository, audio_dir: Path) -> None:
        self._people = people
        self._stories = stories
        self._audio_dir = audio_dir

    def all(self) -> list[tuple[Person, int]]:
        """Proches et nombre de récits visibles de chacun."""
        return self._people.list_with_story_count()

    def add(self, display_name: str, relationship: str) -> Person:
        name, link = self._check(display_name, relationship)
        return self._people.add(name, link)

    def rename(self, person_id: int, display_name: str, relationship: str) -> None:
        name, link = self._check(display_name, relationship, person_id)
        self._people.rename(person_id, name, link)

    def delete(self, person_id: int) -> int:
        """Supprime le proche, ses récits et leurs fichiers audio. Retourne le nombre de récits."""
        own = [s for s in self._stories.list_all(include_hidden=True) if s.person_id == person_id]
        for story in own:
            (self._audio_dir / story.audio_path).unlink(missing_ok=True)
        self._people.delete(person_id)
        return len(own)

    def _check(
        self, display_name: str, relationship: str, person_id: int | None = None
    ) -> tuple[str, str]:
        name = " ".join(display_name.split())
        link = " ".join(relationship.split()).lower() or relationships()[-1]
        if not name:
            raise PersonError(_("Indique comment tu appelles cette personne."))
        if len(name) > MAX_NAME_LENGTH:
            raise PersonError(_("Ce nom est trop long."))
        taken = {fold(p.display_name) for p in self._people.list_all() if p.id != person_id}
        if fold(name) in taken:
            raise PersonError(_("« {name} » est déjà dans tes proches.").format(name=name))
        return name, link
