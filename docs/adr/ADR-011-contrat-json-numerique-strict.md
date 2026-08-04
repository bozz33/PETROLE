# ADR-011 — Contrat JSON numérique strict

- **Identifiant stable :** `ADR-DATA-JSON-001`
- **Statut :** accepté
- **Date :** 2026-08-04
- **Décision :** architecture et qualité des données

## Contexte

Les moteurs scientifiques peuvent produire des valeurs IEEE 754 non finies (`NaN`, `+Infinity`, `-Infinity`) lors d'une non-convergence, d'une singularité ou d'une erreur numérique. Ces valeurs ne font pas partie de la grammaire JSON définie par la RFC 8259 et sont refusées par PostgreSQL dans les colonnes JSON/JSONB.

Une valeur non finie avait atteint la persistance d'un résultat de calcul et transformé à tort une non-convergence scientifique en erreur technique du worker.

## Décision

1. Toute donnée quittant le noyau scientifique à destination de l'API, de PostgreSQL, des rapports, de l'audit ou de la file de tâches doit être JSON conforme à la RFC 8259.
2. `NaN`, `+Infinity` et `-Infinity` sont remplacés par `null` uniquement après classification du résultat et avec un diagnostic contenant leur chemin et leur nature.
3. Un résultat non convergent conserve son statut scientifique et devient non approuvable.
4. Un résultat déclaré convergent contenant une valeur non finie devient `SIM_NUMERIC_ERROR`, non approuvable et non éligible à la décision.
5. Le sérialiseur SQLAlchemy utilise `json.dumps(..., allow_nan=False)` comme barrière finale. Toute fuite non normalisée échoue explicitement avant l'écriture.
6. Les scalaires numériques issus de bibliothèques scientifiques sont convertis vers des types Python JSON-compatibles avant validation.
7. Une valeur `null` n'est jamais interprétée comme zéro ni comme une conformité. Une règle obligatoire portant sur une valeur indisponible est `not_evaluated` et bloque l'approbation.

## Statuts

- `SIM_NOT_CONVERGED` : le solveur n'a pas convergé ;
- `SIM_INVALID_INPUT` : données d'entrée invalides ;
- `SIM_NO_PHYSICAL_SOLUTION` : absence de solution physique admissible ;
- `SIM_NUMERIC_ERROR` : incohérence numérique d'un résultat annoncé convergent ;
- `SIM_TECHNICAL_ERROR` : panne d'infrastructure ou exception de programmation.

## Conséquences

- Les résultats sont portables entre l'API, les rapports et PostgreSQL.
- Les anomalies numériques restent traçables sans produire de JSON invalide.
- Les résultats incomplets ne peuvent pas être approuvés silencieusement.
- Les schémas de base et OpenAPI incluent `SIM_NUMERIC_ERROR`.
- Les tests unitaires couvrent le normaliseur et les tests d'intégration couvrent la persistance PostgreSQL.

## Implémentation de référence

- `packages/shared/hydro_shared/json_safety.py`
- `apps/api/hydro_api/services/core.py`
- `apps/api/hydro_api/database/session.py`
- `apps/api/hydro_api/models/constraints.py`
- `packages/shared/hydro_shared/codes.py`
- `database/migrations/versions/8b1f2d6c4e90_ajoute_erreur_numerique_calcul.py`
- `tests/unit/test_json_safety.py`
- `tests/unit/test_model_constraints.py`
- `tests/api/test_json_persistence.py`

## Références officielles

- IETF RFC 8259 — The JavaScript Object Notation (JSON) Data Interchange Format : https://www.rfc-editor.org/rfc/rfc8259
- Python `json` — `allow_nan` : https://docs.python.org/3/library/json.html
- SQLAlchemy Engine — `json_serializer` : https://docs.sqlalchemy.org/en/20/core/engines.html
- Pydantic configuration — `allow_inf_nan` : https://docs.pydantic.dev/latest/api/config/
