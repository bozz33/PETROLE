# P6-B — Solveur stationnaire Weymouth borné

Statut : implémentation logicielle de fondation, non certifiante et non qualifiée industriellement.

## 1. Objet

Cette brique transforme la chaîne pré-solveur déjà disponible en une première résolution numérique de réseau :

`x -> état physique -> bilans nodaux + Weymouth -> r(x) -> least_squares(TRF)`.

Le domaine physique PETROLE reste exprimé en pression absolue `Pa` et débit massique `kg/s`. La coordonnée `p²` n'existe que dans l'adapter numérique.

## 2. Méthode implémentée

La première méthode disponible est `scipy.optimize.least_squares` avec l'algorithme `TRF` (Trust Region Reflective) et des bornes explicites.

Référence méthode PETROLE :

`solver-method://scipy/least-squares/trf/v1`

Référence représentation numérique :

`numerics://gas/weymouth/psqr-scaled/v1`

La documentation officielle SciPy décrit `least_squares` comme une résolution de moindres carrés non linéaires avec bornes sur les variables. Le mode `trf` supporte les bornes et maintient des itérés faisables. Cette propriété permet d'imposer directement `p² >= 0` sans corriger silencieusement une pression négative après calcul.

Référence primaire : `https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html`.

## 3. Aucun paramètre numérique caché

`ScipyLeastSquaresTrfConfiguration` exige explicitement :

- référence de configuration ;
- référence de source ;
- méthode ;
- représentation numérique ;
- politique d'échelle ;
- politique d'initialisation ;
- `ftol` ;
- `xtol` ;
- `gtol` ;
- `x_scale` ;
- `diff_step` ;
- `max_nfev` ;
- schéma de Jacobien `2-point` ou `3-point` ;
- solveur de sous-problème `exact` ou `lsmr`.

Les trois tolérances SciPy doivent être finies et strictement supérieures à l'epsilon machine. Aucun budget d'évaluations par défaut PETROLE n'est utilisé.

La loss est fixée à `linear`, car cette brique résout un système de résidus physiques et ne doit pas réduire artificiellement le poids d'une équation considérée comme un outlier.

## 4. Bornes

Pour un layout ayant `Np` pressions inconnues :

- coordonnées `0 .. Np-1` : borne inférieure `0` sur `p²` ;
- débits de conduites : non bornés par cette couche ;
- débit externe des nœuds slack : non borné par cette couche.

Les limites opérationnelles de débit, pression, station ou compresseur doivent être ajoutées par leurs modèles métier respectifs et ne sont pas inventées dans P6-B.

## 5. Convergence PETROLE != success SciPy

Le booléen `success` et le code de terminaison SciPy sont conservés comme diagnostics algorithmiques.

Ils ne suffisent pas pour produire le statut `CONVERGED`.

Le résultat final est réévalué par le moteur scientifique canonique, puis comparé au `ApprovedStationaryConvergenceCriterion` pré-enregistré pour le contexte exact :

- norme infinie du résidu adimensionné ;
- limite massique physique optionnelle en `kg/s` ;
- limite de résidu de conduite optionnelle en `Pa²`.

`CONVERGED` n'est émis que lorsque tous les critères approuvés applicables passent.

Ainsi, un arrêt SciPy avec `success=True` peut légitimement produire `NON_CONVERGED` si le résidu PETROLE reste supérieur au critère approuvé.

## 6. Contexte qualifié

Le critère approuvé conserve désormais l'intégralité du contexte :

- protocole ;
- famille de problème ;
- représentation numérique ;
- méthode solveur ;
- politique d'échelle ;
- politique d'initialisation ;
- source ;
- enregistrement pré-run ;
- approbation.

L'exécution refuse toute divergence entre le contexte, la configuration et le critère approuvé.

## 7. Résultat traçable

`StationaryWeymouthSolveResult` conserve :

- `solve_ref` ;
- statut PETROLE ;
- vecteur initial ;
- vecteur final ;
- évaluation physique finale complète ;
- évaluation des critères de convergence ;
- `scipy_success` ;
- code et message de terminaison ;
- version SciPy réellement chargée ;
- `nfev`, `njev` ;
- coût et optimalité retournés par SciPy ;
- masque des bornes actives ;
- références de configuration et de provenance.

## 8. Tests couverts

Les tests utilisent uniquement des références et seuils marqués `synthetic-test-only`.

Ils vérifient notamment :

1. résolution d'un réseau `A -> B` avec pression slack et demande imposée ;
2. récupération du débit massique attendu par conservation ;
3. récupération de la pression aval compatible avec l'équation Weymouth implémentée ;
4. maintien de `p² >= 0` ;
5. refus d'une configuration liée à une autre politique d'échelle ;
6. refus d'un vecteur initial avec `p² < 0` ;
7. cas où SciPy annonce un succès mais où le critère PETROLE plus strict refuse `CONVERGED` ;
8. cas sans solution exacte dans le domaine borné, retourné `NON_CONVERGED`.

## 9. Ce que cette implémentation ne prouve pas

Elle ne prouve pas :

- que Weymouth est le modèle approprié à tout réseau gaz ;
- que les paramètres de friction, vitesse du son ou propriétés gaz d'un site réel sont corrects ;
- que les seuils synthétiques des tests sont acceptables industriellement ;
- qu'un cas GasModels et un cas 2-nœuds suffisent pour qualifier le moteur ;
- la stabilité numérique sur grands réseaux ;
- la robustesse près de changements de sens de débit ;
- la validité hors domaine des hypothèses stationnaires/isothermes associées au modèle de référence ;
- les compresseurs, vannes, régulateurs, line-pack dynamique ou transitoires.

## 10. Gates avant qualification P6-B

Avant de déclarer le solveur P6-B `benchmarked` ou publiable :

- exécuter plusieurs cas indépendants avec données et unités rapprochées ;
- pré-enregistrer les tolérances avant comparaison ;
- comparer pressions et débits à GasModels et à une seconde référence indépendante si disponible ;
- tester réseaux ramifiés, bouclés, multi-slack par composantes séparées et flux inverses ;
- qualifier l'initialisation et la politique d'échelle ;
- documenter les échecs de convergence ;
- effectuer une revue thermofluides indépendante ;
- exécuter ensuite la validation pilote D20 sur données représentatives.
