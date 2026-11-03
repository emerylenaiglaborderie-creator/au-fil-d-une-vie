# Au fil d'une vie

[![CI](https://github.com/emerylenaiglaborderie-creator/au-fil-d-une-vie/actions/workflows/ci.yml/badge.svg)](https://github.com/emerylenaiglaborderie-creator/au-fil-d-une-vie/actions/workflows/ci.yml)

<p align="center"><img src="assets/logo/logo-complet.png" alt="Logo Au fil d'une vie" width="280"></p>

Application de bureau pour les 12 à 25 ans : partir en quête de son histoire familiale en interviewant ses proches. Chaque récit est enregistré, transcrit **sur l'ordinateur**, puis relié aux autres par ses mots-clés pour former un graphe de souvenirs.

> Tout reste sur cet ordinateur. Rien n'est envoyé en ligne.

Projet de BTS SIO option SLAM.

<p align="center"><img src="docs/captures/quete.png" alt="Écran Ma quête" width="760"></p>

## État

| Partie | Avancement |
|---|---|
| Base de données, repositories | fait |
| Mots-clés (TF-IDF) et liens entre récits | fait |
| Écran « Ma quête » | fait |
| Interview, Récits, Fiche récit, Graphe | à venir |
| Transcription locale, livre de famille | à venir |

## Prérequis

- [uv](https://docs.astral.sh/uv/) (installe aussi la bonne version de Python)
- macOS, Windows ou Linux

## Installation et lancement

```bash
git clone https://github.com/emerylenaiglaborderie-creator/au-fil-d-une-vie.git
cd au-fil-d-une-vie
uv sync
uv run au-fil-d-une-vie          # ta propre quête
uv run au-fil-d-une-vie --demo   # avec le jeu de démo fictif
```

## Développement

```bash
uv run pytest          # tests
uv run ruff check .    # lint
uv run ruff format .   # formatage
uv run mypy            # typage
uv run python scripts/captures.py       # captures d'écran (docs/captures/)
uv run python scripts/generer_images.py # images de l'interface à partir du logo
```

## Architecture

Trois couches dans `src/au_fil_d_une_vie/` :

- `ui/` : vues et contrôleurs
- `services/` : logique métier (enregistrement, transcription, mots-clés, liens, export)
- `repositories/` : accès SQLite

Détails dans [`docs/`](docs/).
