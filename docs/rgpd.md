# Conformité RGPD

L'application recueille des **voix et des souvenirs de proches**, souvent par des **mineurs**. La confidentialité est donc un choix de conception, pas une option : ce document décrit les mesures prises dans le code. Il ne remplace pas un avis juridique.

## Données traitées

| Donnée | Pourquoi | Où |
|---|---|---|
| Prénom, nom de famille (facultatif) du jeune | Personnaliser l'accueil (« Bonjour Camille », « Famille Morvan ») | Base locale (`profile`) |
| Tranche d'âge (moins de 15 ans ou non), date de l'accord parental | Respecter l'âge du consentement numérique | Base locale |
| Nom et lien des proches | Savoir qui raconte | Base locale (`person`) |
| Enregistrements audio | Le récit lui-même | Dossier audio, fichiers WAV |
| Transcription, version corrigée, mots-clés, carnet | Lire, relier et garder les récits | Base locale |
| Consentement du proche, horodaté, avec le texte exact accepté | Preuve de l'accord, pour chaque enregistrement | Base locale (`consent`) |

Le dossier de données est celui que le système réserve aux applications (`platformdirs`) ; l'écran Réglages, carte « Mes données », l'affiche et permet de l'ouvrir.

## Minimisation

- **Pas de date de naissance** : seulement « 15 ans ou plus » ou « moins de 15 ans ».
- **Nom de famille facultatif**, utilisé seulement pour l'affichage.
- **Pas de compte**, pas d'adresse e-mail, pas d'identifiant en ligne.
- **Aucune mesure d'audience**, aucun suivi d'usage.

## Traitement local

- La transcription (faster-whisper) et l'analyse des mots-clés (spaCy) tournent **sur l'ordinateur**.
- **Seule opération réseau** : le téléchargement du modèle de transcription, une fois, après accord explicite et refusable. Le modèle est ensuite chargé sans accès au réseau (`local_files_only=True`). Voir [transcription.md](transcription.md).
- Le pied de page le rappelle en permanence : « Tout reste sur cet ordinateur. Rien n'est envoyé en ligne. »

## Consentement

- **Le jeune** : en France, le consentement numérique seul est valable à partir de 15 ans. En dessous, l'accord d'un parent est demandé au premier lancement ; la base refuse un profil de moins de 15 ans sans date d'accord parental (contrainte `CHECK`).
- **Le proche interrogé** : avant **chaque** enregistrement, une case confirme qu'il sait être enregistré et qu'il est d'accord (« Mamie Yvonne sait que la conversation est enregistrée et est d'accord… »). L'accord se redonne à chaque fois et pour chaque personne. Le texte exact accepté et l'heure sont conservés avec le récit.
- Un récit ne peut pas exister sans consentement : récit et consentement sont enregistrés dans la même transaction.

## Droits des personnes

| Droit | Mise en œuvre |
|---|---|
| Accès | Toutes les données sont sur l'ordinateur, dans le dossier affiché par les Réglages ; chaque récit se lit et s'écoute dans sa fiche |
| Rectification | Correction du texte de chaque récit, renommage des proches, modification du profil |
| Effacement | Supprimer un récit efface en cascade son consentement, son texte, ses mots-clés, sa note **et son fichier audio** ; supprimer un proche efface tous ses récits et leurs audios |
| Limitation | Un récit peut être **masqué** : il disparaît des listes, des liens, du graphe et du livre, sans être effacé |
| Portabilité | Le livre de famille exporte les récits choisis en PDF |

## Le dépôt de code

- **Aucune vraie voix ni donnée réelle** : le jeu de démonstration est entièrement fictif (`data/demo.json`) et ne contient aucun enregistrement, seulement des textes.
- Les modèles de transcription ne sont jamais versionnés.
- Les tests créent leurs données dans des bases temporaires.

## Synchronisation familiale (prévue)

Le partage entre les ordinateurs de la famille est en préparation (brief, section 7). Les choix déjà faits :

- **Rien ne sort de la maison** : le serveur familial (boîtier Raspberry Pi) n'est jamais joignable depuis Internet ; chaque échange est chiffré (HTTPS, certificat épinglé) et authentifié (appairage par code, jeton révocable par poste).
- **L'effacement reste effectif** : une suppression ne transmet que l'identifiant (UUID) de ce qui a été supprimé, jamais son contenu ; la suppression l'emporte sur une modification faite ailleurs.
- Le profil (âge, accord parental) reste propre à chaque poste et n'est pas synchronisé.
- Analyse des risques et niveaux de protection du boîtier : [materiel.md](materiel.md).

Le pied de page deviendra « Tout reste à la maison. Rien n'est envoyé sur Internet. » quand la synchronisation sera en place.

## Pistes d'amélioration

- Chiffrement des fichiers audio sur l'ordinateur (protège en cas de vol ou de partage de l'ordinateur).
- Chiffrement du disque de données du boîtier et des sauvegardes.
- Export complet des données (base et audios) dans une archive, au-delà du livre PDF.
