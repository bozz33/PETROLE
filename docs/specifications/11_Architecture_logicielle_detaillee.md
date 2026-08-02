Plateforme de transport et de stockage des hydrocarbures

D11

Architecture logicielle détaillée

Architecture cible, composants, déploiement et décisions techniques

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D11 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Principes

- Architecture logique

- Domaines

- Moteur de calcul

- Frontend

- Backend

- Tâches longues

- Stockage

- Déploiement

- Évolutivité

- Environnements

- Décisions ADR

- Risques

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Principes d’architecture

- Monolithe modulaire au MVP afin de rester maîtrisable par deux développeurs.

- Séparation forte des domaines : projets, réseau, physique, scénarios, stockage, données, rapports et administration.

- Le noyau scientifique doit être utilisable comme bibliothèque Python indépendante du web.

- Les calculs longs s’exécutent dans des workers et produisent des résultats immuables.

- PostgreSQL est la source transactionnelle ; PostGIS gère la géométrie ; stockage objet pour fichiers et rapports.

- Les intégrations industrielles sont isolées dans des connecteurs et restent en lecture seule au départ.

- Les moteurs non Python futurs communiquent par API/version de modèle, pas par couplage direct au code.

| Choix directeur Python + FastAPI + PostgreSQL/PostGIS + React/TypeScript constitue le socle. Cette stack maximise la productivité scientifique, l’écosystème de données et la capacité de recrutement tout en restant adaptée à une petite équipe. |



# 2. Vue logique

| Couche | Composants | Responsabilité |

| Présentation | React, TypeScript, ECharts/Plotly, MapLibre | Éditeur, tableaux, cartes, graphiques, administration |

| API applicative | FastAPI, Pydantic | Cas d’usage, validation, permissions, orchestration |

| Domaines métier | Modules Python | Projets, actifs, produits, scénarios, calculs, rapports |

| Noyau scientifique | NumPy, SciPy, fluids, fonctions internes | Équations, solveurs, diagnostics et validation |

| Optimisation | Pyomo + solveurs | Configurations de pompes, planning futur |

| Persistance | PostgreSQL, PostGIS, Alembic | Données structurées, géométrie, versions et audit |

| Fichiers | S3/MinIO ou filesystem abstrait | Imports, exports, courbes, rapports, journaux |

| Asynchrone | Worker Python + broker léger | Calculs, imports, rapports et optimisations |

| Observabilité | Logs structurés, métriques, traces | Diagnostic opérationnel et scientifique |

| Intégrations futures | OPC UA, PLC4X, MQTT, TimescaleDB | Lecture OT et historiques |



# 3. Domaines et modules du monolithe

| Module | Responsabilités | Dépendances autorisées |

| identity | Utilisateurs, rôles, organisations | shared uniquement |

| projects | Sites, projets, versions, statuts | identity, standards |

| assets | Nœuds, tronçons, stations, équipements | projects, catalog |

| catalog | Pompes, vannes, matériaux, produits | shared |

| standards | Standards, rule sets, évaluations | projects, shared |

| scenarios | Conditions, overrides, comparaison | projects, assets |

| physics | Modèles et solveurs purs | catalog scientifique uniquement |

| calculations | Orchestration, tâches, résultats | physics, scenarios, standards |

| tanks | Stocks, barémages, transferts | assets, physics |

| datahub | Imports, séries, qualité | projects, assets |

| optimization | Modèles Pyomo et stratégies | calculations, scenarios |

| reports | Documents, exports, modèles | tous via services publics |

| audit | Événements immuables | transversal |

| integrations | Connecteurs externes | datahub, identity |



# 4. Architecture du noyau scientifique

| Paquet | Contenu |

| core.units | Grandeurs, conversions, validation dimensionnelle |

| core.properties | Interfaces de propriétés, interpolation, corrélations, CoolProp adapter |

