# Partie matérielle : le boîtier familial

Ce document décrit le boîtier « Au fil d'une vie » : son rôle, les choix retenus et son fonctionnement. Les décisions de référence sont dans le [brief](brief.md), section 7.

## 1. Rôle du boîtier

Le boîtier est le **serveur familial**. Il garde la version de référence des récits de la famille et permet aux ordinateurs de la maison de se les partager.

- Chaque poste garde sa propre base locale et fonctionne **hors connexion**. Le boîtier sert de point de rendez-vous : un poste se synchronise dès qu'il le joint.
- Le boîtier crée **son propre réseau** (Wi-Fi et Ethernet), séparé de celui de la box Internet.
- Il n'est **jamais joignable depuis Internet**, quel que soit son réglage.
- Il se pilote sans clavier ni écran externe : boutons, LED et petit écran en façade.

Le boîtier est un bonus du projet. L'application et le serveur familial fonctionnent aussi sans lui, par exemple avec le serveur lancé sous Docker sur un ordinateur.

## 2. Vue d'ensemble

```
┌──────────────────────────── Boîtier ─────────────────────────────┐
│                                                                  │
│   Module Wi-Fi ──USB──┐                                          │
│   (AuFil-Famille,     │                                          │
│    WPA3)              │                                          │
│                  ┌────┴─────────┐   Ethernet    ┌──────────────┐ │
│   SSD ───USB──── │ Raspberry Pi │ ────────────  │ Switch       │ │
│   (base, audios) │ routeur,     │  (VLAN 10+20) │ administrable│ │
│                  │ pare-feu,    │               │ 8 ports      │ │
│                  │ serveur      │               └──┬───────────┘ │
│                  └────┬─────────┘                  │             │
│                       │ GPIO / I2C                 │             │
│   Écran OLED, 3 boutons, 5 LED rouges,             │             │
│   sélecteur de niveau (intérieur)                  │             │
└────────────────────────────────────────────────────┼─────────────┘
                                                     │
                  Façade : 6 ports « famille » + 1 port « box »
```

## 3. Composants

| Composant | Rôle | Prix indicatif |
|---|---|---|
| Raspberry Pi 5 (4 Go), ou Pi 4 (4 Go) | Serveur, routeur et pare-feu | 60 à 65 € |
| Alimentation officielle | Alimentation stable sous charge | 12 € |
| SSD USB (ou NVMe sur Pi 5) | Base PostgreSQL et fichiers audio | 25 à 35 € |
| Module Wi-Fi USB compatible « point d'accès » sous Linux | Diffuse le réseau `AuFil-Famille` | 20 à 30 € |
| Switch administrable 8 ports (VLAN) | 7 ports en façade + liaison au Pi | 25 à 35 € |
| Grand boîtier + ventilateur | Intégration et refroidissement | 25 à 45 € |
| Écran OLED 0,96" I2C (SSD1306) | Code d'appairage, état, niveau | 6 à 10 € |
| 3 boutons, 5 LED rouges, sélecteur 3 positions, résistances, fils | Façade | 10 à 15 € |
| **Total** | | **environ 185 à 250 €** |

Prix relevés à titre indicatif en novembre 2026, à vérifier au moment de l'achat.

## 4. Choix retenus et justifications

| Choix | Raison |
|---|---|
| **Raspberry Pi** | Peu cher, faible consommation, Linux complet, broches GPIO pour la façade. Fait tourner PostgreSQL et l'API dans les mêmes conteneurs Docker que sur le Mac (images ARM64). |
| **Données sur SSD** | PostgreSQL écrit en permanence et use une carte microSD en quelques mois. Le système reste sur la carte, les données vont sur le SSD. |
| **Module Wi-Fi dédié** | Le Wi-Fi intégré du Pi fait un point d'accès faible (portée, nombre d'appareils). Le module dédié diffuse le réseau du boîtier, le Wi-Fi intégré reste désactivé. |
| **Clé d'authentification WPA3** | Seuls les appareils qui connaissent la clé rejoignent le réseau du boîtier. |
| **Switch administrable (VLAN)** | Sans VLAN, brancher la box Internet sur un des ports mélangerait les deux réseaux : deux serveurs DHCP en conflit et plus aucun filtrage possible. Le VLAN isole le port « box » des ports « famille ». |
| **Le Pi fait routeur et pare-feu** | Un seul appareil à configurer, des règles écrites et versionnées dans le dépôt, un seul point de contrôle pour les niveaux de protection. |
| **Façade en Python** (`gpiozero`, `luma.oled`) | Même langage que le reste du projet, et testable sans matériel. |
| **5 LED rouges** | Reprise du motif du logo, « des points rouges sur un fil », pour l'état du boîtier. |
| **Blocs d'alimentation certifiés uniquement** | Aucun câblage secteur fait maison à l'intérieur du boîtier. |

