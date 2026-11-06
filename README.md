# Au fil d'une vie

[![CI](https://github.com/emerylenaiglaborderie-creator/au-fil-d-une-vie/actions/workflows/ci.yml/badge.svg)](https://github.com/emerylenaiglaborderie-creator/au-fil-d-une-vie/actions/workflows/ci.yml)

<p align="center"><img src="assets/logo/logo-complet.png" alt="Logo Au fil d'une vie" width="280"></p>

Application de bureau pour les 12 à 25 ans : partir en quête de son histoire familiale en interviewant ses proches. Chaque récit est enregistré, transcrit **sur l'ordinateur**, puis relié aux autres par ses mots-clés : les souvenirs se cousent les uns aux autres le long d'un fil.

> Tout reste sur cet ordinateur. Rien n'est envoyé en ligne.

Projet de BTS SIO option SLAM.

<p align="center">
  <img src="docs/captures/arbre.png" alt="Accueil : l'arbre et ses étiquettes" width="420">
  <img src="docs/captures/quete.png" alt="Les pistes" width="420">
  <img src="docs/captures/interview.png" alt="Interview" width="420">
  <img src="docs/captures/recits.png" alt="Mes récits" width="420">
  <img src="docs/captures/recit.png" alt="Fiche d'un récit" width="420">
  <img src="docs/captures/graphe.png" alt="Graphe des liens : le mètre ruban" width="420">
  <img src="docs/captures/arbre-nuit.png" alt="Thème Nuit" width="420">
  <img src="docs/captures/parametres.png" alt="Réglages" width="420">
</p>

## État

| Partie | Avancement |
|---|---|
| Base de données, repositories | fait |
| Mots-clés (TF-IDF) et liens entre récits | fait |
| Accueil en arbre (étiquettes d'herbier, racines des proches), style herbier sur tous les écrans | fait |
| Écrans « Les pistes » et « Interview » (enregistrement audio, consentement du proche) | fait |
| Transcription locale (faster-whisper) et mots-clés proposés | fait |
| Récits (fil, recherche, filtres) et Fiche récit (écoute, correction, mots-clés, carnet, masquer, supprimer) | fait |
| Graphe des liens (mètre ruban chronologique, liens cousus, filtres par proche, piste ou mot) | fait |
| Premier lancement (prénom, nom de famille facultatif, accord parental sous 15 ans) et gestion des proches | fait |
| Réglages : profil, thème Jour / Nuit / comme l'ordinateur ; icône de l'application | fait |
| Pistes personnalisables : créer, renommer, réordonner, supprimer pistes et questions | fait |
| Interface en français et en anglais (transcription, mots-clés et pistes compris) | fait |
| Livre de famille en PDF (sommaire, Voir aussi, index des mots) : [exemple](docs/captures/livre-exemple.pdf) | fait |
| Préparation de la synchronisation familiale (UUID, journal des modifications) | fait |
| Serveur familial (PostgreSQL, API FastAPI) et synchronisation entre les ordinateurs | à faire |
| Boîtier Raspberry Pi (serveur familial, réseau isolé) | bonus, à faire |

## Stack technique

| Domaine | Choix | Rôle dans l'application |
|---|---|---|
| Langage | **Python 3.12** | Tout le code, de l'interface au calcul des liens |
| Interface | **PySide6** (Qt 6) : QtWidgets, QGraphicsScene, QSS, QPainter | Écrans, arbre d'accueil, composants maison dessinés (étiquettes d'herbier, racines, rameaux, mètre ruban, points rouges) |
| Polices | Sacramento, Jost, Lora (licence OFL, embarquées) | Écriture manuscrite, interface, texte des récits |
| Audio | **QtMultimedia** (`QAudioSource`, `QMediaPlayer`) + module `wave` | Enregistrement WAV 16 kHz mono, lecture des récits |
| Transcription | **faster-whisper** (CTranslate2, processeur, int8), modèle `small` ou `base` | Texte des récits, calculé sur l'ordinateur |
| Analyse de la langue | **spaCy** `fr_core_news_md`, `en_core_web_sm` | Lemmes, noms, entités (personnes, lieux) |
| Traduction | module `i18n` maison (principe de gettext) | Interface en français et en anglais, catalogue vérifié par les tests |
| Mots-clés | **TF-IDF** écrit en Python | Proposition des mots les plus caractéristiques, validés par l'utilisateur |
| Liens | Mots partagés pondérés par leur **rareté** (IDF) | Force du lien entre deux récits, « Voir aussi » |
| Graphe | Diagramme en arcs (QPainter), **networkx** pour les composantes connexes | Récits sur un mètre ruban chronologique, liens cousus, paliers, défilement, filtres |
| Livre de famille | **ReportLab** (`multiBuild`, `TableOfContents`, `SimpleIndex`) | PDF avec sommaire, renvois « Voir aussi » et index |
| Base de données | **SQLite** via `sqlite3`, SQL écrit à la main, mode WAL | Récits, consentements, textes, mots-clés, carnet |
| Dossiers de données | **platformdirs** | Emplacement propre à chaque système, jamais en dur |
| Tests | **pytest**, **pytest-qt** | Services, base, interface (sans écran) |
| Qualité | **ruff** (lint, format), **mypy** (strict) | Style et typage vérifiés |
| CI | **GitHub Actions** | Lint, typage et tests sur macOS, Windows et Ubuntu |
| Dépendances | **uv** (`pyproject.toml`, `uv.lock`) | Installation reproductible en une commande |

Architecture en trois couches (`ui/`, `services/`, `repositories/`) : l'interface ne parle qu'aux services, seuls les repositories touchent la base. Détails dans [`docs/`](docs/).

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

### Premier lancement

L'application propose de télécharger le modèle de transcription (environ 465 Mo, une seule fois). C'est la seule fois où elle utilise internet ; on peut refuser et enregistrer quand même, les textes seront préparés plus tard. Sur une machine modeste : `uv run au-fil-d-une-vie --modele base`. Détails : [docs/transcription.md](docs/transcription.md).

### Micro

L'enregistrement utilise le micro par défaut du système (WAV 16 kHz mono, gardé dans le dossier de données).

- **macOS** : au premier enregistrement, le système demande l'accès au micro pour l'application qui lance le programme (Terminal, iTerm, VS Code...). En cas de refus : Réglages Système, Confidentialité et sécurité, Micro.
- **Linux** : un serveur audio (PipeWire ou PulseAudio) doit être actif.

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

- `ui/` : vues, composants maison dessinés, fenêtres
- `services/` : logique métier (enregistrement, transcription, mots-clés, liens, graphe, livre)
- `repositories/` : accès SQLite (seule couche qui touche la base)

## Dossier

| Document | Contenu |
|---|---|
| [Brief](docs/brief.md) | Décisions, direction artistique, état d'avancement |
| [Architecture](docs/architecture.md) | Couches, parcours d'un récit, threads, qualité |
| [Interface](docs/interface.md) | Navigation par l'arbre, style herbier, accessibilité |
| [Graphe des liens](docs/graphe.md) | Mètre ruban, paliers, défilement, filtres |
| [Modèle de données](docs/modele-donnees.md) | Tables, règles portées par la base, préparation de la synchronisation |
| [Mots-clés et liens](docs/mots-cles-et-liens.md) | TF-IDF, validation, pondération par la rareté |
| [Transcription](docs/transcription.md) | faster-whisper hors ligne, mesures, limites |
| [Livre de famille](docs/livre.md) | PDF avec sommaire, renvois et index |
| [Conformité RGPD](docs/rgpd.md) | Données, consentement, droits, synchronisation prévue |
| [Partie matérielle](docs/materiel.md) | Boîtier Raspberry Pi, réseau, niveaux de protection |
