# Phase 5 — Buffer local, checkpoint et idempotence

Référence principale : D15 §6, complétée par D09, D12 et D17.

## Implémentation

`hydro_api.industrial.buffer_checkpoint` définit le noyau déterministe qui sera utilisé par le stockage local de la passerelle :

- séquence locale strictement positive ;
- clé d'idempotence ;
- empreinte SHA-256 du payload brut ;
- `SourceTimestamp` et provenance ;
- checkpoint versionné du dernier point confirmé ;
- déduplication d'un replay strictement identique ;
- refus d'une même clé d'idempotence associée à deux payloads différents ;
- détection d'un trou de séquence après checkpoint ;
- progression du checkpoint uniquement sur un préfixe contigu déjà traité.

## Architecture

Cette brique est volontairement indépendante de SQLite/PostgreSQL/fichier append-only. Le futur adaptateur de persistance doit garantir durabilité et transactions, puis appeler ce noyau pour décider ce qui peut être rejoué/acquitté.

## Règles

- aucun trou n'est silencieusement ignoré ;
- aucun replay modifié n'est traité comme doublon ;
- l'ordre local ne dépend pas de l'horloge du capteur ;
- la conservation brute précède toute conversion SI ;
- un arrêt/restart de PETROLE ne doit avoir aucun effet sur le système de contrôle.

## Gate

La résistance réelle aux coupures devra être testée sur le futur stockage persistant de la passerelle par arrêt brutal/reprise et vérification de l'absence de perte, duplication et réordonnancement.
