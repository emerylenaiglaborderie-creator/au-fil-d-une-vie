"""Analyseur de texte basé sur spaCy, en français ou en anglais.

Les modèles (fr_core_news_md, en_core_web_sm) sont des dépendances Python installées
par `uv sync` ; ils sont chargés à la première utilisation.
"""

from typing import Any

from au_fil_d_une_vie.services.keywords import Term

MODELS = {"fr": "fr_core_news_md", "en": "en_core_web_sm"}
DEFAULT_MODEL = MODELS["fr"]
KEPT_POS = frozenset({"NOUN", "PROPN"})
ENTITY_LABELS = frozenset({"PER", "PERSON", "LOC", "GPE"})  # étiquettes françaises et anglaises
MIN_LENGTH = 3

ORAL_STOPWORDS = {
    "fr": frozenset({
        "chose", "truc", "machin", "fois", "moment", "temps", "jour", "an", "année",
        "gens", "monde", "façon", "manière", "côté", "coup", "peu", "bout", "euh", "ben",
    }),
    "en": frozenset({
        "thing", "stuff", "time", "day", "year", "people", "way", "lot", "bit", "kind",
        "sort", "um", "uh", "yeah", "something", "anything", "everything",
    }),
}  # fmt: skip
"""Mots trop vagues à l'oral pour être des mots-clés utiles."""


class SpacyAnalyzer:
    """Retient les noms communs et propres, et les entités personnes et lieux."""

    def __init__(self, model_name: str = DEFAULT_MODEL, language: str = "fr") -> None:
        self._model_name = model_name
        self._stopwords = ORAL_STOPWORDS.get(language, ORAL_STOPWORDS["fr"])
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
            if lemma in self._stopwords:
                continue
            label = token.text if token.pos_ == "PROPN" else lemma
            terms.append(Term(lemma=lemma, label=label))
        return terms
