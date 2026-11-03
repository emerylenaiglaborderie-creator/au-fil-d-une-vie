# Au fil d'une vie : consignes de travail

- Le brief complet (décisions, stack, DA) est dans `docs/brief.md`. Le lire avant toute tâche importante.
- Répondre et documenter en français, ton professionnel et concis.
- Ne jamais utiliser de tiret cadratin dans les textes, commentaires et documents.
- Architecture : `ui/` ne parle qu'à `services/`, seuls les `repositories/` touchent SQLite.
- Aucune requête réseau hors téléchargement initial des modèles (explicite et refusable).
- Aucune vraie voix ni donnée réelle dans le dépôt : jeu de démo fictif uniquement.
- Interface : **PySide6** (QSS + QPainter pour les composants maison, QThread pour les tâches longues).
- Base : module `sqlite3`, SQL écrit à la main, pas d'ORM, `foreign_keys = ON`, requêtes paramétrées.
- Commandes : `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run mypy`.
