# Phase 5 — Spool SQLite durable de passerelle

Référence principale : D15 §6, complétée par D09/D12/D17.

## Implémentation

`hydro_api.industrial.sqlite_spool` fournit un stockage local durable indépendant du connecteur réseau :

- SQLite en mode WAL ;
- `synchronous=FULL` ;
- payload brut BLOB conservé avant conversion SI ;
- SHA-256 du payload ;
- séquence locale `AUTOINCREMENT` ;
- clé d'idempotence unique ;
- `SourceTimestamp`, provenance et date d'écriture ;
- replay strictement identique retournant la même séquence ;
- conflit si une même clé d'idempotence porte un payload différent ;
- lecture ordonnée après checkpoint ;
- checkpoint persistant par `connector_ref + checkpoint_version` ;
- séquence et dernière clé d'idempotence conservées dans le checkpoint ;
- refus d'une régression de checkpoint ;
- refus de changer la clé d'idempotence pour une séquence de checkpoint identique ;
- absence de checkpoint représentée explicitement par `None` ;
- compaction uniquement jusqu'à une séquence explicitement acquittée.

Le `StoredSpoolRecord` se projette vers le contrat `BufferedIndustrialRecord` du noyau checkpoint/ordre. Le checkpoint durable utilise directement `ConnectorCheckpoint` afin d'éviter un second contrat divergent.

## Validation logicielle

Les tests ferment/réouvrent réellement la base SQLite et vérifient que payloads, ordre, séquences **et checkpoint** persistent. Ils vérifient également l'idempotence, la monotonie du checkpoint et la compaction de préfixe.

## Limites

Cette preuve n'est pas encore un test de coupure électrique/process kill au milieu d'une transaction. La qualification de passerelle devra ajouter des crash tests, rotation/capacité disque et chiffrement/permissions adaptés à l'environnement de déploiement.

Le spool ne contient aucune fonction de Write OPC UA, de commande PLC/RTU ou d'acquittement d'alarme.
