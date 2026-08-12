# Phase 7 — P7-I partition figée du dataset labellisé

Statut : contrat de partition et empreinte reproductible implémentés, **sans créer de labels, sans données de fuite réelles et sans revendication de performance**.

## Références

- D17 : Phase 7, données labellisées et jeu d'essai indépendant avant performance LDS ;
- D20 : protocole de pilote, métriques et décision humaine ;
- `phase7_leak_digital_twin_execution.md`.

## Objectif

`hydro_leak.validation_dataset` empêche qu'une campagne P7-I choisisse après coup uniquement les événements favorables. Chaque événement labellisé disponible doit être affecté explicitement à l'un des groupes suivants :

- calibration ;
- validation ;
- test indépendant ;
- exclusion justifiée.

Le jeu de test est obligatoirement non vide. Calibration et validation peuvent rester vides lorsqu'une méthode ou un protocole n'en a pas besoin ; PETROLE n'impose pas un workflow apprenant à une méthode déterministe.

## Exclusions

Une exclusion n'est jamais silencieuse. Elle exige :

- l'identifiant de l'événement ;
- une référence de motif ;
- une référence de preuve.

Un événement ne peut appartenir qu'à un seul groupe.

## Exhaustivité

`freeze_leak_validation_dataset(...)` refuse :

- un événement labellisé dupliqué ;
- un événement affecté à plusieurs groupes ;
- une référence vers un événement absent du dataset ;
- un événement disponible laissé sans affectation ;
- un jeu de test vide ;
- une exclusion sans motif ou preuve.

Cette règle rend visible toute sélection ou exclusion avant calcul des métriques.

## Empreinte

Le manifeste calcule un SHA-256 canonique sur :

- référence du dataset ;
- référence du protocole ;
- définition des labels ;
- identifiant, timestamp et provenance de chaque événement ;
- groupe assigné ;
- motif/preuve des exclusions.

L'ordre d'entrée des événements ou des identifiants de test ne modifie pas l'empreinte.

## Relation avec les autres briques P7-I

- `event_matching` associe ensuite événements et alertes selon une fenêtre pré-enregistrée ;
- `metrics` calcule TP/FP/FN/TN et délais ;
- `validation_campaign` compare les métriques aux critères pré-enregistrés ;
- aucune de ces couches ne transforme le résultat en décision automatique Go/No-Go.

## Ce qui reste externe

- événements de fuite réels labellisés ou essais contrôlés ;
- définition de label approuvée ;
- protocole de partition choisi avant analyse ;
- seuils/critères approuvés ;
- procédure opérateur ;
- revue indépendante.

## Statut de qualification

`IMPLEMENTED_DATASET_PARTITION_CONTRACT_NO_LABELLED_FIELD_DATA`
