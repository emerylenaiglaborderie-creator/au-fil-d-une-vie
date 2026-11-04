"""Bibliothèque des récits : liste, fiche détaillée, correction, mots-clés, carnet.

Masquer ou supprimer un récit est possible à tout moment (RGPD) : la suppression
efface aussi le fichier audio.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from au_fil_d_une_vie.models import StoryRow, StoryStatus
from au_fil_d_une_vie.repositories import (
    KeywordRepository,
    NoteRepository,
    StoryRepository,
    TranscriptRepository,
)
from au_fil_d_une_vie.services.keywords import KeywordService, TextAnalyzer, lemma_of
from au_fil_d_une_vie.services.links import LinkService

EXCERPT_LENGTH = 180


@dataclass(frozen=True, slots=True)
class Tag:
    """Mot-clé tel qu'affiché : plein s'il est partagé avec un autre récit."""

    keyword_id: int
    label: str
    lemma: str
    shared: bool
    validated: bool = True


@dataclass(frozen=True, slots=True)
class StoryCard:
    """Une entrée de la liste « Mes récits »."""

    id: int
    question: str
    theme_id: int
    theme_label: str
    person_name: str
    recorded_at: datetime
    duration_s: float
    status: StoryStatus
    is_hidden: bool
    link_count: int
    excerpt: str | None
    tags: list[Tag]


@dataclass(frozen=True, slots=True)
class RelatedStory:
    """Un récit lié (« Voir aussi ») et les mots qu'il partage."""

    id: int
    question: str
    person_name: str
    shared_labels: list[str]


@dataclass(frozen=True, slots=True)
class StoryDetail:
    card: StoryCard
    raw_text: str | None
    book_text: str | None
    tags: list[Tag]
    suggestions: list[Tag]
    related: list[RelatedStory]
    note: str
    audio_path: Path

    @property
    def text(self) -> str | None:
        return self.book_text if self.book_text is not None else self.raw_text


