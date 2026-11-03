"""Analyseur de texte français basé sur spaCy (modèle fr_core_news_md).

Le modèle est chargé à la première utilisation : il est téléchargé au premier
lancement de l'application, jamais présent dans le dépôt.
"""

from typing import Any

from au_fil_d_une_vie.services.keywords import Term

DEFAULT_MODEL = "fr_core_news_md"
KEPT_POS = frozenset({"NOUN", "PROPN"})
ENTITY_LABELS = frozenset({"PER", "LOC"})
MIN_LENGTH = 3

ORAL_STOPWORDS = frozenset(
    {
        "chose", "truc", "machin", "fois", "moment", "temps", "jour", "an", "année",
        "gens", "monde", "façon", "manière", "côté", "coup", "peu", "bout", "euh", "ben",
    }
)  # fmt: skip
"""Mots trop vagues à l'oral pour être des mots-clés utiles."""


class SpacyAnalyzer:
    """Retient les noms communs et propres, et les entités personnes et lieux."""

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self._model_name = model_name
        self._nlp: Any = None

    def _model(self) -> Any:
        if self._nlp is None:
            import spacy

            self._nlp = spacy.load(self._model_name, disable=["parser"])
        return self._nlp

    def terms(self, text: str) -> list[Term]:
        doc = self._model()(text)
        terms: list[Term] = []
        covered: set[int] = set()

        for ent in doc.ents:
            if ent.label_ in ENTITY_LABELS:
                terms.append(Term(lemma=ent.text.lower(), label=ent.text, is_entity=True))
                covered.update(range(ent.start, ent.end))

        for token in doc:
            if (
                token.i in covered
                or token.pos_ not in KEPT_POS
                or token.is_stop
                or not token.is_alpha
                or len(token.text) < MIN_LENGTH
            ):
                continue
            lemma = token.lemma_.lower()
            if lemma in ORAL_STOPWORDS:
                continue
            label = token.text if token.pos_ == "PROPN" else lemma
            terms.append(Term(lemma=lemma, label=label))
        return terms
