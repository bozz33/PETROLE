# Phase 5 — Configuration OPC UA read-only sécurisée

Référence principale : D15 §5, complétée par D08/D17/D20.

## Implémentation

`hydro_api.industrial.opcua_config` définit le contrat de configuration indépendamment du futur SDK réseau :

- endpoint `opc.tcp://` avec hôte et port explicites ;
- mode `SignAndEncrypt` obligatoire ;
- URI de politique de sécurité explicite ;
- référence du certificat applicatif ;
- référence externe de clé privée ;
- trust-list versionnée ;
- référence d'identité/credential facultative, elle aussi externalisée ;
- mapping stable `tag PETROLE ↔ namespace URI + NodeId` avec provenance ;
- unicité des tags et des nœuds sources.

## Règles

- aucun secret ni bloc PEM n'est accepté dans la configuration ;
- aucune politique de sécurité n'est choisie automatiquement par PETROLE ;
- aucune découverte dynamique n'est utilisée comme mapping métier permanent ;
- la configuration ne confère aucune capacité `Write`, `Call`, alarm acknowledge ou commande procédé.

## Choix de bibliothèque

Aucun SDK OPC UA concret n'est encore sélectionné dans D15/D17 ni dans les dépendances du dépôt. Le client réseau reste donc derrière ce contrat jusqu'à décision technique explicite et qualification sur simulateur. PETROLE ne sélectionne pas `asyncua`, `open62541` ou une autre bibliothèque uniquement par convenance d'implémentation.
