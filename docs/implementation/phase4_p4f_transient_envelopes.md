# Phase 4 — P4-F Enveloppes transitoires H/Q

Références : D07 §11, D10, D17 et D19.

## Implémentation

`hydro_transients.results` calcule, pour chaque nœud d'une séquence de snapshots MOC cohérente :

- charge minimale et maximale ;
- temps de ces deux extrêmes ;
- débit minimal et maximal ;
- temps de ces deux extrêmes.

Le post-traitement refuse les temps non ordonnés, les tailles de vecteurs incohérentes et les valeurs non finies.

## Limite volontaire

Aucune pression n'est reconstruite à partir de la charge seule. D07 définit `H` comme charge totale ; le passage à `p(x,t)` exige au minimum altitude, densité et terme cinétique locaux cohérents avec le modèle. Cette conversion sera ajoutée seulement lorsque la géométrie/propriété temporelle nécessaire sera explicitement disponible.

## Gate

Les enveloppes H/Q sont un post-traitement du solveur, pas une validation MOC. La publication du moteur transitoire reste conditionnée aux benchmarks indépendants et à la revue thermofluides prévues par D10/D17.
