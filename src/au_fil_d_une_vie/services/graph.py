"""Graphe des liens : les récits et les mots qu'ils partagent, placés avec networkx.

Le graphe est biparti : un fil relie un récit à chaque mot validé qu'il partage
avec au moins un autre récit. Les positions sont calculées par `spring_layout`
(graine fixe : le dessin ne change pas d'une ouverture à l'autre) et ramenées
entre 0 et 1 ; l'interface les met à l'échelle de son plateau.
"""

import math
from dataclasses import dataclass

import networkx as nx

from au_fil_d_une_vie.repositories import KeywordRepository, StoryRepository
from au_fil_d_une_vie.services.links import StoryLink, compute_links, keyword_weights

SEED = 7
# Zones du plateau (fractions) : les récits sans lien sont rangés dans une colonne à droite.
LINKED_X = (0.10, 0.76)
LINKED_X_ALONE = (0.10, 0.90)
LINKED_Y = (0.10, 0.82)
ISOLATED_X = 0.88
ISOLATED_Y = (0.18, 0.80)


@dataclass(frozen=True, slots=True)
class StoryNode:
    id: int
    question: str
    person_name: str
    x: float
    y: float
    linked: bool


@dataclass(frozen=True, slots=True)
class WordNode:
    keyword_id: int
    label: str
    x: float
    y: float
    story_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class GraphView:
    stories: list[StoryNode]
    words: list[WordNode]
    word_edges: list[tuple[int, int]]  # (récit, mot)
    story_links: list[StoryLink]
    groups: int  # groupes de récits reliés entre eux (composantes connexes)

    def story(self, story_id: int) -> StoryNode | None:
        return next((s for s in self.stories if s.id == story_id), None)

    def busiest_story(self) -> int | None:
        """Le récit qui a le plus de mots communs (sélection par défaut)."""
        if not self.stories:
            return None
        counts = {s.id: 0 for s in self.stories}
        for story_id, _keyword in self.word_edges:
            counts[story_id] += 1
        return max(self.stories, key=lambda s: (counts[s.id], -s.id)).id


def _normalize(
    positions: dict[object, tuple[float, float]],
    x_range: tuple[float, float],
    y_range: tuple[float, float],
) -> dict[object, tuple[float, float]]:
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    span_x = (max(xs) - min(xs)) or 1.0
    span_y = (max(ys) - min(ys)) or 1.0
    result = {}
    for node, (x, y) in positions.items():
        fx = (x - min(xs)) / span_x if len(xs) > 1 else 0.5
        fy = (y - min(ys)) / span_y if len(ys) > 1 else 0.5
        result[node] = (
            x_range[0] + fx * (x_range[1] - x_range[0]),
            y_range[0] + fy * (y_range[1] - y_range[0]),
        )
    return result


class GraphService:
    def __init__(self, stories: StoryRepository, keywords: KeywordRepository) -> None:
        self._stories = stories
        self._keywords = keywords

    def build(self) -> GraphView:
        rows = {r.story.id: r for r in self._stories.list_rows(include_hidden=False)}
        pairs = [(s, k) for s, k in self._keywords.validated_pairs() if s in rows]
        weights = keyword_weights(pairs)
        stories_by_word: dict[int, set[int]] = {}
        for story_id, keyword_id in pairs:
            stories_by_word.setdefault(keyword_id, set()).add(story_id)
        shared = {kw: ids for kw, ids in stories_by_word.items() if len(ids) >= 2}

        graph = nx.Graph()
        for story_id in rows:
            graph.add_node(("s", story_id))
        for keyword_id, ids in shared.items():
            for story_id in ids:
                graph.add_edge(("s", story_id), ("k", keyword_id), weight=weights[keyword_id])

        linked = {story_id for ids in shared.values() for story_id in ids}
        isolated = [sid for sid in rows if sid not in linked]
        connected = graph.subgraph([n for n in graph.nodes if graph.degree(n) > 0])

        positions: dict[object, tuple[float, float]] = {}
        if connected.number_of_nodes():
            # k plus grand que la valeur par défaut (1/√n) : les nœuds s'écartent davantage,
            # pour laisser la place aux plaques de titre et aux étiquettes de mots.
            k = 2.2 / math.sqrt(connected.number_of_nodes())
            raw = nx.spring_layout(connected, seed=SEED, weight="weight", k=k, iterations=300)
            x_range = LINKED_X if isolated else LINKED_X_ALONE
            positions = _normalize(
                {node: (float(p[0]), float(p[1])) for node, p in raw.items()}, x_range, LINKED_Y
            )
        for index, story_id in enumerate(isolated):
            share = (index + 1) / (len(isolated) + 1)
            y = ISOLATED_Y[0] + share * (ISOLATED_Y[1] - ISOLATED_Y[0])
            x = ISOLATED_X if linked else 0.5
            positions[("s", story_id)] = (x, y if linked else 0.2 + share * 0.6)

        labels = {k.id: k.label for k in self._keywords.get_many(shared).values()}
        story_projection = nx.Graph()
        story_projection.add_nodes_from(rows)
        links = compute_links(pairs)
        story_projection.add_edges_from((link.story_a, link.story_b) for link in links)

        return GraphView(
            stories=[
                StoryNode(
                    id=sid,
                    question=row.question_text,
                    person_name=row.person_name,
                    x=positions[("s", sid)][0],
                    y=positions[("s", sid)][1],
                    linked=sid in linked,
                )
                for sid, row in rows.items()
            ],
            words=[
                WordNode(
                    keyword_id=kw,
                    label=labels.get(kw, ""),
                    x=positions[("k", kw)][0],
                    y=positions[("k", kw)][1],
                    story_ids=tuple(sorted(ids)),
                )
                for kw, ids in sorted(shared.items())
            ],
            word_edges=sorted((sid, kw) for kw, ids in shared.items() for sid in ids),
            story_links=links,
            groups=sum(1 for c in nx.connected_components(story_projection) if len(c) > 1),
        )
