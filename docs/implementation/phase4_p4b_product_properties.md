# Phase 4 — P4-B Propriétés produit tabulées

Référence principale : D07 §3, complétée par D10 et D17.

## Implémentation

`hydro_transients.product_properties` fournit des tables 1D versionnées `propriété = f(T)` avec provenance obligatoire et interpolation linéaire strictement bornée.

Le contrat `ProductPropertyTables` impose actuellement les grandeurs minimales retenues par D07 pour les produits pétroliers :

- densité `kg/m^3` ;
- viscosité cinématique `m^2/s` ;
- pression de vapeur `Pa`.

Chaque table exige au moins deux températures absolues strictement croissantes. Toute extrapolation hors du domaine publié est refusée.

## Règles

- les tables laboratoire/opérateur sont prioritaires ;
- aucune corrélation académique n'est injectée automatiquement ;
- aucune conversion d'unité cachée dans ce sous-lot : les tables internes respectent le contrat SI ;
- provenance et version restent obligatoires ;
- des tables ayant des domaines de température différents peuvent provoquer un refus d'évaluation, ce qui est préférable à une extrapolation silencieuse.

## Suite

Le transport spatial d'une interface multiproduit, la dispersion/mélange et un éventuel modèle thermique longitudinal restent des sous-modèles distincts à sourcer et valider avant intégration.
