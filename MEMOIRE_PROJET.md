# Mémoire du projet PETROLE

Dernière mise à jour : 3 août 2026.

Ce fichier sert de point de reprise entre deux sessions de développement. Il décrit l'état
constaté du dépôt, les preuves disponibles et les prochaines actions. Toute nouvelle session
doit d'abord lire ce fichier, puis vérifier les informations variables avec `git status`,
`git log`, Docker et les tests. Une affirmation ancienne ne remplace jamais une vérification.

## Objectif du MVP

Construire une plateforme web d'ingénierie pour le transport et le stockage d'hydrocarbures
liquides : pipelines, stations de pompage, réservoirs, transferts, scénarios, contrôles
physiques, optimisation et rapports. Le backend doit être terminé et qualifié avant que le
frontend soit considéré comme livré.

Le frontend est développé en parallèle. Ses fichiers, branches et travaux non validés doivent
être préservés. Aucun remplacement massif de `apps/web` n'est autorisé sans comparaison et
accord explicite.

## Sources de vérité

- spécification MVP : `docs/specifications/` ;
- qualification backend : `docs/validation/qualification_backend_mvp.md` ;
- conformité normative : `docs/validation/matrice_conformite_normative.md` ;
- recette backend : `docs/validation/recette_backend_mvp.md` ;
- décisions d'architecture : `docs/adr/` ;
- procédure VPS : `deployment/VPS.md` ;
- code et tests du dépôt : preuve finale en cas de divergence documentaire.

## État vérifié avant préparation VPS

- branche de référence : `main` ;
- dernier commit de qualification connu avant cette préparation : `2127f9d` ;
- validation Docker : 482 tests ;
- validation hôte : 473 tests ;
- couverture mesurée : 83 % ;
- validation scientifique : 41 cas sur 41 réussis ;
- comparaisons externes présentes : STANET, OpenModelica, pandapipes et DWSIM ;
- écart documenté du cas de transition : 24,889 %, accepté uniquement dans le cadre et avec
  les réserves décrits par le dossier de qualification ;
- analyses Trivy et ZAP locales non terminées lors de la dernière campagne à cause de délais de
  téléchargement. Elles doivent être relancées sur le VPS ;
- GitHub Actions indisponible pour raison de quota. La preuve de livraison repose donc sur les
  tests locaux ou VPS, leurs journaux et le commit Git exact.

Ces résultats qualifient le périmètre testé. Ils ne démontrent pas une conformité réglementaire
complète ni une aptitude à exploiter un site réel sans données industrielles, textes officiels
applicables et validation par un ingénieur habilité.

## Résultats de la préparation VPS du 3 août 2026

- images Docker de qualification API et web construites depuis un environnement propre ;
- 483 tests backend réussis dans Docker après correction de l'isolation de configuration FastAPI ;
- frontend : typecheck réussi, 2 tests unitaires réussis et build de production réussi ;
- Compose validé pour développement et production avec Caddy et services de qualification ;
- Caddyfile validé par Caddy 2.11.4 ;
- scripts Bash validés par `bash -n` et ShellCheck ;
- script de transfert Windows validé par l'analyseur PowerShell ;
- défaut de dépendance corrigé : le serveur de test récent utilise `httpx2`, tandis que le test
  de charge autonome utilise `httpx` ; les deux dépendances sont désormais explicites.

Un essai de charge effectué pendant les constructions Docker sur la machine Windows a mesuré un
p95 de 6,73 s avec une erreur sur 500 requêtes. Un second essai sur API dédiée, sans rechargement,
a obtenu 500 réponses HTTP 200 mais un p95 de 7,65 s. Les 25 requêtes simultanées uniques passent
à 1,69 s, mais les rafales répétées dépassent le seuil. Ces mesures contredisent l'ancien p95 de
0,603 s et ne doivent pas être masquées. La campagne VPS conserve le détail des statuts et doit
décider si l'écart vient de Docker Desktop, du dimensionnement ou du backend.

