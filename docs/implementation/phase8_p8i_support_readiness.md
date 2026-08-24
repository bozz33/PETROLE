# Phase 8 — P8-I readiness opérationnelle du support

Statut : contrat de couverture support/runbooks implémenté, **sans prétendre qu'une astreinte ou un SLA de production existe réellement**.

## Références

- D05 : maintenabilité, observabilité, continuité et recette non fonctionnelle ;
- D15 §12 : détecter, contenir, préserver, éradiquer, restaurer, apprendre, notifier ;
- D17 : passage site unique → multi-sites conditionné notamment par la supervision et la capacité support ;
- `phase8_p8i_incident_drill.md`.

## Objectif

Le drill P8-I existant mesure un exercice réel contre des objectifs de temps et vérifie communication/escalade. Le présent contrat couvre le verrou précédent : avant de tester un incident, les classes d'incident requises doivent disposer d'un runbook actif, versionné et revu.

`hydro_shared.support_readiness` ne contacte personne et ne crée aucune organisation d'astreinte. Il vérifie uniquement des références et une couverture explicite.

## Phases de réponse

`IncidentResponsePhase` reprend les phases structurées par D15 :

- `detect` ;
- `contain` ;
- `preserve` ;
- `eradicate` ;
- `restore` ;
- `learn` ;
- `notify`.

PETROLE ne suppose pas que chaque classe exige systématiquement les sept phases. `IncidentClassRequirement` reçoit du protocole/opérateur la liste exacte des phases obligatoires pour chaque classe.

## Runbooks

Chaque `SupportRunbookDescriptor` conserve :

- classe d'incident ;
- référence du runbook ;
- version ;
- SHA-256 du contenu ;
- rôle responsable ;
- référence de revue ;
- date de revue timezone-aware ;
- phases couvertes.

Le contrat refuse un runbook sans identité de contenu, sans revue ou sans phase déclarée.

## Organisation de support

`SupportOrganizationEvidence` exige des références vers :

- politique support ;
- matrice d'escalade ;
- roster de contacts ;
- politique de maintenance ;
- archive de preuve.

Aucune donnée personnelle n'est stockée par cette couche. La référence du roster pointe vers le système organisationnel approprié.

## Évaluation

`assess_support_readiness(...)` refuse notamment :

- une classe requise sans runbook ;
- une phase obligatoire absente du runbook ;
- deux exigences actives pour la même classe ;
- deux runbooks actifs pour la même classe ;
- une référence de runbook dupliquée ;
- un runbook actif pour une classe qui n'appartient plus au protocole courant.

Le dernier cas est volontaire : un ancien runbook ne doit pas rester silencieusement présenté comme couverture courante après modification du protocole.

## Relation avec l'exercice incident

La readiness documentaire ne remplace pas `IncidentDrillEvidence`. Une organisation peut avoir tous ses runbooks et échouer un exercice. Inversement, un drill ponctuel réussi ne prouve pas un service de support durable.

La séquence attendue est :

1. protocole/classes d'incident approuvés ;
2. readiness support positive ;
3. exercices représentatifs utilisant les versions exactes des runbooks ;
4. preuves de temps, communication et escalade ;
5. revue humaine des résultats et du modèle de support.

## Ce qui reste externe

- organisation réelle du support ;
- personnes et rôles effectivement disponibles ;
- horaires/astreinte ;
- contrats et SLA ;
- canaux de notification ;
- outils de ticketing/on-call ;
- exercices représentatifs et post-mortems ;
- capacité multi-sites mesurée.

## Statut de qualification

`IMPLEMENTED_SUPPORT_READINESS_CONTRACT_NOT_OPERATIONALLY_VALIDATED`
