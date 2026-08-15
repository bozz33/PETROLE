# Phase 6 — P6-H — adaptateur de benchmark des propriétés gaz

Statut : `IMPLEMENTED_OBSERVATION_ADAPTER_NO_REFERENCE_OR_TOLERANCE_BUNDLED`

## Objet

Ce lot relie l'artefact canonique P6-A des propriétés de mélange à la chaîne de benchmark P6-H existante.

Il ne calcule pas de nouvelles propriétés et n'embarque :

- aucune valeur de référence ;
- aucune tolérance ;
- aucune conversion d'unité ;
- aucune composition de gaz naturel ;
- aucun verdict de qualification.

Les valeurs PETROLE viennent exclusivement de `CoolPropGasMixturePropertyArtifact`. Les valeurs externes sont obligatoirement fournies par l'appelant avec une provenance explicite.

## Grandeurs exposées

`GasMixturePropertyBenchmarkQuantity` autorise actuellement :

- `density` — `kg/m3` ;
- `compressibility_factor` — `1` ;
- `molar_mass` — `kg/mol` ;
- `speed_of_sound` — `m/s` ;
- `gas_constant` — `J/(mol*K)` ;
- `eos_pressure_density_coefficient` — `m2/s2` ;
- `eos_pressure_density_scale` — `m/s`.

La vitesse du son CoolProp et l'échelle EOS restent deux observations différentes même si elles ont toutes les deux l'unité `m/s`.

## Binding externe

`GasMixturePropertyBenchmarkBinding` exige :

- `observation_id` ;
- quantité ;
- valeur externe finie ;
- unité exacte ;
- `reference_source_ref`.

L'adaptateur refuse une unité différente de l'unité canonique de la grandeur. Il ne convertit donc pas `bar`, `g/L`, `kmol`, etc. avant comparaison. Une conversion éventuelle doit être effectuée et tracée en amont dans un artefact/référentiel dédié.

## Construction des observations

`build_coolprop_gas_property_benchmark_observations(...)` :

1. vérifie le SHA-256 de l'artefact P6-A ;
2. vérifie schéma, modèle, version et `property_state_ref` ;
3. vérifie la provenance de composition ;
4. lit exactement la valeur PETROLE du champ canonique ;
5. vérifie l'unité demandée ;
6. crée un `GasBenchmarkObservation` avec :
   - `location_ref = property_state_ref` ;
   - `petrole_source_ref = artifact.evidence_ref` ;
   - `reference_source_ref` fourni par l'appelant.

Les identifiants d'observation doivent être uniques.

## Tolérances et approbation

L'adaptateur ne contient aucune tolérance.

Pour qu'une observation soit évaluée, elle doit ensuite passer par le protocole P6-H déjà en place :

- `PreRegisteredGasBenchmarkCriterion` ;
- contexte exact modèle/formulation/cas ;
- limite explicite ;
- `registration_ref` ;
- état `APPROVED` ;
- `approval_ref` ;
- `materialize_approved_gas_benchmark_criteria(...)`.

Ainsi, la référence externe et le critère d'acceptation sont deux preuves séparées et versionnées.

## Tests

Les tests utilisent des valeurs externes et des tolérances **synthétiques** uniquement pour vérifier le mécanisme logiciel.

Elles ne constituent :

- ni des données de référence thermodynamiques PETROLE ;
- ni une tolérance de validation du produit ;
- ni une composition recommandée ;
- ni un critère industriel.

Les tests couvrent :

- lecture exacte de l'artefact sans conversion ;
- densité, Z, masse molaire, vitesse du son et coefficient EOS ;
- unités exactes ;
- observations uniques ;
- références externes finies ;
- intégrité SHA-256 ;
- passage vers un critère explicitement `APPROVED`.

## Gates restant avant benchmark réel

Il faut encore fournir, pour chaque cas réel :

1. une composition réelle sourcée ;
2. un état P/T et domaine documentés ;
3. une source indépendante de référence pour chaque grandeur ;
4. une méthode/formulation de référence clairement identifiée ;
5. des critères enregistrés avant comparaison puis approuvés ;
6. plusieurs états et compositions indépendants ;
7. une revue thermofluides ;
8. une analyse des divergences de modèle et d'incertitude.

Ce lot ne couple toujours aucune propriété calculée aux paramètres Weymouth ou line-pack et ne produit aucune qualification/certification industrielle.
