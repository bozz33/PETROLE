# Phase 6 P6-H — adaptateur benchmark du solveur mixte

Statut : `IMPLEMENTED_OBSERVATION_ADAPTER_NO_BENCHMARK_CLAIM`.

## Objet

Cette brique projette les sorties déjà calculées du solveur stationnaire conduites + compresseurs vers le contrat P6-H existant `GasBenchmarkObservation`.

Elle n'introduit :

- aucune conversion d'unité ;
- aucune tolérance ;
- aucun critère `PASS/FAIL` ;
- aucun changement du statut du solveur source ;
- aucune qualification automatique `benchmark_ready` ou `benchmarked`.

## Grandeurs supportées

Les bindings peuvent sélectionner :

- pression absolue d'un nœud — `Pa` ;
- débit massique signé d'une conduite — `kg/s` ;
- débit massique d'un compresseur actif — `kg/s` ;
- rapport de pression compresseur — unité dimensionless `1` ;
- débit massique signé d'une frontière — `kg/s`.

Chaque binding porte :

- `observation_id` ;
- quantité ;
- identifiant de l'entité ;
- unité exacte ;
- valeur de référence externe ;
- provenance de la référence externe.

## Refus des conversions implicites

L'unité du binding doit être exactement celle de la grandeur PETROLE. Par exemple une pression externe fournie en `bar` n'est pas automatiquement convertie en `Pa` dans cet adapter.

La normalisation/conversion d'un jeu de référence doit être une étape explicite, versionnée et traçable en amont.

## Statut du solveur source

`StationaryEquipmentBenchmarkObservationBundle` conserve :

- `solve_ref` ;
- le statut exact du solveur PETROLE ;
- la provenance PETROLE des observations ;
- les observations P6-H.

Un résultat source `NON_CONVERGED` peut être archivé comme observation diagnostique, mais l'adapter ne le transforme jamais en benchmark accepté.

## Prochain gate

Les observations produites doivent encore être associées à :

1. une preuve du solveur externe et de ses hashes entrée/sortie ;
2. des critères de benchmark pré-enregistrés puis `APPROVED` ;
3. un cas/formulation/version exacts ;
4. une revue scientifique ;
5. plusieurs cas indépendants avant toute qualification du solveur mixte.

Les tests de ce module utilisent uniquement des valeurs synthétiques pour vérifier le routage des observations.
