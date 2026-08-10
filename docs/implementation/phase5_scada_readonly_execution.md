# Phase 5 — SCADA / historian en lecture seule

Statut : contrat d’implémentation OT, non certifiant et sans commande procédé.

Base de travail : `6d18ef39d16c2dd9ae34128ccf6d87f4788e19bc`, afin de réutiliser les tags/séries V1. Cette branche sera rebasée sur la baseline Phase 2 consolidée avant intégration.

## 1. Références projet

- D15 : sécurité, SCADA et historisation ;
- D17 : Phase 5 ;
- D20 : fichiers d’abord, historian/OPC UA read-only après revue OT ;
- D08 : IEC 62541 / IEC 62443 et règles locales applicables.

## 2. Règle non négociable

PETROLE reste un client analytique **lecture seule**. Aucun endpoint ou connecteur ne doit exposer `Write`, commande d’équipement, appel de méthode procédé, acquittement d’alarme, SIS/ESD ou changement de consigne.

## 3. Sous-lots

1. P5-A — modèle de configuration de connecteur et secrets externalisés ;
2. P5-B — simulateur OPC UA de laboratoire ;
3. P5-C — client OPC UA read-only avec certificats et trust list ;
4. P5-D — subscriptions contrôlées, `SourceTimestamp`, `ServerTimestamp`, `StatusCode` complet ;
5. P5-E — buffer local, checkpoint, déduplication et reprise ;
6. P5-F — normalisation vers les `tags`/`samples_raw` existants ;
7. P5-G — santé connecteur : latence, trous, pertes, certificat, reconnexions ;
8. P5-H — historian import/read adapter ;
9. P5-I — qualification OT-0 à OT-5 selon D15.

## 4. OPC UA

Implémentation alignée sur les spécifications OPC Foundation actives au moment du développement. Les profils et services supportés doivent être listés explicitement. Le connecteur refuse toute opération non incluse dans l’allow-list de lecture.

Exigences minimales : `SignAndEncrypt`, certificats, Endpoint configuré, namespace URI + NodeId stable, qualité réversible, timestamps doubles, backoff et trous de reconnexion visibles.

## 5. Cybersécurité

- zones/conduits et moindre privilège inspirés d’IEC 62443 ;
- aucun secret dans Git ;
- compte de service dédié ;
- réseau OT/DMZ/application séparé ;
- journalisation et rotation certificats ;
- perte de PETROLE sans effet sur la conduite.

## 6. Gate site réel

Aucune connexion à une installation réelle sans architecture approuvée par l’opérateur/OT, comptes temporaires, allow-list réseau, certificats, procédure d’incident et test sur réplique/simulateur.
