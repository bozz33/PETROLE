# Phase 6 P6-D/P6-E — coordonnées numériques du réseau mixte

Statut : `IMPLEMENTED_X_TO_R_NO_COUPLED_SOLVER`.

## Objet

Cette brique transforme le problème physique conduites + compresseurs actifs à vitesse imposée en représentation numérique déterministe, sans encore lancer de solveur couplé.

Le chemin est :

`x -> état inconnu physique -> candidat mixte -> résidus physiques -> r(x)`.

## Ordre du vecteur des inconnues

Le vecteur suit exactement `StationaryActiveCompressorUnknownLayout` :

1. pressions inconnues en coordonnées `p² / scale_p²` ;
2. débits des conduites divisés par l'échelle de débit ;
3. débits des compresseurs actifs divisés par la même échelle de débit ;
4. débits externes des noeuds slack divisés par l'échelle de débit.

Les coordonnées `p²` négatives sont refusées. Un débit compresseur actif non positif est également refusé par cette représentation.

## Échelles obligatoires

`StationaryActiveCompressorNumericalScale` exige explicitement :

- `pressure_squared_scale_pa2` ;
- `mass_flow_scale_kg_s` ;
- `mass_residual_scale_kg_s` ;
- `pipe_residual_scale_pa2` ;
- `compressor_residual_scale_pa` ;
- une référence de provenance.

Aucune valeur par défaut n'est fournie.

## Ordre du vecteur des résidus

Le vecteur `r(x)` suit exactement les équations du layout :

1. bilans massiques nodaux en `kg/s` mis à l'échelle ;
2. résidus Weymouth en `Pa²` mis à l'échelle ;
3. résidus de rapport de pression compresseur en `Pa` mis à l'échelle.

La taille du vecteur de résidus reste égale au nombre d'inconnues pour le problème mixte structurellement carré.

## Garde-fous

- round-trip physique/numérique déterministe ;
- couverture exacte des identifiants ;
- conservation des identifiants de frontières via le template d'état ;
- aucune extrapolation de carte ;
- aucune tolérance de convergence ;
- aucun solveur couplé activé ;
- aucune puissance, température ou limite anti-surge calculée.

## Tests

Les valeurs numériques des tests sont synthétiques et servent uniquement à vérifier le mécanisme d'encodage, de décodage et l'ordre de `r(x)`. Elles ne sont pas des échelles industrielles ou des critères PETROLE approuvés.

## Prochain gate

Avant d'appeler un algorithme de résolution sur ce problème mixte, il faut encore :

1. pré-enregistrer et approuver les politiques d'échelle et d'initialisation du problème mixte ;
2. pré-enregistrer un critère de convergence couvrant les trois familles de résidus ;
3. définir les bornes numériques compatibles avec les domaines des cartes compresseurs ;
4. ajouter des benchmarks indépendants réseau + compresseurs ;
5. seulement ensuite brancher un solveur borné sur la fonction canonique `x -> r(x)`.
