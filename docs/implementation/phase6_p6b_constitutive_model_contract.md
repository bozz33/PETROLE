# Phase 6 — P6-B : contrat des modèles constitutifs de conduite gaz

Statut : **IMPLEMENTED_MODEL_REGISTRY_NO_PIPE_SOLVER_VALIDATED**.

## 1. Objet

P6-B doit à terme relier pression, débit massique, géométrie et propriétés du gaz pour une conduite stationnaire compressible. Cette étape ne choisit volontairement **aucune équation universelle** et n'active aucun solveur de conduite.

Le premier incrément impose un contrat de sélection et de traçabilité avant tout calcul :

- modèle constitutif identifié et versionné ;
- formulation et équation référencées sans reproduire de texte protégé ;
- source technique identifiée ;
- schéma des paramètres identifié ;
- domaine de validité explicite ;
- hypothèses explicites ;
- état de qualification explicite ;
- jeu de paramètres lié à chaque conduite avec empreinte SHA-256 ;
- références distinctes de géométrie, propriétés gaz et provenance de configuration.

## 2. Pourquoi ce gate précède l'équation

D07 exige que chaque modèle physique soit identifié, sourcé, versionné et accompagné de son domaine de validité. Le même document prévoit un moteur gaz distinct du moteur liquide et interdit de transformer une simple substitution de densité en modèle gaz.

Les bibliothèques de référence utilisées pour le benchmark peuvent proposer plusieurs formulations d'un même problème. PETROLE ne doit donc pas rendre une formulation implicite en la codant directement dans la topologie du réseau.

Le bilan nodal déjà présent dans `network_balance.py` reste indépendant du modèle de conduite. De même, les cartes et enveloppes compresseurs restent des modèles machine séparés.

## 3. Module implémenté

`packages/hydrogas/hydro_gas/constitutive_models.py`

### `GasConstitutiveQualification`

États purement techniques :

- `declared` : modèle documenté mais pas encore prêt pour benchmark ;
- `benchmark_ready` : données, paramètres et contrat suffisamment définis pour préparer une comparaison indépendante ;
- `benchmarked` : benchmark exécuté avec références de preuves obligatoires.

Aucun de ces états ne signifie certification, approbation réglementaire ou autorisation d'exploitation.

### `GasPipeConstitutiveModelDescriptor`

Le descripteur exige :

- `model_id` et `version` ;
- `formulation_ref` ;
- `equation_ref` ;
- `source_ref` ;
- `parameter_schema_ref` ;
- au moins une référence de domaine ;
- au moins une hypothèse explicite ;
- état de qualification ;
- preuves obligatoires si l'état vaut `benchmarked`.

### `GasPipeConstitutiveBinding`

Le binding relie une conduite à :

- un couple modèle/version ;
- un jeu de paramètres versionné ;
- l'empreinte SHA-256 de ce jeu ;
- la géométrie utilisée ;
- les propriétés gaz utilisées ;
- la provenance de la configuration.

Un seul binding actif est admis par conduite dans un manifeste donné.

### `GasConstitutiveManifest`

Le manifeste regroupe les modèles disponibles et les bindings retenus pour un réseau/scénario précis. Les couples modèle/version doivent être uniques.

### `assess_constitutive_manifest`

Cette fonction ne résout aucune équation. Elle contrôle seulement :

- conduites du réseau sans binding ;
- bindings vers des conduites absentes du réseau ;
- bindings vers un modèle/version non déclaré ;
- modèles encore au statut `declared`.

Elle expose deux indicateurs :

- `complete` : toutes les conduites sont liées à un modèle/version déclaré et il n'existe pas de binding étranger au réseau ;
- `benchmark_ready` : le manifeste est complet et tous les modèles effectivement sélectionnés sont au moins `benchmark_ready`.

`benchmark_ready` ne signifie jamais que le modèle est valide pour un site réel.

## 4. Tests

`tests/test_gas_constitutive_models.py` vérifie :

- manifeste complet et prêt benchmark ;
- distinction entre `complete` et `benchmark_ready` ;
- détection séparée d'une conduite manquante, inconnue ou d'un modèle inconnu ;
- preuve obligatoire pour un modèle `benchmarked` ;
- domaine et hypothèses obligatoires ;
- empreinte SHA-256 obligatoire pour le jeu de paramètres ;
- unicité modèle/version et binding par conduite.

## 5. Ce qui n'est pas encore implémenté

Ce sous-lot ne fournit pas :

- équation de Weymouth, Panhandle, Darcy compressible ou autre corrélation ;
- calcul automatique d'un coefficient/résistance de conduite ;
- solveur pression-débit ;
- résolution d'un réseau non linéaire ;
- choix automatique d'une formulation ;
- seuil de convergence industriel ;
- validation d'un modèle pour gaz naturel, hydrogène ou mélange particulier.

## 6. Gate avant l'évaluateur constitutif

Avant d'ajouter une équation exécutable :

1. sélectionner explicitement la formulation cible et sa source ;
2. documenter ses unités, variables, hypothèses et domaine ;
3. définir le schéma des paramètres et leur provenance ;
4. construire des cas indépendants P6-H ;
5. comparer l'évaluateur PETROLE à une référence indépendante ;
6. faire relire le modèle et les cas par un spécialiste gaz/thermofluides ;
7. seulement ensuite coupler l'évaluateur au futur solveur réseau.

Cette séquence évite qu'une convention de bibliothèque ou une corrélation de démonstration devienne silencieusement la physique officielle du produit.
