# Phase 6 — P6-A — propriétés de mélange CoolProp explicites

Statut : `IMPLEMENTED_PROPERTY_EVALUATION_NO_NETWORK_PARAMETER_COUPLING`

## Objet

Ce lot généralise la composition explicite déjà utilisée pour la thermodynamique des compresseurs et fournit une évaluation P6-A d'un mélange gazeux à un état `P,T` donné.

Il calcule et trace :

- densité massique `rho` ;
- facteur de compressibilité `Z` ;
- masse molaire CoolProp ;
- vitesse du son thermodynamique CoolProp ;
- constante molaire du gaz exposée par le backend ;
- coefficient EOS `Z R T / M` associé à la relation `p = coefficient * rho` ;
- racine de ce coefficient, nommée **échelle EOS pression/densité** ;
- densité reconstruite depuis `p, Z, R, T, M` ;
- résidu brut entre densité CoolProp et densité reconstruite ;
- masse molaire déclarée dans la composition PETROLE et son résidu brut par rapport à la masse molaire retournée par CoolProp.

Aucun de ces résidus ne reçoit un seuil implicite, un verdict PASS/FAIL ou une qualification automatique.

## Contrat mélange partagé

Le module `coolprop_gas_mixture.py` contient désormais le contrat commun :

- `CoolPropGasMixtureComponentBinding` ;
- `CoolPropGasMixtureDefinition`.

Le post-traitement compresseur réutilise exactement ce contrat. Les anciens noms `CoolPropCompressorMixtureComponentBinding` et `CoolPropCompressorMixtureDefinition` restent des alias compatibles.

Le mapping :

- couvre exactement tous les composants de `GasComposition` ;
- conserve l'ordre de la composition PETROLE pour les fractions molaires envoyées à CoolProp ;
- exige un identifiant CoolProp simple par composant ;
- refuse les syntaxes de mélange cachées (`::`, `&`, crochets et `.mix`) ;
- conserve `source_ref` et `mapping_source_ref`.

Aucune composition de gaz naturel représentative n'est embarquée par défaut.

## État P/T et domaine

`CoolPropGasMixtureStateRequest` exige :

- température absolue ;
- pression absolue ;
- `CoolPropEvaluationEnvelope` ;
- `state_source_ref` ;
- `property_method_ref`.

L'état est contrôlé contre l'enveloppe projet **avant** l'appel CoolProp. Le domaine reste donc une donnée de projet sourcée et non une plage inventée par le moteur.

## Propriétés et diagnostics

`evaluate_coolprop_gas_mixture_properties(...)` crée un `AbstractState` avec le backend et les composants explicitement fournis, affecte les fractions molaires et évalue l'état P/T.

`CoolPropGasMixturePropertyResult` conserve notamment :

```text
density_kg_m3
compressibility_factor
molar_mass_kg_mol
declared_composition_molar_mass_kg_mol
molar_mass_residual_kg_mol
speed_of_sound_m_s
gas_constant_j_mol_k
eos_pressure_density_coefficient_m2_s2
eos_pressure_density_scale_m_s
density_from_eos_kg_m3
density_eos_residual_kg_m3
```

avec :

```text
eos_pressure_density_coefficient = Z * R * T / M
eos_pressure_density_scale = sqrt(eos_pressure_density_coefficient)
density_from_eos = p / eos_pressure_density_coefficient
```

Le résidu de masse molaire est uniquement :

```text
declared_composition_molar_mass - coolprop_molar_mass
```

Les tests utilisent volontairement des masses molaires PETROLE synthétiques différentes des valeurs physiques des fluides mappés afin de vérifier que cette divergence est **visible** et jamais corrigée silencieusement.

## Distinction critique : vitesse du son vs échelle EOS

Deux sorties différentes sont conservées :

- `speed_of_sound_m_s` : propriété thermodynamique retournée par CoolProp ;
- `eos_pressure_density_scale_m_s` : racine algébrique de `ZRT/M` pour l'état évalué.

PETROLE **ne les identifie pas automatiquement** et ne copie aucune de ces valeurs dans `WeymouthSiPipeParameters.sound_speed_m_s`.

Cette séparation est volontaire : le paramètre du modèle constitutif Weymouth doit être choisi par un contrat scientifique/versionné propre au modèle, puis benchmarké. Un champ ayant l'unité `m/s` ne suffit pas à prouver une équivalence physique ou numérique.

## Artefact canonique P6-A

`coolprop_gas_property_artifact.py` ajoute :

- `CoolPropGasMixturePropertyArtifact` ;
- `export_coolprop_gas_mixture_property_artifact(...)` ;
- schéma `phase6/coolprop-gas-mixture-properties/1` ;
- modèle `coolprop-explicit-mixture-properties` / `abstractstate-pt-runtime-v1` ;
- référence de preuve `sha256://petrole/gas/coolprop-mixture-properties/<hash>`.

L'artefact JSON canonique contient :

- état P/T et références d'état/enveloppe ;
- composition, mapping, backend, noms de composants et fractions ;
- version et révision Git CoolProp réellement exécutées ;
- propriétés ;
- diagnostics EOS et masse molaire ;
- claims fixés à `false`.

Le constructeur de l'artefact revalide le SHA-256 et les références essentielles. Une altération du contenu invalide l'artefact.

Le même résultat et le même `property_state_ref` donnent le même contenu/hash **dans le même runtime scientifique**. Une autre version de CoolProp ou un résultat numérique différent doit produire une autre preuve, ce qui est précisément l'objectif de la provenance runtime.

## Ce que le lot ne fait pas

Il n'existe volontairement aucune fonction automatique pour :

- créer un `GasState` de line-pack à partir de cet artefact ;
- remplacer la masse molaire déclarée PETROLE par la masse molaire CoolProp ;
- injecter `Z`, `rho`, `speed_of_sound` ou l'échelle EOS dans le solveur Weymouth ;
- construire un `WeymouthSiPipeParameters` ;
- déclarer qu'un résidu EOS ou de masse molaire est acceptable ;
- qualifier une composition industrielle.

Ces ponts nécessitent une politique scientifique explicite, des références de modèle, des critères pré-enregistrés et des benchmarks dédiés.

## Tests

Les tests exécutent réellement CoolProp pour un mélange synthétique Methane/Ethane servant uniquement au mécanisme logiciel.

Ils vérifient :

- ordre composition -> composants CoolProp ;
- `rho`, `Z`, `M`, vitesse du son et constante du gaz ;
- reconstruction EOS et diagnostics ;
- enveloppe P/T ;
- provenance complète ;
- absence de claims ;
- export canonique déterministe dans le runtime ;
- SHA-256 et détection d'altération ;
- absence de champ/contrat Weymouth dans l'artefact.

Les fractions et masses molaires des tests ne sont ni une composition recommandée ni une composition PETROLE approuvée.

## Gates restant avant couplage réseau

Avant de dériver un état line-pack ou un paramètre constitutif depuis cette brique, il faut au minimum :

1. retenir des compositions réelles et sourcées ;
2. approuver le mapping des composants ;
3. fixer le backend/méthode et l'environnement scientifique ;
4. définir la politique de masse molaire utilisée par chaque modèle ;
5. définir le paramètre EOS attendu par le modèle Weymouth et sa méthode de calcul ;
6. pré-enregistrer les critères de comparaison ;
7. benchmarker plusieurs états/compositions contre des références indépendantes ;
8. faire relire le choix par un ingénieur gaz/thermofluides.

Aucune prétention de qualification ou de certification industrielle n'est produite par ce lot.
