# Phase 6 / P6-H — évaluation quantitative gouvernée des propriétés gaz

Statut : `IMPLEMENTED_GOVERNED_QUANTITATIVE_ASSESSMENT_NO_QUALIFICATION`.

## Objet

Cette couche exécute la comparaison quantitative P6-H uniquement lorsqu'une chaîne de preuve de benchmark propriétés est déjà cohérente et que les critères ont été pré-enregistrés puis `APPROVED`.

Elle est implémentée dans `hydro_gas.coolprop_gas_property_benchmark_assessment`.

## Entrées obligatoires

L'évaluation reçoit :

- l'artefact canonique `CoolPropGasPropertyBenchmarkEvidenceArtifact` ;
- le bundle d'observations runtime ;
- le paquet `ApprovedGasBenchmarkCriteria` ;
- le `GasBenchmarkProtocolContext` exact ;
- une référence de campagne ;
- la version du moteur PETROLE ;
- l'identité et les SHA-256 de la référence externe via `ExternalGasSolverEvidence`.

Aucune tolérance n'est créée par cette fonction.

## Vérifications avant calcul

Avant tout calcul d'erreur, le moteur vérifie notamment :

1. le SHA-256 des octets exacts de la preuve canonique ;
2. le schéma P6-H attendu ;
3. l'absence de prétention de qualification/certification dans la preuve ;
4. l'égalité du contexte APPROVED complet : protocole, modèle, version, formulation et cas ;
5. l'identité du bundle PETROLE : état, artefact source, composition et version/runtime CoolProp ;
6. l'égalité exacte des observations sérialisées et runtime, valeurs incluses ;
7. l'égalité exacte des critères APPROVED, de leurs limites, `source_ref`, `approval_ref` et `registration_ref` ;
8. l'identité de la référence externe et ses SHA-256 d'entrée/sortie.

Toute dérive documentaire ou de provenance provoque un refus fail-closed avant comparaison.

## Calcul quantitatif

Une fois la chaîne vérifiée, `assess_coolprop_gas_property_benchmark_evidence` délègue le calcul à `assess_external_gas_benchmark`.

Le comparateur existant calcule pour chaque observation :

- erreur absolue ;
- erreur relative lorsque la référence n'est pas nulle ;
- verdict par rapport aux seules limites déjà APPROVED ;
- violations explicites lorsqu'une limite est dépassée ;
- état inévaluable lorsqu'un critère relatif est demandé avec une référence nulle.

Le résultat global conserve aussi l'identité de la preuve canonique, les identifiants des critères, leurs approvals et leurs registrations.

## Différence entre FAIL et erreur technique

Un dépassement d'un critère APPROVED est un **résultat scientifique factuel** :

- `passed=false` pour l'observation concernée ;
- `all_evaluable_criteria_passed=false` au niveau campagne lorsque nécessaire ;
- aucune exception de gouvernance n'est levée pour ce simple dépassement.

À l'inverse, une preuve falsifiée, un hash externe différent, un contexte différent ou un approval différent est une incohérence de preuve et l'évaluation est refusée.

## Aucune qualification implicite

`CoolPropGasPropertyBenchmarkAssessmentResult` maintient explicitement :

- `qualification_claim=false` ;
- `certification_claim=false`.

Un benchmark qui passe ses critères ne devient donc pas automatiquement un modèle qualifié, certifié ou approprié à un domaine industriel.

## Tests actuels

Les tests utilisent exclusivement des observations, références, hashes et limites `synthetic` / `test-only` pour valider le mécanisme logiciel :

- cas conforme ;
- critère synthétique dépassé ;
- dérive d'une valeur PETROLE ;
- dérive d'un `approval_ref` ;
- dérive du contexte ;
- dérive de la référence externe ou de son hash.

Ces valeurs ne sont pas des tolérances PETROLE ni des limites industrielles.

## Gate scientifique restant

Une campagne réelle de propriétés gaz exige encore des compositions représentatives approuvées, des références indépendantes adéquates, un domaine P/T défini, des critères numériques justifiés et approuvés avant comparaison, plusieurs cas indépendants et une revue thermofluides documentée.

Cette couche rend la comparaison traçable et reproductible ; elle ne remplace pas la qualification scientifique du modèle.
