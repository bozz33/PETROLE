# Phase 6 — P6-B : matérialisation de l'état inconnu stationnaire

Statut : **IMPLEMENTED_PHYSICAL_STATE_MAPPING_NOT_NUMERICAL_VECTOR**.

## 1. Objet

Relier le contrat structurel `pressure-slack` à l'assemblage des résidus réseau sans introduire prématurément une représentation numérique de solveur.

Le module prend :

- un `StationaryWeymouthProblem` ;
- son `StationaryWeymouthUnknownLayout` ;
- les valeurs physiques des seules inconnues ;

et produit un `WeymouthNetworkCandidateState` complet pouvant être évalué par `assemble_weymouth_network_residuals`.

## 2. Implémentation

Module : `packages/hydrogas/hydro_gas/stationary_candidate.py`.

### `StationaryWeymouthUnknownState`

Contient exclusivement :

- `state_ref` ;
- pressions inconnues des nœuds non-slack ;
- débits inconnus de toutes les conduites ;
- débits externes inconnus des nœuds slack.

Le type refuse les doublons de nœuds, conduites, identifiants de frontières slack et nœuds slack.

### `materialize_stationary_weymouth_candidate`

La fonction :

1. reconstruit le layout attendu depuis le problème ;
2. refuse un layout périmé ou provenant d'un autre problème ;
3. exige la couverture exacte des pressions inconnues ;
4. exige la couverture exacte des débits de conduite ;
5. exige exactement un débit externe par slack ;
6. refuse toute collision d'identifiant entre frontière imposée et frontière slack ;
7. réinjecte les pressions imposées des slacks ;
8. ordonne les pressions selon l'ordre des nœuds du réseau ;
9. ordonne les débits selon l'ordre des conduites du réseau ;
10. conserve d'abord les frontières imposées puis ajoute les frontières slack dans l'ordre du layout.

Aucune valeur absente n'est calculée ou supposée.

## 3. Pourquoi il n'y a pas encore de vecteur numérique

L'état physique conserve des unités différentes :

- pressions en Pa ;
- débits massiques en kg/s.

Le futur solveur peut choisir de représenter la pression par `p`, `p²` ou une variable mise à l'échelle. Ce choix affecte le conditionnement, les dérivées et les critères de convergence. Il ne doit donc pas être enfoui dans le contrat physique.

La présente couche garantit qu'une future représentation numérique peut être convertie vers un état physique complet avant l'évaluation des équations.

## 4. Propriétés testées

Les tests couvrent :

- réinjection de la pression slack ;
- ordre déterministe nœuds/conduites ;
- conservation des provenances ;
- composition frontière imposée + débit externe slack ;
- bilan massique nul sur un état physiquement cohérent ;
- rejet d'un layout périmé ;
- rejet des couvertures incomplètes ;
- rejet des collisions d'identifiants de frontière ;
- rejet des doublons et d'une provenance d'état vide.

## 5. Gate suivant

Le prochain incrément autorisé est la **spécification de représentation numérique** du problème :

- variable de pression retenue (`p` ou `p²`) ;
- ordre du vecteur ;
- échelles de référence ;
- conversion vecteur → état physique ;
- conversion des résidus physiques → résidus numériques ;
- conservation parallèle des résidus bruts en unités physiques.

Aucun solveur ne doit être activé avant :

1. une stratégie de mise à l'échelle documentée et testée ;
2. des critères de benchmark approuvés ;
3. des cas indépendants suffisants ;
4. des statuts de convergence explicites ;
5. une validation de la méthode numérique sélectionnée.
