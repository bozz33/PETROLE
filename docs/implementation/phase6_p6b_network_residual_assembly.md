# Phase 6 — P6-B : assemblage des résidus réseau Weymouth-SI

Statut : **IMPLEMENTED_CANDIDATE_EVALUATION_NOT_NETWORK_SOLVER**.

## 1. Objet

Préparer le futur solveur stationnaire gaz sans introduire prématurément une méthode de résolution, une mise à l'échelle numérique ou une tolérance de convergence.

La brique assemble, pour un état candidat fourni :

- les résidus de conservation de masse à chaque nœud en `kg/s` ;
- les résidus constitutifs Weymouth de chaque conduite en `Pa²` ;
- les références de provenance des pressions, débits et frontières.

Elle ne cherche aucune inconnue et ne modifie pas l'état candidat.

## 2. Implémentation

Module : `packages/hydrogas/hydro_gas/weymouth_network_residual.py`.

### `GasNodePressure`

Pression absolue candidate avec :

- `node_id` ;
- `pressure_pa` ;
- `source_ref`.

La valeur doit être finie et positive ou nulle, conformément au contrat de l'observation Weymouth-SI existante.

### `WeymouthNetworkCandidateState`

Contient :

- une référence de l'état candidat ;
- exactement une pression candidate par nœud fourni ;
- exactement un débit candidat par conduite fournie ;
- les injections/soutirages externes.

Les doublons de pression ou de débit sont refusés avant évaluation.

### `assemble_weymouth_network_residuals`

La fonction exige :

- couverture exacte des nœuds par les pressions ;
- couverture exacte des conduites par les débits ;
- couverture exacte des conduites par les paramètres Weymouth ;
- un seul jeu de paramètres par conduite.

Elle réutilise :

- `assess_stationary_mass_balance` pour la conservation de masse ;
- `evaluate_weymouth_si_residual` pour chaque conduite.

Aucune équation n'est dupliquée dans cette couche.

## 3. Séparation des unités

Les deux familles de résidus ne sont volontairement pas concaténées dans un même vecteur numérique :

- bilan nodal : `kg/s` ;
- conduite Weymouth : `Pa²`.

Un solveur non linéaire aura besoin d'une stratégie explicite de variables, de mise à l'échelle et de convergence. Choisir ces facteurs sans justification pourrait modifier le conditionnement et la convergence. Le présent incrément garde donc les grandeurs physiques brutes séparées.

## 4. Ce que cette brique prouve

Elle permet de vérifier qu'un état complet proposé par :

- un futur solveur PETROLE ;
- un calcul manuel ;
- GasModels ;
- un autre solveur indépendant ;

est évalué par le même assemblage de conservation et de loi constitutive.

Elle constitue aussi le point d'entrée naturel des futurs tests du Jacobien, de l'échelle des variables et des méthodes de racines.

## 5. Ce qu'elle ne fait pas

Cette brique ne :

- détermine pas le débit d'une conduite ;
- détermine pas une pression inconnue ;
- choisit pas les conditions limites du problème ;
- ne construit pas de Jacobien ;
- ne choisit pas Newton, `scipy.optimize.root`, least-squares, Pyomo/Ipopt ou autre solveur ;
- ne définit pas de tolérance ;
- ne déclare pas un état convergé ;
- ne traite pas encore les compresseurs comme équations couplées du réseau.

## 6. Gate avant le premier solveur

Avant d'ajouter une méthode de résolution P6-B :

1. fermer la CI du protocole de critères P6-H ;
2. pré-enregistrer et faire approuver les critères des benchmarks retenus ;
3. exécuter plusieurs cas indépendants dans le domaine revendiqué ;
4. définir les inconnues et conditions limites autorisées ;
5. définir et tester la stratégie de mise à l'échelle ;
6. choisir la méthode de résolution et ses statuts de convergence ;
7. conserver les résidus physiques bruts à côté des résidus éventuellement normalisés.

Le présent module reste donc une fondation du solveur, et non le solveur lui-même.
