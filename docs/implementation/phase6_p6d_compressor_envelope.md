# Phase 6 — P6-D Enveloppe fournisseur compresseur

Références : D07 §10, D10 et D17.

## Implémentation

`hydro_gas.compressor_limits` représente des limites min/max de débit massique par vitesse issues d'une source fournisseur versionnée.

Le moteur :

- vérifie l'ordre des vitesses ;
- vérifie `débit_min < débit_max` ;
- interpole linéairement les limites entre deux vitesses publiées ;
- refuse l'extrapolation hors domaine ;
- calcule les marges de débit vers la limite minimale et maximale ;
- indique seulement si le point se situe dans l'enveloppe fournie.

## Limite volontaire

Cette brique n'est pas un système anti-surge. Elle ne calcule aucune marge de sûreté cachée, n'ouvre aucun recycle et ne commande aucun compresseur. Les limites et leur provenance sont des entrées fournisseur/projet.

La carte débit/rapport de pression/rendement reste séparée de l'enveloppe opératoire afin que les deux sources puissent être versionnées et auditées indépendamment.

## Gate

Un usage pilote exige cartes et enveloppes réelles, propriétés gaz/composition validées et revue thermofluides. Aucune conformité constructeur ou réglementaire n'est déduite des tests logiciels.
