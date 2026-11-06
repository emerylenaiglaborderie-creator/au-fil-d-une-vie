# Au fil d'une vie : brief projet

Document de référence : décisions prises et direction artistique (DA). À lire en entier avant d'écrire du code.

Conventions de travail : répondre et documenter en français, ton professionnel et concis, ne jamais utiliser de tiret cadratin dans les textes, commentaires et documents.

Maquette de référence (artefact privé, 6 écrans, accueil en arbre) : https://claude.ai/artifact/EnoUtgkJpUAg7S6kQz9kCv. L'application s'en est écartée sur plusieurs points (section 4) ; ce brief décrit ce qui a été décidé et réalisé.

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
- **Tout reste à la maison.** Pas de compte en ligne, pas de cloud, aucun envoi sur Internet (hors téléchargement initial explicite des modèles, refusable). Les seuls échanges réseau autorisés se font avec le **serveur familial** (boîtier Raspberry Pi) sur le réseau local, voir section 7.
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
| Graphe | **Diagramme en arcs** : récits sur un fil chronologique, liens en arcs portant les mots partagés, palier compact au-delà de 15 récits (titres au survol, 3 liens forts par récit) ; **networkx** pour les composantes connexes |
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
- Arbre d'accueil dans une `QGraphicsScene` ; tâches longues dans des threads de travail dont les signaux Qt ramènent les résultats à l'interface (voir [architecture.md](architecture.md)) ; tests d'interface avec pytest-qt.

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
- Logo « Au fil d'une vie » : texte manuscrit, arbre à fil avec points rouges et feuilles. Fichiers sources : `assets/logo/logo-complet.png`, `assets/logo/arbre-seul.png`.
- Déclinaisons générées par `scripts/generer_images.py` (fond blanc rendu transparent) : arbre de l'accueil, mini arbre de l'en-tête, logo de l'écran de premier lancement, icône de l'application.
- Le logo complet n'apparaît plus dans les colonnes des écrans : l'arbre est devenu l'accueil.

### 4.3 Couleurs

| Rôle | Valeur (Jour) |
|---|---|
| Fond crème (papier) | `#FDFCF8`, avec un grain très fin |
| Fiches et étiquettes | papier `#FFFDF6` |
| Encre (texte, traits) | `#2F2F2F` / `#3B3B3B` |
| Fil | `#444444` |
| Rouge principal (points, boutons, fil des liens) | `#C73A45` |
| Rouge ombre (bas des boutons) | `#8F2530` |
| Rouge texte | `#B0303B` |
| Vert feuille (étiquettes) | `#D5E6AB` / `#CFE3A0` |
| Vert texte | `#2F5A1C` / `#3E6B2A` |
| Lavis vert (ombres pleines décalées) | `#CFE0A0` |
| Encarts verts | fond `#F1F6E4`, pointillés `#6B8F4A` |
| Pointillés des listes | `#8A8A8A` |
| Écorce (racines de l'arbre) | `#A4827C` |
| Mètre ruban (graphe) | `#EFD45A`, graduations `#2B2B2B` |

Une palette Nuit reprend chaque rôle (`ui/theme.py`).

### 4.4 Typographies
- **Sacramento** (manuscrite) : titres d'écran, accroches, noms des proches (racines de l'arbre, « Mamie Yvonne raconte »). Grandes tailles, **en touches**, jamais pour de longs textes.
- **Jost** (sans-serif géométrique) : interface (boutons, métadonnées, mois du mètre ruban).
- **Lora** (serif) : le **contenu des récits** (questions, extraits, transcription), souvent en italique.
- Polices **embarquées** (licence OFL), pas de CDN.

