# Phase 6 — P6-B : résidu Weymouth SI

Statut : **IMPLEMENTED_RESIDUAL_DIAGNOSTIC_NOT_NETWORK_SOLVER_VALIDATED**.

## 1. Objet

Cette brique est le premier calcul constitutif exécutable de P6-B. Elle reste volontairement limitée à l'évaluation d'une observation déjà connue : pressions amont/aval, débit massique et paramètres de conduite sont fournis explicitement.

Elle ne résout pas :

- le débit d'une conduite ;
- la pression d'un nœud ;
- un réseau non linéaire ;
- une station de compression ;
- un problème d'optimisation ;
- une consigne ou une commande procédé.

## 2. Équation de référence

La formulation est celle documentée par GasModels 0.13.4 pour l'écoulement gaz stationnaire de type Weymouth :

`p_to² - p_from² = - λ L a² f |f| / (D A²)`

avec :

- `A = π D² / 4` ;
- `p` : pression absolue en Pa ;
- `λ` : facteur de frottement sans dimension ;
- `L` : longueur en m ;
- `a` : vitesse du son en m/s ;
- `f` : débit massique en kg/s ;
- `D` : diamètre en m.

Le résidu PETROLE est donc défini comme :

`R = p_to² - p_from² + K f |f|`

avec :

`K = λ L a² / (D A²)`.

Un résidu égal à zéro signifie seulement que les valeurs fournies satisfont algébriquement cette équation. Aucun seuil numérique, aucune validation industrielle et aucune certification ne sont déduits par cette couche.

## 3. Implémentation

Module : `packages/hydrogas/hydro_gas/weymouth_si.py`.

### `WeymouthSiPipeParameters`

Exige :

- identifiant de conduite ;
- longueur strictement positive ;
- diamètre strictement positif ;
- facteur de frottement fini et non négatif ;
- vitesse du son strictement positive ;
- référence de l'équation ;
- provenance des paramètres.

Le module calcule la section `A` et le coefficient `K`, mais ne déduit aucun de ces paramètres depuis une donnée incomplète.

### `WeymouthSiObservation`

Exige :

- la conduite ;
- deux pressions absolues finies et non négatives ;
- un débit massique signé et fini ;
- une provenance.

Le signe du débit est conservé dans `f|f|`, donc le flux inverse n'est pas transformé en flux positif.

### `WeymouthSiResidual`

Expose uniquement :

- différence de pression au carré ;
- terme de frottement ;
- résidu brut en Pa² ;
- coefficient de résistance utilisé ;
- références de l'équation, des paramètres et de l'observation.

Il n'existe volontairement aucun champ `passed`, `validated`, `compliant` ou seuil implicite.

## 4. Conversion du cas GasModels de référence

Le cas externe P6-H reste stocké en per-unit. Pour le commit GasModels épinglé, le code de conversion `pu_to_si!` applique :

- `p_SI = p_pu × base_pressure` ;
- `f_SI = f_pu × base_flow`.

Le cas `case-6-gf.m` déclare explicitement :

- `base_pressure = 3 000 000` ;
- `base_flow = 200` ;
- unités d'entrée `si` ;
- `sound_speed = 371.6643`.

Aucune autre conversion n'est reconstruite dans l'évaluateur.

## 5. Référence P6-H utilisée dans les tests

Artefact de référence :

- workflow run : `31657331294` ;
- artifact id : `9164893821` ;
- JSON SHA-256 : `1ad529221dc0f4e05e30f0e73c1e01b8b4c80925f65d135a4c9b908a902e386e` ;
- GasModels : `0.13.4` ;
- commit : `21422f18e7e328732ec8edd7995446d33f58e789` ;
- formulation : `WPGasModel` ;
- solveur : Ipopt `1.15.0` ;
- terminaison : `LOCALLY_SOLVED` ;
- objectif : `0.0`.

Le test `tests/test_gas_weymouth_si.py` applique l'évaluateur aux quatre conduites avec les pressions et débits du JSON de référence convertis par les bases ci-dessus. Les résidus bruts sont figés comme observations de non-régression :

| Conduite | Résidu Pa² |
| --- | ---: |
| 1 | `0.0` |
| 2 | `1.04248046875` |
| 3 | `1.06103515625` |
| 4 | `-33.4970703125` |

Ces nombres ne sont accompagnés d'aucun seuil d'acceptation PETROLE. Ils servent à rendre reproductible le diagnostic obtenu à partir de l'artefact externe, pas à déclarer le modèle validé.

## 6. Limites et hypothèses

La formulation de référence suppose notamment :

- régime stationnaire ;
- conduite 1D ;
- section constante ;
- débit massique constant le long de la conduite ;
- relation d'état `p = a²ρ` ;
- vitesse du son fournie ;
- facteur de frottement fourni ;
- absence de modèle transitoire, thermique distribué ou multiphase dans cette équation.

Ces hypothèses doivent rester attachées au `GasPipeConstitutiveModelDescriptor` correspondant avant toute utilisation de la formule dans un futur solveur.

## 7. Gate suivant

Avant de construire un solveur stationnaire P6-B :

1. enregistrer la formulation Weymouth-SI dans le manifeste constitutif avec domaine et hypothèses ;
2. définir un jeu de paramètres complet pour le cas P6-H et son empreinte ;
3. pré-enregistrer les critères de comparaison scientifiques ;
4. multiplier les cas de référence indépendants ;
5. valider les conventions de pression, débit, friction et propriétés gaz avec un spécialiste thermofluides ;
6. seulement ensuite introduire un solveur de racines/réseau et documenter ses non-convergences.

Le résidu actuel est donc une brique de diagnostic et de benchmark, pas un moteur de dimensionnement ni une fonction de protection.
