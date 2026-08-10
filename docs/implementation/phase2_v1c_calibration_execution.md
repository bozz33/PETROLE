# Phase 2 — V1-C Calibration contrôlée

## Objet

V1-C ajoute une calibration paramétrique contrôlée au-dessus des comparaisons mesure ↔ modèle de V1-B1. Cette capacité ne vaut ni validation scientifique indépendante, ni qualification industrielle, ni certification réglementaire.

## Règles obligatoires

1. Les observations de calibration et de validation sont identifiées séparément et ne peuvent pas être réutilisées dans les deux jeux.
2. Par défaut, au moins un régime de validation doit être absent du jeu ayant servi à l'ajustement.
3. Le jeu de validation n'entre jamais dans la fonction objectif de l'optimiseur.
4. Les paramètres sont explicitement nommés, bornés et accompagnés d'une unité.
5. Un cas avec moins d'observations de calibration que de paramètres ajustés est refusé comme sous-déterminé au premier ordre.
6. Les sorties du modèle doivent être finies ; NaN/Inf provoquent un arrêt explicite.
7. Les métriques calculées sont descriptives : MAE, RMSE, biais et erreur absolue maximale.
8. Aucun seuil industriel PASS/FAIL n'est codé sans protocole de pilote approuvé et source normative/contractuelle traçable.

## Contrat logiciel

Le module `hydro_optimization.calibration` expose :

- `CalibrationParameter` ;
- `CalibrationObservation` ;
- `CalibrationDataset` ;
- `ErrorMetrics` ;
- `CalibrationResult` ;
- `calibrate_parameters(...)`.

L'algorithme utilise un moindres-carrés borné. L'évaluateur physique reste injecté par l'appelant : le module n'invente donc ni équation de conduite, ni loi de rugosité, ni corrélation thermophysique.

## Gate terrain

Le code peut être vérifié sur cas synthétiques et benchmarks publics, mais V1-C ne sera déclaré **validé pour un pilote réel** qu'après exécution sur des données terrain comprenant au minimum un régime tenu hors ajustement, avec provenance, qualité de mesure et protocole d'acceptation approuvés.

Tant que cette preuve n'existe pas, le statut fonctionnel est : `IMPLEMENTED_NOT_FIELD_VALIDATED`.

## Suite vers RPT-08

RPT-08 pourra consommer un résultat V1-C pour documenter paramètres initiaux/finals, bornes, jeux utilisés, métriques calibration/validation et avertissements. La génération du document ne doit pas transformer une calibration réussie en certification ou validation industrielle.
