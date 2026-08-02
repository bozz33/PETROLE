# ADR-003 — Moteurs scientifiques derrière une interface commune

- **Statut** : Acceptée
- **Date** : 2026-08-02
- **Source** : Documentation complète du MVP v2.0 (annexe E) et D11 § 12

## Contexte

Les liquides, les gaz, les régimes transitoires et l'optimisation reposent sur des modèles physiques différents. Aucun moteur universel n'existe.

## Décision

Tous les moteurs implémentent l'interface `HydraulicEngine` (`validate`, `simulate`, `explain`). Le MVP fournit `LongDistanceLiquidEngine` (moteur principal oléoduc) et `PandapipesEngine` (adaptateur pour les cas compatibles et le benchmark). Les moteurs futurs (`Gas Network Core`, `Transient Core`) suivront le même contrat, éventuellement comme services.

## Conséquences

Positif : comparaison croisée systématique, remplacement d'un moteur sans toucher au produit, aucune dépendance irréversible à `pandapipes` (DEC-ENGINE-002).

Négatif : une couche d'abstraction supplémentaire ; justifiée par la stratégie de validation D10.
