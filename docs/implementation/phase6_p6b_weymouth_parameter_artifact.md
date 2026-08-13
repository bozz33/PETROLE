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

### Schema v1

Version : `phase6/weymouth-si-parameters/1`.

Chaque document contient exactement :

- `schema_version` ;
- `unit_system = SI` ;
- `model_id = weymouth-si` ;
- `model_version = gasmodels-0.13.4-reference-v1` ;
- `parameter_set_ref` ;
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

L'objet est **auto-validant** à sa construction :

- références non vides ;
- SHA-256 minuscule de 64 caractères ;
- hash recalculé égal au hash déclaré ;
- JSON UTF-8 valide ;
- schéma/unité/modèle/version cohérents ;
- `parameter_set_ref`, `pipe_id`, `geometry_ref` et `gas_property_ref` cohérents entre enveloppe et contenu ;
- équation égale à la formulation Weymouth épinglée.

Un artefact dont le contenu a été modifié après calcul du hash est donc refusé. Un artefact cohérent peut naturellement contenir d'autres **valeurs** de paramètres : son nouveau SHA-256 les identifiera. La vérification de leur justesse physique appartient au benchmark et à la revue scientifique, pas au mécanisme d'intégrité.

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

Pour les valeurs du cas upstream épinglé et la vitesse du son `371.6643 m/s`, les artefacts canoniques v1 auto-descriptifs sont :

| Conduite | D (m) | L (m) | λ | SHA-256 paramètres |
| --- | ---: | ---: | ---: | --- |
| 1 | 0.6 | 50 000 | 0.01 | `d8d38334b5cd3477ffe658514373c12dcce48833a6876c7cd67e330760cfe52c` |
| 2 | 0.6 | 80 000 | 0.01 | `81674ea1452942c6d2283df1344f5802967cfdc601142b42c57cd65e096a8425` |
| 3 | 0.6 | 80 000 | 0.01 | `7b39768267f3284b954d55e583719afa0e9a776f9f9971bf4b594f35d1890b58` |
| 4 | 0.3 | 80 000 | 0.01 | `a69bc30dbc1669f4f96ebccc95a6c353abb0cfff6d4a0dcf8426768fc5cf61fe` |

Ces empreintes figent les entrées PETROLE du diagnostic, y compris le modèle/version et la référence logique du jeu de paramètres. Elles ne sont pas les hashes du résultat GasModels et ne dépendent pas du temps solveur.

## 5. Tests

`tests/test_gas_weymouth_parameter_artifact.py` vérifie :

- sérialisation canonique ;
- empreinte exacte de chaque conduite du cas de référence ;
- normalisation des espaces externes des références ;
- conservation des références géométrie/propriétés ;
- binding sans recalcul ;
- descripteur `benchmark_ready` sans fausse preuve `benchmarked` ;
- manifeste complet sur les quatre conduites ;
- refus des références obligatoires absentes ;
- refus d'une autre équation sous la version épinglée ;
- refus d'un contenu modifié avec ancien hash ;
- refus d'une enveloppe incohérente avec son contenu scellé.

## 6. Gate restant

Cette brique ferme la traçabilité et l'intégrité des paramètres, mais ne ferme pas la validation scientifique. Avant un solveur réseau :

1. pré-enregistrer les critères de benchmark PETROLE ;
2. exécuter plusieurs cas indépendants couvrant le domaine revendiqué ;
3. vérifier la définition/provenance du facteur de frottement sur les données réelles ;
4. vérifier les propriétés gaz et leur domaine ;
5. faire relire équation, paramètres, conversions et cas par un spécialiste thermofluides ;
6. seulement ensuite ajouter une stratégie de résolution et ses diagnostics de non-convergence.

Le hash garantit l'identité et l'intégrité des paramètres utilisés ; il ne garantit pas leur justesse physique.
