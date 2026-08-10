# V1-A3 — séries temporelles et qualité

Statut : tranche de développement Pilote/V1, sans effet de certification.

Base : `feat/pilot-v1-measurements-foundation` à `5043ac1fdaa1b59dc08d7efa86e58100309ff48d`.

Références : D04 FR-DAT-004, D09 §10 et §13, D12 §7, D17 Phase 2, D20.

## Objectif

Rendre les séries temporelles V1-A2 directement exploitables par l'ingénieur sans modifier les données brutes ni masquer les points de mauvaise qualité.

## Contrat fonctionnel

- sélectionner un tag de mesure d'un site ;
- consulter sa série normalisée SI sur une plage temporelle ;
- filtrer par code qualité sans supprimer les données sources ;
- afficher les trous temporels, doublons et points hors ordre ;
- fournir les statistiques de la période : nombre total, nombre exploitable, min, max, moyenne et écart-type ;
- détecter des valeurs aberrantes avec une méthode explicitement choisie et des paramètres visibles ;
- conserver la version de traitement et le lignage vers `SampleRaw`, dataset et ligne source ;
- permettre d'afficher les points exclus afin qu'aucune correction ne soit silencieuse.

## Méthodes d'aberrants admises dans cette tranche

La détection reste analytique, déterministe et désactivée par défaut.

- `none` : aucune détection ;
- `zscore` : seuil configurable sur l'écart-type, uniquement si l'échantillon est suffisant ;
- `iqr` : facteur configurable autour de Q1/Q3.

Un point signalé comme aberrant reste stocké et visible. Cette classification ne modifie ni `samples_raw` ni `samples_normalized`.

## Contrat API cible

`GET /api/v1/measurement-tags/{tag_id}/series-analysis`

Paramètres :

- `start_timestamp`, `end_timestamp` ;
- `qualities` facultatif ;
- `processing_version` facultatif ;
- `outlier_method=none|zscore|iqr` ;
- `outlier_threshold` selon la méthode ;
- pagination des points.

Réponse :

- métadonnées du tag et unité SI ;
- plage temporelle ;
- version de traitement utilisée ;
- compteurs qualité ;
- statistiques descriptives ;
- nombre de doublons ;
- nombre de trous selon cadence de référence ;
- définition de la cadence observée/référence ;
- points paginés avec drapeaux `duplicate`, `gap_after`, `outlier`, qualité et lignage.

## Règles de qualité

- `bad` est exclu des statistiques par défaut mais reste retournable ;
- `uncertain`, `substituted` et `estimated` restent distingués ;
- les doublons ne sont pas fusionnés automatiquement ;
- un trou n'est déclaré que si une cadence de référence peut être déterminée ou fournie explicitement ;
- les horodatages restent en UTC au contrat API ;
- aucune interpolation automatique dans V1-A3.

## Interface cible

La page Données doit ajouter un panneau « Séries temporelles » séparé du flux d'import :

1. site/tag ;
2. plage temporelle et version de traitement ;
3. filtres qualité ;
4. graphique valeur SI / temps ;
5. métriques de qualité et statistiques ;
6. tableau paginé avec lignage et drapeaux ;
7. paramètres d'aberrants visibles.

## Critères d'acceptation

- tests PostgreSQL sur ordre, doublons, trous, qualités et deux méthodes d'aberrants ;
- aucune écriture sur `samples_raw` ou `samples_normalized` pendant l'analyse ;
- résultats déterministes à entrées identiques ;
- filtrage par `processing_version` pour éviter de mélanger plusieurs projections d'un même brut ;
- TypeScript strict et tests UI ;
- Playwright bureau/mobile ;
- migration inchangée sauf nécessité démontrée ;
- backend, frontend, migrations et CodeQL verts avant fermeture.

## Hors portée

- interpolation/réconciliation automatique ;
- comparaison mesure-modèle FR-DAT-005 ;
- calibration ;
- SCADA/historian ;
- alertes temps réel ;
- détection de fuite.
