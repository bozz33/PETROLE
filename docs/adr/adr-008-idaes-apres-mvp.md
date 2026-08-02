# ADR-008 — IDAES reporté après le MVP

- **Statut** : Acceptée
- **Date** : 2026-08-02
- **Source** : Documentation complète du MVP v2.0 (annexe E) et D11 § 12

## Contexte

IDAES est un environnement orienté équations basé sur Pyomo, adapté aux procédés intégrés complexes. Le MVP ne traite pas de procédés.

## Décision

IDAES n'est **pas requis au MVP**. Il pourra devenir un moteur complémentaire (`Process Optimization Core`) pour les terminaux complexes, la réconciliation de données, l'estimation de paramètres et le contrôle prédictif.

## Conséquences

Positif : évite une complexité prématurée et un temps d'apprentissage important.

Négatif : aucun ; le choix reste ouvert car Pyomo est déjà le socle d'optimisation.
