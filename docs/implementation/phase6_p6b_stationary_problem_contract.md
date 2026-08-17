# Phase 6 — P6-B : contrat du problème stationnaire pressure-slack

Statut : **IMPLEMENTED_STRUCTURAL_PROBLEM_NOT_NUMERICAL_SOLVER**.

## 1. Objet

D07 autorise plusieurs familles de conditions aux limites : pression imposée, débit imposé, demande, injection et caractéristiques de machines. La première famille P6-B est volontairement plus stricte afin de préparer un solveur démontrable sans accepter des combinaisons mal contraintes.

Pour chaque composante connexe du réseau, PETROLE exige exactement **un nœud de pression slack** :

- sa pression absolue est imposée ;
- son débit externe reste une inconnue ;
- les pressions des autres nœuds sont inconnues ;
- les débits de toutes les conduites sont inconnus ;
- les autres injections/soutirages fournis restent des frontières connues.

Cette convention conserve toutes les équations de masse et toutes les équations constitutives.

## 2. Implémentation

Module : `packages/hydrogas/hydro_gas/stationary_problem.py`.

### `GasPressureSlack`

Contient :

- `node_id` ;
- `pressure_pa` ;
- `source_ref`.

La pression doit être finie, absolue et positive ou nulle, conformément à la convention SI actuelle du domaine gaz.

### `StationaryWeymouthProblem`

Contient :

- référence du problème ;
- topologie `SteadyGasNetwork` ;
- pressions slack ;
- frontières de débit connues.

Le contrat refuse :

- référence de problème vide ;
- deux slacks sur le même nœud ;
- slack sur nœud inexistant ;
- doublon d'identifiant de frontière de débit ;
- frontière de débit sur nœud inexistant.

### `build_stationary_weymouth_unknown_layout`

La fonction calcule les composantes connexes du graphe sans changer son orientation métier. Elle exige exactement un slack par composante.

Pour une composante comportant `N` nœuds et `E` conduites :

- pressions inconnues : `N - 1` ;
- débits de conduites inconnus : `E` ;
- débit externe du slack : `1` ;
- total inconnues : `N + E` ;
- équations de masse conservées : `N` ;
- équations de conduite conservées : `E` ;
- total équations : `N + E`.

Le système est donc **structurellement carré** pour cette famille de frontières. Cette égalité ne prouve ni unicité de solution, ni conditionnement numérique, ni convergence.

Pour plusieurs composantes indépendantes, la même règle est appliquée composante par composante.

## 3. Pourquoi le débit du slack est une inconnue

Fixer une pression absolue ancre le niveau de pression. Si PETROLE supprimait arbitrairement l'équation de masse de ce nœud, la conservation ne serait plus vérifiée au même niveau que les autres nœuds.

Le contrat conserve donc l'équation de masse et introduit explicitement le débit externe du slack comme inconnue. Le futur solveur déterminera cette valeur comme la quantité nécessaire pour fermer le bilan de la composante.

## 4. Ce que ce contrat ne prouve pas

Un nombre d'équations égal au nombre d'inconnues ne garantit pas :

- existence d'une solution ;
- unicité ;
- domaine physique valide ;
- Jacobien non singulier ;
- bonne mise à l'échelle ;
- convergence de Newton ou d'un autre solveur ;
- respect de contraintes de pression ou d'équipement.

Ces vérifications appartiennent aux incréments suivants.

## 5. Frontières non encore activées

La première version ne prétend pas résoudre toutes les combinaisons autorisées par D07. Sont notamment à traiter ultérieurement avec leur propre analyse structurelle :

- plusieurs pressions imposées dans une même composante ;
- pression imposée avec débit externe simultanément fixé sans variable slack additionnelle ;
- régulateur de pression ;
- compresseur ;
- vanne avec loi constitutive ;
- stockage dynamique ;
- frontière température/propriétés couplées ;
- réseaux transitoires.

Le logiciel devra déclarer ces classes non supportées tant qu'un contrat spécifique n'existe pas.

## 6. Gate suivant

Le prochain incrément P6-B pourra définir le **mapping déterministe état ↔ vecteur d'inconnues**, mais il ne devra toujours pas choisir une tolérance ou annoncer une convergence.

Avant l'activation d'un vrai solveur :

1. critères de benchmark approuvés ;
2. cas indépendants suffisants ;
3. stratégie de mise à l'échelle documentée ;
4. méthode numérique sélectionnée ;
5. statuts de convergence explicites ;
6. tests de cas simple, série, ramifié et flux inverse ;
7. comparaison indépendante.
