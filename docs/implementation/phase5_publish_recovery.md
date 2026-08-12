# Phase 5 — Publish acknowledgements et reprise Republish

Statut : logique déterministe de transport implémentée, **sans appel réseau OPC UA réel**.

## Références

- D15 : subscriptions, acknowledgements/Republish, trous de séquence, reprise et buffer local ;
- OPC UA Part 4 v1.05.07 : services Publish et Republish ;
- `opcua_sequence.py` : détection des doublons, messages anciens et séquences manquantes ;
- `buffer_checkpoint.py` / `sqlite_spool.py` : durabilité locale avant ingestion aval.

## Distinction de sécurité

PETROLE distingue désormais deux notions qui ne doivent pas être confondues :

- `SUBSCRIPTION_ACKNOWLEDGE` : acknowledgement de transport d'un `NotificationMessage` déjà reçu et durablement persisté ; autorisé car il ne modifie pas le procédé ;
- `ACKNOWLEDGE` : acquittement d'alarme/événement procédé ; interdit dans le périmètre read-only, au même titre que `WRITE` et `CALL`.

`REPUBLISH` est également une opération read-only autorisée : elle demande la retransmission d'un `NotificationMessage` manquant encore présent dans la retransmission queue du serveur.

## Règle de durabilité

`plan_publish_recovery(...)` ne propose l'acknowledgement du message reçu que lorsque l'appelant indique `notification_durable=True`.

Si la persistance locale n'est pas confirmée, aucun acknowledgement n'est produit. Cette règle évite qu'un futur gateway fasse supprimer de la retransmission queue serveur un message qui n'aurait pas encore été rendu durable côté PETROLE.

Les numéros manquants détectés par `OpcUaSequenceTracker` sont transformés en `OpcUaRepublishRequest`. Le module ne reconstruit, n'interpole et ne synthétise aucune donnée absente.

## Limites

La brique produit uniquement un plan d'actions. Elle ne réalise pas :

- le `PublishRequest` réseau ;
- l'encodage des `subscriptionAcknowledgements[]` ;
- le `RepublishRequest` réseau ;
- la gestion d'une Session/SecureChannel ;
- le mapping des StatusCodes réseau retournés par le serveur ;
- la politique opérateur en cas de `Bad_MessageNotAvailable`.

Ces fonctions appartiennent au futur adapter/gateway P5-C et devront être vérifiées sur un serveur OPC UA réel ou un simulateur wire-protocol pendant OT-1/OT-2.

## Tests

`tests/test_opcua_publish_recovery.py` couvre :

- acknowledgement d'un message durable ;
- absence totale d'acknowledgement tant que le message n'est pas durable ;
- génération des demandes Republish pour les trous ;
- ré-acknowledgement possible d'un doublon déjà durable ;
- validation des SubscriptionId et numéros de séquence.

## Statut de qualification

`IMPLEMENTED_TRANSPORT_RECOVERY_PLAN_NOT_NETWORK_QUALIFIED`
