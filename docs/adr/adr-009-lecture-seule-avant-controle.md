# ADR-009 — Lecture seule avant tout contrôle

- **Statut** : Acceptée
- **Date** : 2026-08-02
- **Source** : Documentation complète du MVP v2.0 (annexe E) et D11 § 12

## Contexte

Une plateforme d'analyse raccordée trop tôt à un système de conduite crée un risque opérationnel majeur.

## Décision

Le MVP est un **outil d'analyse et d'aide à la décision**. Il n'émet aucune commande vers un automate, un PLC ou un SIS (DEC-SAFETY-001). Les futurs connecteurs industriels (OPC UA, PLC4X) seront en lecture seule et isolés par une passerelle sur un réseau segmenté.

## Conséquences

Positif : réduction du risque, validation progressive du cœur scientifique.

Négatif : certaines fonctions d'exploitation restent manuelles ; c'est le périmètre assumé du MVP.

Contrôle : aucun endpoint d'écriture vers l'OT n'est exposé, et un test d'architecture le vérifie.
