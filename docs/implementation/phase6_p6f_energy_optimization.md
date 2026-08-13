# Phase 6 — P6-F : sélection énergétique sous contraintes

Statut : **IMPLEMENTED_DISCRETE_SELECTION_NOT_NETWORK_OPTIMIZER_VALIDATED**.

## 1. Objet

P6-F introduit une première capacité d'optimisation énergétique gaz sans anticiper le solveur stationnaire compressible P6-B encore incomplet.

La brique implémentée parcourt un ensemble fini de plans de fonctionnement **déjà évalués** par les couches physiques amont, élimine ceux dont une contrainte explicite est violée, puis classe les candidats restants par énergie totale croissante.

Elle ne calcule pas :

- une perte de charge de conduite gaz ;
- un débit ou une pression de réseau ;
- un point de carte compresseur ;
- un rendement ou une puissance compresseur ;
- une marge anti-surge ;
- une consigne ou une commande d'équipement.

## 2. Pourquoi une sélection discrète d'abord

D07 prévoit l'énumération filtrée pour les petits espaces de recherche, puis NLP/MILP/MINLP lorsque les équations physiques et leurs domaines sont qualifiés. D17 place l'optimisation dans Phase 6, mais le solveur constitutif P6-B n'est pas encore validé.

Coupler Pyomo aujourd'hui à une équation de conduite ou à une fonction énergétique inventée créerait une fausse maturité scientifique. La première étape P6-F est donc volontairement analogue à la sélection discrète déjà utilisée pour le liquide : la physique produit des candidats et leurs preuves ; la couche de décision ne fait que sélectionner parmi ceux-ci.

## 3. Contrat implémenté

Module : `packages/hydrogas/hydro_gas/energy_optimization.py`.

### `GasDispatchConstraintEvidence`

Chaque contrainte exige :

- un identifiant stable ;
- un statut `passed` explicite ;
- une référence de preuve.

Aucune faisabilité implicite n'est acceptée.

### `GasEnergyDispatchCandidate`

Chaque candidat exige notamment :

- identifiant du plan ;
- station concernée ;
- durée de l'intervalle ;
- énergie totale en joules ;
- références des points de fonctionnement calculés en amont ;
- preuves de contraintes ;
- version du modèle d'évaluation ;
- provenance du scénario/candidat.

L'énergie est une **entrée traçable** de cette couche. P6-F ne la reconstruit pas depuis des hypothèses thermodynamiques cachées.

### `select_minimum_energy_dispatch`

Le sélecteur :

1. refuse un espace vide et les identifiants de candidats dupliqués ;
2. sépare candidats faisables et candidats rejetés ;
3. conserve les codes de violations et les références de preuves ;
4. classe les candidats faisables par `energy_j`, puis par `candidate_id` pour les égalités ;
5. retourne `GAS_ENERGY_INFEASIBLE` si aucun candidat ne satisfait toutes ses preuves ;
6. retourne `GAS_ENERGY_OPTIMAL_DISCRETE` si au moins un candidat est faisable.

`optimality_gap = 0` signifie uniquement que **l'espace discret fourni a été parcouru complètement**. Cela ne prouve ni l'optimalité continue, ni l'optimalité globale d'un réseau gaz.

## 4. Tests

`tests/test_gas_energy_optimization.py` vérifie notamment :

- classement déterministe par énergie ;
- départage reproductible des égalités ;
- exclusion des candidats violant une contrainte même s'ils consomment moins ;
- absence de solution de secours en cas d'infaisabilité ;
- obligation de fournir des preuves de contraintes ;
- refus d'énergie négative, de durée nulle et de contraintes dupliquées ;
- refus des candidats dupliqués ;
- conservation des références de points, preuves, versions et provenance.

## 5. Étapes futures avant optimisation gaz complète

P6-F ne pourra évoluer vers NLP/MILP/MINLP couplé au réseau qu'après :

1. sélection et validation de la loi constitutive P6-B ;
2. propriétés gaz représentatives et domaines P6-A qualifiés ;
3. cartes et enveloppes compresseurs P6-D provenant de sources acceptées ;
4. formulation explicite de l'énergie/du coût et des contraintes ;
5. cas indépendants P6-H ;
6. revue thermofluides ;
7. benchmark du solveur d'optimisation et journalisation des non-convergences.

Une future implémentation Pyomo devra rester derrière un contrat indépendant du solveur et produire les mêmes preuves de contraintes, objectifs, versions et diagnostics. Elle ne devra jamais transformer une recommandation analytique en commande procédé.
