# Phase 3 — P3-D baseline naïve de persistance

Statut : baseline naïve et comparaison hors échantillon implémentées, **sans seuil de publication automatique**.

## Références

- D17 : prévisions et validation hors échantillon ;
- D20 : séparation calibration/validation ;
- `phase3_analytics_execution.md` : baseline naïve documentée requise avant publication P3-D/P3-E.

## Baseline

La baseline `last-value persistence` prend uniquement la dernière observation chronologique du jeu `train` et maintient cette valeur sur les jeux `validation` et `test`.

Elle ne consulte aucune valeur future pour s'ajuster et ne réentraîne rien après le split.

## Métriques

La baseline calcule séparément sur validation et test :

- nombre d'observations ;
- MAE ;
- RMSE ;
- biais signé.

`compare_linear_to_persistence(...)` compare ensuite la baseline OLS existante à la persistance sur les mêmes populations. Les deltas sont définis comme `métrique_modèle - métrique_baseline` ; une valeur négative signifie uniquement que l'erreur mesurée est plus petite sur ce jeu.

Aucun seuil de supériorité, aucune règle de significativité et aucun verdict `GO` n'est codé dans cette fonction.

## Pourquoi cette baseline

Elle donne une référence minimale explicable pour éviter de considérer un modèle comme utile simplement parce que ses erreurs paraissent petites en valeur absolue. Une future validation métier pourra imposer d'autres baselines adaptées aux horizons et régimes réels.

## Tests

`tests/test_forecast_baselines.py` couvre :

- utilisation exclusive de la dernière valeur du train ;
- comparaison OLS/persistance sur tendance linéaire ;
- égalité sur série constante ;
- refus de comparer des métriques calculées sur des populations de tailles différentes.

## Limites

`IMPLEMENTED_NAIVE_BASELINE_NOT_FIELD_VALIDATED`

La présence d'une baseline naïve ne valide pas une capacité prédictive industrielle. Les horizons métier, datasets représentatifs, protocole de campagne, incertitudes et critères d'acceptation restent à fixer et valider avant publication.
