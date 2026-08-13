# Phase 6 — P6-B : artefacts de paramètres Weymouth-SI

Statut : **IMPLEMENTED_CANONICAL_PARAMETERS_NOT_NETWORK_SOLVER_VALIDATED**.

## 1. Objet

Le résidu Weymouth-SI ne doit jamais dépendre d'un jeu de paramètres implicite ou modifiable sans trace. Cette brique sérialise donc chaque jeu de paramètres de conduite dans un document JSON canonique, puis calcule son SHA-256 avant de le lier au manifeste constitutif.

Elle ne :

- déduit aucun paramètre ;
- choisit aucune corrélation ;
- modifie aucune unité ;
- arrondit aucune valeur ;
- ne qualifie pas le modèle comme `benchmarked` ;
- ne résout ni pression ni débit.

## 2. Implémentation

Module : `packages/hydrogas/hydro_gas/weymouth_parameter_artifact.py`.

### Schéma v1

Version : `phase6/weymouth-si-parameters/1`.

Chaque document contient exactement :

- `schema_version` ;
- `unit_system = SI` ;
- `pipe_id` ;
- `length_m` ;
- `diameter_m` ;
- `friction_factor` ;
- `sound_speed_m_s` ;
- `equation_ref` ;
- `parameter_source_ref` ;
- `geometry_ref` ;
- `gas_property_ref`.

Le JSON est sérialisé avec clés triées, sans `NaN`/`Infinity`, sans espaces décoratifs et en UTF-8. Le SHA-256 porte sur les octets exacts de ce document.

### `WeymouthSiParameterArtifact`

Conserve :

- la référence logique du jeu de paramètres ;
- la conduite ;
- les références géométrie/propriétés gaz ;
- le contenu canonique ;
- le SHA-256.

### Binding constitutif

`build_weymouth_si_binding` produit un `GasPipeConstitutiveBinding` en réutilisant exactement :

- `parameter_set_ref` ;
- `parameter_set_sha256` ;
- `geometry_ref` ;
- `gas_property_ref`.

Aucun paramètre scientifique n'est recalculé lors du binding.

## 3. Descripteur de formulation

`weymouth_si_reference_descriptor()` enregistre :

- `model_id = weymouth-si` ;
- `version = gasmodels-0.13.4-reference-v1` ;
- la formulation/équation au commit GasModels `21422f18e7e328732ec8edd7995446d33f58e789` ;
- le domaine PETROLE documenté dans `phase6_p6b_weymouth_si_residual.md` ;
- les hypothèses stationnaires explicitement listées.

Le statut est volontairement `benchmark_ready`, pas `benchmarked`. Aucune preuve de qualification finale n'est attachée tant que les critères PETROLE n'ont pas été pré-enregistrés et que plusieurs cas indépendants n'ont pas été revus.

## 4. Empreintes du cas GasModels `case-6-gf.m`

Pour les valeurs du cas upstream épinglé et la vitesse du son `371.6643 m/s`, les artefacts canoniques v1 sont :

| Conduite | D (m) | L (m) | λ | SHA-256 paramètres |
| --- | ---: | ---: | ---: | --- |
| 1 | 0.6 | 50 000 | 0.01 | `8750cdf95bbc1b2b73a4dab6881c736b29ef3ad6de19d69d03c2565fcf00f3ed` |
| 2 | 0.6 | 80 000 | 0.01 | `f83d3607d95e6175daf037967214749899bedb21ea360407dee7d8fc588ab31b` |
| 3 | 0.6 | 80 000 | 0.01 | `ed5a742fd5ef6e129f6ebbacdc99d3202487685cc784fca18e8bbe9698cdf998` |
| 4 | 0.3 | 80 000 | 0.01 | `245cf1ab92e9030493e13be3464fd4418e8d42b59ffb2ff681271bfdfc8169a5` |

Ces empreintes figent les entrées PETROLE du diagnostic. Elles ne sont pas les hashes du résultat GasModels et ne dépendent pas du temps solveur.

## 5. Tests

`tests/test_gas_weymouth_parameter_artifact.py` vérifie :

- sérialisation canonique ;
- empreinte exacte de chaque conduite du cas de référence ;
- conservation des références géométrie/propriétés ;
- binding sans recalcul ;
- descripteur `benchmark_ready` sans fausse preuve `benchmarked` ;
- manifeste complet sur les quatre conduites ;
- refus des références obligatoires absentes.

## 6. Gate restant

Cette brique ferme la traçabilité des paramètres, mais ne ferme pas la validation scientifique. Avant un solveur réseau :

1. pré-enregistrer les critères de benchmark PETROLE ;
2. exécuter plusieurs cas indépendants couvrant le domaine revendiqué ;
3. vérifier la définition/provenance du facteur de frottement sur les données réelles ;
4. vérifier les propriétés gaz et leur domaine ;
5. faire relire équation, paramètres, conversions et cas par un spécialiste thermofluides ;
6. seulement ensuite ajouter une stratégie de résolution et ses diagnostics de non-convergence.

Le hash garantit l'identité des paramètres utilisés ; il ne garantit pas leur justesse physique.