def fold(text: str) -> str:
    """Minuscules sans accents, pour une recherche tolérante (« ecole » trouve « école »)."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def excerpt(text: str, length: int = EXCERPT_LENGTH) -> str:
    """Début du texte, coupé proprement sur un mot."""
    clean = " ".join(text.split())
    if len(clean) <= length:
        return clean
    cut = clean[:length].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


def keyword_spans(text: str, tags: list[Tag]) -> list[tuple[int, int]]:
    """Positions des mots-clés dans le texte, pour le surlignage « marqueur ».

    On cherche le libellé et le lemme (avec une terminaison courte : « sabot »
    trouve « sabots »), sans tenir compte des accents ni des majuscules.
    """
    folded = fold(text)
    spans: list[tuple[int, int]] = []
    for tag in tags:
        for word in {fold(tag.label), fold(tag.lemma)}:
            if not word:
                continue
            pattern = rf"(?<!\w){re.escape(word)}(?:s|x|e|es)?(?!\w)"
            spans.extend(m.span() for m in re.finditer(pattern, folded))
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


class StoryService:
    def __init__(
        self,
        stories: StoryRepository,
        transcripts: TranscriptRepository,
        keywords: KeywordRepository,
        notes: NoteRepository,
        links: LinkService,
        audio_dir: Path,
        analyzer: TextAnalyzer | None = None,
    ) -> None:
        self._stories = stories
        self._transcripts = transcripts
        self._keywords = keywords
        self._notes = notes
        self._links = links
        self._audio_dir = audio_dir
        self._analyzer = analyzer

    # Lecture

    def cards(self, search: str = "", theme_id: int | None = None) -> list[StoryCard]:
        """Récits du plus récent au plus ancien, filtrés par piste et par recherche.

        La recherche porte sur la question, la personne, la piste, le texte et les mots-clés.
        """
        rows = self._stories.list_rows()
        links = self._links.links()
        shared = {kw for link in links for kw in link.shared_keyword_ids}
        counts: dict[int, int] = {}
        for link in links:
            counts[link.story_a] = counts.get(link.story_a, 0) + 1
            counts[link.story_b] = counts.get(link.story_b, 0) + 1
        validated = self._keywords.validated_by_story()
        needle = fold(search.strip())

        cards = []
        for row in rows:
            if theme_id is not None and row.theme_id != theme_id:
                continue
            keywords = validated.get(row.story.id, [])
            if needle and needle not in fold(self._haystack(row, [k.label for k in keywords])):
                continue
            tags = [Tag(k.id, k.label, k.lemma, k.id in shared) for k in keywords]
            cards.append(self._card(row, tags, counts.get(row.story.id, 0)))
        return cards

    def themes_with_stories(self) -> list[tuple[int, str]]:
        """Pistes qui ont au moins un récit, pour les filtres."""
        seen: dict[int, str] = {}
        for row in sorted(self._stories.list_rows(), key=lambda r: r.theme_id):
            seen.setdefault(row.theme_id, row.theme_label)
        return list(seen.items())

    def detail(self, story_id: int) -> StoryDetail | None:
        row = next((r for r in self._stories.list_rows() if r.story.id == story_id), None)
        if row is None:
            return None
        links = self._links.links()
        shared = {kw for link in links for kw in link.shared_keyword_ids}
        all_keywords = self._keywords.for_story(story_id)
        tags = [
            Tag(sk.keyword.id, sk.keyword.label, sk.keyword.lemma, sk.keyword.id in shared)
            for sk in all_keywords
            if sk.is_validated
        ]
        suggestions = [
            Tag(sk.keyword.id, sk.keyword.label, sk.keyword.lemma, False, validated=False)
            for sk in all_keywords
            if not sk.is_validated
        ]
        mine = [link for link in links if story_id in (link.story_a, link.story_b)]
        by_id = {r.story.id: r for r in self._stories.list_rows()}
        labels = {
            k.id: k.label
            for k in self._keywords.get_many(
                {kw for link in mine for kw in link.shared_keyword_ids}
            ).values()
        }
        related = [
            RelatedStory(
                id=other.story.id,
                question=other.question_text,
                person_name=other.person_name,
                shared_labels=[labels[kw] for kw in link.shared_keyword_ids if kw in labels],
            )
            for link in mine
            if (other := by_id.get(link.other(story_id))) is not None
        ]
        transcript = self._transcripts.get(story_id)
        note = self._notes.get(story_id)
        return StoryDetail(
            card=self._card(row, tags, len(mine)),
            raw_text=transcript.raw_text if transcript else None,
            book_text=transcript.book_text if transcript else None,
            tags=tags,
            suggestions=suggestions,
            related=related,
            note=note.content if note else "",
            audio_path=self._audio_dir / row.story.audio_path,
        )

    # Actions

    def save_book_text(self, story_id: int, text: str) -> None:
        """Enregistre la version livre (on peut reformuler), puis repropose des mots-clés."""
        clean = text.strip()
        if not clean:
            raise ValueError("Le texte est vide.")
        self._transcripts.save_book_text(story_id, clean)
        self._suggest_again(story_id)

    def save_raw_text(self, story_id: int, text: str) -> None:
        """Corrige la transcription elle-même (mot mal entendu, nom mal écrit).

        La version livre, si elle existe, n'est pas modifiée.
        """
        clean = text.strip()
        if not clean:
            raise ValueError("Le texte est vide.")
        if self._transcripts.get(story_id) is None:
            raise LookupError(f"Le récit {story_id} n'a pas encore de texte.")
        self._transcripts.save_raw(story_id, clean)
        self._suggest_again(story_id)

    def _suggest_again(self, story_id: int) -> None:
        """Nouvelles propositions de mots-clés ; ceux déjà validés restent."""
        if self._analyzer is not None:
            KeywordService(self._analyzer, self._transcripts, self._keywords).suggest(story_id)

    def validate_keyword(self, story_id: int, keyword_id: int) -> None:
        self._keywords.set_validated(story_id, keyword_id, True)

    def remove_keyword(self, story_id: int, keyword_id: int) -> None:
        self._keywords.remove(story_id, keyword_id)

    def add_keyword(self, story_id: int, label: str) -> None:
        clean = " ".join(label.split())
        if not clean:
            raise ValueError("Le mot-clé est vide.")
        self._keywords.add_validated(story_id, lemma_of(clean, self._analyzer), clean)

    def save_note(self, story_id: int, content: str) -> None:
        self._notes.save(story_id, content)

    def set_hidden(self, story_id: int, hidden: bool) -> None:
        self._stories.set_hidden(story_id, hidden)

    def delete(self, story_id: int) -> None:
        """Supprime le récit, tout ce qui s'y rattache et son fichier audio."""
        story = self._stories.get(story_id)
        if story is None:
            return
        self._stories.delete(story_id)
        (self._audio_dir / story.audio_path).unlink(missing_ok=True)

    # Interne

    @staticmethod
    def _haystack(row: StoryRow, keyword_labels: list[str]) -> str:
        return " ".join(
            [row.question_text, row.person_name, row.theme_label, row.text or "", *keyword_labels]
        )

    @staticmethod
    def _card(row: StoryRow, tags: list[Tag], link_count: int) -> StoryCard:
        return StoryCard(
            id=row.story.id,
            question=row.question_text,
            theme_id=row.theme_id,
            theme_label=row.theme_label,
            person_name=row.person_name,
            recorded_at=row.story.recorded_at,
            duration_s=row.story.duration_s,
            status=row.story.status,
            is_hidden=row.story.is_hidden,
            link_count=link_count,
            excerpt=excerpt(row.text) if row.text else None,
            tags=tags,
        )
