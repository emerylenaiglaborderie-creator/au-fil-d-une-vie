"""Données de l'écran « Ma quête » : avancement des pistes et prochaine piste."""

from collections.abc import Collection
from dataclasses import dataclass

from au_fil_d_une_vie.models import Person, Question, Theme
from au_fil_d_une_vie.repositories import PersonRepository, ProfileRepository, ThemeRepository


@dataclass(frozen=True, slots=True)
class ThemeProgress:
    theme: Theme
    done: int
    total: int


@dataclass(frozen=True, slots=True)
class PersonProgress:
    person: Person
    story_count: int


@dataclass(frozen=True, slots=True)
class Track:
    """Une piste à suivre : une question d'un thème."""

    theme: Theme
    question: Question


@dataclass(frozen=True, slots=True)
class QuestOverview:
    first_name: str | None
    themes: list[ThemeProgress]
    people: list[PersonProgress]

    @property
    def story_count(self) -> int:
        return sum(p.story_count for p in self.people)

    @property
    def interviewed_count(self) -> int:
        return sum(1 for p in self.people if p.story_count > 0)


class QuestService:
    def __init__(
        self, profile: ProfileRepository, people: PersonRepository, themes: ThemeRepository
    ) -> None:
        self._profile = profile
        self._people = people
        self._themes = themes

    def overview(self) -> QuestOverview:
        profile = self._profile.get()
        progress = self._themes.progress()
        return QuestOverview(
            first_name=profile.first_name if profile else None,
            themes=[
                ThemeProgress(theme, *progress.get(theme.id, (0, 0)))
                for theme in self._themes.list_themes()
            ],
            people=[PersonProgress(p, n) for p, n in self._people.list_with_story_count()],
        )

    def next_track(self, skip: Collection[int] = ()) -> Track | None:
        """Prochaine question à poser : d'abord dans les pistes les moins explorées.

        `skip` contient les questions déjà écartées (« Une autre piste »). Quand toutes
        ont été écartées, on repart du début.
        """
        questions = self._themes.open_questions()
        if not questions:
            return None
        remaining = [q for q in questions if q.id not in skip] or questions
        themes = {t.id: t for t in self._themes.list_themes()}
        progress = self._themes.progress()

        def explored(question: Question) -> float:
            done, total = progress.get(question.theme_id, (0, 0))
            return done / total if total else 0.0

        best = min(remaining, key=lambda q: (explored(q), themes[q.theme_id].position))
        return Track(theme=themes[best.theme_id], question=best)
