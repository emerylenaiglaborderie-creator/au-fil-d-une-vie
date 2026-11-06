"""Graphe des liens : les récits posés sur un fil, reliés par des arcs.

Les récits visibles sont rangés dans l'ordre où ils ont été recueillis, à intervalles
réguliers le long d'un fil horizontal (positions entre 0 et 1, que l'interface met à
l'échelle). Deux récits qui partagent des mots validés sont reliés par un arc qui
porte ces mots ; plus les mots sont rares, plus le lien est fort.

Pour rester lisible quel que soit le nombre de récits, l'affichage change de palier :

* jusqu'à `FULL_MAX` récits, tout est affiché (titres, tous les arcs) ;
* au-delà, le fil est compact : titres au survol, et chaque récit ne montre que ses
  `STRONG_PER_STORY` liens les plus forts ; tous ses liens apparaissent quand on le
  sélectionne. Aucun récit n'est jamais retiré du fil.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

import networkx as nx

from au_fil_d_une_vie.repositories import KeywordRepository, StoryRepository
from au_fil_d_une_vie.services.links import StoryLink, compute_links

FULL_MAX = 15
STRONG_PER_STORY = 3


class Density(StrEnum):
    """Palier d'affichage du fil."""

    FULL = "full"
    COMPACT = "compact"


@dataclass(frozen=True, slots=True)
class StoryNode:
    """Un récit, posé sur le fil."""

    id: int
    question: str
    person_name: str
    recorded_at: datetime
    position: float  # de 0 (le plus ancien) à 1 (le plus récent)
    linked: bool


@dataclass(frozen=True, slots=True)
class Arc:
    """Lien entre deux récits, dessiné comme un arc au-dessus du fil."""

    story_a: int  # le plus ancien des deux
    story_b: int
    weight: float
    words: tuple[str, ...]  # mots partagés, du plus rare au plus courant
    strong: bool  # parmi les liens les plus forts de l'un de ses deux récits

    def touches(self, story_id: int | None) -> bool:
        return story_id in (self.story_a, self.story_b)


@dataclass(frozen=True, slots=True)
class MonthMark:
    """Début d'un mois sur le fil (le premier récit recueilli ce mois-là)."""

    month: date  # premier jour du mois
    position: float


@dataclass(frozen=True, slots=True)
class GraphView:
    stories: list[StoryNode]  # dans l'ordre du fil
    arcs: list[Arc]  # du plus fort au plus faible
    months: list[MonthMark]
    density: Density
    groups: int  # groupes de récits reliés entre eux (composantes connexes)

    def story(self, story_id: int) -> StoryNode | None:
        return next((s for s in self.stories if s.id == story_id), None)

    def busiest_story(self) -> int | None:
        """Le récit qui a le plus de liens (sélection par défaut)."""
        if not self.stories:
            return None
        counts = {s.id: 0 for s in self.stories}
        for arc in self.arcs:
            counts[arc.story_a] += 1
            counts[arc.story_b] += 1
        return max(self.stories, key=lambda s: (counts[s.id], -s.id)).id

    def visible_arcs(self, focus: set[int]) -> list[Arc]:
        """Arcs à dessiner : tous en palier complet, sinon les forts et ceux du focus."""
        if self.density is Density.FULL:
            return list(self.arcs)
        return [a for a in self.arcs if a.strong or a.story_a in focus or a.story_b in focus]


def strongest_links(links: list[StoryLink], per_story: int) -> set[tuple[int, int]]:
    """Paires (a, b) qui font partie des `per_story` liens les plus forts d'un des récits."""
    by_story: dict[int, list[StoryLink]] = defaultdict(list)
    for link in links:  # déjà triés du plus fort au plus faible
        by_story[link.story_a].append(link)
        by_story[link.story_b].append(link)
    return {
        (link.story_a, link.story_b)
        for story_links in by_story.values()
        for link in story_links[:per_story]
    }


def _positions(count: int) -> list[float]:
    """Intervalles réguliers ; un récit seul est au milieu du fil."""
    if count == 1:
        return [0.5]
    return [index / (count - 1) for index in range(count)]


class GraphService:
    def __init__(self, stories: StoryRepository, keywords: KeywordRepository) -> None:
        self._stories = stories
        self._keywords = keywords

    def build(self) -> GraphView:
        rows = sorted(
            self._stories.list_rows(include_hidden=False),
            key=lambda r: (r.story.recorded_at, r.story.id),
        )
        visible = {r.story.id for r in rows}
        pairs = [(s, k) for s, k in self._keywords.validated_pairs() if s in visible]
        links = compute_links(pairs)
        strong = strongest_links(links, STRONG_PER_STORY)

        keyword_ids = {kw for link in links for kw in link.shared_keyword_ids}
        labels = {k.id: k.label for k in self._keywords.get_many(keyword_ids).values()}
        df: dict[int, int] = defaultdict(int)
        for _story, keyword_id in pairs:
            df[keyword_id] += 1
        linked = {story_id for link in links for story_id in (link.story_a, link.story_b)}

        positions = _positions(len(rows))
        stories = [
            StoryNode(
                id=row.story.id,
                question=row.question_text,
                person_name=row.person_name,
                recorded_at=row.story.recorded_at,
                position=position,
                linked=row.story.id in linked,
            )
            for row, position in zip(rows, positions, strict=True)
        ]
        order = {s.id: s.position for s in stories}
        arcs = []
        for link in links:
            a, b = sorted((link.story_a, link.story_b), key=lambda sid: order[sid])
            words = sorted(link.shared_keyword_ids, key=lambda kw: (df[kw], labels.get(kw, "")))
            arcs.append(
                Arc(
                    story_a=a,
                    story_b=b,
                    weight=link.weight,
                    words=tuple(labels[kw] for kw in words if kw in labels),
                    strong=(link.story_a, link.story_b) in strong,
                )
            )

        months: list[MonthMark] = []
        for story in stories:
            month = story.recorded_at.date().replace(day=1)
            if not months or months[-1].month != month:
                months.append(MonthMark(month=month, position=story.position))

        projection = nx.Graph()
        projection.add_nodes_from(visible)
        projection.add_edges_from((link.story_a, link.story_b) for link in links)

        return GraphView(
            stories=stories,
            arcs=arcs,
            months=months,
            density=Density.FULL if len(stories) <= FULL_MAX else Density.COMPACT,
            groups=sum(1 for c in nx.connected_components(projection) if len(c) > 1),
        )
