# Phase 6 — P6-A/P6-D — mélanges CoolProp explicites

Statut : `IMPLEMENTED_EXPLICIT_MIXTURE_NO_REPRESENTATIVE_GAS_APPROVED`

## Objet

Ce lot permet au post-traitement thermodynamique des compresseurs d'utiliser un mélange gazeux **explicitement fourni** par PETROLE, sans adopter de composition « gaz naturel type » ni de mélange prédéfini comme valeur par défaut.

Le principe est de conserver séparément :

- la composition molaire PETROLE ;
- la provenance de cette composition ;
- le mapping entre les noms de composants PETROLE et les identifiants de fluides CoolProp ;
- le backend CoolProp ;
- la provenance du mapping ;
- la version et la révision Git de CoolProp réellement exécutées.

## Contrats

### Composition PETROLE

`GasComposition` conserve une liste ordonnée de `GasComponentFraction` avec :

- identifiant de composant ;
- fraction molaire ;
- masse molaire ;
- `source_ref` de la composition.

La composition existante reste responsable de la validation des fractions molaires.

### Mapping CoolProp

`CoolPropCompressorMixtureComponentBinding` contient :

- `composition_component` ;
- `coolprop_fluid`.

Le mapping doit couvrir **exactement** les composants de la composition PETROLE. Les composants PETROLE sont uniques et chaque composant doit viser un fluide CoolProp distinct.

Le binding refuse une syntaxe de mélange déjà encodée (`::`, `&`, crochets, `.mix`) afin que PETROLE conserve explicitement la composition et le mapping au lieu de les masquer dans une chaîne opaque.

### Définition du mélange

`CoolPropCompressorMixtureDefinition` contient :

- `composition` ;
- `component_bindings` ;
- `backend` ;
- `source_ref` ;
- `mapping_source_ref`.

Aucun backend, mapping ou mélange n'est injecté automatiquement.

## Évaluation thermodynamique

Le chemin mélange utilise l'interface bas niveau CoolProp :

```text
AbstractState(backend, component_1&component_2&...)
set_mole_fractions([...])
```

Le post-traitement compresseur utilise ensuite :

1. l'état d'aspiration `P,T` ;
2. l'état de refoulement isentropique `P,s` ;
3. l'enthalpie réelle calculée avec le rendement isentropique issu de la carte compresseur ;
4. la fermeture réelle `h,P` pour obtenir la température de refoulement.

Le rendement n'est jamais inventé par l'adaptateur.

## Traçabilité d'exécution

`CoolPropCompressorStateResult` publie maintenant notamment :

- `coolprop_version` ;
- `coolprop_gitrevision` ;
- `coolprop_backend` ;
- `composition_source_ref` ;
- `component_mapping_source_ref` ;
- noms des composants PETROLE ;
- noms des composants CoolProp ;
- fractions molaires exactes ;
- provenance de la définition fluide/mélange ;
- provenance de l'état et du rendement.

Le chemin fluide pur reste disponible et publie les champs de composition à `None`/vide.

## Export P6-G v2

L'export thermodynamique est versionné :

- `phase6-gas/stationary-compressor-thermodynamics/2` ;
- modèle `phase6/stationary-compressor-thermodynamics/2`.

Pour un mélange explicite, l'export publie la composition, le mapping et le backend réellement utilisés.

Il refuse :

- plusieurs références de composition cachées sous une seule provenance globale ;
- une `composition_source_ref` globale différente de la composition réellement évaluée.

Les références composition/mapping sont incluses dans `source_refs`.

## Politique sur les mélanges prédéfinis

CoolProp peut connaître des mélanges prédéfinis. PETROLE **ne les adopte pas comme composition gaz par défaut** dans ce lot.

En particulier, une chaîne comme `Amarillo.mix` est refusée par le contrat `CoolPropCompressorFluidDefinition` simple. Si une composition industrielle doit être utilisée, elle devra être fournie explicitement, sourcée, revue et versionnée dans PETROLE.

## Tests réels

Les tests exécutent réellement CoolProp et ne mockent pas le calcul thermodynamique mélange.

Le cas de mécanisme utilise deux labels PETROLE synthétiques mappés vers `Methane` et `Ethane`, avec fractions molaires `0.8/0.2`, uniquement pour vérifier la chaîne logicielle.

Ces valeurs :

- ne constituent pas une composition de gaz naturel recommandée ;
- ne constituent pas une composition PETROLE approuvée ;
- ne sont pas utilisées comme valeur par défaut ;
- ne qualifient pas l'exactitude industrielle de CoolProp pour un gaz réel donné.

Les tests couvrent :

- évaluation réelle du mélange ;
- P-T, P-s et h-P ;
- intégration dans le post-traitement stationnaire compresseur ;
- couverture exacte du mapping ;
- doublons de composants/mapping ;
- refus de syntaxes de mélange cachées ;
- provenance de composition dans l'export P6-G v2.

## Limites actuelles

Ce lot couvre **la thermodynamique compresseur**. Il ne couple pas encore automatiquement les propriétés de mélange au solveur réseau Weymouth.

Restent notamment à traiter séparément :

- une ou plusieurs compositions de gaz naturel représentatives, provenant de sources réelles et `APPROVED` ;
- la sélection/version du modèle de mélange retenu pour les cas industriels ;
- densité, facteur de compressibilité `Z`, masse molaire et vitesse du son du mélange comme contrat P6-A général ;
- le couplage de ces propriétés aux paramètres de conduite/line-pack avec modèle et benchmark dédiés ;
- validation indépendante sur données thermodynamiques de référence ;
- domaine de validité et incertitudes ;
- données constructeur réelles pour cartes et limites compresseurs.

Aucune prétention de qualification ou certification industrielle n'est produite par ce lot.
