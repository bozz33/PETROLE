# Phase 6 P6-D/P6-E — gouvernance du futur solveur mixte

Statut : `IMPLEMENTED_APPROVAL_GATES_NO_COUPLED_SOLVER`.

## Objet

Le problème conduites + compresseurs actifs possède désormais une fonction numérique pure `x -> r(x)`. Ce document définit les preuves obligatoires avant d'autoriser un algorithme de résolution à déclarer une convergence.

## Artefact d'échelle

`PreRegisteredStationaryEquipmentScaleArtifact` enregistre explicitement :

- échelle de pression au carré ;
- échelle de débit massique ;
- échelle du résidu massique ;
- échelle du résidu Weymouth ;
- échelle du résidu compresseur ;
- politique, version, source et référence de pré-enregistrement.

L'état par défaut est `DRAFT`. Seul `APPROVED` avec `approval_ref` peut être matérialisé pour une future exécution.

## Artefact d'initialisation

`PreRegisteredStationaryEquipmentInitialGuessArtifact` lie l'état initial :

- au `problem_ref` exact ;
- au SHA-256 canonique du layout ;
- à une politique/version ;
- à une source et une pré-inscription ;
- à une preuve d'approbation lorsqu'il devient `APPROVED`.

Le hash du layout couvre l'ordre des pressions, débits de conduites, débits compresseurs, débits slack et les trois familles d'équations.

## Critère de convergence

`PreRegisteredStationaryEquipmentConvergenceCriterion` peut porter explicitement :

- une norme infinie maximale du résidu numérique mis à l'échelle ;
- une limite de résidu massique en `kg/s` ;
- une limite de résidu Weymouth en `Pa²` ;
- une limite de résidu compresseur en `Pa`.

Aucune de ces limites n'est déduite ni fournie par défaut. Les nombres présents dans les tests sont uniquement synthétiques.

## Contexte exact

Un critère approuvé doit correspondre exactement au tuple :

`protocol + problem family + numerical representation + solver method + scale policy + initial guess policy`.

Un critère approuvé dans un autre contexte est refusé.

## Ce que cette brique n'autorise pas encore

- aucun `least_squares`, Newton, Ipopt ou autre solveur couplé ;
- aucune tolérance industrielle implicite ;
- aucune puissance ou température compresseur ;
- aucune limite anti-surge inventée ;
- aucune qualification `benchmarked` du problème mixte.

## Prochain gate

Le prochain développement autorisé est un **solveur couplé borné** qui consomme uniquement :

1. un contexte exact ;
2. un artefact d'échelle APPROVED ;
3. un artefact d'initialisation APPROVED ;
4. un critère de convergence APPROVED ;
5. des cartes compresseurs et paramètres Weymouth déjà liés au problème.

Avant toute qualification scientifique, ce solveur devra ensuite être confronté à plusieurs cas indépendants avec critères de benchmark pré-enregistrés.
