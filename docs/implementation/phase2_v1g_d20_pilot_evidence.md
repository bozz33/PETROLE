# Phase 2 — V1-G Dossier de preuves du pilote D20

## Objet

Cette brique transforme la campagne D20 en registre logiciel vérifiable sans automatiser la décision finale du pilote.

D20 définit douze tests :

- PIL-01 : reproduction d’un régime stable ;
- PIL-02 : deuxième débit ou configuration ;
- PIL-03 : pompe indisponible / secours ;
- PIL-04 : sensibilité rugosité / propriétés ;
- PIL-05 : transfert bac-à-bac ;
- PIL-06 : import de données imparfaites ;
- PIL-07 : rapport utilisateur ;
- PIL-08 : performance et charge ;
- PIL-09 : sécurité / RBAC / audit ;
- PIL-10 : restauration ;
- PIL-11 : UX ;
- PIL-12 : mode hors connexion si exigé.

## Contrat logiciel

`hydro_api.pilot_evidence` fournit :

- `PilotTestCode` ;
- `PilotEvidenceStatus` (`not_run`, `pass`, `fail`, `blocked`) ;
- `PilotTestEvidence` avec référence de preuve obligatoire pour un test exécuté PASS/FAIL ;
- `PilotCampaignEvidence` avec site, baseline et protocole référencés ;
- `assess_pilot_campaign(...)`.

L’évaluation détecte : tests manquants, non exécutés, bloqués, échoués et réussis.

## Séparation avec la décision Go/No-Go

Une campagne est **prête pour la revue de décision** lorsque PIL-01 à PIL-12 sont tous renseignés et qu’aucun test n’est encore `not_run` ou `blocked`.

Un test `fail` n’empêche pas la revue : il doit être présenté aux responsables pour décider, selon D20, entre GO, GO conditionnel, REWORK, NO-GO ou RESEARCH. Le logiciel ne choisit pas cette décision et ne convertit pas une somme de tests en certification.

## Gate externe

Les preuves doivent provenir du pilote réel ou anonymisé : fichiers, rapports, journaux, mesures, tests de sécurité, restauration, UX et validation ingénieur selon le cas. Les tests synthétiques du code vérifient seulement le registre et sa logique de complétude.