### 4.5 Style herbier et composants
Tous les écrans partagent le langage d'une **planche d'herbier** à l'encre :
- **Papier** : fond crème avec un grain fin (PNG raccordable, posé en lumière douce).
- **En-tête** : séparé du contenu par un trait d'encre ; à droite, le nom de la section avec un point rouge et le **mini arbre cliquable** qui ramène à l'accueil. Sur l'arbre : résumé de la famille et accès aux réglages.
- **Fiches** : fond papier, bord d'encre 1,5 px, coins quasi droits (3 px), **ombre pleine décalée** de lavis vert, aucune ombre floue.
- **Encarts verts** (consentement, conseils) : bord pointillé. **Listes** : séparateurs pointillés. **Pied de page** : ligne pointillée.
- **Boutons** : coins presque droits (4 px) ; le bouton principal reste rouge avec son ombre pleine `0 3px 0 #8F2530`.
- **Étiquettes mots-clés « feuille »** (deux coins arrondis, deux presque droits) : remplies si le mot est partagé, bord gris encre sinon.
- **Rameaux d'encre** décoratifs (tige effilée, feuilles en lavis vert décalé, bourgeon rouge) dans les zones vides, jamais derrière du texte.
- **Séparateur** : fil avec boucle se terminant par un point rouge. **Surlignage « marqueur »** vert sur les mots-clés dans le texte d'un récit.
- Points de progression : **point rouge plein = fait**, **point vide = à faire**.
- **Pied de page constant** : « Tout reste sur cet ordinateur. Rien n'est envoyé en ligne. », qui deviendra « Tout reste à la maison. Rien n'est envoyé sur Internet. » avec la synchronisation (section 7).

### 4.6 Les écrans

Détails et choix techniques : [interface.md](interface.md) et [graphe.md](graphe.md).

**0. Mon arbre (accueil, sans menu)**
- « Bonjour Camille » en Sacramento, sur l'aquarelle de l'arbre du logo.
- **Cinq étiquettes d'herbier** numérotées, pendues au feuillage par un fil noué sur un point rouge, sur deux colonnes et trois rangées : N° 1 Interview (étiquette rouge, prochaine piste), N° 2 Les pistes, N° 3 Mes récits, N° 4 Au fil des mots, N° 5 Livre de famille (en haut, comme un fruit). Elles se balancent au survol et au focus clavier, et apparaissent en fondu.
- **Racines** effilées et sinueuses portant le nom des proches, écrit le long de la racine ; leurs récits y sont des perles rouges. Clic : les récits du proche.

**1. Les pistes** (étiquette N° 2) : prochaine piste et question, proches à interroger (boutons feuille qui passent à la ligne), « Lancer l'interview », pistes à explorer avec leurs points, personnes à interroger.

**2. Interview** : question en grand, choix du proche, **consentement** à cocher avant chaque enregistrement, enregistreur avec l'**onde dessinée comme un fil**, relances « Pour creuser », conseils d'écoute.

**3. Mes récits** : **fil vertical** des récits avec points rouges, recherche, onglets par piste, extraits et étiquettes feuilles.

**4. Fiche récit** : écoute avec progression en fil, version livre et transcription brute, correction, mots-clés, « Voir aussi », « Mon carnet », ajout au livre, masquer, supprimer.

