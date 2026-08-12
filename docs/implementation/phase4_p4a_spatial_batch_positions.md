# Phase 4 — P4-A position spatiale idéale des interfaces

Statut : transformation géométrique volume→abscisse implémentée, **sans modèle de mélange ni dispersion**.

## Références

- D07 : unités SI, graphe orienté et séparation explicite des hypothèses ;
- D17 : Phase 4 multiproduits et transitoires ;
- `phase4_multiproduct_transients_execution.md` : P4-A lots/interfaces et besoin de position spatiale.

## Hypothèse explicitement limitée

La brique `hydro_transients.batch_positions` représente un **déplacement piston idéal**. Elle ne constitue pas un modèle industriel d'interface multiproduit. Elle sert uniquement à transformer un volume déplacé explicitement fourni en position géométrique dans une conduite dont la section interne est connue segment par segment.

Aucune largeur d'interface, dispersion axiale, diffusion, contamination, contraction/expansion thermiques ou correction de compressibilité n'est ajoutée.

## Modèle

Chaque segment fournit :

- longueur interne `L` ;
- aire interne `A` ;
- provenance géométrique.

Sa capacité géométrique vaut `V = A × L`.

Pour une interface logique créée au volume injecté cumulé `V_interface`, le volume parcouru depuis l'entrée est :

`V_parcouru = V_déplacé_cumulé - V_interface`

La conversion en abscisse traverse les segments dans l'ordre inlet→outlet et applique localement `Δx = ΔV / A`.

## États exposés

- `pending` : `V_parcouru < 0`, l'interface n'a pas encore été injectée ;
- `in_pipeline` : `0 ≤ V_parcouru ≤ capacité`, une abscisse et un segment sont fournis ;
- `exited` : `V_parcouru > capacité`, l'interface a quitté la conduite.

Les positions exactement à l'entrée et à la sortie restent représentées explicitement par `x=0` et `x=L_total`.

## Contrôles

- segments non vides et identifiants uniques ;
- longueurs et sections strictement positives et finies ;
- volume déplacé cumulé positif ou nul et fini ;
- provenance géométrique obligatoire ;
- aucune extrapolation spatiale après la sortie.

## Tests

`tests/test_batch_positions.py` couvre :

- capacité et longueur du profil ;
- localisation dans plusieurs diamètres/sections ;
- interfaces pending et exited ;
- positions entrée/sortie ;
- géométrie invalide ou dupliquée ;
- refus d'un déplacement négatif.

## Limites et gate

`IMPLEMENTED_IDEAL_PLUG_DISPLACEMENT_NOT_MULTIPRODUCT_VALIDATED`

Cette fondation permet d'afficher et tracer un déplacement spatial idéal. La largeur physique des interfaces, le mélange, la contamination et leur dépendance aux propriétés produit restent bloqués jusqu'à sélection d'un modèle sourcé, disponibilité de données représentatives et benchmarks indépendants.
