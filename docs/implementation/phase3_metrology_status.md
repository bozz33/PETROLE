# Phase 3 — Statut métrologique et échéance de calibration

Référence principale : D15 §9, complétée par D09/D12/D17.

## Implémentation

`hydro_api.services.metrology_status` suit les métadonnées de calibration d'un instrument sans effectuer de calibration :

- référence instrument ;
- provenance du registre métrologique ;
- date de calibration ;
- date de fin de validité ;
- certificat facultatif ;
- fenêtre d'anticipation explicitement définie par une politique opérateur.

L'évaluation retourne `valid`, `due`, `expired` ou `not_available` avec le nombre de secondes jusqu'à échéance lorsqu'il est connu.

## Règles

- aucune périodicité de calibration n'est inventée par PETROLE ;
- une date de calibration sans date de validité, ou l'inverse, est refusée ;
- une absence de métadonnée produit `not_available`, jamais `valid` ;
- l'échéance est un diagnostic qualité/métrologie, pas une alarme de contrôle.

## Gate

Le pilote réel devra fournir les références métrologiques des capteurs utilisés pour la comparaison/calibration et définir sa propre politique d'anticipation.
