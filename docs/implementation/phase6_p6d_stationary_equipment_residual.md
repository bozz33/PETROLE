# Phase 6 — P6-D — assemblage stationnaire réseau + compresseurs

## Objet

Ce lot assemble, sur un **état candidat fourni**, deux familles de diagnostics qui doivent rester séparées scientifiquement :

1. la conservation de masse du réseau mixte conduites + compresseurs ;
2. la contrainte de rapport de pression issue d'une carte compresseur fournisseur versionnée.

Le module implémenté est `hydro_gas.stationary_equipment_residual`.

## Entrées

- topologie gaz stationnaire ;
- débits de conduites fournis ;
- arêtes compresseurs orientées ;
- débit massique et vitesse de chaque compresseur actif ;
- pression absolue de tous les noeuds ;
- binding explicite entre chaque compresseur et sa carte versionnée ;
- enveloppe d'exploitation optionnelle déjà définie en amont ;
- injections et soutirages externes.

La couverture est fermée : pressions, états compresseurs et bindings doivent correspondre exactement à la topologie déclarée. Les identifiants dupliqués sont refusés.

## Sorties

`StationaryEquipmentResidualAssembly` expose :

- le bilan massique détaillé par noeud ;
- le résidu global de masse ;
- un `StationaryCompressorMapConstraint` par compresseur ;
- les références de provenance des pressions, états d'exploitation et bindings de cartes.

Pour chaque compresseur actif, l'état physique est construit depuis les pressions des noeuds `from_node` et `to_node`. Le résidu reste celui déjà défini par P6-D :

`p_out - ratio_carte(debit, vitesse) * p_in`

Aucun seuil de réussite n'est appliqué.

## Limites explicites

Ce lot **ne constitue pas** un solveur couplé gaz + compresseurs. Il ne calcule pas :

- la puissance compresseur ;
- la température de refoulement ;
- la consommation de combustible ou électrique ;
- une marge anti-surge ;
- la commande compresseur ;
- le partage optimal entre unités ;
- un débit, une pression ou une vitesse inconnue ;
- une convergence réseau mixte.

Le mode arrêt/bypass n'est pas déguisé en point de carte à débit nul : l'objet `StationaryCompressorOperatingInput` décrit uniquement un compresseur **actif**, donc son débit et sa vitesse doivent être strictement positifs.

## Suite

La prochaine étape P6-D/P6-E pourra construire un layout d'inconnues pour un réseau mixte uniquement après définition explicite des modes d'équipement et de leurs équations actives. Le solveur Weymouth P6-B existant ne doit pas être étendu implicitement à cette topologie.
