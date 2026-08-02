# ADR-010 — Règles normatives versionnées, non codées en dur

- **Statut** : Acceptée
- **Date** : 2026-08-02
- **Source** : Documentation complète du MVP v2.0 (annexe E) et D11 § 12

## Contexte

Les référentiels applicables (ASME B31.4, ISO 13623, API 610/650/653/2350…) varient selon le pays, l'opérateur et l'édition.

## Décision

Les règles normatives sont stockées comme **données versionnées** (`Standard`, `RuleSet`, `Rule`, `RuleParameter`) et évaluées par un moteur de règles distinct des équations physiques. Le texte intégral des normes protégées n'est jamais reproduit ; seules les règles issues de textes acquis légalement sont paramétrées.

## Conséquences

Positif : changement de jeu de règles sans modification du solveur (FR-GEN-004) ; traçabilité de l'édition appliquée.

Négatif : une règle doit être approuvée par un expert avant activation ; le produit n'affiche jamais une « conformité complète » lorsqu'il n'a vérifié qu'un sous-ensemble.
