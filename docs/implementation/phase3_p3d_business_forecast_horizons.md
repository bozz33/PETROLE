# Phase 3 — P3-D horizons métier de prévision

Statut : contrat d'horizon et évaluation horizon-scoped implémentés, **sans choisir d'horizon métier à la place de l'opérateur et sans revendiquer de performance prédictive terrain**.

## Références

- D17 : Phase 3, prévisions analytiques et gate « horizon métier convenu » ;
- D20 : protocole et données pilote ;
- `phase3_analytics_execution.md`.

## Problème fermé

La baseline OLS, la persistance naïve et le split `train/validation/test` existaient déjà, mais une métrique pouvait encore être calculée sur des prédictions dont le lead-time n'était pas représenté par un objet métier explicite.

`hydro_api.services.forecast_horizons` introduit donc un contrat séparé :

- `horizon_ref` ;
- cible analytique ;
- usage métier ;
- décision approuvée ;
- provenance du protocole ;
- intervalle d'échantillonnage en secondes ;
- nombre de pas de prévision.

PETROLE ne fournit aucune durée par défaut. Un horizon de 30 minutes n'existe dans le logiciel que si le contexte métier l'a défini, par exemple comme 6 pas de 300 secondes.

## Points d'évaluation

Chaque point conserve :

- référence unique ;
- instant d'émission de la prévision ;
- instant cible ;
- valeur prédite SI ;
- valeur observée SI ;
- provenance de la prédiction ;
- provenance de l'observation.

L'instant cible doit être strictement postérieur à l'émission et les deux timestamps doivent être timezone-aware.

## Gate d'alignement

`evaluate_forecast_horizon(...)` exige pour chaque point :

`target_timestamp - issued_at == sampling_interval × lead_steps`

Tout point à un autre lead-time fait échouer l'évaluation. Le logiciel ne mélange donc pas silencieusement des performances à 30 minutes, 1 heure ou une autre échéance.

Les références de points et les instants d'émission doivent également être uniques dans une campagne.

## Métriques

Pour les points correctement alignés, la couche calcule uniquement :

- nombre de points ;
- MAE ;
- RMSE ;
- biais.

Aucun seuil de victoire, PASS/FAIL ou publication n'est ajouté. La porte `BUSINESS_HORIZON_AGREED` reste une preuve externe : le présent contrat matérialise et vérifie l'horizon décidé, mais ne remplace pas l'accord métier.

## Ce qui reste

- données historiques représentatives ;
- horizons réellement choisis avec le pilote ;
- campagnes hors échantillon sur ces horizons ;
- critères de performance pré-enregistrés ;
- comparaison horizon par horizon contre les baselines ;
- revue ingénieur avant publication pilote.

## Statut de qualification

`IMPLEMENTED_HORIZON_CONTRACT_NOT_FIELD_VALIDATED`
