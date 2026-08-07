# Mémoire du projet PETROLE

Dernière mise à jour : 8 août 2026.

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

## Reprise du déploiement conteneurisé du 3 août 2026

- dépôt de développement installé sous `/opt/petrole` ; les sources montées sont accessibles en
  lecture par l'utilisateur non privilégié `hydro` (UID 10001) des conteneurs ;
- pile de développement démarrée avec PostgreSQL, MinIO, API, worker et web ; les ports hôte
  constatés sont `127.0.0.1:15432`, `127.0.0.1:19000`, `127.0.0.1:19001`,
  `127.0.0.1:18000` et `127.0.0.1:15173` ;
- migrations Alembic appliquées jusqu'à `4d7f9a3b2c85 (head)` ; le worker a ensuite démarré sans
  erreur et l'endpoint `http://127.0.0.1:18000/api/v1/health/ready` a retourné
  `database=ready` et `object_storage=ready` ; le serveur Vite a retourné sa page HTML ;
- correction de portabilité : les scripts VPS détectent maintenant Compose v2 sous la forme
  `docker compose` ou `docker-compose`, afin de fonctionner avec les deux installations prises
  en charge ;
- commandes de contrôle réussies : `bash -n deployment/scripts/vps/*.sh`, ShellCheck lorsque
  disponible, détection Compose et `config --quiet` pour les fichiers Compose de développement ;
- état Git de départ : `main` au commit `d6fbbfe`; `docs/charte graphique.png` reste non suivi et
  n'a pas été modifié.

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

## Synchronisation GitHub du 5 août 2026

Le serveur `/opt/petrole` était en retard de 28 commits sur `origin/release/mvp-rc1`
(localement `4d7a91e`, distant `adf0082`). Les corrections décrites par la note de
reprise « Corrections appliquées sur release/mvp-rc1 » ont été intégrées par
fast-forward pur, après vérification que l'arbre de travail était propre et qu'aucun
worktree frontend ni fichier non suivi n'était à préserver.

Appliqué sur le serveur :

- `git pull --ff-only origin release/mvp-rc1` → HEAD désormais `adf0082`, arbre propre ;
- 22 fichiers modifiés, 8 créés : migration `8b1f2d6c4e90`, `apps/api/hydro_api/models/constraints.py`,
  `packages/shared/hydro_shared/testing/postgres.py`, ADR-011 et ADR-012, tests
  `test_json_persistence.py` et `test_model_constraints.py` ;
- migration Alembic appliquée à la base de développement : `4d7f9a3b2c85 → 8b1f2d6c4e90 (head)` ;
- `alembic check` sans dérive (« No new upgrade operations detected ») ;
- la contrainte `ck_calculation_runs_status_valid` contient bien `SIM_NUMERIC_ERROR` ;
- redémarrage de l'API et du worker ; `/api/v1/health/ready` retourne
  `{"status":"ready","database":"ready","object_storage":"ready"}` ;
- validation scientifique : **41/41 cas réussis**, empreinte
  `004684cf11b9fd469540fce7ad866b6fe7f6702341388a256925481b1adb0b17`.

Limites constatées sur ce serveur :

- la politique PostgreSQL des tests (`deployment/scripts/check_test_database_policy.py`)
  n'était pas exécutable depuis le conteneur `api` car `deployment/` était en mode `0700`
  (propriétaire root uniquement), alors que le processus applicatif tourne sous
  l'utilisateur non privilégié `hydro` (UID 10001). La campagne `qualify.sh` l'exécute
  dans une base jetable dédiée ; ce point de droits reste à assouplir pour permettre
  le contrôle depuis l'intérieur du conteneur ;
- la campagne `qualify.sh` complète (Ruff, mypy, tests PostgreSQL, Trivy, Gitleaks,
  ZAP, Playwright, HTTPS public) reste à exécuter sur le VPS pour lever le tag
  `v0.1.0-rc.1`. Ce qui précède valide la synchronisation du code, la migration et la
  non-régression du noyau scientifique, pas la pleine qualification production.

