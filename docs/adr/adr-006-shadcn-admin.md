# ADR-006 — Shadcn Admin comme base d'interface

- **Statut** : Acceptée
- **Date** : 2026-08-02
- **Source** : Documentation complète du MVP v2.0 (annexe E) et D11 § 12

## Contexte

Le frontend doit être productif rapidement pour une équipe de deux développeurs, sans figer la logique métier.

## Décision

Le frontend part de **Shadcn Admin** (React + TypeScript + Vite + Tailwind + Radix). Les pages de démonstration et l'authentification partielle du gabarit sont **remplacées**. React Flow assure l'éditeur de réseau, ECharts les graphiques scientifiques, MapLibre la cartographie.

## Conséquences

Positif : navigation, thème, accessibilité et composants disponibles immédiatement.

Négatif : ce gabarit n'est pas une application métier prête ; le remplacement des données de démonstration est un travail explicite du backlog.
