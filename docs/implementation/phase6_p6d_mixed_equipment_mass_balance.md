# P6-D — bilan massique mixte conduites + compresseurs

Statut : fondation logicielle non certifiante.

## Objet

Cette brique étend la conservation de masse stationnaire à un réseau contenant à la fois des conduites et des compresseurs, sans assimiler artificiellement un compresseur à une conduite.

À chaque nœud, le résidu est :

`m_pipe_in - m_pipe_out + m_compressor_in - m_compressor_out + m_external`

Aucune tolérance PASS/FAIL n'est appliquée.

## Équipements séparés

Les conduites conservent `GasPipeMassFlow` et leur convention de débit signé : une valeur négative signifie un écoulement opposé à l'orientation documentaire.

Les compresseurs utilisent :

- `SteadyGasCompressorEdge` pour l'identité et les deux nœuds ;
- `GasCompressorMassFlow` pour le débit dans le sens documentaire du compresseur.

Le débit compresseur est fini et positif ou nul. Un débit négatif n'est pas utilisé pour représenter un bypass ou un flux inverse à travers une unité active ; ces modes doivent être modélisés explicitement par la configuration de station/réseau.

## Validation topologique

`assess_stationary_equipment_mass_balance(...)` vérifie :

- couverture exacte de toutes les conduites ;
- identifiants de compresseurs uniques ;
- extrémités compresseur présentes dans le réseau ;
- couverture exacte d'un débit par compresseur ;
- frontières externes uniques et rattachées à des nœuds connus.

## Diagnostics

Chaque `GasNodeEquipmentMassBalance` conserve séparément :

- débit conduit entrant ;
- débit conduit sortant ;
- débit compresseur entrant ;
- débit compresseur sortant ;
- injection/soutirage externe ;
- résidu massique total.

Le résultat réseau expose aussi :

- résidu global ;
- résidu nodal absolu maximal ;
- provenances des débits conduites ;
- provenances des débits compresseurs ;
- provenances des frontières.

Les transports internes par conduite et compresseur s'annulent dans le résidu global. Le résidu global est donc égal au débit externe net, sous réserve des erreurs numériques des valeurs fournies.

## Séparation avec la carte compresseur

Cette brique ne contient pas le rapport de pression du compresseur. La contrainte `p_out - ratio_map × p_in` est évaluée séparément par `evaluate_stationary_compressor_map_constraint(...)`.

Cette séparation permet de distinguer clairement :

1. conservation de masse ;
2. relation de pression issue de la carte fournisseur ;
3. enveloppe de fonctionnement fournisseur.

## Non-objectifs

Cette brique ne calcule pas :

- puissance ;
- température ;
- rendement thermodynamique hors valeur interpolée de carte ;
- anti-surge/recycle ;
- logique station ;
- dynamique ;
- décision de convergence du futur réseau mixte.

## Tests

Les tests couvrent :

- chaîne conduite puis compresseur ;
- séparation des contributions dans les diagnostics ;
- annulation des transports internes dans le bilan global ;
- débit de conduite inversé avec compresseur directionnel ;
- couverture exacte des compresseurs ;
- endpoints inconnus ;
- identifiants compresseurs dupliqués ;
- refus d'un débit compresseur négatif.