| core.hydraulics | Reynolds, frottement, pertes, composants |

| core.pumps | Courbes, ajustements, série/parallèle, vitesse, NPSH |

| core.network | Graphe calculable, assemblage des équations, conditions aux limites |

| core.solvers | Newton, bracketing, continuation, convergence et diagnostics |

| core.tanks | Barémage, inventaire, transfert quasi-stationnaire |

| core.rules | Interface d’évaluation de règles, sans texte normatif intégral |

| core.optimization | Adaptateurs vers Pyomo et énumération |

| core.validation | Cas de référence, comparaisons et tolérances |



| Règle de dépendance Le noyau scientifique ne dépend ni de FastAPI, ni de SQLAlchemy, ni du frontend. Il reçoit des objets typés et retourne des résultats typés. Cette règle est indispensable à la testabilité et à la réutilisation. |



# 5. Frontend

| Zone | Choix | Notes |

| Framework | React + TypeScript | Composants fonctionnels et typage strict |

| État serveur | TanStack Query ou équivalent | Cache, erreurs, invalidation |

| Formulaires | React Hook Form + schémas partagés | Validation claire et unités |

| Schéma réseau | Bibliothèque de graphe à évaluer | Éditeur contrôlé, pas de logique scientifique côté client |

| Cartographie | MapLibre GL | Open source, couches et tracés |

| Graphiques | Apache ECharts ou Plotly | Profils, séries, courbes pompe |

| Design system | Composants internes sobres | Accessibilité, densité adaptée aux ingénieurs |

| Internationalisation | i18next ou équivalent | Français d’abord |

| Exports | Téléchargements via API | Traçabilité et permissions |



# 6. Backend et API

| Composant | Choix | Rôle |

| Serveur | FastAPI + Uvicorn/Gunicorn | API HTTP et OpenAPI |

| Modèles API | Pydantic | Validation et sérialisation |

| ORM | SQLAlchemy 2.x | Accès PostgreSQL |

| Migrations | Alembic | Évolution versionnée |

| Auth | OIDC futur ou auth interne initiale | JWT court + sessions/refresh contrôlés |

| Permissions | Service RBAC | Décisions centralisées |

| Fichiers | Interface Storage | Local, S3 ou MinIO |

| Rapports | python-docx + moteur PDF contrôlé | Templates et exports |

| Configuration | Variables d’environnement et fichiers versionnés | Séparation des environnements |



# 7. Tâches longues et orchestration

Le MVP doit permettre l’exécution asynchrone sans imposer une infrastructure complexe. Une abstraction JobQueue sera créée. Le premier déploiement peut utiliser Dramatiq, Celery, RQ ou un worker PostgreSQL selon la preuve de concept. Le choix final doit privilégier robustesse, visibilité et faible charge d’exploitation.

| Type de tâche | Propriétés |

| Calcul hydraulique | Idempotent, annulable si possible, journal scientifique |

| Optimisation | Durée longue, progression, meilleur résultat intermédiaire |

| Import | Validation, reprise, rapport d’erreurs |

| Rapport | Reproductible depuis calculation_id |

| Calibration future | Version des données et des paramètres |

| Synchronisation future | Checkpoint et déduplication |



# 8. Stockage et persistance

| Donnée | Stockage recommandé | Motif |

| Métadonnées/projets | PostgreSQL | Transactions et contraintes |

| Géométries | PostGIS | Index spatial et fonctions SIG |

| Résultats structurés | PostgreSQL + JSONB ciblé | Requêtes et extensibilité |

| Profils/résultats massifs | Tables normalisées ou fichiers Parquet futurs | Performance et réutilisation |

| Imports originaux | Stockage objet | Immutabilité et traçabilité |

| Rapports | Stockage objet | Version et téléchargement |

| Séries temporelles MVP | PostgreSQL partitionné | Simplicité |

| Historian futur | TimescaleDB ou IoTDB après benchmark | Volume industriel |



