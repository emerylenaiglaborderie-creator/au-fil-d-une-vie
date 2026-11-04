"""Proposition de mots-clés par TF-IDF, à partir des termes fournis par un analyseur.

L'analyseur (spaCy en production) découpe et lemmatise. Ce module ne fait que du calcul,
il reste donc testable sans modèle de langue.
"""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from au_fil_d_une_vie.i18n import _
from au_fil_d_une_vie.models import StoryKeyword
from au_fil_d_une_vie.repositories import (
    KeywordCandidate,
    KeywordRepository,
    TranscriptRepository,
)

DEFAULT_MAX_SUGGESTIONS = 8
ENTITY_BOOST = 1.5
"""Les noms de personnes et de lieux comptent davantage : ils relient bien les récits."""


@dataclass(frozen=True, slots=True)
class Term:
    """Terme retenu dans un texte."""

    lemma: str
    label: str
    is_entity: bool = False


class TextAnalyzer(Protocol):
    """Extrait les termes porteurs de sens d'un texte (noms, entités), déjà lemmatisés."""

    def terms(self, text: str) -> list[Term]: ...


def tf_idf(document: Sequence[str], corpus: Sequence[Sequence[str]]) -> dict[str, float]:
    """Score TF-IDF de chaque lemme du document par rapport au corpus (qui l'inclut).

    IDF lissé : ln((1 + N) / (1 + df)) + 1, pour qu'un mot présent partout garde un
    score positif et qu'un corpus d'un seul récit reste exploitable.
    """
    if not document:
        return {}
    n = len(corpus)
    df = Counter(lemma for doc in corpus for lemma in set(doc))
    counts = Counter(document)
    total = len(document)
    return {
        lemma: (count / total) * (math.log((1 + n) / (1 + df[lemma])) + 1)
        for lemma, count in counts.items()
    }


def rank_candidates(
    document: Sequence[Term],
    corpus: Sequence[Sequence[Term]],
    limit: int = DEFAULT_MAX_SUGGESTIONS,
) -> list[KeywordCandidate]:
    """Meilleurs mots-clés du document, poids ramenés entre 0 et 1."""
    scores = tf_idf([t.lemma for t in document], [[t.lemma for t in doc] for doc in corpus])
    entities = {t.lemma for t in document if t.is_entity}
    for lemma in entities:
        scores[lemma] *= ENTITY_BOOST

    labels: dict[str, Counter[str]] = {}
    for term in document:
        labels.setdefault(term.lemma, Counter())[term.label] += 1

    best = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]
    if not best:
        return []
    top = best[0][1]
    return [
        KeywordCandidate(
            lemma=lemma, label=labels[lemma].most_common(1)[0][0], weight=round(score / top, 4)
        )
        for lemma, score in best
    ]


def lemma_of(label: str, analyzer: TextAnalyzer | None) -> str:
    """Lemme d'un mot-clé saisi : celui de l'analyseur s'il en trouve un."""
    terms = analyzer.terms(label) if analyzer else []
    return " ".join(t.lemma for t in terms) if terms else label.strip().lower()


class KeywordService:
    """Propose des mots-clés pour un récit et enregistre les choix de l'utilisateur."""

    def __init__(
        self,
        analyzer: TextAnalyzer,
        transcripts: TranscriptRepository,
        keywords: KeywordRepository,
        max_suggestions: int = DEFAULT_MAX_SUGGESTIONS,
    ) -> None:
        self._analyzer = analyzer
        self._transcripts = transcripts
        self._keywords = keywords
        self._max = max_suggestions

    def suggest(self, story_id: int) -> list[StoryKeyword]:
        """Analyse le texte du récit et remplace les propositions non validées.

        Les autres récits servent de corpus : un mot fréquent partout pèse moins.
        """
        texts = self._transcripts.all_display_texts()
        if story_id not in texts:
            raise LookupError(f"Le récit {story_id} n'a pas encore de texte.")
        analyses = {sid: self._analyzer.terms(text) for sid, text in texts.items()}
        candidates = rank_candidates(analyses[story_id], list(analyses.values()), self._max)
        self._keywords.replace_suggestions(story_id, candidates)
        return self._keywords.for_story(story_id)

    def validate(self, story_id: int, keyword_id: int) -> None:
        self._keywords.set_validated(story_id, keyword_id, True)

    def reject(self, story_id: int, keyword_id: int) -> None:
        self._keywords.remove(story_id, keyword_id)

    def add(self, story_id: int, label: str) -> None:
        """Ajoute un mot tapé par l'utilisateur (validé d'office)."""
        clean = " ".join(label.split())
        if not clean:
            raise ValueError(_("Le mot-clé est vide."))
        self._keywords.add_validated(story_id, lemma_of(clean, self._analyzer), clean)
