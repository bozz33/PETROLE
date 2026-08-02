# ADR-001 — Monolithe modulaire au MVP

- **Statut** : Acceptée
- **Date** : 2026-08-02
- **Source** : Documentation complète du MVP v2.0 (annexe E) et D11 § 12

## Contexte

Deux développeurs doivent livrer un MVP scientifique complet. Une architecture distribuée dès le départ multiplierait les coûts d'exploitation sans bénéfice.

## Décision

Le backend du MVP est un **monolithe modulaire** : un seul déploiement, une seule base, mais des frontières de domaine strictes (`identity`, `projects`, `catalog`, `network`, `scenarios`, `simulations`, `tanks`, `optimization`, `reports`, `audit`, `standards`). Les calculs longs s'exécutent dans des workers séparés.

## Conséquences

Positif : complexité maîtrisée, tests d'intégration simples, déploiement Docker Compose.

Négatif : discipline requise pour ne pas créer de dépendances croisées ; contrôlée par des tests d'architecture.

Évolution : chaque module possède une façade de service, ce qui permet d'extraire un moteur en service sans réécrire le backend central (DEC-ARCH-001).
