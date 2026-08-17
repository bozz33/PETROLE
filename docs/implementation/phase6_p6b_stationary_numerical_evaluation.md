# Phase 6 — P6-B : fonction résiduelle numérique pure

Statut : **IMPLEMENTED_PURE_RESIDUAL_FUNCTION_NOT_SOLVER**.

## 1. Objet

Fournir au futur solveur une unique fonction conceptuelle `x → r(x)` sans permettre à la couche numérique de dupliquer ou modifier la physique PETROLE.

Module : `packages/hydrogas/hydro_gas/stationary_numerical_evaluation.py`.

## 2. Chaîne de calcul imposée

`evaluate_stationary_weymouth_numerical_vector` exécute uniquement :

1. vecteur adimensionné `x` ;
2. décodage `p²/f/f_slack` vers `StationaryWeymouthUnknownState` en unités physiques ;
3. matérialisation du candidat complet avec pressions slack et frontières connues ;
4. évaluation canonique du bilan de masse et des résidus Weymouth ;
5. mise à l'échelle explicite des résidus vers le vecteur numérique `r(x)`.

Le résultat conserve simultanément :

- le vecteur d'entrée ;
- l'état physique décodé ;
- l'évaluation physique complète ;
- le vecteur de résidus adimensionné ;
- la provenance des échelles.

## 3. Absence volontaire de convergence

Cette couche n'expose aucun champ :

- `converged` ;
- `passed` ;
- `tolerance` ;
- `iteration_count` ;
- `solver_status`.

Un vecteur de résidus numériquement petit n'est donc jamais transformé ici en solution validée.

## 4. Propriétés importantes

- le nombre de variables suit `unknown_count` ;
- le nombre de résidus suit `equation_count` ;
- pour le contrat pressure-slack, le problème est structurellement carré ;
- les résidus physiques bruts restent accessibles ;
- les échelles restent explicitement sourcées ;
- toute coordonnée `p² < 0` est refusée ;
- toute incohérence de layout, couverture ou paramètres échoue fermée dans la couche spécialisée correspondante.

## 5. Gate avant un algorithme de résolution

Le moteur dispose maintenant du chemin de calcul requis par un solveur non linéaire, mais il manque encore les décisions de qualification suivantes :

1. politique de construction des échelles numériques sur cas réels ;
2. critères de convergence pré-enregistrés et approuvés ;
3. choix de la méthode numérique et de son domaine ;
4. stratégie pour respecter `p² >= 0` ;
5. initialisation des inconnues ;
6. diagnostic de singularité/échec ;
7. benchmarks indépendants sur plusieurs topologies ;
8. revue thermofluides/numérique.

Aucun appel à Newton, SciPy, Ipopt ou autre solveur ne doit être ajouté avant fermeture de ces gates.