**5. Au fil des mots (graphe)**
- Les récits sont des marques sur un **mètre ruban** (rappel de la toise des tailles d'enfants), dans l'ordre où ils ont été recueillis ; les mois sont imprimés sur le ruban ; bout gauche coupé en biais, bout droit enroulé.
- Les liens sont **cousus** : fil rouge pour le récit choisi, faufilage en pointillés pour les autres ; mots partagés sur de petites étiquettes de papier à œillet.
- **Paliers** : tout est affiché jusqu'à 15 récits, puis fil compact (titre au survol, 3 liens forts par récit), puis fil qui défile avec une vue d'ensemble. **Filtres** par proche, piste ou mot.

**6. Réglages** (depuis l'arbre) : prénom et nom de famille, thème, langue, proches, pistes, données, modèle de transcription.

### 4.7 Ton éditorial de l'interface
- Tutoiement, phrases courtes, chaleureuses, jamais infantilisantes.
- Vocabulaire : quête, piste, récit, fil, « ce que j'en retiens », livre de famille.
- Pas de jargon technique visible (pas de « transcription Whisper », dire « le texte de ce qu'elle a raconté »).
- Rappel de confidentialité visible en permanence (pied de page).

---

## 5. État d'avancement

| Étape | État |
|---|---|
| Dépôt, CI trois systèmes, base SQLite, repositories, tests | fait |
| Transcription locale (faster-whisper) avec file d'attente | fait |
| Mots-clés (spaCy, TF-IDF) et liens pondérés par la rareté | fait |
| Interface : arbre d'accueil, style herbier, tous les écrans, thème Nuit, anglais | fait |
| Graphe en mètre ruban, paliers, défilement, filtres | fait |
| Livre de famille PDF (ReportLab) | fait (sans le style herbier) |
| Préparation de la synchronisation (UUID, journal des modifications) | fait |
| Serveur familial (PostgreSQL, API FastAPI, appairage) | à faire (section 7.6, étape 2) |
| Synchronisation client et serveur | à faire |
| Boîtier Raspberry Pi | à faire (bonus) |

L'interface est figée : les prochaines étapes portent sur le serveur familial et la synchronisation.

## 6. Base de données (décision du 3 novembre 2026)

> Mise à jour du 5 novembre 2026 : SQLite reste la **base locale de chaque poste** (fonctionnement hors connexion). La base de référence de la famille est **PostgreSQL** sur le serveur familial. Voir section 7.

- Module standard `sqlite3`, **sans ORM** : les repositories isolent déjà l'accès, et le SQL écrit à la main est un point évalué.
- Schéma dans `schema.sql`, migrations suivies par `PRAGMA user_version`.
- `PRAGMA foreign_keys = ON` et `ON DELETE CASCADE` : supprimer un récit efface transcription, mots-clés, consentement et note (droit à l'effacement).
- Requêtes paramétrées uniquement.
- Une connexion par thread (la transcription tourne hors du thread d'interface).
- Bonus : FTS5 pour la recherche dans les récits. Le chiffrement éventuel porte sur les audios plutôt que sur la base (SQLCipher complique l'installation multi-OS).

## 7. Serveur familial, boîtier et synchronisation (décision du 5 novembre 2026)

Validé avec le professeur : partage des récits entre les ordinateurs de la famille, **boîtier Raspberry Pi** comme serveur familial, et application **utilisable hors connexion** avec synchronisation au retour sur le réseau.

### 7.1 Architecture d'ensemble
- **Client lourd** (PySide6) sur chaque poste : base **SQLite locale** complète, tout fonctionne sans serveur (enregistrement, transcription, mots-clés, graphe, livre).
- **Serveur familial** : API REST **FastAPI** + **PostgreSQL** + dossier des audios, déployés par `docker compose` (même fichier sur Mac et sur le Pi, images ARM64).
- PostgreSQL n'est jamais exposé sur le réseau : seule l'API l'est.
- Rôles PostgreSQL séparés : `aufil_owner` (schéma, migrations), `aufil_api` (lecture et écriture des données uniquement), `aufil_backup` (lecture seule).
- Arborescence : `src/au_fil_d_une_vie/` (client), `src/au_fil_server/` (serveur), `src/au_fil_shared/` (schémas d'échange communs).
- Règle d'architecture inchangée des deux côtés : interface, puis services, puis repositories.

### 7.2 Sécurité du réseau local
- Découverte du serveur par mDNS (`zeroconf`), saisie manuelle de l'adresse en repli.
- **Appairage** de chaque poste par code à 6 chiffres valable 5 minutes, échangé contre un jeton. Le serveur ne garde que l'empreinte du jeton, le client le range dans le trousseau du système (`keyring`). Révocation possible.
- **HTTPS** avec certificat auto-signé généré au premier lancement, empreinte affichée à l'appairage puis épinglée par le client.

### 7.3 Synchronisation
- Identifiants globaux **UUID** sur toutes les données synchronisées (plus d'identifiant entier partagé entre machines).
- Le serveur numérote chaque modification (séquence croissante). Le client récupère les changements depuis le dernier numéro connu (**pull**), puis envoie ses modifications en attente (**push**), chacune avec la version sur laquelle elle s'appuie.
- Aucune confiance dans l'horloge des postes pour ordonner les modifications.
- Suppressions transmises par **pierres tombales** (identifiant seul, sans contenu), purgées ensuite.
- Règles de conflit par type de donnée :
  - création de récit, consentement, audio : immuables, pas de conflit possible ;
  - texte corrigé (« version livre ») : en cas de conflit, les deux versions sont conservées et l'utilisateur choisit ;
  - mots-clés validés d'un récit : fusion des ensembles ;
  - drapeaux (masqué, dans le livre), notes, pistes et questions : la dernière modification reçue par le serveur l'emporte ;
  - suppression contre modification : **la suppression l'emporte** (droit à l'effacement) ;
  - même proche créé sur deux postes : détection par nom, fusion proposée à l'utilisateur.
- Données dérivées (poids IDF, liens, graphe) **non synchronisées** : recalculées localement à partir des mots-clés synchronisés.
- Audios envoyés à part, reprenables, vérifiés par SHA-256.
- Déclenchement : au lancement, à la détection du serveur, périodiquement et par un bouton « Synchroniser ». Toujours dans un `QThread`.

### 7.4 Boîtier Raspberry Pi
- **Grand boîtier ventilé** qui regroupe tout le matériel réseau de la famille :
  - un Raspberry Pi 4 ou 5 (4 Go), **données sur SSD** (jamais PostgreSQL sur la carte microSD) ;
  - un **module Wi-Fi émetteur** relié au Pi, qui diffuse le réseau du boîtier (`AuFil-Famille`), **verrouillé par une clé d'authentification** WPA3 ;
  - un **switch** dont le Pi est l'entrée, et **7 ports Ethernet** en façade pour brancher des postes ou la box Internet.
- Le Pi fait office de routeur et de pare-feu (`nftables`) pour le Wi-Fi et les ports Ethernet, et sert les adresses (DHCP).
- Pour que brancher la box sur un des ports ne mélange pas les deux réseaux, le switch est **administrable (VLAN)** : un port de façade est réservé et repéré « box », isolé des autres et traité par le Pi comme sa sortie vers Internet.
- Uniquement des blocs d'alimentation certifiés, aucun câblage secteur fait maison.
- Raspberry Pi OS Lite 64 bits, démarrage automatique du serveur par `systemd`, SSH par clé (attention : les ports publiés par Docker contournent les règles du pare-feu de l'hôte, seul le port de l'API est publié).
- Démon `aufil-box` en Python (`gpiozero`, `luma.oled`), testé sans matériel grâce à `MockFactory`. Il appelle l'API par des routes d'administration accessibles uniquement en local.
- Boutons : **Associer** (code d'appairage sur l'écran), **Sauvegarder** (`pg_dump` et audios vers une clé USB, archive chiffrée par phrase de passe), **Éteindre** (appui long, arrêt propre).
- Cinq LED rouges en façade, reprise du motif « points rouges sur un fil » pour l'état du boîtier.

### 7.5 Niveaux de protection
Le boîtier laisse à chaque famille le choix de son niveau de protection, selon ses usages. Un sélecteur à trois positions, **à l'intérieur du boîtier**, fixe le niveau. Le niveau actif s'affiche sur l'écran du boîtier et dans l'application.

| Niveau | Box branchée sur le port « box » | API joignable depuis | Internet pour le Pi | Usage |
|---|---|---|---|---|
| **1. Confort** | Oui | Réseau de la maison, Wi-Fi et ports du boîtier | Mises à jour uniquement | Les postes restent sur leur Wi-Fi habituel et gardent Internet, synchronisation automatique |
| **2. Filtré** | Oui | Wi-Fi et ports du boîtier uniquement | Mises à jour uniquement | On rejoint le réseau du boîtier (Wi-Fi ou câble) le temps de synchroniser |
| **3. Hermétique** | Non | Wi-Fi et ports du boîtier uniquement | Aucun | Isolation totale, interviews chez un proche, mises à jour manuelles |

- Dans tous les niveaux : HTTPS avec certificat épinglé, appairage par jeton, aucune connexion entrante depuis Internet, PostgreSQL jamais exposé.
- Le sélecteur pilote les règles du pare-feu du Pi. Box débranchée : le boîtier passe de fait au niveau 3.
- Niveau 1 : le réseau de la maison et celui du boîtier restent séparés par le Pi, la découverte mDNS ne les traverse pas. Il faut un relais mDNS sur le Pi (`avahi` en mode réflecteur) ou la saisie manuelle de l'adresse.
- L'application fonctionne hors connexion quel que soit le niveau, la synchronisation reprend dès que le serveur est joignable.

### 7.6 Ordre de réalisation
1. Migration des identifiants vers UUID et colonnes de synchronisation dans SQLite (fait : UUID, journal `sync_outbox` tenu par des déclencheurs, `SyncRepository`).
2. Serveur familial (PostgreSQL, API, appairage) sous Docker sur le Mac.
3. Synchronisation client et serveur, avec scénarios de conflits testés.
4. Déploiement sur le Pi et démarrage automatique.
5. Boutons, LED et écran (`aufil-box`).
6. Module Wi-Fi, switch et niveaux de protection.

Les étapes 5 et 6 sont des bonus : le projet doit rester complet et défendable sans elles.
