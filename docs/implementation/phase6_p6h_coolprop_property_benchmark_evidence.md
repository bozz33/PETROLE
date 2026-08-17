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

## Contexte APPROVED immuable

`ApprovedGasBenchmarkCriteria` conserve désormais le protocole, le modèle, la version, la formulation et le cas qui ont gouverné sa matérialisation. L'export P6-H propriétés refuse le paquet si ce contexte complet diffère du `GasBenchmarkProtocolContext` demandé. Une dérive de `formulation_ref` ou de `case_ref` est donc rejetée même si le protocole, le modèle et la version restent identiques.

## Règles fail-closed de préparation

L'export est refusé notamment si :

- le protocole des critères APPROVED ne correspond pas au protocole du benchmark ;
- le modèle ou la version ne correspondent pas au modèle P6-A de propriétés CoolProp ;
- la formulation ou le cas diffèrent du contexte APPROVED ;
- la source PETROLE n'est pas un artefact P6-A canonique hashé ;
- un hash de référence externe n'est pas un SHA-256 hexadécimal valide ;
- des observations sont absentes ou dupliquées ;
- une observation ne correspond pas à l'état ou à l'artefact P6-A du bundle ;
- les critères APPROVED ne couvrent pas exactement les observations ;
- les preuves d'approbation/enregistrement sont désalignées ;
- une référence obligatoire est vide.

## Ce que cette couche ne fait pas

Elle ne recalcule aucune propriété thermodynamique, ne choisit aucune composition ou modèle de mélange, n'invente aucune tolérance, ne convertit aucune unité, ne calcule aucun `PASS/FAIL` et ne déclare aucune qualification ou certification.

Les champs `qualification_claim` et `certification_claim` restent explicitement à `false`.

## Tests actuels

Les tests automatisés utilisent uniquement des données marquées `synthetic` / `test-only`. Ils couvrent notamment la dérive du protocole, du modèle, de la version, de la formulation et du cas, ainsi que la falsification des hashes et la couverture exacte des observations.

Ces nombres **ne sont pas des tolérances PETROLE**, des limites industrielles ni des critères de qualification.

## Gate scientifique restant

Avant toute campagne réelle, il faut encore des compositions représentatives sourcées et approuvées, des références indépendantes adaptées aux propriétés et à la plage P/T, des méthodes de comparaison figées avant exécution, des critères numériques justifiés et approuvés, plusieurs cas indépendants et une revue ingénieur gaz/thermofluides documentée.

L'artefact P6-H fournit la traçabilité nécessaire à cette campagne ; il ne remplace pas cette campagne.