## Correction de l'environnement VPS du 5 août 2026

- permissions corrigées : `deployment/` et `var/` sont désormais traversables et
  lisibles par l'utilisateur `hydro` des conteneurs, ce qui permet d'exécuter la
  politique PostgreSQL et d'écrire les preuves depuis l'intérieur des conteneurs ;
- le `.venv` local (structure Windows `Scripts/`, inutilisable sur Linux) a été
  supprimé et recréé sous `/opt/petrole/.venv` avec Python 3.12.3 système ;
  l'installation éditable `pip install -e ".[dev]"` réussit, `pip check` est propre
  et les outils `ruff`, `mypy`, `pytest`, `hydro-validate` sont disponibles.

## Qualification exécutable du 5 août 2026 (commit 8c52b87)

Le serveur n'expose pas de domaine public ni de TLS pour PETROLE, donc les étapes
Playwright, OWASP ZAP et `curl https://…` de `qualify.sh` ne sont pas exécutables
ici. Toutes les autres étapes ont été lancées et archivées sous
`var/validation-vps/qualification-run/`. Quatre défauts bloquants introduits ou
révélés par la série ADR-TEST-DB-001 ont été corrigés sur `release/mvp-rc1` :

1. `style` — `ruff format` 0.16 du serveur plus strict que la version des commits :
   reformatage de `postgres.py`, `test_auth_and_sites.py`, `test_json_persistence.py`.
2. `fix(policy)` — le scanneur AST signalait faussement `tests/qualification/import_million.py`,
   un benchmark autonome piloté par `qualify.sh` (exception prévue par l'ADR-TEST-DB-001) ;
   `tests/qualification/` est désormais exclu du contrôle.
3. `fix(api)` — `SimulationResult` est `frozen`, donc `result.status = …` du commit
   JSON strict aurait levé `FrozenInstanceError`, et `SimulationStatus.SIM_NUMERIC_ERROR`
   n'existe pas (le membre est `NUMERIC_ERROR`). Un résultat convergé avec NaN aurait
   persisté `SIM_CONVERGED` au lieu de `SIM_NUMERIC_ERROR`. Remplacé par un statut
   effectif local recopié dans `result_payload` et `calculation.status`.
4. `test(json)` — avec psycopg3, le blocage d'un NaN remonte en `ValueError` (adaptateur
   `Jsonb`) et non `StatementError` ; le test accepte désormais les deux.

Résultats vérifiés (preuves dans `var/validation-vps/qualification-run/`) :

| Contrôle | Résultat |
|---|---|
| Politique PostgreSQL (AST) | verte |
| Ruff format / lint | 131 fichiers, aucune alerte |
| Mypy | 0 erreur sur 95 fichiers |
| Base jetable PostgreSQL/PostGIS + Alembic `upgrade head` | `8b1f2d6c4e90` |
| `alembic check` | aucune dérive |
| Tests `not slow` | **499 réussis** |
| Tests `slow` (performance) | **3 réussis** (p95 1000 tronçons 0,125 s ; 10 000 tronçons 11,7 s) |
| Validation scientifique | **41/41** |
| Charge API (25 users, 500 req) | **0 erreur**, p95 **0,94 s** (NFR-PERF-005 < 2 s) |
| Frontend typecheck / tests / build | 2 tests, build 2 714 modules |
| npm audit (high+) | **0 vulnérabilité** |
| Gitleaks (137 commits) | **aucun secret** |
| Trivy image API production (`runtime`) | **0 HIGH/CRITICAL non corrigée** |
| Trivy image web production (`nginx`) | **0 HIGH/CRITICAL non corrigée** |

