# Phase 5 — P5-C contexte de sécurité OPC UA

Statut : validation déterministe des preuves de sécurité implémentée, **sans client réseau réel et sans manipulation de clé privée dans l'application**.

## Références

- D14 §6 et §9 : `open62541` dans une passerelle dédiée et POC-OS-08 lecture seule ;
- D15 §§4, 6 et 7 : certificats, trust-list/révocation, secrets hors Git, `SignAndEncrypt`, politique approuvée et endpoint contrôlé ;
- `phase5_scada_readonly_execution.md`.

## Séparation des responsabilités

`hydro_api.industrial.opcua_security_context` n'ouvre aucun `SecureChannel`, ne parse aucun certificat et ne résout aucun secret. Ces opérations appartiennent à la future passerelle réseau open62541.

La couche PETROLE reçoit uniquement des métadonnées et preuves déjà extraites :

- référence du certificat ;
- `ApplicationUri` ;
- empreinte SHA-256 ;
- période de validité ;
- noms DNS déclarés ;
- référence de preuve ;
- snapshot versionné de trust-list et révocation.

Ainsi, aucune clé privée, aucun mot de passe et aucun certificat brut n'est persisté par ce contrat.

## Politique approuvée

`OpcUaSecurityApproval` exige explicitement :

- une référence d'approbation OT ;
- une ou plusieurs URI `SecurityPolicy` approuvées ;
- l'`ApplicationUri` attendue du serveur.

Aucune `SecurityPolicy` n'est choisie par défaut dans PETROLE. La sélection reste une décision du site et de la revue OT conformément à D15.

## Gate fail-closed

`assess_opcua_security_context(...)` refuse le contexte lorsque l'une des situations suivantes est observée :

- `SecurityPolicy` configurée non approuvée ;
- certificat client différent de celui référencé par la configuration ;
- trust-list différente de la version référencée ;
- certificat client ou serveur pas encore valide ;
- certificat client ou serveur expiré ;
- certificat serveur absent de la trust-list ;
- certificat serveur révoqué ;
- `ApplicationUri` serveur différente de celle approuvée ;
- hôte de l'endpoint absent des identités DNS observées du certificat serveur.

L'instant d'évaluation est obligatoire et timezone-aware. Les empreintes SHA-256 sont normalisées sans supprimer leurs références de preuve.

## Ce qui reste à P5-C

Cette brique ferme le **contrat de décision de sécurité**, pas le réseau OPC UA. Restent notamment :

1. passerelle dédiée construite avec la version open62541 approuvée et verrouillée ;
2. chargement réel du certificat applicatif et de la clé depuis le mécanisme de secrets du site ;
3. configuration réelle du `CertificateGroup` / trust-list / révocation ;
4. sélection d'endpoint avec `SignAndEncrypt` et `SecurityPolicy` approuvée ;
5. session, reconnexion et backoff réseau ;
6. subscriptions réelles et flux `Publish`/acknowledgements/`Republish` ;
7. conversion des `DataValue` réseau vers le contrat PETROLE déjà implémenté ;
8. qualification POC-OS-08 puis OT-0…OT-5 sur environnement représentatif.

Aucun `Write`, `Call` procédé, acquittement d'alarme, SIS/ESD ou changement de consigne n'est ajouté.

## Tests

`tests/test_opcua_security_context.py` couvre :

- contexte entièrement approuvé ;
- politique non approuvée ;
- incohérence de références ;
- serveur non approuvé ou révoqué ;
- validité temporelle des certificats ;
- `ApplicationUri` et identité DNS de l'endpoint ;
- validation/normalisation des empreintes ;
- absence de politique implicite ;
- obligation d'un instant d'évaluation timezone-aware.

## Statut de qualification

`IMPLEMENTED_SECURITY_EVIDENCE_GATE_NOT_NETWORK_VALIDATED`
