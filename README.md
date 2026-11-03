# Au fil d'une vie

[![CI](https://github.com/emerylenaiglaborderie-creator/au-fil-d-une-vie/actions/workflows/ci.yml/badge.svg)](https://github.com/emerylenaiglaborderie-creator/au-fil-d-une-vie/actions/workflows/ci.yml)

<p align="center"><img src="assets/logo/logo-complet.png" alt="Logo Au fil d'une vie" width="280"></p>

Application de bureau pour les 12 à 25 ans : partir en quête de son histoire familiale en interviewant ses proches. Chaque récit est enregistré, transcrit **sur l'ordinateur**, puis relié aux autres par ses mots-clés pour former un graphe de souvenirs.

> Tout reste sur cet ordinateur. Rien n'est envoyé en ligne.

Projet de BTS SIO option SLAM.

## État

En cours d'initialisation : structure du dépôt, outillage et CI.

## Prérequis

- [uv](https://docs.astral.sh/uv/) (installe aussi la bonne version de Python)
- macOS, Windows ou Linux

## Installation et lancement

```bash
git clone https://github.com/emerylenaiglaborderie-creator/au-fil-d-une-vie.git
cd au-fil-d-une-vie
uv sync
uv run au-fil-d-une-vie
```

## Développement

```bash
uv run pytest          # tests
uv run ruff check .    # lint
uv run ruff format .   # formatage
uv run mypy            # typage
```

## Architecture

Trois couches dans `src/au_fil_d_une_vie/` :

- `ui/` : vues et contrôleurs
- `services/` : logique métier (enregistrement, transcription, mots-clés, liens, export)
- `repositories/` : accès SQLite

Détails dans [`docs/`](docs/).
