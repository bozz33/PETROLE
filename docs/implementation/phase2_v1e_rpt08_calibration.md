# Phase 2 — V1-E2 Rapport RPT-08 Calibration

## Objet

RPT-08 documente une exécution V1-C sans transformer l'ajustement numérique en validation scientifique ou industrielle.

Le rapport expose :

- provenance/référence du jeu de données ;
- version du modèle de rapport ;
- paramètres calibrés, valeurs, bornes et unités ;
- convergence numérique et nombre d'évaluations ;
- régimes utilisés pour la calibration ;
- régimes tenus à part pour la validation ;
- MAE, RMSE, biais et erreur absolue maximale pour les deux jeux ;
- statut explicite de validation terrain.

## Règles

Le rapport doit toujours rappeler que le jeu de validation n'a pas participé à l'objectif de calibration. Une convergence numérique n'est pas un critère d'acceptation industrielle. Aucun seuil PASS/FAIL n'est généré sans protocole de pilote approuvé et traçable.

Le statut par défaut reste `IMPLEMENTED_NOT_FIELD_VALIDATED` jusqu'à exécution documentée sur données terrain distinctes conformément à D20.

## Implémentation

`hydro_reporting.calibration.CalibrationReportData` porte les données du document et `build_calibration_report_pdf(...)` produit un PDF A4 déterministe en réutilisant le socle commun des rapports opérationnels.
