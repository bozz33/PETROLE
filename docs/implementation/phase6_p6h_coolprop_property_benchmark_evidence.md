# Phase 6 / P6-H — preuve canonique des benchmarks de propriétés CoolProp

Statut : `IMPLEMENTED_EVIDENCE_CHAIN_NO_REAL_PROPERTY_REFERENCE_APPROVED`

## Objet

Cette couche relie les résultats de propriétés gaz P6-A à un futur benchmark P6-H sans transformer un jeu de test, une référence externe ou un seuil de développement en qualification industrielle.

Le contrat est implémenté dans :

- `hydro_gas.coolprop_gas_property_artifact` ;
- `hydro_gas.coolprop_gas_property_benchmark_adapter` ;
- `hydro_gas.benchmark_protocol` ;
- `hydro_gas.coolprop_gas_property_benchmark_evidence`.

## Chaîne de preuve

L'artefact `CoolPropGasPropertyBenchmarkEvidenceArtifact` fige sous JSON canonique SHA-256 :

1. le protocole, le cas et la formulation explicitement choisis ;
2. l'identifiant et la version exacts du modèle P6-A ;
3. le hash SHA-256 de l'artefact canonique P6-A de propriétés ;
4. la référence de composition, l'état de propriétés et l'identité runtime CoolProp (`version` et `gitrevision`) ;
5. les observations PETROLE et les valeurs de la référence externe, sans conversion d'unité implicite ;
6. les critères pré-enregistrés `APPROVED`, avec leurs limites numériques exactes, `source_ref`, `approval_ref` et `registration_ref` ;
7. l'identité de la référence externe et les SHA-256 de ses entrées et sorties ;
8. une référence de revue éventuelle et la source de la preuve.

L'artefact s'auto-vérifie : une modification de son contenu invalide son SHA-256.

## Règles fail-closed de préparation

L'export est refusé notamment si :

- le protocole des critères APPROVED ne correspond pas au protocole du benchmark ;
- le modèle ou la version ne correspondent pas au modèle P6-A de propriétés CoolProp ;
- la source PETROLE n'est pas un artefact P6-A canonique hashé ;
- un hash de référence externe n'est pas un SHA-256 hexadécimal valide ;
- des observations sont absentes ou dupliquées ;
- une observation ne correspond pas à l'état ou à l'artefact P6-A du bundle ;
- les critères APPROVED ne couvrent pas exactement les observations ;
- les preuves d'approbation/enregistrement sont désalignées ;
- une référence obligatoire est vide.

## Ce que cette couche ne fait pas

Elle ne :

- recalcule aucune propriété thermodynamique ;
- choisit aucune composition gaz ;
- choisit aucun modèle de mélange ;
- invente aucune tolérance ;
- crée aucune référence externe ;
- convertit aucune unité ;
- calcule aucun PASS/FAIL ;
- déclare aucun modèle `BENCHMARKED` ;
- déclare aucune qualification ou certification.

Les champs `qualification_claim` et `certification_claim` restent explicitement à `false`.

## Tests actuels

Les tests automatisés utilisent uniquement des données marquées `synthetic` / `test-only` : mélange Methane/Ethane de test, état P/T de test, valeurs externes synthétiques et critères numériques synthétiques destinés uniquement à vérifier le mécanisme logiciel.

Ces nombres **ne sont pas des tolérances PETROLE**, des limites industrielles ni des critères de qualification.

## Gate scientifique restant

Avant toute campagne réelle de qualification des propriétés gaz, il faut encore disposer de :

- compositions représentatives du domaine projet, sourcées et approuvées ;
- références indépendantes adaptées aux propriétés observées et à la plage P/T ;
- unités et méthodes de comparaison figées avant l'exécution ;
- critères numériques justifiés, pré-enregistrés et approuvés avant comparaison ;
- plusieurs cas indépendants couvrant le domaine d'utilisation ;
- revue ingénieur gaz/thermofluides documentée.

L'artefact P6-H fournit la traçabilité nécessaire à cette campagne ; il ne remplace pas cette campagne.
