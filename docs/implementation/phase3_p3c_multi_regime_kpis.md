# Phase 3 — P3-C Suivi des KPI multi-régimes

Références : D04 FR-DAT-005, D17 Phase 3, D19 et D20.

## Implémentation

`hydro_api.services.regime_kpis` consomme uniquement des KPI issus de comparaisons V1-B déjà figées et associées à un identifiant de régime explicite.

Pour des régimes utilisant la même unité SI, la synthèse publie :

- nombre de régimes ;
- nombre total de points comparés ;
- biais pondéré par le nombre de points ;
- MAE pondérée ;
- RMSE poolée `sqrt(sum(n_i * RMSE_i^2) / sum(n_i))` ;
- RMSE minimale et maximale entre régimes ;
- résultats individuels conservés.

## Règles

- aucun résidu n'est recalculé ;
- aucun régime n'est fusionné s'il utilise une unité différente ;
- les identifiants de régime sont uniques dans une synthèse ;
- aucun seuil PASS/FAIL, score ou classement industriel n'est produit ;
- une synthèse multi-régimes ne remplace pas la séparation calibration/validation de D20.

## Gate

La valeur produit réelle exige des régimes terrain identifiés et des comparaisons dont la provenance est approuvée. Les tests synthétiques vérifient uniquement les identités mathématiques et le contrat logiciel.
