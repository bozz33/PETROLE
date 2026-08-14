# Phase 6 — P6-B : coordonnées numériques stationnaires Weymouth

Statut : **IMPLEMENTED_NUMERICAL_COORDINATES_NOT_SOLVER**.

## 1. Objet

Préparer le futur solveur non linéaire en séparant strictement :

- l'état physique PETROLE : pression absolue en Pa et débit massique en kg/s ;
- les coordonnées numériques du solveur ;
- les résidus physiques ;
- les résidus adimensionnés utilisés par un futur algorithme numérique.

Aucun solveur, aucune tolérance de convergence et aucune échelle par défaut ne sont activés par cette brique.

## 2. Pourquoi la coordonnée de pression est `p²`

La loi Weymouth implémentée dans P6-B est écrite avec la différence de pressions au carré. La formulation `WPGasModel` de la référence GasModels épinglée au commit `21422f18e7e328732ec8edd7995446d33f58e789` utilise également une variable `psqr` pour la contrainte Weymouth et relie explicitement `p²` à cette variable.

PETROLE conserve néanmoins `pressure_pa` comme représentation physique. `p²` n'existe que dans l'adapter numérique du problème Weymouth stationnaire.

## 3. Implémentation

Module : `packages/hydrogas/hydro_gas/stationary_numerics.py`.

### `StationaryWeymouthNumericalScale`

Quatre échelles doivent être fournies explicitement :

- `pressure_squared_scale_pa2` ;
- `mass_flow_scale_kg_s` ;
- `mass_residual_scale_kg_s` ;
- `pipe_residual_scale_pa2` ;
- `source_ref` de la décision d'échelle.

Toutes doivent être finies et strictement positives. Il n'existe aucune valeur par défaut.

Cette séparation permet de modifier plus tard le conditionnement numérique sans modifier les unités ou résultats physiques du moteur.

### Vecteur d'inconnues

L'ordre est celui de `StationaryWeymouthUnknownLayout` :

1. pressions inconnues sous forme `p² / pressure_squared_scale_pa2` ;
2. débits des conduites sous forme `f / mass_flow_scale_kg_s` ;
3. débits externes des slacks sous forme `f_slack / mass_flow_scale_kg_s`.

Le vecteur est adimensionné.

### Décodage

Le décodage :

- exige une taille exactement égale au nombre d'inconnues ;
- refuse une coordonnée `p²` négative ;
- reconstruit la pression physique par racine carrée ;
- préserve les identifiants de frontières slack du template ;
- produit de nouvelles références de provenance liées au vecteur numérique.

Une future méthode numérique devra donc gérer explicitement le domaine `p² >= 0`. Cette brique ne corrige jamais silencieusement une coordonnée hors domaine.

### Vecteur de résidus

Les résidus physiques restent produits par l'évaluateur canonique :

- bilan nodal en kg/s ;
- résidu Weymouth en Pa².

L'adapter numérique les transforme ensuite en :

- `r_mass / mass_residual_scale_kg_s` ;
- `r_pipe / pipe_residual_scale_pa2`.

La concaténation n'a donc lieu qu'après mise à l'échelle explicitement sourcée.

## 4. Ce qui n'est pas une tolérance

Les échelles numériques :

- ne sont pas des critères PASS/FAIL ;
- ne sont pas des tolérances scientifiques ;
- ne sont pas des limites d'exploitation ;
- ne prouvent pas la convergence ;
- ne sont pas déduites automatiquement des benchmarks.

Les valeurs utilisées dans `tests/test_gas_stationary_numerics.py` sont exclusivement des fixtures synthétiques destinées à vérifier les conversions et le round-trip.

## 5. Gate avant le solveur

Avant de choisir Newton, `scipy.optimize.root`, `least_squares`, Ipopt ou une autre méthode :

1. faire approuver les critères numériques/scientifiques du benchmark ;
2. définir une politique de construction des échelles depuis le problème réel ;
3. tester le conditionnement sur plusieurs cas ;
4. définir le traitement des bornes `p² >= 0` ;
5. définir les statuts `CONVERGED`, `NON_CONVERGED`, `OUT_OF_DOMAIN`, `INSUFFICIENT_DATA` sans ambiguïté ;
6. conserver les résidus physiques bruts dans tout résultat ;
7. comparer le premier solveur à plusieurs références indépendantes.

La prochaine brique autorisée peut être une **fonction résiduelle numérique pure** `x -> r(x)` construite uniquement avec les adapters déjà validés. Elle ne doit pas encore décider qu'un résidu est suffisamment petit.