Note honnête sur Trivy : les images **de développement** (`hydro-platform-api`,
`hydro-platform-web`, targets `development`) contiennent des vulnérabilités HIGH/CRITICAL
**corrigées** dans des outils de build (`esbuild`, `tar`, `wheel`, `setuptools`,
`brace-expansion`). Elles ne sont jamais déployées : l'image dev monte le code en volume
et n'est utilisée qu'en développement. Seules les images **production** (`runtime` pour
l'API, `nginx` pour le web) ont été scannées propres.

Reste pour lever `v0.1.0-rc.1` : configurer un domaine public + TLS, puis
exécuter Playwright, OWASP ZAP et le contrôle HTTPS public, et réaliser la sauvegarde
et la restauration réelles sur l'infrastructure cible. Les commits correctifs
(`8206b1f`, `2766d44`, `ba94693`, `8c52b87`) sont locaux à `release/mvp-rc1` et
restent à pousser vers `origin` après revue.

## Déploiement public et qualification complète du 5 août 2026

Le domaine `petrole.distesage.com` est désormais déployé publiquement et qualifié.

### Résolution du conflit de terminaison TLS

Le VPS héberge un nginx natif servant déjà trois sites (`app.blocksdevs.com`,
`gesty.site`, `salonducinemaufeminin.net`) sur les ports 80/443, et un PostgreSQL
natif sur `127.0.0.1:5432`. Le conteneur Caddy prévu par `docker-compose.vps.yml`
ne pouvait donc pas binder ces ports. Décision d'architecture documentée par le
commit `162633b` : utiliser le **nginx natif comme terminaison TLS**, avec un
certificat Let's Encrypt géré par certbot, et reverse-proxyer vers le conteneur
`petrole-web` publié uniquement sur `127.0.0.1:15174` via l'override
`deployment/docker-compose.prod-internal.yml`. C'est cohérent avec les autres
sites du serveur et respecte la règle VPS (seuls 443 public + SSH exposés).

### Configuration DNS et TLS

- enregistrement `A petrole.distesage.com → 62.171.133.156` créé via l'API
  Cloudflare (DNS only, pour le challenge HTTP-01), token en méthode legacy ;
- certificat Let's Encrypt émis pour `petrole.distesage.com` via certbot,
  valide jusqu'au 2026-11-02, renouvellement automatique ;
- vhost nginx `/etc/nginx/sites-available/petrole.distesage.com` (hors dépôt,
  configuration hôte) avec redirection HTTP→HTTPS et headers de sécurité
  alignés sur le Caddyfile PETROLE.

### Campagne de qualification complète (commit 162633b)

`https://petrole.distesage.com` est public et `GET /api/v1/health/ready` retourne
`{"status":"ready","database":"ready","object_storage":"ready"}`. Dernières étapes
exécutées et archivées sous `var/validation-vps/qualification-run/` :

| Contrôle | Résultat |
|---|---|
| HTTPS public `ready` | HTTP 200, TLS Let's Encrypt valide |
| Playwright (bureau + mobile) | **31 tests réussis**, 3 ignorés de contexte |
| OWASP ZAP baseline | **0 FAIL**, 60 PASS (7 warnings attendus pour une SPA) |
| Sauvegarde PostgreSQL | dump 102 Ko, 239 entrées TOC, SHA `77554c…` |
| Restauration PostgreSQL (base jetable) | **35 tables**, tête Alembic `8b1f2d6c4e90` |

### Commandes de gestion du déploiement production

```bash
# Pile production (nginx hôte + conteneurs internes)
COMPOSE_PROJECT_NAME=petrole \
  docker compose --env-file deployment/.env.vps \
  -f deployment/docker-compose.yml \
  -f deployment/docker-compose.vps.yml \
  -f deployment/docker-compose.prod-internal.yml up --detach

# Redémarrage après changement de code
COMPOSE_PROJECT_NAME=petrole \
  docker compose ... restart api worker web

# Renouvellement TLS (automatique via certbot timer)
certbot renew --nginx
```

Toutes les portes de sortie de la définition de fin du MVP (§15.2 du cahier des
charges) sont désormais vertes sur ce serveur, à l'exception de l'essai utilisateur
par un ingénieur métier (décision externe). La limite « certification industrielle
non démontrée » reste inchangée : un MVP logiciel qualifié n'est pas une
autorisation d'exploiter un site réel.

## Release Candidate v0.1.0-rc.1 — 6 août 2026

Tag annoté `v0.1.0-rc.1` (commit `f71a176`) créé et poussé sur `origin`.
Cette RC ajoute à la qualification complète un **typage des payloads
scientifiques** dans l'OpenAPI public : les champs réellement consommés par les
moteurs (courbes de pompe H/Q/η/P/NPSHr, propriétés de fluide, conditions aux
limites, configuration des stations, options du solveur, surcharges
d'équipements), auparavant enfouis dans des `dict[str, Any]` opaques, sont
désormais documentés et validés par 15 sous-schémas `*Input`
(`apps/api/hydro_api/schemas/scientific.py`).

L'OpenAPI public passe de 108 à **125 schémas** et expose ces contrats avec
leurs descriptions et bornes physiques sur `https://petrole.distesage.com/docs`.

Campagne finale vérifiée avant le tag :

| Contrôle | Résultat |
|---|---|
| Tests pytest (`not slow`) | **517 réussis** (+18 nouveaux tests de schémas) |
| Tests `slow` (performance) | **3 réussis** |
| Validation scientifique | **41/41** |
| ruff format / lint / mypy | verts (132 / 96 fichiers) |
| OpenAPI public | **125 schémas** (payloads scientifiques typés) |
| Trivy image API prod (rebuilt) | **0 HIGH/CRITICAL** |
| HTTPS public `ready` | HTTP 200 |

Commit du typage : `f71a176`. Les 9 commits de la série RC (`8206b1f` →
`f71a176`) sont désormais poussés sur `origin/release/mvp-rc1`.

## Fermeture MVP — lots F04 à F07 (8 août 2026)

### MVP-F05 — transfert piloté par le réseau

`TransferCreate` reçoit un bloc `hydraulic_context` facultatif : version de
modèle, scénario, nœuds de raccordement, chemin orienté et groupe de pompage. Le
résolveur du point de fonctionnement interroge HydroLiquid à chaque évolution des
niveaux ; le débit redevient l'inconnue, pression de refoulement et puissance
deviennent des sorties. Les fournir en entrée est refusé.

Le chemin n'est jamais deviné : continuité, orientation, absence de boucle et
aboutissement sont vérifiés avant tout calcul.

**Blocage levé au passage** : le normaliseur refusait purement et simplement les
nœuds de type réservoir, alors que le moteur sait convertir un niveau en pression
statique dès que le pipeline porte ses bacs d'extrémité. Un raccordement de bac
est désormais admis aux extrémités du chaînage et alimente `origin_tank` et
`destination_tank` du paquet canonique. Sans cela, aucun transfert couplé
n'était possible.

### MVP-F04 — résultats et graphiques

Bilans par tronçon, par station et par pompe ; informations numériques de
résolution ; graphiques du profil hydraulique, de la pression et de la vitesse,
du rendement et de la puissance, du NPSH, de l'évolution d'un transfert et de la
comparaison des calculs. La courbe réseau du graphique pompe-réseau est
explicitement désignée comme reconstituée, faute d'être publiée par le moteur.

### MVP-F06 — entrées et sorties de données

Import JSON accepté sous deux formes, une forme ambiguë étant refusée plutôt que
devinée. Pièces jointes documentaires séparées de l'import scientifique, avec
leurs propres formats. Exports XLSX, CSV par section et JSON canonique des
résultats persistés.

### MVP-F07 — validation et Pyomo

Approbation de la simulation elle-même, distincte de celle du rapport :
irréversible, tracée, et refusée si le calcul n'est pas éligible à une décision.

Voie Pyomo fournie sans travestir la physique : le comportement hydraulique
reste évalué par simulation, faute de formulation algébrique fermée ; Pyomo pose
le problème réellement linéaire qui subsiste, choisir une configuration parmi
celles évaluées. Un test de concordance vérifie que les deux voies retiennent le
même optimum. Le solveur MILP HiGHS est embarqué : sans lui, la voie serait
purement déclarative.

### Preuves

Campagne complète : [`docs/validation/qualification_backend_mvp_20260808.md`](docs/validation/qualification_backend_mvp_20260808.md).

540 tests backend, 41/41 scientifiques avec empreinte **inchangée**, 45 tests
web, 33 Playwright, ruff, mypy, TypeScript et build verts, `npm audit` sans
vulnérabilité, gitleaks sans secret, Trivy sans HIGH/CRITICAL corrigeable, ZAP
sans échec, sauvegarde et restauration vérifiées.

### Comptes de recette

Deux comptes dédiés existent sur l'instance, avec leurs rôles métier :
`recette-engineer@petrole.distesage.com` (engineer) et
`recette-approver@petrole.distesage.com` (approver). Leurs mots de passe ne
figurent ni dans le dépôt ni dans la documentation.

### Restant

`MVP-F03` éditeur graphique du réseau ; `MVP-F08` recette par un ingénieur
métier extérieur, puis release `v1.0.0-mvp`.

## Correction de l'audit et livraison du 7 août 2026 (commits `73cd3d6` → `01982a5`)

Un audit technique externe a relevé cinq écarts : frontend déployé issu d'une branche
non fusionnée, expression « multi-tenant actif » trop forte, indicateurs fictifs sur le
tableau de bord, parcours Scénario absent de l'interface, et identifiants techniques
demandés à l'utilisateur. Le commit `ffc4b38` avait traité la première série ; cette
session a corrigé ce qui restait et vérifié l'ensemble.

### Attestation scientifique réellement vérifiable

L'endpoint `/api/v1/health/validation` publiait un fichier figé dont l'empreinte
(`b476c957…`) ne correspondait à aucune exécution reproductible : le condensat portait
sur un contenu incluant l'horodatage, les durées mesurées et la machine.

Le dossier de preuve distingue désormais deux condensats :

- `proof_hash` — résultats scientifiques seuls, **reproductible** d'une exécution à
  l'autre ; c'est lui qui est publié ;
- `sha256` — dossier complet avec horodatage et environnement, pour tracer une
  exécution précise.

Une observation peut être marquée `reproducible=False` lorsqu'elle mesure une grandeur
dépendante de la machine. Un seul cas est concerné : `V-020` (durée de calcul).

L'attestation est produite par la commande d'exécution :

```bash
hydro-validate \
  --attestation apps/api/hydro_api/scientific_validation_proof.json \
  --attestation-source docs/validation/qualification_backend_mvp_20260807.md
```

Le test `test_attestation_publiee_correspond_a_une_execution_reelle` relance les 41 cas
et compare comptage, moteur et empreinte au fichier embarqué : plus aucune valeur ne
peut être saisie à la main sans faire échouer la qualification.

`scientific_engine_version` expose désormais `ENGINE_VERSION` (`hydroliquid-0.1.0`), la
version normative du noyau, et non l'identifiant du solveur longue distance.

### Écran Scénarios

Les conditions d'étude se saisissaient dans une zone JSON libre. L'écran `/scenarios`
les expose sous forme de formulaire typé aligné sur `ScenarioPayloadInput` :
identification, température, débit imposé, conditions amont et aval, état et rapport de
vitesse de chaque pompe, disponibilité des stations et des tronçons, pertes singulières
ajoutées, limites de vitesse, options du solveur, prévisualisation de l'entrée
canonique. Les équipements sont choisis dans les listes du modèle.

La règle de contrainte du moteur est reproduite avant enregistrement : le formulaire
signale les problèmes sous-contraints et sur-contraints.

### Optimiseur et rapports

La page Comparaison et décision expose l'ensemble du contrat de l'optimiseur : durée de
référence, prix de l'énergie, bornes de débit et de pression, nombre maximal de pompes
actives, pompes imposées ou exclues, tolérance aux violations, bornes d'énumération. Le
résultat affiche l'état de l'espace exploré, l'écart d'optimalité et les configurations
rejetées avec leur motif.

La page Rapports ne demande plus de recopier des identifiants : le calcul se choisit par
projet, version, scénario puis calcul, et la source d'un rapport opérationnel est
restreinte aux ressources réellement acceptées par l'API.

### Défauts corrigés au passage

- le pied de la barre latérale et l'écran Administration lisaient les métadonnées de
  build sans garde : une réponse de santé incomplète faisait échouer le rendu de toute
  l'application ;
- les simulations de bout en bout servaient une santé sans bloc `build` et attendaient
  encore le graphique d'activité de démonstration retiré du tableau de bord ;
- le conteneur Caddy tentait de binder les ports 80 et 443 occupés par le nginx natif :
  chaque déploiement se terminait par une erreur de conflit. Il est désormais placé dans
  un profil inactif par l'override de production.

### Preuves de cette campagne

| Contrôle | Résultat |
|---|---:|
| Suite backend Docker (`-m "not slow"`) | **520 tests réussis** en 75,36 s |
| Validation scientifique | **41/41**, empreinte `6973bd97…` reproductible |
| ruff format / lint / mypy | verts (198 / 97 fichiers) |
| Tests unitaires web | **23 réussis** |
| Playwright bureau et mobile | **33 réussis** |
| TypeScript et build Vite | sans erreur |

Document de campagne : `docs/validation/qualification_backend_mvp_20260807.md`.

### Déploiement effectué

Images construites avec `HYDRO_BUILD_GIT_SHA`, `HYDRO_BUILD_REF` et `HYDRO_BUILD_DATE`,
puis mises en service sur `petrole.distesage.com`. La production sert donc exactement
`main` :

```json
{"git_sha":"d1df3b09dc3de0ecf7eec5c31a62cf858fb75eb3","ref":"main",
 "scientific_engine_version":"hydroliquid-0.1.0","deployment":{"mode":"single_org"}}
```

`main` a été poussée sur `origin`. Dernier état déployé et publié : `666141d`.

### Formulaires industriels structurés

Les fiches produit, pompe et bac ne se saisissent plus en JSON brut :

- **produit** — catégorie, conditions de référence, masse volumique, viscosité, pression
  de vapeur, dilatation, identifiant CoolProp, origine et lot ; tables
  température–propriété éditées point par point avec pression, incertitude, méthode
  d'essai et qualité ;
- **pompe** — courbe H(Q) et séries optionnelles η(Q), P(Q), NPSHr(Q), vitesse de
  référence, interpolation, puissance moteur, marge de NPSH, rapports de vitesse, débit
  minimal continu ; débits en m³/h et puissances en kW ;
- **bac** — type, altitude du fond, état, volume mort, produit et produits compatibles,
  cinq seuils d'exploitation, table de barémage éditable. L'origine de la table est
  explicite : théorique pour les études, ou jaugeage certifié. Le mode théorique affiche
  sa limite (ne remplace pas une table ISO 7507, exclu des mouvements commerciaux).

Les règles appliquées par les moteurs sont vérifiées avant l'envoi : source de masse
volumique obligatoire, tables strictement croissantes, séries de même longueur, seuils
ordonnés, niveau courant dans le domaine barémé. La saisie JSON reste accessible en mode
expert pour les produits et les pompes.

### Limites restantes

- le parcours complet projet → fluide → pompes → réseau → scénario → calcul →
  comparaison → rapport n'a pas encore été déroulé sur une instance réelle : la base de
  production ne contient aucun projet ;
- les fiches vanne, matériau et accessoire se saisissent toujours en JSON brut ;
- aucune politique PostgreSQL de sécurité au niveau des lignes n'est en place ;
- aucune donnée constructeur, table de jaugeage certifiée ni conformité clause par
  clause n'est établie ;
- l'organisation de l'instance de production s'appelle encore « test ».

## Fermeture MVP — lots F01 et F02 (7 août 2026)

Le périmètre est gelé : plus aucune fonctionnalité hors des huit lots de fermeture
définis avec l'audit. Une fonction n'est considérée terminée que si elle existe dans le
backend, est utilisable dans l'interface sans JSON ni ligne de commande, est testée et
participe au parcours métier réel.

### MVP-F01 — instance mono-exploitant

Le backend imposait déjà l'organisation, mais six pages métier continuaient de charger
la liste des organisations et d'en demander une : Projets, Modélisation, Visualisation du
réseau, Bibliothèques, Stockage et Données.

`apps/web/src/deployment.ts` résout l'espace courant depuis l'état de santé publié par
l'API. `OrganizationField` devient une mention en lecture seule en mono-exploitant et
redevient un sélecteur en multi-organisations. Le formulaire de création d'organisation
disparaît du parcours mono-exploitant.

L'organisation de production a été renommée **PETROLE / DISTESAGE**
(`petrole-distesage`) et son identifiant est fixé dans `deployment/.env.vps` par
`HYDRO_DEFAULT_ORGANIZATION_ID`, ce qui rend le périmètre déterministe.

### MVP-F02 — fiches industrielles et réseau typé

Nouvelles fiches guidées, sans JSON dans le parcours normal :

- **vanne** — type, diamètre, K, Cv, Kv, taux d'ouverture, temps de manœuvre, position de
  repli, classe de pression ;
- **matériau** — rugosité, pression maximale admissible, spécification, grade, SMYS,
  résistance ultime, géométrie, surépaisseur de corrosion, température de conception ;
- **accessoire** — type, K, longueur équivalente, diamètre.

Ces trois familles sont typées côté API (`ValveInput`, `MaterialInput`,
`AccessoryInput`) mais **volontairement hors de l'union du payload de catalogue** : tous
leurs champs étant facultatifs, Pydantic pourrait retenir le mauvais modèle et effacer
silencieusement les champs propres à l'autre famille. La validation est appliquée par le
service, qui connaît la famille demandée ; un test vérifie la survie des champs.

Le réseau devient typé :

- le formulaire de nœud change selon le type — configuration complète de station, débit
  imposé pour injection et soutirage, rappel de la condition aval pour un terminal ;
  latitude, longitude et état sont saisissables ;
- le tronçon reçoit sa géométrie mécanique, un profil altimétrique multi-points avec
  coordonnées, et une table d'accessoires typée.

Les règles du backend sont reproduites avant l'envoi : profil croissant couvrant
exactement le tronçon, cohérence diamètres/épaisseur, bornes de la station.

### Preuves

| Contrôle | Résultat |
|---|---:|
| Suite backend Docker | **522 tests réussis** |
| Tests unitaires web | **40 réussis** |
| Playwright bureau et mobile | **33 réussis** |
| ruff, mypy, TypeScript, build Vite | verts |

### Lots restants

`MVP-F03` modélisation complète et React Flow éditeur ; `MVP-F04` résultats détaillés et
graphiques obligatoires ; `MVP-F05` transfert connecté à HydroLiquid — chantier critique ;
`MVP-F06` imports JSON, liaison imports, pièces jointes et exports ; `MVP-F07`
optimisation finale et workflow de validation ; `MVP-F08` qualification complète, recette
métier et release `v1.0.0-mvp`.

## Requalification backend du 3 août 2026

La requalification consolidée est consignée dans
[`docs/validation/qualification_backend_mvp_20260803.md`](docs/validation/qualification_backend_mvp_20260803.md).
Elle confirme 485 tests Docker, 41/41 cas scientifiques, les scans d'images et le
DAST local, tout en maintenant explicitement la frontière entre un MVP logiciel
validé et une certification industrielle ou normative non démontrée.
