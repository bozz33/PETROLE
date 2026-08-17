# Phase 6 — P6-H : protocole de critères pré-enregistrés

Statut : **IMPLEMENTED_APPROVAL_GATE_NO_REAL_GAS_TOLERANCE_APPROVED**.

## 1. Objet

Le moteur de comparaison P6-H savait déjà appliquer une erreur absolue ou relative lorsqu'un critère lui était fourni. Il manquait cependant une preuve structurelle qu'un critère appartenait au bon modèle, à la bonne formulation et au bon cas, et qu'il avait été approuvé **avant** son utilisation.

Cette brique ajoute ce gate sans définir aucune tolérance métier ou industrielle par défaut.

## 2. Implémentation

Module : `packages/hydrogas/hydro_gas/benchmark_protocol.py`.

### `GasBenchmarkCriterionState`

Deux états sont autorisés :

- `draft` : critère en préparation, jamais exécutable ;
- `approved` : critère exécutable uniquement si une référence d'approbation existe.

Un brouillon ne peut pas porter une approbation active et un critère `approved` sans `approval_ref` est refusé.

### `PreRegisteredGasBenchmarkCriterion`

Chaque critère pré-enregistré conserve :

- `criterion_id` ;
- `criterion_version` ;
- `protocol_ref` ;
- `model_id` ;
- `model_version` ;
- `formulation_ref` ;
- `case_ref` ;
- `observation_id` ;
- `quantity_ref` ;
- `unit` ;
- `source_ref` ;
- `registration_ref` ;
- état et référence d'approbation ;
- limite absolue, relative, ou les deux.

Aucune limite implicite n'existe. Au moins une limite doit être fournie explicitement et toute limite doit être finie et positive ou nulle.

### `GasBenchmarkProtocolContext`

Le contexte d'exécution fixe exactement :

- protocole ;
- modèle ;
- version du modèle ;
- formulation ;
- cas.

Un critère rattaché à un autre contexte ne peut pas être matérialisé.

### `ApprovedGasBenchmarkCriteria`

Le paquet matérialisé conserve désormais **le contexte complet et immuable** qui a autorisé son exécution :

- `protocol_ref` ;
- `model_id` ;
- `model_version` ;
- `formulation_ref` ;
- `case_ref`.

La propriété `context` restitue exactement un `GasBenchmarkProtocolContext` à partir de ces cinq références. Une couche de preuve P6-H peut donc revalider après matérialisation que le paquet APPROVED est toujours utilisé pour le même modèle, la même version, la même formulation et le même cas, sans dépendre de l'historique de l'appel qui l'a créé.

Cette conservation évite notamment qu'un ensemble de critères approuvés pour un cas soit transporté puis réutilisé silencieusement sur un autre cas ou une autre formulation partageant seulement le même protocole.

### `materialize_approved_gas_benchmark_criteria`

La matérialisation échoue fermée si :

- la liste de critères est vide ;
- un critère est `draft` ;
- deux critères partagent le même identifiant ;
- deux critères ciblent la même observation ;
- le contexte modèle/version/formulation/cas diffère ;
- l'observation n'existe pas ;
- la grandeur diffère ;
- l'unité diffère.

La fonction ne calcule et ne choisit aucune tolérance. Elle copie uniquement dans le `GasBenchmarkCriterion` bas niveau les limites qui ont déjà été pré-enregistrées et approuvées.

`ApprovedGasBenchmarkCriteria` conserve en parallèle les identifiants des critères, références d'approbation, références d'enregistrement et le contexte complet utilisé afin que le transport bas niveau ne fasse pas perdre la preuve documentaire.

## 3. Relation avec D10

D10 exige que les cas de validation conservent la source de vérité, les résultats attendus, les tolérances, les checksums, la version du moteur et l'approbation. Les seuils chiffrés présentés dans D10 restent des cibles de développement générales ; ils ne sont pas automatiquement convertis en critères gaz.

Le protocole P6-H exige donc une décision explicite pour chaque comparaison réellement revendiquée.

## 4. Cas Weymouth GasModels actuel

Le cas `case-6-gf.m` dispose maintenant :

- d'une recette GasModels épinglée et exécutée ;
- d'un artefact de référence figé ;
- d'une équation Weymouth-SI explicite ;
- de paramètres canoniques/hashés par conduite ;
- d'un évaluateur de résidu sans seuil.

Il **ne dispose pas encore d'une tolérance PETROLE approuvée** permettant de transformer ses quatre résidus en PASS/FAIL scientifique. Aucun objet de production n'est donc créé dans le dépôt avec une valeur de tolérance pour ce cas à ce stade.

Les valeurs numériques utilisées dans `tests/test_gas_benchmark_protocol.py` sont uniquement des fixtures synthétiques destinées à tester le mécanisme d'approbation ; elles ne constituent ni une exigence du produit, ni une tolérance scientifique, ni une recommandation industrielle.

## 5. Gate suivant

Avant de déclarer le modèle Weymouth `benchmarked` :

1. définir les observations réellement évaluées et leur unité ;
2. sélectionner la source de vérité pour chaque grandeur ;
3. proposer des limites et documenter leur justification ;
4. faire approuver ces limites par la revue thermofluides/scientifique ;
5. créer un `registration_ref` antérieur à la comparaison acceptée ;
6. matérialiser uniquement les critères `approved` ;
7. exécuter la comparaison et archiver résultats, versions, hashes et approbations ;
8. répéter sur plusieurs cas indépendants couvrant le domaine revendiqué.

Le statut `benchmark_ready` de la formulation signifie seulement que ces étapes peuvent être préparées. Il ne devient pas `benchmarked` par la seule présence du protocole.
