# PETROLE — avancement du plan maître au 14 août 2026

Référence : `docs/implementation/remaining_development_master_plan.md`.

Ce document ne remplace pas le plan maître. Il enregistre l'état réel des incréments implémentés sur la branche `feat/phase6-gas-foundation` et les gates qui restent externes ou non encore qualifiés.

## 1. Release / intégration

- `main` reste volontairement intact pendant les travaux post-MVP.
- aucune fusion Phase 3–8 n'est réalisée dans `main` ;
- aucune release `v1.0.0-mvp` n'est créée par ces travaux ;
- la DAG d'intégration Phase 2/V1 est documentée dans le plan maître.

## 2. P6-H — benchmark et pré-enregistrement

Implémenté :

- référence GasModels 0.13.4 réellement exécutable et épinglée ;
- artefacts/hashes/version solveur/formulation/cas ;
- contrat de comparaison externe ;
- critères de benchmark `DRAFT` / `APPROVED` ;
- contexte exact modèle/version/formulation/cas/grandeur/unité ;
- approbation obligatoire avant matérialisation d'un critère ;
- aucune tolérance réelle Weymouth/PETROLE créée automatiquement.

Reste externe :

- sélectionner plusieurs cas indépendants ;
- proposer puis faire approuver les tolérances scientifiques ;
- revue thermofluides ;
- validation sur données/pilote représentatifs.

## 3. P6-B — chaîne pré-solveur désormais implémentée

### 3.1 Physique et provenance

- topologie gaz indépendante ;
- bilan massique nodal/global ;
- flux inverses ;
- injections/soutirages ;
- registre constitutif et bindings hashés ;
- équation Weymouth-SI évaluée sous forme de résidu ;
- paramètres canoniques/hashés ;
- couverture et provenance explicites.

### 3.2 Assemblage réseau

Implémenté :

`pressions candidates + débits candidats + frontières + paramètres Weymouth`

→ résidus de masse en `kg/s`

→ résidus Weymouth en `Pa²`.

Les familles de résidus physiques restent séparées et aucun seuil PASS/FAIL n'est implicite.

### 3.3 Contrat structurel `pressure-slack`

Première famille de problème supportée : exactement un nœud de pression slack par composante connexe.

Pour une composante `N` nœuds / `E` conduites :

- pressions inconnues : `N - 1` ;
- débits de conduites : `E` ;
- débit externe du slack : `1` ;
- inconnues totales : `N + E` ;
- équations de masse : `N` ;
- équations de conduite : `E` ;
- équations totales : `N + E`.

Le système est structurellement carré, sans implication d'existence, unicité ou convergence.

### 3.4 Matérialisation de l'état physique

Implémenté :

`StationaryWeymouthUnknownState`

→ réinjection des pressions slack ;

→ ordre déterministe des nœuds/conduites ;

→ frontières imposées + débits slack ;

→ `WeymouthNetworkCandidateState` complet.

Les couvertures incomplètes, layouts périmés et collisions de frontières sont refusés.

### 3.5 Évaluation physique canonique

Implémenté :

`unknown state → candidate → bilan massique + résidus Weymouth`.

Le futur solveur ne doit pas dupliquer ces équations.

### 3.6 Coordonnées numériques explicites

Implémenté :

- domaine physique conservé en `Pa` / `kg/s` ;
- coordonnée numérique de pression `p²`, cohérente avec la formulation Weymouth de référence ;
- échelles obligatoires et sourcées pour `p²`, débit, résidu massique et résidu de conduite ;
- aucun facteur d'échelle par défaut ;
- conversion état physique ↔ vecteur adimensionné ;
- refus de `p² < 0` ;
- vectorisation des résidus seulement après mise à l'échelle explicite.

Les échelles utilisées dans les tests sont synthétiques et ne constituent aucune politique produit.

### 3.7 Fonction résiduelle pure

Implémenté :

`x → décodage physique → évaluation canonique → r(x)`.

La trace conserve :

- vecteur d'entrée ;
- état physique décodé ;
- résidus physiques ;
- vecteur de résidus adimensionné ;
- provenance des échelles.

Aucun champ `converged`, aucune tolérance et aucun compteur d'itérations n'est produit.

### 3.8 Gouvernance du futur solveur

Implémenté :

- états `DRAFT` / `APPROVED` pour le critère de convergence ;
- contexte exact protocole/famille de problème/représentation/méthode/scaling/initialisation ;
- norme infinie maximale du résidu adimensionné explicitement fournie ;
- limites physiques optionnelles explicitement fournies ;
- provenance/enregistrement/approbation ;
- vocabulaire futur de statuts : `CONVERGED`, `NON_CONVERGED`, `OUT_OF_DOMAIN`, `INSUFFICIENT_DATA`, `NUMERICAL_FAILURE`.

Aucun de ces statuts n'est encore produit par un solveur réel.

## 4. Ce qui bloque volontairement le solveur concret

Avant d'implémenter Newton, `scipy.optimize.root`, `least_squares`, Ipopt ou une autre méthode, il reste à fermer :

1. choix/version de la méthode numérique ;
2. politique de respect de `p² >= 0` ;
3. politique d'initialisation ;
4. politique de construction des échelles sur cas représentatifs ;
5. critères de convergence pré-enregistrés ;
6. approbation de ces critères ;
7. plusieurs benchmarks indépendants ;
8. diagnostics de singularité/non-convergence/hors domaine ;
9. revue numérique/thermofluides.

Le solveur concret reste donc volontairement non activé.

## 5. Suite du plan maître

Après fermeture des gates P6-B :

- propriétés gaz qualifiées P6-A ;
- couplage line-pack P6-C ;
- compresseurs thermodynamiques/cartes réelles P6-D ;
- stations/régulation P6-E ;
- optimisation couplée P6-F ;
- API/UI/rapports P6-G ;
- benchmarks/pilote P6-H ;
- consolidation Phase 2 après release officielle ;
- fermeture Phase 3, Phase 4 et Phase 5 selon leurs dépendances ;
- Phase 7 seulement avec données/OT qualifiés ;
- Phase 8 sur infrastructure et pilote réels.

## 6. Règle de poursuite

Le prochain code P6-B ne doit pas contourner le gate scientifique. Tant que les critères/méthodes ne sont pas approuvés, le développement peut porter sur :

- interfaces de solveur sans implémentation ;
- preuves d'initialisation ;
- provenance des politiques d'échelle ;
- cas de benchmark supplémentaires ;
- autres sous-lots indépendants ne nécessitant pas de conclusion de convergence.
