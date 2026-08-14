# P6-H — adapter d'observations du solveur stationnaire

Statut : fondation de benchmark, non certifiante.

## Objet

`build_stationary_weymouth_benchmark_observations(...)` transforme des sorties déjà calculées par le solveur stationnaire PETROLE en `GasBenchmarkObservation` consommables par le contrat P6-H existant.

Cette couche ne réalise aucune conversion d'unité et n'applique aucun critère de réussite.

## Grandeurs actuellement supportées

Deux grandeurs seulement sont autorisées :

- `node_absolute_pressure` avec unité exacte `Pa` ;
- `pipe_signed_mass_flow` avec unité exacte `kg/s`.

Une liaison demandant par exemple `bar` ou `Sm3/h` est refusée. Une conversion éventuelle devra être une transformation explicite, versionnée, sourcée et testée en amont.

## Liaison explicite

Chaque `StationaryGasBenchmarkBinding` contient :

- identifiant d'observation ;
- grandeur ;
- identifiant du nœud ou de la conduite ;
- unité ;
- valeur de référence ;
- provenance de la référence.

Les identifiants d'observation doivent être uniques et l'entité doit exister dans le résultat PETROLE.

## Statut du solveur conservé

Le bundle produit contient :

- `solve_ref` ;
- `solver_status` ;
- provenance PETROLE ;
- observations.

L'adapter ne transforme donc jamais silencieusement une sortie `NON_CONVERGED` en observation sans contexte. La couche P6-H peut décider séparément si une campagne accepte ou exclut ce type de résultat.

## Séparation des responsabilités

L'adapter :

- extrait les valeurs PETROLE ;
- vérifie identité et unité ;
- construit les observations.

`assess_external_gas_benchmark(...)` reste responsable du calcul des erreurs signées, absolues et relatives ainsi que de l'application de critères explicitement fournis.

Le protocole de pré-enregistrement reste responsable de décider quels critères sont approuvés avant la comparaison.

## Tests

Les tests vérifient :

- extraction de pression et débit signé ;
- refus d'une unité différente ;
- refus d'une entité inconnue ;
- refus d'identifiants dupliqués ;
- conservation explicite d'un statut source `NON_CONVERGED`.

Toutes les références de test sont synthétiques et ne constituent aucune tolérance industrielle.
