# Phase 6 — P6-B : gouvernance du futur solveur stationnaire

Statut : **IMPLEMENTED_GOVERNANCE_GATE_NO_SOLVER_SELECTED**.

## 1. Objet

La chaîne P6-B sait désormais construire un problème stationnaire `pressure-slack`, matérialiser un état physique, calculer les résidus de masse et Weymouth, représenter les inconnues avec des coordonnées `p²` mises à l'échelle et évaluer une fonction pure `x -> r(x)`.

Il reste interdit de convertir cette fonction en solveur tant que la politique numérique n'est pas pré-enregistrée et approuvée.

Module : `packages/hydrogas/hydro_gas/stationary_solver_governance.py`.

## 2. Contexte de qualification

`StationarySolverQualificationContext` fixe explicitement :

- protocole ;
- famille de problème ;
- représentation numérique ;
- méthode de solveur ;
- politique de mise à l'échelle ;
- politique d'initialisation.

Un critère enregistré pour un autre contexte ne peut pas être matérialisé.

## 3. Critère de convergence pré-enregistré

`PreRegisteredStationaryConvergenceCriterion` conserve :

- identifiant/version ;
- contexte complet ;
- provenance ;
- référence d'enregistrement antérieure à l'exécution acceptée ;
- norme infinie maximale du résidu adimensionné ;
- éventuellement une limite physique de bilan massique en kg/s ;
- éventuellement une limite physique de résidu de conduite en Pa² ;
- état `DRAFT` ou `APPROVED` ;
- référence d'approbation.

Aucune valeur par défaut n'existe. Toutes les limites doivent être fournies explicitement, être finies et positives ou nulles.

Un critère `DRAFT` ne peut pas être exécuté. Un critère `APPROVED` sans `approval_ref` est invalide.

Les nombres utilisés dans `tests/test_gas_stationary_solver_governance.py` sont exclusivement des fixtures synthétiques. Ils ne sont ni des tolérances PETROLE, ni des tolérances GasModels, ni des exigences industrielles.

## 4. Vocabulaire de statut réservé

`StationaryWeymouthSolverStatus` réserve les statuts :

- `CONVERGED` ;
- `NON_CONVERGED` ;
- `OUT_OF_DOMAIN` ;
- `INSUFFICIENT_DATA` ;
- `NUMERICAL_FAILURE`.

La présence de cet enum ne signifie pas qu'un solveur existe déjà. Aucun objet actuel n'est autorisé à produire `CONVERGED` tant qu'une méthode de résolution réelle n'a pas été implémentée et qualifiée.

## 5. Gate avant implémentation d'une méthode numérique

Avant tout appel réel à Newton, `scipy.optimize.root`, `least_squares`, Ipopt ou un autre solveur :

1. sélectionner et versionner la méthode ;
2. documenter le traitement de la contrainte `p² >= 0` ;
3. définir une politique d'initialisation ;
4. définir une politique de construction des échelles sur cas réels ;
5. pré-enregistrer les critères de convergence ;
6. faire approuver ces critères ;
7. exécuter plusieurs benchmarks indépendants ;
8. vérifier singularité, non-convergence et sortie hors domaine ;
9. conserver les résidus physiques bruts dans tout résultat ;
10. faire une revue numérique/thermofluides avant de qualifier le solveur.

Le prochain développement autorisé peut préparer les interfaces de méthode et d'initialisation, mais ne doit toujours pas retourner un résultat `CONVERGED` sans politique approuvée.
