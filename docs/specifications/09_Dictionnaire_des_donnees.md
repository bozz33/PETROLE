Plateforme de transport et de stockage des hydrocarbures

D09

Dictionnaire des données

Entités, attributs, unités, qualité et gouvernance des données

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec validation métier et scientifique |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D09 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Principes

- Identifiants et versions

- Projet et organisation

- Réseau

- Équipements

- Fluides

- Réservoirs

- Scénarios

- Résultats

- Séries temporelles

- Normes

- Audit

- Règles de qualité

- Formats d’import

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Principes

- Chaque donnée possède un identifiant stable, une version ou une période de validité, une unité et une source.

- Les données brutes ne sont pas écrasées par les données nettoyées ou réconciliées.

- Les valeurs calculées sont séparées des valeurs mesurées et saisies.

- Les coordonnées sont stockées avec leur système de référence.

- Les unités internes sont SI et les valeurs d’origine sont conservées.

- Toute donnée critique possède un code qualité et une traçabilité de modification.

# 2. Conventions générales

| Champ commun | Type | Règle |

| id | UUID | Identifiant interne immuable |

| organization_id | UUID | Propriétaire logique de la donnée |

| created_at / updated_at | timestamptz | UTC, affichage dans le fuseau du site |

| created_by / updated_by | UUID utilisateur/service | Audit |

| version | entier ou chaîne semver | Incrément contrôlé |

| status | enum | draft, reviewed, approved, archived |

| source_type | enum | manual, import, sensor, computed, reconciled |

| source_ref | texte/UUID | Référence du fichier, capteur ou calcul |

| metadata | JSONB | Extension contrôlée, non substitut aux champs structurés |



# 3. Organisation, site et projet

| Entité.Champ | Type/unité | Obligatoire | Description |

| organization.name | texte | Oui | Nom de l’organisation |

| site.name | texte | Oui | Nom du dépôt, terminal ou système |

| site.timezone | IANA timezone | Oui | Fuseau d’exploitation |

| site.srid | entier | Oui si SIG | Système de coordonnées |

| project.name | texte | Oui | Nom du projet |

| project.project_type | enum | Oui | liquid_pipeline, terminal, gas_pipeline, combined |

| project.country_code | ISO 3166-1 | Oui | Pays principal |

| project.unit_system | enum | Oui | SI au MVP ; affichage configurable |

| project.rule_set_ids | UUID[] | Oui | Référentiels sélectionnés |

| model_version.label | texte | Oui | Version de modèle calculable |



# 4. Réseau et topologie

| Entité.Champ | Type/unité | Validation |

| node.node_type | enum | source, sink, junction, station, tank, boundary |

| node.geometry | PostGIS Point | SRID du site |

| node.elevation_m | m | Plage projet et datum identifié |

| edge.from_node_id / to_node_id | UUID | Nœuds existants et non identiques |

| edge.length_m | m | > 0 ; calcul SIG ou saisie |

| edge.inner_diameter_m | m | > 0 |

| edge.outer_diameter_m | m | ≥ diamètre interne |

| edge.wall_thickness_m | m | > 0 et cohérente |

| edge.roughness_m | m | ≥ 0, source identifiée |

| edge.material_id | UUID | Référentiel matériau |

| edge.maop_pa | Pa | > pression minimale ; absolue/manométrique indiqué |

| profile_point.chainage_m | m | Ordre croissant |

| profile_point.elevation_m | m | Datum identique |

| edge.status | enum | available, unavailable, bypassed, maintenance |



# 5. Équipements

| Équipement | Champs principaux |

| PumpModel | fabricant, modèle, vitesse, Q_min/Q_max, H(Q), η(Q), P(Q), NPSHr(Q), source, température/viscosité de référence |

| PumpInstance | station, pump_model_id, rôle, état, vitesse, moteur, heures de marche, limites |

| Valve | type, diamètre, Cv/Kv ou K, position, temps d’ouverture/fermeture, état de sécurité |

| Filter | coefficient/perte propre, perte limite, état de colmatage |

| FlowMeter | type, plage, précision, incertitude, tag, méthode de correction |

| PressureSensor | plage, précision, pression absolue/manométrique, élévation, tag |

| CompressorModel futur | carte, vitesse, rapport de pression, rendement, anti-surge, puissance |

| Station | coordonnée, altitude, configuration, collecteurs, conditions de limite |



# 6. Fluides et propriétés

| Champ | Type/unité | Description |

| fluid.name | texte | Nom commercial ou échantillon |

| fluid.category | enum | crude, gasoline, diesel, kerosene, fuel_oil, water, gas, custom |

| fluid.batch_ref | texte | Lot ou analyse laboratoire |

| property.property_type | enum | density, kinematic_viscosity, vapor_pressure, heat_capacity, etc. |

| property.value | double | Valeur mesurée ou calculée |

| property.unit | UCUM/enum | Unité d’origine |

| property.temperature_k | K | Condition de mesure |

| property.pressure_pa | Pa abs | Condition de mesure |

| property.uncertainty | double + unité | Incertitude si disponible |

| property.method | texte/code | Méthode laboratoire, corrélation ou bibliothèque |

| property.valid_range | JSONB structuré | Bornes T/p/composition |

| property.quality_status | enum | measured, approved, estimated, extrapolated |



# 7. Réservoirs et stocks

| Champ | Type/unité | Règle |

| tank.tank_type | enum | vertical_fixed_roof, floating_roof, horizontal, sphere, custom |

| tank.nominal_capacity_m3 | m³ | > 0 |

| tank.min_operating_level_m | m | ≥ 0 |

| tank.max_operating_level_m | m | > min |

