# Phase 6 P6-D/P6-E — bornes numériques du problème mixte

Statut : `IMPLEMENTED_DOMAIN_DERIVED_BOUNDS_NO_COUPLED_SOLVER`.

## Principe

Les débits des compresseurs actifs ne reçoivent aucune borne arbitraire. À la vitesse imposée, PETROLE calcule :

1. le domaine de débit utilisable par la carte de performance sans extrapolation ;
2. les limites de débit de l'enveloppe fournisseur lorsqu'elle existe ;
3. l'intersection stricte de ces deux intervalles.

Un intervalle vide ou dégénéré est refusé.

## Domaine de carte

`compressor_map_flow_domain_at_speed(...)` retourne :

- la vitesse ;
- le débit minimum ;
- le débit maximum ;
- la source de carte ;
- la version de carte.

À une vitesse exactement publiée, la ligne correspondante est utilisée directement. Entre deux lignes, le domaine de débit admissible est leur intersection, car l'interpolation en vitesse doit pouvoir évaluer les deux lignes sans extrapolation.

## Enveloppe fournisseur

`compressor_envelope_flow_limits_at_speed(...)` expose les limites interpolées de l'enveloppe sans ajouter de marge anti-surge ou de marge de sécurité cachée.

## Bornes du vecteur mixte

`build_stationary_active_compressor_numerical_bounds(...)` produit :

- `p² >= 0` pour les pressions inconnues ;
- conduites non bornées par cette couche ;
- débits compresseurs bornés par `carte ∩ enveloppe` ;
- débits externes slack non bornés par cette couche.

Les bornes de débit sont converties en coordonnées numériques avec l'échelle de débit explicitement fournie.

## Limites

Cette brique ne représente pas :

- une marge anti-surge opérationnelle ;
- un recycle ;
- un choke dynamique ;
- une limite moteur/turbine ;
- une puissance maximale ;
- une température maximale ;
- un solveur couplé.

Ces limites devront venir de données réelles/versionnées et être ajoutées comme contraintes séparées lorsque leur source est disponible.
