# Phase 5 — P5-B simulateur OPC UA de laboratoire

Statut : simulateur déterministe OT-1 implémenté, **pas un serveur OPC UA wire-protocol et pas une qualification IEC 62541**.

## Références

- D14 : POC-OS-08 open62541/PLC4X en lecture seule ;
- D15 : OT-1 POC hors ligne sur simulateur OPC UA ;
- D15 : `StatusCode`, `SourceTimestamp`, `ServerTimestamp`, séquences, buffer/reprise et absence totale de commande ;
- `docs/implementation/phase5_scada_readonly_execution.md` : sous-lot P5-B.

## Objectif

Le module `hydro_api.industrial.opcua_lab_simulator` permet de qualifier hors ligne la logique PETROLE située **au-dessus** du futur client/gateway OPC UA réel. Il génère des messages de laboratoire déterministes qui réutilisent les contrats `OpcUaDataValue`, `OpcUaSequenceTracker` et la politique read-only existants.

## Portée implémentée

- `SimulatedMonitoredItem` avec `tag_ref`, namespace URI, NodeId et `OpcUaDataValue` ;
- `SimulatedNotificationMessage` avec Subscription, numéro de séquence, timestamp Publish et provenance ;
- génération séquentielle de messages ;
- rollover du numéro de séquence `0xFFFFFFFF -> 1` ;
- cache Republish de taille explicitement configurée ;
- éviction FIFO déterministe des messages hors cache ;
- récupération exacte d'un message encore disponible par numéro de séquence ;
- conservation intégrale du `StatusCode`, du `SourceTimestamp` et du `ServerTimestamp` ;
- réutilisation de l'allow-list centrale qui refuse `Write`, `Call`, acquittement et toute opération hors lecture.

## Scénario OT-1 couvert

Un scénario peut publier les séquences 100, 101 et 102, ne livrer que 100 et 102 au `OpcUaSequenceTracker`, constater que 101 manque puis demander `republish(101)`. Le simulateur restitue exactement le message 101 si celui-ci est encore dans le cache. Si le cache l'a évincé, l'indisponibilité reste explicite et doit conduire le futur connecteur à marquer un trou ou à appliquer sa stratégie de reprise — jamais à fabriquer une donnée.

## Limites volontaires

Ce module ne fournit pas :

- encodage binaire OPC UA ;
- TCP, SecureChannel ou Session ;
- Endpoint Discovery ;
- certificats ou trust list réels ;
- signature/chiffrement wire `SignAndEncrypt` ;
- création de Subscription côté serveur réel ;
- acknowledgements réseau ;
- interopérabilité avec un SDK ou serveur OPC UA réel.

Ces éléments relèvent de P5-C et du POC-OS-08 avec la passerelle dédiée retenue par D14, notamment open62541, puis des gates OT-1/OT-2 en laboratoire.

## Tests

`tests/test_opcua_lab_simulator.py` vérifie :

- détection d'un trou puis récupération Republish ;
- éviction bornée du cache ;
- rollover des séquences ;
- refus de `Write` et `Call` ;
- conservation qualité et double horodatage ;
- refus d'un timestamp Publish sans fuseau ;
- fonctionnement avec cache Republish désactivé.

## Statut de qualification

`IMPLEMENTED_OFFLINE_SIMULATOR_NOT_WIRE_PROTOCOL_QUALIFIED`

P5-B ferme la brique de simulation comportementale interne. OT-1 n'est considéré comme complètement fermé qu'après exécution du même contrat contre un vrai serveur/simulateur OPC UA et la future passerelle réseau avec certificats et `SignAndEncrypt`.
