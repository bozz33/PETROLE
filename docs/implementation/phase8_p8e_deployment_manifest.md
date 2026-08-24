# Phase 8 — P8-E Manifeste de déploiement reproductible

Références : D05, D11, D15, D17 et D18.

## Implémentation

`hydro_shared.deployment_manifest` lie une tentative de déploiement à :

- identifiant et environnement ;
- release et SHA Git complet ;
- empreinte du manifeste de release ;
- révision de migration ;
- empreinte de configuration ;
- images OCI identifiées uniquement par digest `sha256:` ;
- release précédente et référence du runbook de rollback lorsqu'un retour arrière est prévu.

Le manifeste est sérialisé canoniquement et possède sa propre empreinte SHA-256.

## Règles

- aucun tag mutable tel que `latest` n'est accepté comme identité d'image ;
- un seul digest par service dans un manifeste ;
- rollback et release précédente sont atomiques : les deux sont présents ou absents ;
- ce manifeste ne contient pas de secret ;
- le manifeste ne déclenche pas lui-même le déploiement.

## Limite

La reproductibilité documentaire n'est pas une preuve de disponibilité, de failover, de compatibilité de migration ou de restauration. Ces propriétés restent à démontrer par CI, staging, exercices de reprise et infrastructure représentative.
