# Phase 3 — Provenance des runs de prévision

Références : D09, D12, D17 et D20.

## Implémentation

`hydro_api.services.forecast_provenance` construit un manifeste immuable pour la baseline OLS Phase 3 :

- référence du run et de la série source ;
- famille/version de modèle ;
- version de code ;
- date UTC ;
- empreinte SHA-256 séparée de `train`, `validation` et `test` ;
- nombre de points de chaque split ;
- coefficients du modèle ajusté ;
- MAE, RMSE et biais de chaque split ;
- empreinte SHA-256 du manifeste complet.

## Règles

- les trois splits restent identifiables séparément ;
- aucune donnée de validation/test n'est mélangée au hash d'entraînement ;
- le manifeste n'ajuste ni ne réentraîne le modèle ;
- la version de code est fournie explicitement par la release/run ;
- un hash identique prouve l'identité des entrées sérialisées, pas la qualité prédictive du modèle.

## Gate

Les prédictions pilotes restent conditionnées aux données terrain, au protocole figé train/validation/test, à une baseline naïve et aux métriques choisies avant observation du jeu de test.
