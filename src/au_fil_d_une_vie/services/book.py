"""Contenu du livre de famille : les récits choisis, rangés par piste.

Ce module ne fait que rassembler les données ; la mise en page PDF est dans
`book_pdf.py`.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from au_fil_d_une_vie.models import StoryStatus
from au_fil_d_une_vie.repositories import ProfileRepository, ThemeRepository
from au_fil_d_une_vie.services.stories import StoryCard, StoryService


@dataclass(frozen=True, slots=True)
class SeeAlso:
    story_id: int
    question: str
    person_name: str


@dataclass(frozen=True, slots=True)
class BookStory:
    id: int
    question: str
    person_name: str
    recorded_at: datetime
    duration_s: float
    text: str
    note: str
    keywords: list[str]
    see_also: list[SeeAlso]


@dataclass(frozen=True, slots=True)
class BookChapter:
    theme_label: str
    stories: list[BookStory]


@dataclass(frozen=True, slots=True)
class Book:
    author: str | None
    created_at: datetime
    chapters: list[BookChapter]
    people: list[str] = field(default_factory=list)

    @property
    def story_count(self) -> int:
        return sum(len(c.stories) for c in self.chapters)


def can_be_in_book(card: StoryCard) -> bool:
    """Un récit peut entrer dans le livre s'il a son texte et n'est pas masqué."""
    return card.status is StoryStatus.TRANSCRIBED and not card.is_hidden


class BookService:
    def __init__(
        self, stories: StoryService, profile: ProfileRepository, themes: ThemeRepository
    ) -> None:
        self._stories = stories
        self._profile = profile
        self._themes = themes

    def candidates(self) -> list[StoryCard]:
        """Récits qu'on peut choisir pour le livre (texte prêt, non masqués)."""
        return [c for c in self._stories.cards() if can_be_in_book(c)]

    def set_included(self, story_id: int, included: bool) -> None:
        self._stories.set_in_book(story_id, included)

    def gather(self) -> Book:
        """Récits choisis, par piste (dans l'ordre des pistes), du plus ancien au plus récent."""
        chosen = [c for c in self.candidates() if c.in_book]
        chosen_ids = {c.id for c in chosen}
        order = {t.id: index for index, t in enumerate(self._themes.list_themes())}
        by_theme: dict[int, list[BookStory]] = {}
        labels: dict[int, str] = {}
        people: list[str] = []
        for card in sorted(chosen, key=lambda c: (c.recorded_at, c.id)):
            detail = self._stories.detail(card.id)
            if detail is None or not detail.text:
                continue
            labels[card.theme_id] = card.theme_label
            if card.person_name not in people:
                people.append(card.person_name)
            by_theme.setdefault(card.theme_id, []).append(
                BookStory(
                    id=card.id,
                    question=card.question,
                    person_name=card.person_name,
                    recorded_at=card.recorded_at,
                    duration_s=card.duration_s,
                    text=detail.text,
                    note=detail.note,
                    keywords=[t.label for t in detail.tags],
                    see_also=[
                        SeeAlso(r.id, r.question, r.person_name)
                        for r in detail.related
                        if r.id in chosen_ids  # seulement les récits présents dans le livre
                    ],
                )
            )
        profile = self._profile.get()
        return Book(
            author=profile.first_name if profile else None,
            created_at=datetime.now(UTC),
            chapters=[
                BookChapter(labels[theme_id], stories)
                for theme_id, stories in sorted(by_theme.items(), key=lambda i: order.get(i[0], 0))
            ],
            people=people,
        )