## 5. Fonctionnement réseau

### 5.1 Découpage

| Réseau | Ports | Adressage (exemple) | Rôle |
|---|---|---|---|
| **Famille** (VLAN 10) | 6 ports de façade + Wi-Fi `AuFil-Famille` | `10.42.0.0/24`, Pi en `10.42.0.1` | Postes de la famille |
| **Box** (VLAN 20) | 1 port de façade repéré « box » | Adresse donnée par la box | Sortie vers la maison et Internet, optionnelle |

Le Pi reçoit les deux VLAN sur son unique port Ethernet (liaison « trunk » vers le switch). Côté système :

- `eth0.10` et le module Wi-Fi sont réunis dans un pont `br-famille` : un poste en Wi-Fi et un poste en câble sont sur le même réseau ;
- `eth0.20` est l'interface de sortie vers la box.

### 5.2 Logiciels réseau du Pi

| Logiciel | Rôle |
|---|---|
| `hostapd` | Point d'accès Wi-Fi WPA3 |
| `dnsmasq` | Adresses (DHCP) et noms locaux sur le réseau famille |
| `nftables` | Pare-feu et routage, règles différentes selon le niveau |
| `avahi` | Annonce mDNS du serveur (`_aufil._tcp.local.`), en réflecteur au niveau 1 |

Les postes trouvent le serveur par mDNS. En repli, l'adresse se saisit à la main dans l'application.

## 6. Niveaux de protection

La famille choisit son niveau selon ses usages, avec un **sélecteur à trois positions placé à l'intérieur du boîtier**. Le niveau actif s'affiche sur l'écran et dans l'application.

| Niveau | Box branchée | API joignable depuis | Internet pour le Pi | Usage |
|---|---|---|---|---|
| **1. Confort** | Oui | Réseau de la maison et réseau famille | Mises à jour uniquement | Les postes restent sur leur Wi-Fi habituel et gardent Internet, synchronisation automatique |
| **2. Filtré** | Oui | Réseau famille uniquement | Mises à jour uniquement | On rejoint le réseau du boîtier (Wi-Fi ou câble) le temps de synchroniser |
| **3. Hermétique** | Non | Réseau famille uniquement | Aucun | Isolation totale, interviews chez un proche, mises à jour manuelles |

Règles de pare-feu par niveau, en résumé :

- **Toujours** : rien n'entre depuis Internet. Seul le port HTTPS de l'API est ouvert, PostgreSQL n'est jamais exposé. Les postes du réseau famille n'ont pas d'accès à Internet par le boîtier.
- **Niveaux 1 et 2** : le Pi peut sortir vers Internet pour ses mises à jour (dépôts du système et des images Docker), rien d'autre.
- **Niveau 1 seulement** : le réseau de la maison peut joindre le port de l'API, et uniquement lui.
- **Niveau 3** : l'interface « box » est coupée. Débrancher la box fait de fait passer le boîtier au niveau 3.

Le démon `aufil-box` lit la position du sélecteur au démarrage et à chaque changement, puis charge le jeu de règles `nftables` correspondant.

## 7. Façade

### 7.1 Boutons

