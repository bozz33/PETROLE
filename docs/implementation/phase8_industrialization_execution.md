# Phase 8 — Industrialisation multi-sites

Statut : fondations d’industrialisation exécutables, sans prétention de certification réglementaire.

Base de travail : `main = 6c0ed6aa1632eef0cb207f5ec3bcce9c382a140e`. Les fonctions seront intégrées progressivement après fermeture des gates produits précédents.

## 1. Références projet

- D05 : exigences non fonctionnelles ;
- D11 : architecture ;
- D15 : sécurité/continuité ;
- D17 : Phase 8 — multi-sites, HA, support et gouvernance ;
- D18 : tests/CI/release ;
- D20 : critères pilote/production.

## 2. Sous-lots

1. P8-A — séparation stricte des sites/projets et politique de données ;
2. P8-B — haute disponibilité PostgreSQL, stockage objet et services stateless ;
3. P8-C — sauvegarde, WAL/PITR, restauration et exercices réguliers ;
4. P8-D — observabilité : métriques, logs, traces, SLO/SLI ;
5. P8-E — déploiements reproductibles, canary/rollback et migrations compatibles ;
6. P8-F — gestion des secrets/certificats, OIDC/MFA et gouvernance des accès ;
7. P8-G — SBOM, signatures, provenance des builds et politique de dépendances ;
8. P8-H — tests de charge, chaos ciblé, reprise et capacité ;
9. P8-I — support, runbooks, incident management et maintenance ;
10. P8-J — gouvernance des règles/normes/éditions et audit multi-sites.

## 3. Fondations déjà codées

- manifeste de provenance de release avec SHA Git et empreintes d’artefacts ;
- objectifs de fiabilité explicitement fournis par le protocole : disponibilité minimale, latence P95 maximale, RPO maximal et RTO maximal ;
- évaluation déterministe des mesures observées contre ces objectifs, sans valeurs cibles cachées ;
- preuve d’exercice de reprise avec chronologie mesurée, RPO/RTO observés, intégrité base, intégrité stockage objet et readiness applicative ;
- refus d’un drill dont la chronologie est incohérente ;
- résultat détaillé des violations plutôt qu’un simple booléen de conformité ;
- preuve de campagne de charge avec objectifs explicitement fournis : latence P95, erreurs, débit et concurrence ;
- contrat de chaos ciblé sans injection de panne intégrée : politique, scénario, cible, temps de reprise et taux d’erreur sont fournis par le protocole ;
- évaluation factuelle d’un exercice de chaos avec récupération du service, intégrité des données et isolation des périmètres ;
- porte de qualification exigeant désormais restauration, migration, charge, chaos, sécurité et readiness positives pour la baseline/environnement référencés ;
- résolveur de portée organisationnelle : `single_org` utilise l’organisation interne par défaut et refuse toute tentative de sélection croisée ; `multi_org`/`saas` exigent une organisation préalablement résolue par la couche d’identité/autorisation ;
- registre d’édition normative avec code, édition, éditeur, provenance, acquisition projet et revue ;
- binding d’un jeu de règles interne versionné vers une édition uniquement lorsqu’elle est marquée acquise et revue ;
- détection explicite d’un changement d’édition exigeant une nouvelle revue ;
- aucune conservation du texte normatif protégé dans le registre de gouvernance.

Ces briques ne prouvent aucune HA à elles seules. La preuve requiert une infrastructure réelle ou représentative et des exercices reproductibles. Le contrat de chaos n’exécute lui-même aucune perturbation : il évalue seulement des observations issues d’un exercice externe pré-enregistré.

## 4. Contraintes produit

- la topologie de déploiement ne modifie jamais les résultats scientifiques ;
- aucune donnée d’un site ne doit fuiter vers un autre ;
- toutes les migrations sont réversibles ou accompagnées d’un plan de restauration ;
- les releases sont immuables, signées et traçables ;
- disponibilité et RPO/RTO sont définis contractuellement avant revendication ;
- les fonctions OT restent read-only sauf projet distinct explicitement autorisé ;
- un changement d’édition normative ne remplace jamais silencieusement le jeu de règles précédemment approuvé.

## 5. Sécurité

- défense en profondeur et segmentation ;
- MFA pour administrateurs ;
- OIDC/annuaire lorsque l’opérateur l’exige ;
- secrets hors dépôt ;
- rotation clés/certificats ;
- journalisation centralisée et conservation définie ;
- scans SAST/SCA/images, SBOM et signatures à chaque release.

## 6. Gate « produit industriel »

Aucune qualification industrielle n’est déclarée uniquement parce que le logiciel possède HA, sécurité ou observabilité. Le passage nécessite contrats, responsabilités, pilote accepté, support, procédures, exigences locales et validations externes applicables.

## 7. Multi-sites

Le produit doit supporter plusieurs sites au niveau architecture/administration lorsque le modèle commercial l’exige, mais l’expérience déployée peut rester mono-exploitant. Les utilisateurs ne choisissent pas arbitrairement une organisation dans une instance `single_org` ; l’identifiant d’organisation reste une clé d’isolation interne. Le résolveur de portée ne remplace pas RBAC/OIDC : il constitue une barrière supplémentaire de cohérence du mode de déploiement.

## 8. Gouvernance normative

Le registre interne stocke les métadonnées d’une édition et les références de revue, pas le contenu protégé de la norme. Une page publique officielle peut servir à identifier une édition ou son statut, mais un jeu de règles contractuelles n’est lié qu’après acquisition légale de l’édition applicable et revue par le responsable compétent. Une nouvelle édition reste une nouvelle référence à examiner ; elle n’est jamais considérée automatiquement compatible avec les règles précédentes.