# 9. Architecture de déploiement MVP

| Service | Conteneur | Ressources indicatives |

| reverse-proxy | Nginx/Caddy | TLS, compression, routage |

| frontend | Static web | Faible |

| api | Python FastAPI | 2-4 vCPU, 4-8 Go selon charge |

| worker | Python | 2-8 vCPU, mémoire selon calcul |

| postgres | PostgreSQL/PostGIS | SSD, sauvegardes, 4-16 Go |

| object-storage | MinIO ou volume | Selon fichiers |

| monitoring | Option initiale | Logs et métriques |



Le déploiement local peut regrouper plusieurs composants sur un seul serveur. La séparation logique reste conservée pour migrer ensuite vers plusieurs machines. Kubernetes n’est pas requis au MVP.

# 10. Évolutivité vers des services spécialisés

| Service futur | Technologie candidate | Contrat |

| gas-engine | GasModels.jl/Julia + moteur interne | API versionnée, cas et résultats JSON/Parquet |

| transient-engine | OpenModelica/FMU ou moteur MOC Python/C++ | Paquet de modèle immuable |

| scada-gateway | open62541/PLC4X | Flux de tags normalisés en lecture seule |

| historian | TimescaleDB/IoTDB | API de requête et qualité |

| leak-detection | Service physique/statistique | Événements avec confiance et preuve |

| reporting-scale | Worker spécialisé | Templates versionnés |



# 11. Environnements

| Environnement | Usage | Données |

| dev | Développement local | Synthétiques uniquement |

| test | CI et intégration | Cas de validation figés |

| staging | Recette et démonstration | Données anonymisées |

| pilot | Site pilote isolé | Données réelles contrôlées |

| production | Exploitation | Sauvegarde, audit et procédures |

| ot-integration futur | Passerelle industrielle | Zone réseau séparée |



# 12. Décisions d’architecture (ADR) initiales

| ADR | Décision | Justification |

| ADR-001 | Python comme langage principal | Calcul scientifique, données, vitesse de développement |

| ADR-002 | PostgreSQL/PostGIS | Relationnel, géospatial, robustesse et écosystème |

| ADR-003 | Monolithe modulaire | Équipe de deux développeurs et complexité maîtrisée |

| ADR-004 | React/TypeScript | Interface riche, typage et écosystème |

| ADR-005 | Calculs asynchrones | Isolation de l’API et gestion des longues tâches |

| ADR-006 | Noyau scientifique pur | Validation et réutilisation |

| ADR-007 | SCADA en lecture seule | Réduction des risques et séparation du contrôle |

| ADR-008 | Moteurs externes par service | Licences, performance et indépendance |

| ADR-009 | Règles normatives versionnées | Multi-pays et audit |

| ADR-010 | Pas de Kubernetes au MVP | Charge d’exploitation disproportionnée |



# 13. Risques architecturaux

| Risque | Réponse |

| Noyau scientifique trop couplé au métier web | Tests d’architecture et interfaces pures |

| JSONB utilisé sans discipline | Schémas, contraintes et champs relationnels pour le cœur |

| Optimisation trop lente | Énumération MVP, profils et solveurs adaptés ensuite |

| Dépendance à une bibliothèque non maîtrisée | Adapters, benchmarks et cas de référence |

| Complexité des graphes/éditeur | Commencer par formulaires et schéma contrôlé |

| Séries temporelles prématurées | PostgreSQL d’abord, migration mesurée |

| Sécurité OT sous-estimée | Passerelle séparée et aucun write au MVP |

| Deux développeurs sur trop de modules | Phases strictes et gel de périmètre |



# Sources et références

- D04/D05 - Exigences.

- D07/D09 - Modèles scientifiques et données.

- D14/D15 - Open source, licences, sécurité et intégration.

- Décisions adaptées à une équipe de deux développeurs avec assistants IA.

Fin du document