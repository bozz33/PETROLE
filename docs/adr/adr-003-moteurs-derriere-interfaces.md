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

## Preuve de concept POC-OS-04

La plage `pandapipes >= 0.14, < 0.15` est validée automatiquement contre le moteur principal
sur une conduite horizontale avec pertes singulières et sur une conduite avec dénivelé. Les
essais contrôlent séparément la pression aval, le facteur de frottement, la perte linéaire, la
perte singulière et le bilan de charge. Ils sont exécutés par
`tests/unit/test_pandapipes_adapter.py` dans l'image de développement.

L'adaptateur reste limité aux chaînes de tronçons entièrement en service, avec débit et
pression absolue amont imposés, modèle de Colebrook–White et points altimétriques placés aux
frontières des tronçons. Il refuse les stations, injections actives, surcharges d'équipement,
accessoires fermés et zones gravitaires. Un résultat pandapipes ne peut jamais être approuvé :
ce moteur de comparaison n'exécute pas l'ensemble des contrôles C-001 à C-012.
