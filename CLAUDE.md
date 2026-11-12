# Au fil d'une vie : consignes de travail

- Le brief complet (décisions, stack, DA) est dans `docs/brief.md`. Le lire avant toute tâche importante.
- Répondre et documenter en français, ton professionnel et concis.
- Ne jamais utiliser de tiret cadratin dans les textes, commentaires et documents.
- Architecture : `ui/` ne parle qu'à `services/`, seuls les `repositories/` touchent SQLite.
- Aucune requête réseau hors téléchargement initial des modèles (explicite et refusable).
- Aucune vraie voix ni donnée réelle dans le dépôt : jeu de démo fictif uniquement.
- Interface : **PySide6** (QSS + QPainter pour les composants maison ; tâches longues dans des threads de travail reliés à l'interface par des signaux Qt, voir `ui/bridge.py`).
- Base : **SQLAlchemy 2.0** et migrations **Alembic** (décision du 12 novembre 2026, validée avec l'enseignant), réécriture complète de la couche d'accès. SQLAlchemy n'est importé que dans `repositories/`, `foreign_keys = ON` conservé.
- Commandes : `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run mypy`.

## Mode de travail (depuis le 12 novembre 2026)

L'étudiante code elle-même la suite du projet ; Claude encadre.

- Ne pas écrire le code de production à sa place : expliquer, orienter, poser des questions, relire.
- Donner des pistes et de courts exemples isolés plutôt que des fichiers complets.
- Relire ce qu'elle produit : signaler les erreurs, en expliquer la cause, la laisser corriger.
- Si elle demande explicitement du code, le fournir, en expliquant les choix.
