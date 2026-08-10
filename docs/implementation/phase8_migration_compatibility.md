# Phase 8 — Compatibilité de migration et retour arrière

Références : D05, D15, D17 et D18.

## Implémentation

`hydro_shared.migration_evidence` enregistre les preuves d'un exercice entre deux releases/révisions :

- environnement représentatif et archive de preuve ;
- application effective de l'upgrade ;
- readiness de la nouvelle release ;
- intégrité des données après upgrade ;
- stratégie de rollback réellement testée (`alembic_downgrade` ou `database_restore`) ;
- exécution du rollback ;
- readiness de la release précédente ;
- intégrité des données après rollback.

L'évaluation produit une liste de violations explicite.

## Règles

- la présence d'une fonction Alembic `downgrade()` ne vaut pas preuve de rollback ;
- une restauration non exécutée ne peut pas fermer le gate ;
- upgrade et rollback doivent être testés sur un environnement représentatif ;
- le mécanisme de rollback choisi est conservé dans la preuve ;
- ce contrôle ne garantit pas à lui seul le zéro-downtime ou la haute disponibilité.

## Gate

Avant production, l'exercice doit être associé au manifeste de déploiement, au backup/restore, aux métriques de readiness et au runbook opérationnel de la release concernée.
