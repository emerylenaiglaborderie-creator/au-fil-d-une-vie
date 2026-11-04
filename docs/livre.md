# Livre de famille

Le livre rassemble les récits choisis en un PDF à lire, imprimer ou offrir. Exemple tiré du jeu de démo (fictif) : [captures/livre-exemple.pdf](captures/livre-exemple.pdf).

## Choisir les récits

- Un récit entre dans le livre par un **ajout volontaire** : bouton « Ajouter au livre de famille » sur sa fiche, ou case à cocher dans la fenêtre « Livre de famille » (en-tête de l'application).
- Seuls les récits **transcrits et visibles** peuvent y entrer. Masquer un récit le retire de fait du livre.
- Le texte utilisé est la **version livre** si elle existe, sinon la transcription.

## Contenu du PDF (format A5)

1. **Couverture** : logo, « Le livre de famille », « recueilli par » le prénom du profil, nombre de récits et voix entendues, date.
2. **Sommaire** : une entrée par piste et par récit, avec numéros de page (`TableOfContents`).
3. **Un chapitre par piste**, dans l'ordre des pistes, récits du plus ancien au plus récent. Pour chaque récit : la question, « Prénom raconte », la date, le texte, l'encadré « Ce que j'en retiens » (le carnet), les mots-clés, les renvois **« Voir aussi »** avec numéro de page et lien cliquable, puis le fil séparateur.
4. **Index des mots** : chaque mot-clé validé et les pages des récits qui le contiennent (`SimpleIndex`).

Le PDF contient aussi des signets (piste puis récit) pour naviguer dans les lecteurs PDF.

## Choix techniques

- **ReportLab** (pur Python) : aucune dépendance système, identique sur les trois systèmes.
- Polices embarquées dans le PDF (Lora, Jost, Sacramento), comme dans l'application.
- Les renvois « Voir aussi » sont des éléments maison (`SeeAlsoLine`) qui lisent la page de destination notée lors de la passe précédente ; `multiBuild` répète la mise en page jusqu'à ce que sommaire, index et numéros soient stables.
- La mise en page tourne dans un thread : l'interface reste utilisable pendant la création.
