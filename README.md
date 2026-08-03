# Plateforme de transport et de stockage des hydrocarbures — MVP

> Pipelines liquides • Stations de pompage • Réservoirs • Transferts • Scénarios • Optimisation

Application web d'ingénierie destinée à modéliser et simuler le **transport stationnaire de
produits pétroliers liquides** dans des pipelines comprenant plusieurs tronçons, plusieurs
stations de pompage et plusieurs réservoirs. Elle permet également de simuler des transferts
bac-à-bac, d'étudier des modes dégradés et de proposer une configuration d'exploitation
techniquement réalisable et énergétiquement intéressante.

Ce dépôt implémente le **MVP** défini par la *Documentation complète du MVP v2.0*
(voir [`docs/specifications/`](docs/specifications/)).

---

## Positionnement

Le MVP n'est ni un prototype graphique, ni un SCADA, ni un logiciel de commande. C'est un
premier produit utilisable de bout en bout, avec moteur scientifique validé, traçabilité,
interface métier et rapports.

**Limites fondamentales assumées** (voir §1.2 de la documentation) :

- écoulement monophasique liquide, conduite pleine, régime principalement permanent ;
- pas de gazoduc complet, pas de line-pack, pas de compresseurs avancés ;
- pas de coup de bélier industriel ni de simulation transitoire détaillée ;
- pas de connexion temps réel au SCADA et **aucune commande directe d'équipement**
  ([ADR-009](docs/adr/adr-009-lecture-seule-avant-controle.md)) ;
- pas de détection de fuite certifiée ni de conformité réglementaire automatique complète ;
- pas de calcul structurel complet des conduites ou des réservoirs.

---

## Architecture

```text
┌─────────────────────────────────────────────────────┐
│ FRONTEND — apps/web                                 │
│ Shadcn Admin + React Flow + ECharts + MapLibre      │
└──────────────────────────┬──────────────────────────┘
                           │  REST /api/v1 (OpenAPI)
┌──────────────────────────▼──────────────────────────┐
│ BACKEND CENTRAL — apps/api                          │
│ Python + FastAPI + Pydantic + SQLAlchemy + Alembic  │
│ Projets, équipements, scénarios, règles, rapports   │
└────────┬──────────────┬──────────────┬──────────────┘
         │              │              │
         ▼              ▼              ▼
  HydroLiquid Core  Tank & Transfer  Operations Optimizer
  fluids/SciPy/     Core             Pyomo + énumération
  CoolProp/Pint     + barémage         filtrée
  + adaptateur
    pandapipes
                             │
                             ▼
                 PostgreSQL + PostGIS
```

Le noyau scientifique ne dépend **ni de FastAPI, ni de SQLAlchemy, ni du frontend**. Il reçoit
des objets typés et retourne des résultats typés (D11 § 4). Il est utilisable comme
bibliothèque Python autonome.

### Organisation du dépôt

```text
hydro-platform/
├── apps/
│   ├── api/                 # FastAPI — hydro_api
│   └── web/                 # React + TypeScript + Vite
├── packages/
│   ├── shared/              # hydro_shared      — unités (Pint), erreurs, codes, journal
│   ├── domain/              # hydro_domain      — modèle métier pur, paquet d'entrée canonique
│   ├── hydroliquid/         # hydroliquid       — HydroLiquid Core
│   ├── tank_transfer/       # hydro_tanks       — Tank & Transfer Core
│   ├── optimization/        # hydro_optimization— Operations Optimizer
│   ├── reporting/           # hydro_reporting   — PDF / XLSX / CSV / JSON
│   └── validation/          # hydro_validation  — cas de référence D10 et rapport de preuve
├── database/migrations/     # Alembic
├── datasets/reference_cases/# jeux d'entrée immuables + résultats attendus
├── deployment/              # Docker Compose, images, sauvegarde/restauration
├── docs/                    # ADR, spécifications, guides
└── tests/                   # unitaires, composants, intégration, scientifiques
```

---

## Démarrage rapide

### Bibliothèque scientifique seule (sans base de données)

```bash
python -m venv .venv && .venv/Scripts/activate   # Linux/macOS : source .venv/bin/activate
pip install -e ".[dev]"
pytest -m "not integration"
```

### Pile locale de développement

Premier démarrage, ou après modification des dépendances :

```bash
docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml up --build
```

