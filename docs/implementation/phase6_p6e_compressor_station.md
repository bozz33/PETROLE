# Phase 6 — P6-E Configuration de station de compression

Référence principale : D07 §10, complétée par D10/D17.

## Implémentation

`hydro_gas.station` décrit la topologie documentaire minimale d'une station :

- unités compresseur `main` ou `standby` ;
- référence de carte de performance et d'enveloppe opératoire pour chaque unité ;
- refroidisseurs ;
- vannes d'isolation, bypass, recycle, check ou control ;
- référence éventuelle du chemin de bypass ;
- provenance/version projet via les références de chaque équipement.

Le contrat exige au moins une unité principale et des identifiants d'équipements uniques à l'échelle de la station.

## Limites

Cette brique n'exécute aucune régulation, aucune sélection main/standby, aucun anti-surge, aucune logique de recycle et aucune commande de vanne. Les rôles `control`/`recycle` décrivent l'inventaire de l'installation, pas une capacité de contrôle de PETROLE.

## Suite

Les futurs solveurs de station consommeront cette configuration avec les cartes fournisseur, les propriétés gaz et les conditions réseau. Les lois énergétiques/régulation seront ajoutées seulement après sélection scientifique explicite et validation indépendante.
