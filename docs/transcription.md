# Transcription locale

## Principe

1. À la fin d'une interview, le récit est mis dans une **file d'attente** (`TranscriptionQueue`).
2. Un **thread à part** le transcrit avec faster-whisper, sur le processeur, sans bloquer l'interface. Il a sa propre connexion SQLite (mode WAL, pour lire et écrire en parallèle).
3. Le texte brut est enregistré, le récit passe au statut `transcribed`, puis les **mots-clés sont proposés** (spaCy, TF-IDF) pour validation.
4. L'avancement s'affiche en bas de la fenêtre. Un récit interrompu (application fermée) est repris au lancement suivant.

## Modèle

| Modèle | Taille | Usage |
|---|---|---|
| `small` | environ 465 Mo | par défaut |
| `base` | environ 145 Mo | machine modeste : `uv run au-fil-d-une-vie --modele base` |

- Téléchargé **une seule fois**, après accord explicite de l'utilisateur (fenêtre de premier lancement, refusable). C'est la **seule opération réseau** de l'application.
- Chargé ensuite avec `local_files_only=True` : la transcription ne peut pas utiliser le réseau.
- Rangé dans le dossier de données (`models/whisper-<taille>`), jamais dans le dépôt.

Le modèle spaCy `fr_core_news_md` est, lui, une dépendance Python installée par `uv sync`.

## Choix et mesures

- **Décodage audio maison** (`read_wav`) : les fichiers de l'application sont toujours en WAV 16 kHz mono 16 bits, lus directement avec `wave` et numpy. Cela évite PyAV, dont la version 19 n'est plus compatible avec faster-whisper 1.2.1.
- **Noms propres** : les noms des proches sont passés à Whisper (`hotwords`). Sur un essai (« Mademoiselle Le Gall »), cela corrige « Legalle » en « Le Gall ». Un `initial_prompt` contenant la question dégradait au contraire le résultat.
- **Mesure** (Mac Apple Silicon, modèle `small`, int8) : environ 3 s de calcul pour 9 s d'audio, soit un tiers du temps réel, plus 2 à 3 s de chargement du modèle au premier récit.

## Limites connues

- Les noms absents de l'application restent mal orthographiés : l'écran de correction fait partie du produit.
- La lemmatisation de spaCy dépend du contexte (« institutrice » peut devenir « instituteur ») : d'où la validation des mots-clés par l'utilisateur.
- Pas d'accélération GPU sur Mac (CTranslate2 tourne sur le processeur).
