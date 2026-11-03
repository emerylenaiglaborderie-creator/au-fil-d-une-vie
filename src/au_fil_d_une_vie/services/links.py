"""Liens entre récits : mots-clés validés en commun, pondérés par leur rareté.

Un mot partagé par deux récits seulement crée un lien plus fort qu'un mot présent
dans presque tous : poids d'un mot = ln(1 + N / df), où N est le nombre de récits
ayant des mots validés et df le nombre de récits qui contiennent ce mot.
"""

import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import combinations

from au_fil_d_une_vie.repositories import KeywordRepository


@dataclass(frozen=True, slots=True)
class StoryLink:
    """Lien non orienté entre deux récits (story_a < story_b)."""

    story_a: int
    story_b: int
    weight: float
    shared_keyword_ids: tuple[int, ...]

    def other(self, story_id: int) -> int:
        """L'autre extrémité du lien."""
        return self.story_b if story_id == self.story_a else self.story_a


def keyword_weights(pairs: Iterable[tuple[int, int]]) -> dict[int, float]:
    """Poids de rareté de chaque mot-clé à partir des couples (récit, mot)."""
    stories_by_keyword: dict[int, set[int]] = defaultdict(set)
    stories: set[int] = set()
    for story_id, keyword_id in pairs:
        stories_by_keyword[keyword_id].add(story_id)
        stories.add(story_id)
    n = len(stories)
    return {kw: math.log(1 + n / len(s)) for kw, s in stories_by_keyword.items()}


def compute_links(pairs: Sequence[tuple[int, int]]) -> list[StoryLink]:
    """Tous les liens, du plus fort au plus faible."""
    weights = keyword_weights(pairs)
    stories_by_keyword: dict[int, set[int]] = defaultdict(set)
    for story_id, keyword_id in pairs:
        stories_by_keyword[keyword_id].add(story_id)

    shared: dict[tuple[int, int], list[int]] = defaultdict(list)
    for keyword_id, stories in stories_by_keyword.items():
        for pair in combinations(sorted(stories), 2):
            shared[pair].append(keyword_id)

    links = [
        StoryLink(
            story_a=a,
            story_b=b,
            weight=round(sum(weights[kw] for kw in kws), 6),
            shared_keyword_ids=tuple(sorted(kws)),
        )
        for (a, b), kws in shared.items()
    ]
    return sorted(links, key=lambda link: (-link.weight, link.story_a, link.story_b))


class LinkService:
    """Liens calculés à la demande sur les mots validés des récits visibles."""

    def __init__(self, keywords: KeywordRepository) -> None:
        self._keywords = keywords

    def links(self) -> list[StoryLink]:
        return compute_links(self._keywords.validated_pairs())

    def related(self, story_id: int) -> list[StoryLink]:
        """Liens d'un récit (« Voir aussi »), du plus fort au plus faible."""
        return [link for link in self.links() if story_id in (link.story_a, link.story_b)]

    def shared_keyword_ids(self) -> set[int]:
        """Mots validés présents dans au moins deux récits visibles (étiquettes remplies)."""
        return {kw for link in self.links() for kw in link.shared_keyword_ids}

    def isolated(self, story_ids: Iterable[int]) -> list[int]:
        """Récits sans aucun lien (« pas encore de lien »)."""
        linked = {s for link in self.links() for s in (link.story_a, link.story_b)}
        return [s for s in story_ids if s not in linked]