| tank.high_level_m / high_high_level_m | m | high_high ≥ high |

| tank.product_compatibility | liste | Règles par produit |

| strapping_table.height_m | m | Monotone croissant |

| strapping_table.volume_m3 | m³ | Monotone croissant |

| inventory.timestamp | timestamptz | Horodatage source |

| inventory.level_m | m | Dans plage capteur |

| inventory.temperature_k | K | Moyenne ou profil indiqué |

| inventory.free_water_m | m | Optionnel |

| inventory.observed_volume_m3 | m³ | Calculé ou mesuré |

| inventory.standard_volume_m3 | m³ | Méthode de correction identifiée |

| inventory.mass_kg | kg | Densité et référence enregistrées |



# 8. Scénarios et calculs

| Entité.Champ | Description |

| scenario.id / parent_id | Identité et filiation du scénario |

| scenario.baseline_model_version_id | Version du modèle source |

| scenario.boundary_conditions | Pressions, débits, niveaux, demandes et températures |

| scenario.equipment_overrides | États, vitesses et positions modifiés |

| scenario.objectives | Débit cible, pression, coût, énergie |

| calculation.engine_version | Version du moteur et du commit |

| calculation.method_config | Tolérances, corrélations, solveur, paramètres |

| calculation.status | queued, running, converged, failed, cancelled |

| calculation.started_at/finished_at | Durée et audit |

| calculation.input_hash | Empreinte des entrées |

| calculation.log_uri | Journal scientifique immuable |



# 9. Résultats

| Résultat | Champs principaux |

| NodeResult | pressure_pa, head_m, temperature_k, quality_flags |

| EdgeResult | flow_m3s, velocity_ms, reynolds, friction_factor, headloss_m, pressure_min/max |

| PumpResult | flow, head, suction/discharge pressure, efficiency, power, NPSHa, NPSHr, margin, operating_status |

| TankTransferResult | time, source/destination levels, flow, energy, final volumes, limit events |

| ScenarioSummary | feasible, objective_value, violations, warnings, KPI |

| NormCheckResult | rule_id, status, value, limit, margin, message |

| ValidationResult | reference_case, expected, actual, error, tolerance, pass/fail |



# 10. Séries temporelles et qualité

| Champ | Type | Description |

| tag.id / external_name | UUID/texte | Identifiant interne et nom SCADA |

| tag.asset_id | UUID | Équipement associé |

| tag.measurement_type | enum | pressure, flow, level, temperature, status, vibration, energy |

| sample.source_timestamp | timestamptz | Horodatage du capteur/PLC |

| sample.ingest_timestamp | timestamptz | Horodatage de réception |

| sample.value | double/bool/text | Valeur |

| sample.unit | unité | Unité source |

| sample.quality_code | enum/bitmask | good, uncertain, bad, substituted, estimated |

| sample.sequence_no | entier | Détection de pertes/ordre |

| sample.raw_payload_ref | URI/hash | Traçabilité optionnelle |

| sample.normalized_value | double | Valeur SI |

| sample.processing_version | texte | Pipeline de nettoyage |



# 11. Normes et règles

| Entité | Champs |

| Standard | organization, code, title, edition, publication_date, status, licensed_copy_ref |

| RuleSet | country, domain, standard_ids, version, approval_status |

| Rule | code, severity, applicability_expression, calculation_expression, parameters, message |

| RuleParameter | name, value, unit, condition, source_clause_ref |

| RuleEvaluation | rule_id, object_id, status, measured, limit, margin, calculation_id |



# 12. Audit et sécurité

| Champ | Description |

| audit_event.timestamp | UTC |

| audit_event.actor | Utilisateur, service ou connecteur |

| audit_event.action | create, update, delete, approve, calculate, export, login, permission_change |

| audit_event.object_type/object_id | Objet concerné |

| audit_event.before/after_hash | Empreintes ou diff contrôlé |

| audit_event.ip/device | Contexte selon politique |

| audit_event.correlation_id | Lien avec requête, tâche et calcul |

| audit_event.result | success/failure et raison |



# 13. Règles de qualité

| Code | Contrôle | Sévérité |

| DQ-001 | Unité inconnue ou incompatible | Bloquant |

| DQ-002 | Diamètre, longueur ou capacité non positive | Bloquant |

| DQ-003 | Profil non ordonné ou doublons incohérents | Bloquant |

| DQ-004 | Barémage non monotone | Bloquant |

| DQ-005 | Courbe pompe avec domaine insuffisant | Avertissement/bloquant selon usage |

| DQ-006 | Propriété extrapolée | Avertissement |

| DQ-007 | Horodatage absent ou hors ordre | Avertissement/bloquant |

| DQ-008 | Code qualité capteur mauvais | Exclure par défaut |

| DQ-009 | Bilan de masse incohérent | Avertissement critique |

| DQ-010 | Référence normative non approuvée | Bloquant pour rapport approuvé |



# 14. Formats d’import MVP

| Format | Usage | Règles |

| CSV UTF-8 | Profils, courbes, propriétés, séries | Séparateur détecté ou choisi, point décimal explicite |

| XLSX | Jeux de données structurés | Feuille et en-têtes mappés |

| JSON versionné | Topologie et scénarios | Schéma JSON publié |

| GeoJSON | Tracé et équipements géographiques | CRS défini/converti |

| Parquet futur | Historique volumineux | Schéma et compression définis |

| OPC UA futur | Tags en lecture seule | Namespace, NodeId, unité et qualité mappés |



# Sources et références

- D04 - Exigences fonctionnelles.

- D07 - Modèles scientifiques.

- D11/D12 - Architecture et modèle de données.

- Pratiques OPC UA pour qualité et horodatage des mesures.

Fin du document