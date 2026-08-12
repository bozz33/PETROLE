# Phase 8 — P8-H preuve de chaos ciblé

Statut : contrat de preuve et évaluation déterministe implémentés, **sans moteur d'injection de panne et sans qualification d'une infrastructure réelle**.

## Références

- D17 : P8-H tests de charge, chaos ciblé, reprise et capacité ;
- D18 : preuves de CI/release et contrôles reproductibles ;
- D20 : critères approuvés avant passage pilote/production ;
- `phase8_industrialization_execution.md`.

## Principe

`hydro_shared.chaos_evidence` ne lance aucun scénario de chaos. L'outil externe ou l'équipe d'exploitation fournit un protocole pré-enregistré avec :

- référence de politique ;
- référence du scénario ;
- cible précise ;
- temps maximal de reprise ;
- fraction maximale d'erreurs ;
- exigences explicites d'intégrité des données et d'isolation des périmètres.

L'évidence observée fournit ensuite le temps de reprise, le nombre de requêtes, les échecs et les constats de récupération, intégrité et isolation.

## Évaluation

`assess_chaos_experiment(...)` compare les observations aux seuls objectifs fournis. Les violations possibles sont explicites :

- service non rétabli ;
- temps de reprise supérieur à l'objectif ;
- fraction d'erreurs supérieure à l'objectif ;
- intégrité des données non préservée lorsqu'elle est exigée ;
- isolation de périmètre non préservée lorsqu'elle est exigée.

Aucune tolérance cachée, aucun scénario par défaut et aucune injection automatique ne sont présents.

## Porte de qualification

`DeploymentQualificationEvidence` exige désormais une `ChaosExperimentAssessment` en plus des preuves de restauration, migration, charge, sécurité et readiness. Une preuve de charge réussie ne peut donc pas suffire à déclarer la baseline logicielle qualifiée si le scénario de résilience requis échoue.

Cette porte reste une qualification **logicielle et environnementale**. Elle ne constitue ni une certification industrielle, ni la preuve d'une haute disponibilité réelle sur un site qui n'a pas exécuté les exercices référencés.

## Tests

`tests/test_chaos_evidence.py` couvre :

- scénario conforme ;
- accumulation de toutes les violations observées ;
- activation explicite des exigences d'intégrité/isolation ;
- validation des références, délais, ratios et compteurs ;
- intégration du résultat dans `tests/test_qualification_gate.py`.

## Statut de qualification

`IMPLEMENTED_EVIDENCE_CONTRACT_NOT_INFRASTRUCTURE_VALIDATED`
