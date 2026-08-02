Plateforme de transport et de stockage des hydrocarbures

D12

Modèle conceptuel et logique des données

Schéma relationnel, agrégats, contraintes et stratégie de versionnement

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D12 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Objectifs

- Agrégats

- Entités principales

- Relations

- Versionnement

- Résultats

- Séries temporelles

- Audit

- Multi-organisation

- Indexation

- Migrations

- Exemple de modèle

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Objectifs du modèle

- Garantir cohérence transactionnelle des projets et équipements.

- Représenter un réseau sous forme de graphe sans limiter la topologie.

- Versionner les modèles et scénarios sans copier inutilement toutes les données.

- Rendre les calculs reproductibles et les résultats immuables.

- Préparer la géographie, les séries temporelles et les moteurs futurs.

- Isoler les organisations et permettre l’audit de toutes les modifications.

# 2. Agrégats métier

| Agrégat | Racine | Contenu |

| Organisation | organization | utilisateurs, rôles, politiques |

| Site | site | emplacement, fuseau, référentiel géographique |

| Projet | project | périmètre, normes, unités, membres |

| Modèle | model_version | réseau, actifs, produits, paramètres |

| Catalogue | catalog_item | modèles de pompes, vannes, matériaux, fluides |

| Scénario | scenario | conditions aux limites et overrides |

| Calcul | calculation_run | entrées figées, moteur, statut, résultats |

| Réservoir | tank | barémage, limites et inventaires |

| Transfert | transfer_plan | source, destination, chemin et résultats |

| Données | dataset | fichier, mapping, qualité, séries |

| Normes | rule_set | standards, règles, approbations |

| Rapport | report | template, version, fichier et approbation |



# 3. Entités principales

| Table | Clé/relations | Description |

| organizations | id | Tenant logique |

| users | id | Compte utilisateur |

| memberships | organization_id, user_id, role_id | Appartenance et rôle |

| sites | organization_id | Site physique ou logique |

| projects | site_id | Projet d’étude/exploitation |

| model_versions | project_id, parent_id | Snapshot logique du modèle |

| nodes | model_version_id | Nœuds du graphe |

| edges | model_version_id, from_node_id, to_node_id | Tronçons |

| asset_instances | model_version_id, catalog_item_id | Équipements placés |

| catalog_items | organization_id nullable | Référentiel global ou privé |

| fluids / fluid_properties | organization_id | Produits et propriétés |

| scenarios | model_version_id, parent_id | Conditions et variations |

| scenario_overrides | scenario_id, target_id | Modification locale |

| calculation_runs | scenario_id | Exécution immuable |

| node_results / edge_results | calculation_run_id | Résultats détaillés |

| rule_evaluations | calculation_run_id, rule_id | Contrôles normatifs |

| files | organization_id | Métadonnées stockage objet |

| audit_events | organization_id | Journal append-only |



# 4. Relations clés

| Relation | Cardinalité | Règle |

| organization → sites/projects/users | 1-N | Suppression protégée, archivage |

| project → model_versions | 1-N | Une version active/approuvée possible selon statut |

| model_version → nodes/edges/assets | 1-N | Immuable après approbation |

| node → edges | N-N via from/to | Intégrité référentielle |

| catalog_item → asset_instances | 1-N | L’instance peut surcharger des paramètres autorisés |

| scenario → overrides | 1-N | Overrides validés selon type de cible |

| scenario → calculation_runs | 1-N | Plusieurs exécutions/version moteur |

| calculation_run → results | 1-N | Résultats non modifiables |

| tank → strapping_points | 1-N | Ordre hauteur/volume |

| dataset → time_series samples | 1-N | Partitionnement futur |



# 5. Stratégie de versionnement

Le modèle doit éviter deux extrêmes : modifier directement une version approuvée ou dupliquer l’intégralité du projet à chaque changement. La stratégie recommandée combine des versions de modèle explicites et des scénarios par overrides.

| Objet | Versionnement |

| Catalogue global | Historique valid_from/valid_to ou version de l’item |

| ModelVersion | Snapshot logique ; copie structurée lors d’une nouvelle baseline |

| Scenario | Référence une ModelVersion et stocke seulement les différences |

| CalculationRun | Capture/empreinte complète des entrées résolues au lancement |

| RuleSet | Version immuable après approbation |

| ReportTemplate | Version et hash |

| Dataset | Fichier brut immuable + versions de transformation |



