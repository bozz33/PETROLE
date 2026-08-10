# V1-F — Sécurité du pilote

Statut : garde-fous applicatifs et dossier de readiness ; ne remplace pas la revue OT/site.

Base : V1-B1 `6d18ef39d16c2dd9ae34128ccf6d87f4788e19bc`.

## Références

- D05 exigences non fonctionnelles ;
- D15 sécurité/SCADA/historisation ;
- D17 Phase 2 « sécurité, première installation » ;
- D18 tests/CI/release ;
- D20 cybersécurité, comptes temporaires, moindre privilège, sauvegarde/restauration et incident.

## Gates logiciel pilote

- environnement staging/production explicite ;
- authentification activée ;
- secret JWT non-développement ;
- SHA de build complet et traçable ;
- mode `single_org` correctement lié pour un déploiement mono-exploitant ;
- preuve HTTPS ;
- test sauvegarde/restauration ;
- scan de vulnérabilités selon politique du projet ;
- revue des accès et contacts d'incident ;
- aucune écriture SCADA/SIS/ESD.

OIDC/MFA doit être intégré avec l'IdP réel du pilote ; aucune implémentation fictive ne sera déclarée conforme avant choix et test du fournisseur d'identité.