| Bouton | Action | Retour |
|---|---|---|
| **Associer** | Génère un code d'appairage à 6 chiffres valable 5 minutes, avec l'empreinte du certificat HTTPS | Code et empreinte sur l'écran, LED qui clignote |
| **Sauvegarder** | Copie chiffrée de la base (`pg_dump`) et des audios sur la clé USB branchée | LED qui s'allument une à une pendant la copie |
| **Éteindre** (appui long, 3 s) | Arrêt propre : API, puis PostgreSQL, puis système | LED qui s'éteignent une à une |

### 7.2 LED et écran

| État | LED | Écran |
|---|---|---|
| Démarrage | Les LED s'allument une à une | « Démarrage... » |
| Prêt | LED 1 fixe | Niveau actif, nombre de postes appairés |
| Appairage en cours | LED 2 clignote | Code et empreinte, compte à rebours |
| Synchronisation d'un poste | LED 3 clignote | Nom du poste |
| Sauvegarde | Progression sur les 5 LED | Pourcentage |
| Erreur (SSD absent, serveur arrêté) | LED 5 clignote rapidement | Message court |

## 8. Démarrage et arrêt

Tout se lance automatiquement par `systemd`, sans intervention :

1. réseau : `nftables` (niveau lu sur le sélecteur), `hostapd`, `dnsmasq`, `avahi` ;
2. montage du SSD de données ;
3. serveur : `docker compose up` (PostgreSQL et API) ;
4. façade : démon `aufil-box`.

Le boîtier est prêt environ une minute après le branchement. L'arrêt passe toujours par le bouton Éteindre, pour que PostgreSQL termine ses écritures avant la coupure.

## 9. Sécurité

Le réseau du boîtier n'est pas considéré comme sûr : la sécurité repose sur le chiffrement et l'authentification, le réseau ne fait que réduire l'exposition.

| Protection | Mise en œuvre |
|---|---|
| Accès au réseau du boîtier | Clé WPA3 pour le Wi-Fi, ports Ethernet séparés de la box par VLAN |
| Accès à l'API | Appairage par code, déclenché uniquement par un appui physique sur Associer, puis jeton par poste, révocable |
| Écoute du réseau | HTTPS, certificat auto-signé épinglé par chaque poste à l'appairage |
| Base de données | PostgreSQL jamais exposé, rôles séparés (`aufil_api` n'a que les droits utiles) |
| Accès administrateur au Pi | SSH par clé uniquement |
| Sauvegardes | Archives chiffrées par phrase de passe |

Point de vigilance : Docker ouvre lui-même les ports qu'il publie, en contournant les règles du pare-feu de l'hôte. Seul le port de l'API est publié, et l'ouverture des ports se vérifie par un scan (`nmap`) depuis un autre poste.

Risques connus et acceptés :

- **Poste compromis** : un logiciel malveillant sur un poste lit sa base locale et peut utiliser son jeton. Réponse : révocation du poste.
- **Vol du boîtier** : le SSD n'est pas chiffré. Un chiffrement (LUKS) empêcherait le démarrage autonome, il reste une évolution possible.

## 10. Tests et vérifications

- **Sans matériel** : `gpiozero` fournit une `MockFactory` qui simule les broches. Les scénarios de la façade (appui long sur Éteindre, appairage, changement de niveau) sont testés avec pytest sur n'importe quel poste et dans la CI.
- **Règles réseau** : les jeux de règles `nftables` sont versionnés dans le dépôt et vérifiés par `nft -c` (contrôle de syntaxe sans les appliquer).
- **Sur le boîtier** : scan `nmap` depuis le réseau famille et depuis le réseau de la maison pour chaque niveau, requêtes sans jeton refusées (`401`), coupure de courant simulée après un arrêt par le bouton.

## 11. Points ouverts

- **Port « box »** : switch administrable avec VLAN (choix actuel) ou switch simple et adaptateur USB-Ethernet dédié sur le Pi.
- **Verrou physique** sur le boîtier : il protégerait le SSD et le sélecteur de niveau, à confirmer.

## 12. Ordre de réalisation

1. Déploiement du serveur familial sur le Pi et démarrage automatique.
2. Façade : boutons, LED et écran (`aufil-box`).
3. Module Wi-Fi, switch et niveaux de protection.

Ces étapes viennent après le serveur familial et la synchronisation : le projet reste complet et défendable sans elles.
