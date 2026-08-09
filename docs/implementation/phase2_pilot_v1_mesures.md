# Phase 2 / Pilote-V1 — mesures, qualité et calibration

Statut : plan d'implémentation post-MVP, sans effet de certification.

Base documentaire : D04, D09, D12, D17, D19 et D20.

Base logicielle de départ : `main` à `6c0ed6aa1632eef0cb207f5ec3bcce9c382a140e`.

## 1. But

Faire passer PETROLE d'un moteur d'étude vérifié sur cas de référence à un produit capable d'ingérer des mesures terrain, d'en qualifier la qualité, de les comparer à une simulation et de conduire une calibration contrôlée sans mélanger calibration et validation.

Cette phase reste analytique et hors contrôle-commande. Aucun accès SCADA write, aucune fonction SIS/ESD et aucune prétention de certification industrielle ne sont introduits.

## 2. Ordre de réalisation

1. **V1-A1 — contrat qualité des mesures**
   - synthèse d'un dataset `measurements` normalisé vers le SI ;
   - distribution des codes qualité et des sources ;
   - détection des horodatages invalides/hors ordre ;
   - détection des doublons source + timestamp ;
   - exclusion par défaut des mesures `bad` ;
   - min/max/moyenne/écart-type en SI ;
   - aucune correction automatique des données.

2. **V1-A2 — persistance temporelle D12**
   - `tags` ;
   - `samples_raw` immuables ;
   - `samples_normalized` dérivés et versionnés ;
   - liaison dataset → job d'import temporel ;
   - index `(tag_id, timestamp)` et stratégie de partitionnement PostgreSQL ;
   - migration Alembic testée sans dérive du schéma.

3. **V1-A3 — séries et qualité FR-DAT-004**
   - série temporelle par tag ;
   - filtrage qualité ;
   - trous, doublons, ordre, statistiques ;
   - détection d'aberrants explicitement paramétrée et traçable ;
   - aucun point n'est supprimé silencieusement.

4. **V1-B — comparaison mesure-modèle FR-DAT-005**
   - correspondance tag ↔ grandeur calculée ↔ actif/emplacement ;
   - alignement temporel et unité SI ;
   - résidus signés ;
   - biais, MAE, RMSE et nombre de points comparés ;
   - séparation claire entre donnée mesurée et sortie simulée.

5. **V1-C — calibration contrôlée**
   - dataset de calibration immuable ;
   - paramètres autorisés et bornes documentées ;
   - objectif et solveur identifiés ;
   - dataset/régime de validation tenu hors ajustement ;
   - comparaison avant/après calibration ;
   - aucune modification silencieuse de paramètres pour forcer un accord.

6. **V1-D — résultats ingénieur D19**
   - annotations stations sur profil ;
   - enveloppes MAOP/pression minimale et seuil vapeur ;
   - zones gravitaires quand le modèle correspondant est explicitement actif ;
   - marges et export image autonome ;
   - cas `COURSEWORK-460KM-01` comme régression visuelle, jamais comme validation terrain.

7. **V1-E — rapports**
   - RPT-07 Qualité des données ;
   - RPT-08 Calibration mesure-modèle ;
   - hypothèses, exclusions, incertitudes et provenance obligatoires.

## 3. Première tranche en cours — V1-A1

Contrat API :

`GET /api/v1/datasets/{dataset_id}/quality-summary`

Le dataset doit être de type `measurements` et avoir un mapping incluant `dimensions.value`.

La réponse contient :

- dimension et unité SI ;
- nombre total et nombre exploitable ;
- nombre exclu ;
- répartition par qualité et source ;
- début/fin de la période exploitable ;
- min/max/moyenne/écart-type ;
- doublons et horodatages hors ordre ;
- problèmes structurés, dont DQ-007 et DQ-008.

Une mesure `quality=bad` reste conservée et visible, mais elle n'entre pas dans les statistiques descriptives par défaut.

## 4. Critères d'acceptation V1-A1

- un dataset non `measurements` est refusé explicitement ;
- aucune donnée brute ou normalisée n'est modifiée par l'analyse ;
- les statistiques sont calculées en un passage et en unité SI ;
- DQ-007 signale les horodatages invalides/hors ordre ;
- DQ-008 signale et exclut les mesures `bad` ;
- un doublon de timestamp est qualifié par source ;
- tests API sur unités variables, ordre, doublon et qualité ;
- CI backend, typage, migrations, frontend existant et preuve scientifique restent verts.

## 5. Porte avant V1-B

La comparaison mesure-modèle ne démarre pas avant que la persistance temporelle D12 soit définie et que la correspondance tag ↔ actif/grandeur soit explicite. Le champ `source` d'un CSV ne doit pas être assimilé silencieusement à un capteur industriel approuvé.

## 5.1 État V1-A2 — implémentation en cours

Le premier flux temporel reste volontairement **fichier hors ligne → dataset
normalisé → tag explicite**. Il crée les tables `tags`, `samples_raw`,
`samples_normalized` et `time_series_imports` :

- un tag appartient à une organisation et à un site ; son rattachement à un
  équipement est facultatif mais vérifié contre le même site ;
- les échantillons bruts conservent horodatage source, heure d'ingestion,
  valeur/unité d'origine, qualité, séquence, dataset et ligne source ;
- les échantillons normalisés conservent la valeur SI, l'unité SI et une version
  de traitement, sans écraser le brut ;
- l'import est idempotent par `dataset + tag + Idempotency-Key` ; les doublons
  `source + timestamp` restent stockables et seront qualifiés par V1-A3 ;
- la source de chaque ligne doit correspondre explicitement au `external_name`
  du tag : un dataset multi-capteurs devra être réparti sur ses tags, jamais
  fusionné silencieusement.

Les endpoints sont `POST/GET /measurement-tags`,
`POST /datasets/{dataset_id}/time-series-imports` et
`GET /measurement-tags/{tag_id}/samples`. Ils ne constituent pas un connecteur
SCADA et n'acceptent pas encore d'écriture temps réel.

## 6. Porte avant calibration

La calibration ne démarre pas avant :

- gel du dataset brut ;
- description de la métrologie et des codes qualité disponibles ;
- paramètres ajustables approuvés ;
- bornes physiques documentées ;
- séparation des régimes calibration/validation ;
- métriques convenues avant observation du résultat de validation.

## 7. Lien avec D20

Le pilote réel utilisera d'abord des fichiers hors ligne. Une intégration historian/OPC UA reste une phase ultérieure et read-only après revue OT/cybersécurité. Les résultats du pilote devront être approuvés par l'ingénieur du site et ne transféreront aucune responsabilité de conduite à PETROLE.
