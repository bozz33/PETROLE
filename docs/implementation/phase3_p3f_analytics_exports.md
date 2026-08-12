# Phase 3 — P3-F Exports analytiques versionnés

Références : D04, D09, D12, D17 et D19.

## Implémentation

`hydro_api.services.analytics_exports` sérialise les résultats déjà produits par `analyze_time_series` sans recalculer les statistiques.

Le JSON conserve : version d'export, tag, `processing_version`, unité SI, qualités incluses, fenêtre demandée, fenêtre source, compteurs inclus/exclus, paramètres de bucket, agrégats et tendance.

Le CSV exporte les buckets avec colonnes stables et horodatages timezone-aware.

Chaque artefact publie une empreinte SHA-256 de ses octets exacts.

## Règles

- aucune imputation ni correction pendant l'export ;
- aucune statistique recalculée dans l'exporteur ;
- aucune valeur `bad` réintroduite si elle avait été exclue du résultat source ;
- version de traitement et unité SI restent visibles ;
- le hash prouve l'identité de l'artefact, pas sa validité scientifique.

## Gate

Les dashboards et prévisions restent soumis aux jeux de données terrain, aux splits train/validation/test et aux seuils métier approuvés prévus par la Phase 3.
