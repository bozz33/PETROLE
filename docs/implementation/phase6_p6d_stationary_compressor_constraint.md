# P6-D — contrainte stationnaire issue de la carte compresseur

Statut : fondation logicielle non certifiante.

## Objet

Cette brique relie un état candidat de compresseur à la carte fournisseur déjà versionnée dans PETROLE.

Pour un débit massique et une vitesse situés à l'intérieur de la carte, l'interpolation existante fournit le rapport de pression et le rendement isentropique. La nouvelle contrainte calcule uniquement :

`résidu_p = p_out - pressure_ratio_map × p_in`

Le résidu reste en `Pa` et aucune tolérance PASS/FAIL n'est ajoutée.

## Entrées

`StationaryCompressorState` exige :

- identifiant compresseur ;
- pression absolue d'aspiration `Pa` ;
- pression absolue de refoulement `Pa` ;
- débit massique positif `kg/s` ;
- vitesse positive `rpm` ;
- provenance de l'état.

Le mode compression actif de cette brique ne prend pas en charge un débit nul ou inverse. Un bypass ou un chemin de flux inverse doit être modélisé séparément au niveau station/réseau.

## Carte fournisseur

`evaluate_stationary_compressor_map_constraint(...)` utilise `interpolate_compressor_map(...)` :

- aucune extrapolation hors débit/vitesse de la carte ;
- provenance et version de carte conservées ;
- interpolation du rapport de pression et du rendement uniquement dans le domaine fourni.

## Enveloppe fournisseur optionnelle

Une `CompressorOperatingEnvelope` peut être fournie séparément.

Dans ce cas, la fonction retourne aussi `CompressorEnvelopeAssessment`, qui indique la position du débit par rapport aux limites minimales/maximales publiées.

Aucune marge anti-surge supplémentaire n'est créée et aucune logique de recycle n'est commandée.

## Sortie

`StationaryCompressorMapConstraint` contient :

- identifiant du compresseur ;
- provenance de l'état ;
- point de carte interpolé ;
- pression de refoulement attendue selon le ratio de carte ;
- résidu brut de pression ;
- évaluation d'enveloppe éventuelle.

## Non-objectifs

Cette brique ne calcule pas :

- puissance absorbée ;
- température de refoulement ;
- travail polytropique/isentropique ;
- consommation de fuel/électricité ;
- contrôle anti-surge ;
- recycle ;
- logique de démarrage/arrêt ;
- dynamique de station.

Ces éléments nécessitent leurs modèles, données constructeur, hypothèses thermodynamiques et benchmarks propres.

## Tests

Les tests vérifient :

- interpolation d'un ratio fournisseur ;
- résidu nul au rapport exact ;
- résidu brut non nul sans statut PASS ;
- refus de l'extrapolation hors carte ;
- refus du débit inverse dans ce mode actif ;
- évaluation séparée de l'enveloppe fournisseur.