| Reproductibilité Au lancement d’un calcul, les overrides sont matérialisés dans un paquet d’entrée canonique. Ce paquet reçoit un hash et reste accessible même si le catalogue ou le scénario évolue ensuite. |



# 6. Modélisation des résultats

| Table | Granularité | Index |

| calculation_runs | Une exécution | scenario_id, status, created_at |

| node_results | Un nœud par exécution | run_id, node_id |

| edge_results | Un tronçon par exécution | run_id, edge_id |

| profile_results | Points le long d’un tracé | run_id, edge/chainage |

| pump_results | Une pompe/état | run_id, asset_id |

| tank_time_results | Un bac et pas de temps | run_id, tank_id, timestamp/elapsed |

| violations | Une contrainte violée | run_id, severity, object_id |

| solver_iterations | Optionnel/échantillonné | run_id, iteration |

| scenario_kpis | Résumé | run_id, key |



# 7. Séries temporelles

Au MVP, les séries sont stockées dans PostgreSQL avec partitionnement par temps et éventuellement par site. Le schéma doit permettre une migration ultérieure vers TimescaleDB ou IoTDB sans changer les identifiants métier.

| Table | Colonnes principales | Remarque |

| tags | id, site_id, asset_id, name, type, unit, source | Métadonnées |

| samples_raw | tag_id, source_ts, ingest_ts, value, quality, sequence | Immuable/partitionnée |

| samples_normalized | tag_id, ts, value_si, quality, processing_version | Dérivée |

| events | site_id, start/end, type, severity, source | Alarmes et opérations |

| time_series_jobs | dataset_id, status, checkpoint | Imports et reprise |



# 8. Audit et approbations

| Table | Fonction |

| audit_events | Événements append-only avec acteur, objet, action et corrélation |

| approvals | Objet, étape, décision, commentaire, signataire, date |

| comments | Discussion liée à un objet/version |

| change_sets | Diff structuré pour nouvelle version |

| security_events | Échecs de connexion, changements de permissions, accès sensibles |



# 9. Isolation multi-organisation

- organization_id obligatoire sur toutes les données privées.

- Filtrage centralisé dans la couche d’accès et vérification au niveau service.

- Row-Level Security PostgreSQL à étudier pour renforcer l’isolation.

- Les catalogues publics sont explicitement marqués et en lecture seule.

- Les fichiers sont stockés dans des préfixes/buckets isolés.

- Les tâches asynchrones transportent l’identité de l’organisation et l’autorisation.

- Les exports et sauvegardes sont auditables.

# 10. Contraintes et indexation

| Objet | Contrainte/index |

| nodes | Unique(model_version_id, code), index GIST geometry |

| edges | from/to existants, longueur > 0, index model_version |

| profile_points | Unique(edge_id, chainage), chainage ≥ 0 |

| strapping_points | Unique(tank_id, height), volume monotone validé applicativement |

| fluid_properties | Index fluid_id, property_type, temperature, pressure |

| samples | Index tag_id + timestamp, partitionnement |

| calculations | Index scenario_id, status, created_at, input_hash |

| audit | Index organization, timestamp, object_id |

| files | Hash unique optionnel pour déduplication |



# 11. Migrations et archivage

- Alembic gère toutes les migrations de schéma ; aucune modification manuelle en production.

- Chaque migration est testée sur une copie représentative et possède une stratégie de sauvegarde.

- Les migrations scientifiques sont distinctes des migrations de base : un résultat ancien reste associé à son moteur.

- Les données volumineuses peuvent être archivées en Parquet avec métadonnées conservées en base.

- La purge respecte les délais de rétention et les obligations contractuelles.

- Un export complet de projet doit permettre la restauration dans une version compatible.

# 12. Exemple de paquet d’entrée canonique

| Section | Contenu |

| manifest | schema_version, project_id, model_version, scenario, engine_version, hashes |

| units | SI + unités d’origine |

| fluid | propriétés résolues et sources |

| network | nodes, edges, profile, components |

| equipment | courbes et états |

| boundary_conditions | pressions, débits, niveaux, demandes |

| rules | rule_set ids et paramètres |

| solver | méthodes, tolérances, limites |

| provenance | utilisateur, date, fichiers et transformations |



# Sources et références

- D09 - Dictionnaire des données.

- D11 - Architecture.

- D13 - Contrats API.

- PostgreSQL/PostGIS comme technologies de référence.

Fin du document