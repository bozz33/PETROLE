# ADR-002 — Python + FastAPI comme socle permanent

- **Statut** : Acceptée
- **Date** : 2026-08-02
- **Source** : Documentation complète du MVP v2.0 (annexe E) et D11 § 12

## Contexte

La plateforme est avant tout un produit scientifique. Le langage doit servir à la fois le calcul, l'API et l'optimisation.

## Décision

Le backend permanent est écrit en **Python** avec **FastAPI**, **Pydantic**, **SQLAlchemy 2.x** et **Alembic**. FastAPI fournit la validation typée des entrées et la génération automatique du schéma OpenAPI, ce qui correspond à une plateforme où chaque donnée technique doit être strictement validée.

## Conséquences

Positif : un seul écosystème pour NumPy/SciPy/`fluids`/CoolProp/Pyomo et pour l'API.

Négatif : performances brutes inférieures à un langage compilé ; compensées par la vectorisation NumPy et l'exécution asynchrone des calculs.

Ce choix est permanent : le backend n'est pas réécrit après le MVP.
