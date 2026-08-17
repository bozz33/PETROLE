# Phase 6 — P6-A Adaptateur CoolProp traçable

Références : D07 §3/§10, D10 et documentation officielle CoolProp High-Level API.

## Implémentation

`hydro_gas.coolprop_adapter` fournit un adaptateur pour fluides purs/pseudo-purs explicitement retenus :

- backend CoolProp fourni (`HEOS`, `INCOMP`, etc.) ;
- fluide fourni sans syntaxe de mélange ;
- provenance de la définition ;
- enveloppe projet explicite `Tmin/Tmax/Pmin/Pmax` avec provenance ;
- évaluation SI via `PropsSI` de densité et viscosité dynamique au point `(T,P)` ;
- viscosité cinématique `nu = mu / rho` ;
- pression de saturation liquide via `Q=0` à la température demandée ;
- version et révision Git CoolProp réellement exécutées enregistrées dans le résultat.

## Règles

- aucun fluide/backend/domaine par défaut ;
- refus avant appel backend si T/P est hors enveloppe projet ;
- aucune extrapolation ou corrélation de secours en cas d'échec CoolProp ;
- les mélanges sont exclus de cet adaptateur car leurs équilibres bulle/rosée nécessitent un contrat distinct ;
- l'existence d'une valeur CoolProp n'en fait pas automatiquement une propriété validée pour un produit pétrolier réel : D07 donne priorité aux données opérateur/laboratoire pour ces produits.

## Documentation officielle vérifiée pendant l'implémentation

CoolProp 8.0.0 documente `PropsSI`, les préfixes de backend, les sorties SI `DMASS`/viscosité et `get_global_param_string("version"/"gitrevision")`. La CI enregistre la version effectivement installée ; aucune version n'est masquée par le wrapper.

## Gate

Pour le gaz réel : composition, choix EOS/backend, domaine et comparaison à des propriétés de référence doivent être approuvés avant toute validation de solveur gaz.
