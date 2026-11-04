"""Données de l'écran « Ma quête » : avancement des pistes et prochaine piste."""

from collections.abc import Collection
from dataclasses import dataclass

from au_fil_d_une_vie.i18n import _
from au_fil_d_une_vie.models import Person, Question, Theme
from au_fil_d_une_vie.repositories import PersonRepository, ProfileRepository, ThemeRepository

DEFAULT_FOLLOW_UPS = (
    "Tu te souviens d'un détail précis ?",
    "Qui était là avec toi ?",
    "Qu'est-ce que tu ressentais à ce moment-là ?",
)
"""Relances utilisées quand une question n'a pas les siennes."""


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

    def track(self, question_id: int) -> Track | None:
        """Piste correspondant à une question donnée."""
        question = self._themes.get_question(question_id)
        if question is None:
            return None
        theme = self._themes.get_theme(question.theme_id)
        return Track(theme=theme, question=question) if theme else None

    def follow_ups(self, question_id: int) -> list[str]:
        """Relances « Pour creuser » de la question, ou relances générales."""
        return self._themes.follow_ups_for(question_id) or [_(text) for text in DEFAULT_FOLLOW_UPS]

    def other_tracks(self, exclude_question_id: int | None, limit: int = 4) -> list[Track]:
        """Autres pistes à proposer : une par thème, les moins explorés d'abord."""
        themes = {t.id: t for t in self._themes.list_themes()}
        progress = self._themes.progress()

        def explored(question: Question) -> tuple[float, int]:
            done, total = progress.get(question.theme_id, (0, 0))
            return (done / total if total else 0.0, themes[question.theme_id].position)

        seen: set[int] = set()
        tracks: list[Track] = []
        candidates = [q for q in self._themes.open_questions() if q.id != exclude_question_id]
        for question in sorted(candidates, key=explored):
            if question.theme_id in seen:
                continue
            seen.add(question.theme_id)
            tracks.append(Track(theme=themes[question.theme_id], question=question))
            if len(tracks) == limit:
                break
        return tracks

    def people(self) -> list[Person]:
        return [p.person for p in self.overview().people]
