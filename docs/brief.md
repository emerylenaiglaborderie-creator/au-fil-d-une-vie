# Au fil d'une vie : brief projet

Document de référence : décisions prises et direction artistique (DA). À lire en entier avant d'écrire du code.

Conventions de travail : répondre et documenter en français, ton professionnel et concis, ne jamais utiliser de tiret cadratin dans les textes, commentaires et documents.

Maquette de référence (artefact privé, 5 écrans) : https://claude.ai/artifact/EnoUtgkJpUAg7S6kQz9kCv

---

## 1. Contexte

- Projet de **BTS SIO option SLAM**, réalisé **seul** par Emery.
- Livrable : un **client lourd**, c'est-à-dire une application installée sur le poste, dont la majorité des traitements s'exécutent en local.
- Le jury accède au travail **via un dépôt GitHub** (pas d'installeur obligatoire, qualité du code et de la documentation prioritaires).
- Développement sur **Mac**. L'application doit fonctionner sur **macOS, Windows et Linux**.
- Aucun langage ni base de données imposés par l'établissement. **Python de préférence.**

## 2. Concept produit

**Nom : « Au fil d'une vie ».**

Application destinée aux personnes de **12 à 25 ans** (enfants accompagnés de leurs parents, adolescents, jeunes adultes) pour partir **en quête de leur histoire familiale** en interviewant leurs proches.

Principe :
1. L'utilisateur choisit une **piste** (thème : enfance, rencontres, cuisine, métier, musique, fêtes...) et une **question**.
2. Il pose la question à un proche et **enregistre la réponse en vocal**.
3. L'enregistrement est **transcrit localement** (hors ligne).
4. Des **mots-clés** sont extraits et validés par l'utilisateur.
5. Les récits qui partagent des mots-clés sont **liés entre eux** : on obtient un **graphe**, pas seulement un arbre.
6. Bonus : export d'un **livre de famille** en PDF.

Principe de progression : **des points rouges sur un fil** (pistes explorées, liens trouvés). **Aucune mécanique de score, de série (streak) ou de gamification agressive.**

## 3. Décisions prises

### 3.1 Produit et RGPD
- **Tout reste local.** Pas de compte, pas de cloud, aucun envoi réseau (hors téléchargement initial explicite des modèles, refusable).
- Public mineur et voix de proches : la confidentialité est un argument central du projet.
- **Consentement** : en France, le consentement numérique seul est valable dès 15 ans, en dessous un parent doit consentir. Le **proche interrogé** consent avant chaque enregistrement (case à cocher dans l'écran d'interview, trace conservée par enregistrement).
- Possibilité de **masquer ou supprimer** un récit à tout moment.
- Bonus sécurité envisagé : chiffrement de la base et des audios.
- Aucune vraie voix ni donnée réelle dans le dépôt GitHub : **jeu de données de démo fictif** uniquement.

### 3.2 Langage et architecture
- **Langage : Python.**
- Architecture en **3 couches** : `ui/` (vues et contrôleurs), `services/` (métier), `repositories/` (accès SQLite).
- Services : `RecordingService`, `TranscriptionService`, `KeywordService`, `LinkService`, `ExportService`.
- Interface `Transcriber` (Protocol) avec adaptateur `FasterWhisperTranscriber`, pour pouvoir changer de moteur sans toucher au reste.
- Les vues ne parlent **jamais** directement à la base : uniquement aux services.
- Tâches longues (transcription, export) hors du thread d'interface, avec progression et sans jamais bloquer l'écran.

### 3.3 Stack technique retenue

| Couche | Choix |
|---|---|
| Base de données | **SQLite** via le module `sqlite3` (SQL écrit à la main, pas d'ORM) |
| Dossiers de données | **platformdirs** (chemins par système, jamais en dur), `pathlib` |
| Enregistrement audio | **QtMultimedia** (`QAudioSource`) + module `wave`, sortie WAV 16 kHz mono (sinon sounddevice en repli) |
| Transcription | **faster-whisper** (CTranslate2, CPU), modèle « small » par défaut, « base » en repli sur machine modeste |
| Mots-clés | **spaCy** `fr_core_news_md` (lemmatisation, mots vides, entités PER et LOC) + **TF-IDF**, avec **validation par l'utilisateur** |
| Liens entre récits | Mots-clés partagés **pondérés par leur rareté** (IDF) ou Jaccard, calculés en SQL / Python |
| Graphe | **networkx** (`spring_layout`, composantes connexes, détection des récits isolés) |
| Livre de famille | **ReportLab** (pur Python), index des mots-clés avec numéros de page via `SimpleIndex`, renvois « voir aussi » |
| Tests | **pytest** (+ pytest-qt si Qt), lancés sur les 3 systèmes par la CI |
| Qualité | ruff, mypy |
| CI | **GitHub Actions**, matrice macos / windows / ubuntu |
| Dépendances | `pyproject.toml` + `uv.lock` |

Modèles Whisper et spaCy : **téléchargés au premier lancement** (écran de progression), jamais dans le dépôt.

### 3.4 Interface : PySide6 (décision du 3 novembre 2026)

**Choix retenu : PySide6 (Qt 6).** Vrai toolkit de bureau, interface entièrement en Python.

- Styles généraux (couleurs, rayons, polices, boutons) en **QSS**.
- Le fil, les points rouges, les étiquettes feuilles et l'onde se dessinent avec `QPainter` / `QPainterPath`.
- Les filtres SVG de la maquette (aquarelle) sont remplacés par des PNG pré-rendus.
- Polices embarquées avec `QFontDatabase.addApplicationFont`.
- Graphe dans `QGraphicsScene`, tâches longues dans `QThread`, tests d'interface avec pytest-qt.

Raisons : client lourd défendable devant le jury, un seul langage, audio natif via QtMultimedia, pas de dépendance à un moteur web par système. pywebview est écarté.

Prévoir une petite bibliothèque de composants maison : `ThreadDivider` (fil), `LeafTag` (étiquette feuille), `RedDot` (point rouge), `StoryCard`, `PrimaryButton`.

### 3.5 Livraison et multi-plateforme
- Livraison principale : **dépôt GitHub** installable par commande (`uv tool install` / `uv sync` puis lancement). Pas d'installeur obligatoire.
- Bonus possibles plus tard : `.dmg` macOS, AppImage Linux, installeur Inno Setup Windows, via CI (PyInstaller ne compile pas en croisé, un build par système).
- Points de vigilance multi-OS : autorisation micro sur macOS (`Info.plist`), polices et échelle d'affichage Windows, serveur audio Linux, avertissements de signature (documentés dans le dossier, pas de certificats achetés).

### 3.6 Contenu attendu du dépôt
- `README.md` : présentation, captures, prérequis, installation en quelques commandes par système, lancement.
- `docs/` : schéma d'architecture, modèle de données, choix techniques justifiés, section conformité RGPD.
- Script de premier lancement (téléchargement des modèles).
- Jeu de démo fictif (quelques récits, un audio d'exemple) pour voir le graphe rempli sans rien enregistrer.
- Tests + badge CI. Historique Git propre (commits lisibles, branches).
- Une courte vidéo ou un GIF de démonstration dans le README.

### 3.7 Modèle de données (esquisse)
- `Family` / `User` : le jeune qui mène la quête.
- `Person` : proche interrogé (nom, lien familial).
- `Theme` et `Question` : pistes et questions associées.
- `Story` : un enregistrement (personne, question, date, durée, chemin audio, statut masqué).
- `Transcript` : texte **brut** et texte **« version livre »** corrigé, par récit.
- `Keyword` et `StoryKeyword` : mots-clés validés et leur lien avec les récits (poids).
- `Consent` : consentement du proche, lié à chaque enregistrement.
- `Note` : « Mon carnet », ce que l'utilisateur retient d'un récit.

### 3.8 Risques et points délicats connus
- **Performance de Whisper** : plusieurs minutes de calcul pour quelques minutes d'audio selon le processeur, d'où file d'attente + progression + modèle « base » de secours. Pas d'accélération GPU sur Mac.
- **Noms propres et accents** mal transcrits : l'écran de correction fait **partie du produit**, pas un bonus.
- **NLP français** : validation humaine des mots-clés obligatoire.
- **Poids de l'application** : 300 à 500 Mo avant modèles, d'où les téléchargements au premier lancement.
- **Hors ligne vérifiable** : aucune requête réseau hors téléchargement initial.

---

## 4. Direction artistique

### 4.1 Intention
Chaleureuse et nostalgique, **terre et crème**, avec une **écriture manuscrite en touches**. Inspirée d'un album ou d'un carnet de famille, pas d'une interface SaaS générique (le premier jet était jugé « trop type IA », à éviter à tout prix : pas de cartes génériques alignées, pas de dégradés violets, pas de coins arrondis uniformes sans intention).

Adaptée au public **12 à 25 ans** : ton direct et chaleureux, tutoiement, vocabulaire de « quête » et de « pistes », progression par points rouges sur un fil, pas de score ni de série.

Motif central, issu du **logo** (fil noir fin, points rouges, arbre, feuilles vertes) : **un fil continu qui relie des points rouges**. Il sert de séparateur, de barre de progression, d'onde sonore, de liste « voir aussi » et de lien dans le graphe.

### 4.2 Logo
- Logo « Au fil d'une vie » : texte manuscrit, arbre à fil avec points rouges et feuilles.
- Fichier source : `assets/logo/logo-complet.png`.
- Deux déclinaisons utilisées dans la maquette : **logo complet** (barre latérale de l'écran Récits) et **arbre seul** (en-tête de toutes les pages, aside de l'écran Quête, fond du Graphe à opacité 0,5 en `multiply`). L'arbre seul reste à extraire.

### 4.3 Couleurs

| Rôle | Valeur |
|---|---|
| Fond crème | `#FDFCF8` |
| Encre (texte) | `#2F2F2F` / `#3B3B3B` |
| Fil | `#444444` |
| Rouge principal (points, boutons) | `#C73A45` |
| Rouge ombre (bas des boutons) | `#8F2530` |
| Rouge texte | `#B0303B` |
| Vert feuille (étiquettes) | `#D5E6AB` / `#CFE3A0` |
| Vert texte | `#2F5A1C` / `#3E6B2A` |
| Vert carte douce | `#F1F6E4` / `#DCE7C3` |
| Bordures | `#E3E6D8` |
| Texte secondaire | `#5B5B5B` / `#555555` |
| Cartes | blanc `#FFFFFF` |

### 4.4 Typographies
- **Sacramento** (manuscrite) : titres d'écran, accroches, noms de personnes en signature (« Mamie Yvonne raconte », « Bonjour Camille », « Au fil des mots »). Grandes tailles (jusqu'à 96 px pour le titre du graphe). À utiliser **en touches**, jamais pour de longs textes.
- **Jost** (sans-serif géométrique) : interface (navigation, boutons, métadonnées, étiquettes).
- **Lora** (serif) : le **contenu des récits** (questions, extraits, transcription), souvent en italique pour les citations. La question de l'interview est en Lora 52 px.
- Polices à **embarquer** dans l'application (pas de CDN, tout reste local).

### 4.5 Composants et motifs
- **Boutons principaux** : rouge `#C73A45`, rayon 12, ombre pleine `0 3px 0 #8F2530` (effet relief, s'enfonce au clic).
- **Étiquettes mots-clés « feuille »** : `border-radius: 14px 2px 14px 2px` (deux coins arrondis, deux presque droits), fond vert `#D5E6AB`, texte vert foncé. **Rempli** quand le mot est partagé avec d'autres récits, **contour** sinon.
- **Cartes blanches** : rayon 18 à 20, ombre douce, bordure `#E3E6D8`.
- **Navigation** : en-tête blanc, liens Ma quête / Interview / Récits / Graphe, le lien actif porte un **petit point rouge**, bouton « Livre de famille » à droite, arbre du logo à gauche.
- **Boutons à bascule « feuille »** pour choisir la personne à interroger.
- **Séparateur** : fil avec boucle se terminant par un point rouge.
- **Surlignage vert « marqueur »** sur les mots-clés dans le texte d'un récit.
- **Lavis aquarelle** : fond décoratif sur plusieurs pages, créé dans la maquette avec un filtre SVG (`feTurbulence` + `feDisplacementMap`). **En Qt, le remplacer par un PNG pré-rendu.**
- **Pied de page constant** : « Tout reste sur cet ordinateur. Rien n'est envoyé en ligne. »
- Points de progression : **point rouge plein = fait**, **point vide (contour) = à faire**.
- Récit isolé (sans lien) dans le graphe : point **blanc à contour rouge** avec la mention « pas encore de lien ».

### 4.6 Les cinq écrans (maquette, 1360 px de large)

**1. Ma quête (accueil)**
- Hero Sacramento « Bonjour Camille ».
- Carte « Prochaine piste » : thème (ex. Musique), question « Quelle chanson te rappelle ta jeunesse ? », « À poser à » avec boutons bascule feuille (Mamie Yvonne, Papa, Tonton Alain, Tata Nadine), bouton rouge « Lancer l'interview », lien « Une autre piste ».
- Grille « Les pistes à explorer » : 6 tuiles (Enfance 3/6, Rencontres 1/4, Cuisine 1/5, Métier 1/4, Musique, Fêtes à démarrer) avec points rouges pleins et vides.
- Aside : arbre du logo, « ton arbre pousse », « 6 récits recueillis auprès de 3 personnes », liste des personnes avec points (Mamie Yvonne 3, Papa 2, Tonton Alain 1, Tata Nadine « Pas encore interrogée »).

**2. Interview (enregistrement)**
- Eyebrow « Enfance · Piste en cours », accroche Sacramento « Pose-lui la question... », question en Lora 52 px.
- Sélecteur « Tu interroges » et **bloc de consentement** : case « Mamie Yvonne sait qu'elle est enregistrée et est d'accord... ».
- Carte enregistreur : état « En cours », chrono (02:14), **forme d'onde dessinée comme un fil** avec un point rouge au bout, ligne pointillée au repos. Boutons Pause / Terminer / Recommencer.
- Aside : « Pour creuser » (3 relances), « Conseils d'écoute », « D'autres pistes » (4 questions).

**3. Récits (bibliothèque)**
- Titre « Mes récits », bouton « Nouvelle interview », logo complet dans l'aside.
- **Fil vertical** (SVG, courbes et boucles) avec points rouges, six entrées à hauteur fixe de 156 px, de la plus récente à la plus ancienne : école / Yvonne (12 oct.), Papi / Yvonne (9 oct.), jour d'école / Papa (5 oct.), plat / Papa (30 sept.), travail / Alain (27 sept.), étés / Yvonne (20 sept.).
- Chaque entrée : thème, métadonnées (« N liens »), extrait en Lora italique, étiquettes feuilles (partagées = remplies).

**4. Fiche récit**
- Lien retour « Récits », eyebrow « Enfance · 12 oct. 2026 · 4 min 12 », Sacramento « Mamie Yvonne raconte », titre = la question.
- Lecteur audio : bouton lecture rouge, **progression en fil** (38 %).
- Onglets « Version livre » / « Transcription brute », action « Corriger le texte ».
- Texte avec surlignages verts (école, bourg, sabots, institutrice, craie), séparateur fil à boucle.
- Aside : « Mots-clés » (étiquettes feuilles), « Voir aussi » (liste verticale en fil avec points rouges), « Mon carnet » (zone de texte « Ce que j'en retiens »), bouton « Ajouter au livre de famille ».

**5. Graphe des liens**
- Titre Sacramento « Au fil des mots » (96 px), case « Afficher les mots communs ».
- Plateau 780 x 580 avec l'arbre du logo en fond (opacité 0,5, multiply).
- **Fils courbes** entre récits, récit sélectionné avec fils plus épais, **points rouges** pour les récits, **étiquettes feuilles** pour les mots communs (bourg, sabots, ferme, école, institutrice, craie), plaques de libellés.
- Panneau « récit sélectionné » avec la liste des récits liés, légende.

### 4.7 Ton éditorial de l'interface
- Tutoiement, phrases courtes, chaleureuses, jamais infantilisantes.
- Vocabulaire : quête, piste, récit, fil, « ce que j'en retiens », livre de famille.
- Pas de jargon technique visible (pas de « transcription Whisper », dire « le texte de ce qu'elle a raconté »).
- Rappel de confidentialité visible en permanence (pied de page).

---

## 5. Ordre de travail suggéré
1. Initialiser le dépôt : `pyproject.toml`, `uv`, structure `ui/ services/ repositories/ tests/ docs/`, CI GitHub Actions (3 OS).
2. Modèle de données SQLite + repositories + tests.
3. `Transcriber` + faster-whisper, avec file d'attente et progression.
4. `KeywordService` (spaCy, TF-IDF) puis `LinkService` (poids par rareté) + tests sur le jeu de démo.
5. Graphe (networkx) et enregistrement audio.
6. Construire l'interface écran par écran en suivant la DA ci-dessus.
7. Export « livre de famille » (ReportLab).
8. Documentation (`docs/`, README, captures, démo), jeu de données fictif, polish.

## 6. Base de données (décision du 3 novembre 2026)

- Module standard `sqlite3`, **sans ORM** : les repositories isolent déjà l'accès, et le SQL écrit à la main est un point évalué.
- Schéma dans `schema.sql`, migrations suivies par `PRAGMA user_version`.
- `PRAGMA foreign_keys = ON` et `ON DELETE CASCADE` : supprimer un récit efface transcription, mots-clés, consentement et note (droit à l'effacement).
- Requêtes paramétrées uniquement.
- Une connexion par thread (la transcription tourne hors du thread d'interface).
- Bonus : FTS5 pour la recherche dans les récits. Le chiffrement éventuel porte sur les audios plutôt que sur la base (SQLCipher complique l'installation multi-OS).