Une sauvegarde locale cohérente a été créée sous
`var/backups/20260803T112142Z` : PostgreSQL 131 321 octets, stockage objet 96 824 octets,
révision Alembic `4d7f9a3b2c85 (head)`. Les empreintes figurent dans son `manifest.json`. Après
l'exercice, une restauration complète de cette sauvegarde a réussi le 3 août 2026 à 11:27 UTC.
Le test a révélé puis corrigé la recherche du conteneur MinIO arrêté (`ps --all --quiet`). API,
worker, PostgreSQL, MinIO et web ont redémarré ; `/api/v1/health/ready` retourne `ready`, le web
retourne HTTP 200 et leurs ports hôte sont liés à `127.0.0.1`.

L'image E2E Playwright n'a pas terminé son téléchargement local en dix minutes. Le test E2E
conteneurisé reste donc à exécuter sur le VPS, comme Trivy et ZAP.

Le test E2E public, Trivy, ZAP, la restauration réelle, le redémarrage et le certificat définitif
restent à exécuter sur le VPS, car ils exigent son domaine, son accès SSH et ses services actifs.

## Architecture utile

- `apps/api` : API FastAPI ;
- `apps/web` : frontend React, TypeScript et Vite ;
- `packages/hydroliquid` : calcul hydraulique ;
- `packages/tank_transfer` : réservoirs et transferts ;
- `packages/optimization` : optimisation ;
- `packages/reporting` : rapports ;
- `packages/validation` et `tests` : validation scientifique et fonctionnelle ;
- `database/migrations` : migrations Alembic ;
- `deployment` : images, Compose, sauvegarde, restauration et VPS.

## Développement local et VPS

Le mode développement monte le dépôt et `apps/web` en volumes. Les changements Python et
TypeScript sont rechargés automatiquement ; une reconstruction reste requise après modification
des dépendances ou d'un Dockerfile.

Sur VPS, utiliser Ubuntu, Docker Engine, Compose, Caddy, PostgreSQL et MinIO. Les ports API,
PostgreSQL, MinIO et Vite/nginx restent liés à `127.0.0.1`. Seuls SSH, HTTP et HTTPS doivent être
exposés. Les secrets résident dans `deployment/.env.vps`, ignoré par Git et limité au propriétaire.

Commandes principales sur le VPS :

```bash
./deployment/scripts/vps/generate-env.sh petrole.exemple.com administrateur@exemple.com
./deployment/scripts/vps/deploy.sh development
./deployment/scripts/vps/restore.sh --confirm-replacement \
  /opt/petrole/var/incoming-backup/<sauvegarde> development
./deployment/scripts/vps/qualify.sh development
./deployment/scripts/vps/backup.sh development
```

Passer à `production` seulement lorsque les modifications nécessitant un rechargement automatique
sont terminées et que la campagne de qualification VPS est réussie.

## Règles de collaboration avec le frontend parallèle

1. Exécuter `git status --short`, `git branch --show-current` et `git worktree list` avant édition.
2. Ne jamais écraser, réinitialiser ou supprimer un travail non commité.
3. Préférer une branche dédiée et des commits ciblés.
4. Synchroniser les contrats OpenAPI avant d'adapter le frontend.
5. Vérifier typecheck, tests, E2E et build après fusion du frontend.
6. Le fichier local `docs/charte graphique.png` était non suivi lors de cette préparation : le
   conserver tant que son propriétaire n'a pas décidé de son intégration.

## Prochaines preuves attendues sur VPS

- HTTPS valide sur le domaine définitif ;
- `GET /api/v1/health/ready` public réussi ;
- campagne `qualify.sh` réussie, y compris Trivy et ZAP ;
- charge API et workflows métier réussis ;
- exercice sauvegarde/restauration réussi ;
- redémarrage du VPS sans perte de disponibilité durable ni de données ;
- copie chiffrée des sauvegardes hors du VPS ;
- revue des scénarios partiels et écarts `MUST` encore ouverts dans les documents de validation ;
- recette du frontend parallèle après intégration.

## Discipline de reprise

- communiquer et documenter en français précis ;
- ne jamais enregistrer de secret dans Git, les journaux ou ce fichier ;
- ne pas annoncer « conforme » ou « 100 % » sans preuve correspondant au périmètre annoncé ;
- corriger d'abord les erreurs réelles, puis mettre à jour tests et documentation ;
- mettre à jour ce fichier à chaque jalon, avec date, commit, tests réussis et limites restantes.
