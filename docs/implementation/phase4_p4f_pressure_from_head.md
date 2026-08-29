# Phase 4 — P4-F Reconstruction de pression depuis la charge totale

Référence principale : D07 §2/§4.

D07 définit la pression interne en Pa absolu et la charge totale par :

`H = z + p/(rho*g) + alpha*v^2/(2g)`

avec `v = 4Q/(pi*D^2)` pour une conduite circulaire pleine.

## Implémentation

`hydro_transients.pressure` fournit :

- `mean_velocity_full_pipe(Q,D)` ;
- `pressure_from_total_head(H,z,rho,v,alpha,g)` ;
- décomposition de la charge cinétique et de la charge de pression ;
- drapeau explicite si la pression absolue candidate devient négative.

## Règles

- altitude, densité, vitesse et `alpha` sont des entrées explicites ;
- aucune densité/altitude par défaut n'est injectée ;
- la pression négative n'est jamais rabattue à zéro : elle reste visible comme état non physique du modèle monophasé ;
- la brique n'ajoute aucun modèle de cavitation ou séparation de colonne ;
- la densité transitoire variable exige un modèle thermique/composition cohérent avant usage.

## Usage

Cette brique permet de produire `P(x,t)` à partir des snapshots `H(x,t)` uniquement lorsque la géométrie, l'altitude et les propriétés requises sont réellement disponibles. Sinon le résultat pression doit rester indisponible plutôt que d'être reconstruit avec des hypothèses cachées.