Démarrages suivants :

```bash
docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml up
```

Le dépôt est monté sous `/workspace` dans les conteneurs API et calcul. Les modifications de `apps/api` et `packages` rechargent automatiquement ces deux processus. Le dossier `apps/web` est monté dans le conteneur Vite et ses modifications sont également prises en compte. Aucune reconstruction d'image n'est nécessaire pour un changement de code ; elle reste requise après une modification des dépendances ou des fichiers Docker.

- API et documentation interactive : <http://localhost:8000/docs>
- Santé de l'API : <http://localhost:8000/api/v1/health>
- Console MinIO : <http://localhost:9001>
- Interface web : <http://localhost:5173>
- Stockage objet : <http://localhost:9000>

La pile de développement active une file de calcul persistante. L'API enregistre la demande, le processus de calcul la traite hors requête HTTP, puis l'interface suit automatiquement son état.

### Validation locale sans CI distante

La validation reproductible du backend s'exécute depuis la racine :

```bash
.venv/Scripts/python -m ruff format --check apps packages tests
.venv/Scripts/python -m ruff check apps packages tests
.venv/Scripts/python -m mypy packages apps/api
.venv/Scripts/python -m pytest --cov=packages --cov=apps/api
```

La validation du frontend s'exécute après démarrage de la pile Docker. Les essais E2E utilisent
Chrome local et couvrent chaque écran en formats bureau et mobile :

```bash
cd apps/web
npm ci
npm run typecheck
npm test
npm run test:e2e
npm run build
npm audit --audit-level=moderate
```

La variable `E2E_BASE_URL` permet de viser une autre instance que `http://localhost:5173`.

Le dernier procès-verbal de recette locale du backend est disponible dans
[`docs/validation/recette_backend_mvp.md`](docs/validation/recette_backend_mvp.md).

### Exécuter le dossier de validation scientifique

Après installation locale du projet en mode éditable :

```bash
hydro-validate --report var/validation/rapport.md
```

Dans la pile Docker de développement, sans installation supplémentaire sur l'hôte :

```bash
docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml \
  exec -T api hydro-validate --report /workspace/var/validation/rapport.md \
  --json /workspace/var/validation/preuve.json
```

La campagne contient 34 cas : les 20 portes de réception `V-001` à `V-020` et 14 cas
analytiques détaillés des familles `VAL-LIQ-*`, `VAL-PMP-*` et `VAL-TNK-*`.

La preuve de concept comparative pandapipes s'exécute dans la même image :

```bash
docker compose -f deployment/docker-compose.yml -f deployment/docker-compose.dev.yml \
  exec -T api pytest tests/unit/test_pandapipes_adapter.py -q
```

---

## Intégrité scientifique

Chaque calcul enregistre ses entrées figées, la version du moteur, la méthode, les tolérances,
les résidus et les avertissements. Le produit **refuse de déclarer valide** un résultat dont la
convergence ou le bilan de masse dépasse la tolérance (NFR-SCI-005).

Les contrôles obligatoires `C-001` à `C-012` (conservation de masse, pression sous la pression
de vapeur, NPSH, pression admissible, vitesse, domaine de courbe, puissance moteur, niveaux de
bac, non-convergence, extrapolation, résidu) sont implémentés dans le moteur et remontés dans
chaque résultat.

Le dossier de validation couvre les cas `V-001` à `V-020` et les familles `VAL-LIQ-*`,
`VAL-PMP-*`, `VAL-TNK-*` du plan D10, avec tolérances explicites par grandeur.

---

## Avertissement

Ce logiciel structure et outille la conception. Il ne remplace ni les textes normatifs officiels,
ni la validation d'un ingénieur habilité, ni une étude de dangers, ni une autorisation
réglementaire ou une certification de site. Les référentiels (ASME, API, ISO, IEC, ISA) sont
enregistrés et versionnés ; **seules les règles effectivement codées et validées sont évaluées**,
et le produit n'affiche jamais une conformité complète lorsqu'il n'a vérifié qu'un sous-ensemble.

## Licence

Apache-2.0 — voir [LICENSE](LICENSE). L'inventaire des dépendances open source, de leurs
licences et de leur justification est tenu dans
[`docs/specifications/14_Strategie_open_source_et_licences.md`](docs/specifications/14_Strategie_open_source_et_licences.md).
