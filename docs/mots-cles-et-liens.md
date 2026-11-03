# Mots-clés et liens entre récits

## Proposition de mots-clés

1. **Analyse** (`SpacyAnalyzer`, modèle `fr_core_news_md`) : on ne garde que les noms communs, les noms propres et les entités personnes et lieux, lemmatisés (« sabots » devient « sabot »). Les mots vides et les mots trop vagues à l'oral (« chose », « truc », « fois »...) sont écartés.
2. **Score TF-IDF**, calculé en Python pur (`services/keywords.py`) :
   - TF : fréquence du mot dans le récit ;
   - IDF lissé : `ln((1 + N) / (1 + df)) + 1`, où N est le nombre de récits et df le nombre de récits qui contiennent le mot. Un mot présent partout pèse moins.
   - Les entités (personnes, lieux) sont multipliées par 1,5 : elles relient bien les récits.
3. Les 8 meilleurs mots sont **proposés**, jamais imposés. L'utilisateur valide, rejette ou ajoute ses propres mots.
4. Une nouvelle analyse (après correction du texte) remplace les propositions, mais **garde les mots déjà validés**.

L'analyseur est derrière une interface (`TextAnalyzer`) : les tests utilisent un analyseur simplifié, sans modèle de langue.

## Liens entre récits

Seuls les mots **validés** des récits **visibles** comptent (`services/links.py`).

- Poids d'un mot : `ln(1 + N / df)`. Un mot partagé par deux récits seulement crée un lien plus fort qu'un mot présent dans presque tous.
- Poids d'un lien entre deux récits : somme des poids de leurs mots communs.
- Un récit sans aucun mot commun est **isolé** (« pas encore de lien » dans le graphe).

Ce choix a été préféré à l'indice de Jaccard, qui traite tous les mots à égalité : avec la pondération par rareté, « institutrice » relie plus fortement que « famille ».

## Exemple : jeu de démo

| Lien | Mots communs | Poids |
|---|---|---|
| École (Yvonne) et Premier jour (Papa) | école, institutrice, craie | 4,16 |
| École (Yvonne) et Étés (Yvonne) | bourg, sabots | 2,49 |
| Plat (Papa) et Étés (Yvonne) | ferme | 1,39 |
| École, Papi et Étés (Yvonne) | bourg | 1,10 |

Le récit du garage (Tonton Alain) reste isolé.
