# Phase 8 — P8-I Exercice incident et runbook

Références : D05, D15, D17 et D18.

## Implémentation

`hydro_shared.incident_drill` représente une preuve d'exercice avec :

- référence du drill ;
- runbook, version et empreinte SHA-256 ;
- horodatages start / acknowledgement / recovery ;
- archive de preuves ;
- vérification communication et escalade ;
- objectifs explicites de temps d'acquittement et de reprise.

L'évaluation publie les temps observés et chaque violation sans marge cachée.

## Règles

- la chronologie doit respecter `start < acknowledgement <= recovery` ;
- les objectifs sont fournis par le protocole/SLA visé, jamais codés par défaut ;
- le runbook est identifié par contenu ;
- communication et escalade sont des preuves distinctes du retour technique du service.

## Limite

Un drill vert ne prouve pas à lui seul un support 24/7, un SLA contractuel ou une capacité de crise en production. Ces éléments exigent organisation, astreinte, contacts, contrats et exercices représentatifs.
