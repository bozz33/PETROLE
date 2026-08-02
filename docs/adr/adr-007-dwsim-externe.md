# ADR-007 — DWSIM comme référence externe uniquement

- **Statut** : Acceptée
- **Date** : 2026-08-02
- **Source** : Documentation complète du MVP v2.0 (annexe E) et D11 § 12

## Contexte

DWSIM est utile pour vérifier des propriétés et des équipements, mais son intégration poserait des questions de licence et de couplage.

## Décision

DWSIM reste un **outil externe de validation**. Son code n'est pas incorporé à la plateforme. Il sert à construire des cas de comparaison documentés dans le dossier de preuve (D10).

## Conséquences

Positif : aucune contamination de licence, aucun couplage.

Négatif : la comparaison est manuelle ou semi-automatisée ; acceptée pour le MVP.
