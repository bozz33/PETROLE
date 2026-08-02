Plateforme de transport et de stockage des hydrocarbures

D13

Spécification des API et intégrations

Contrats REST, tâches, fichiers, événements et connecteurs

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D13 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Principes API

- Authentification

- Conventions

- Ressources

- Calculs

- Imports

- Rapports

- Erreurs

- Idempotence

- WebSocket/événements

- Intégrations

- Versionnement

- Exemples

- Critères

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Principes

- API REST/JSON documentée par OpenAPI pour le MVP.

- Ressources identifiées par UUID et isolées par organisation.

- Opérations longues représentées par des jobs asynchrones.

- Validation stricte des unités et schémas par Pydantic.

- Idempotence pour imports, créations critiques et connecteurs.

- Aucun endpoint de commande SCADA dans les premières versions.

- Les contrats des moteurs spécialisés utilisent des schémas versionnés et des hashes.

# 2. Authentification et autorisation

| Élément | Spécification MVP |

| Authentification | Identifiant/mot de passe sécurisé ou OIDC si fournisseur disponible |

| Jetons | Accès court, renouvellement contrôlé ou session sécurisée |

| Autorisation | RBAC avec contrôles organisation/site/projet |

| Service-to-service | Identité dédiée, secret/certificat, scopes minimaux |

| Audit | Connexion, échec, refresh, révocation et action sensible |

| MFA | SHOULD pour administrateurs, obligatoire avant intégration industrielle |



# 3. Conventions HTTP

| Convention | Règle |

| Base | /api/v1 |

| Formats | application/json ; multipart pour fichiers |

| Dates | ISO 8601 UTC avec offset |

| Pagination | cursor ou page/limit selon ressource, limite maximale |

| Filtrage | Paramètres explicites ; pas de langage de requête arbitraire au MVP |

| Tri | sort=field,-other avec liste blanche |

| Unités | Valeur + unité source ou champs SI explicites |

| ETag/version | Utiliser version/If-Match pour écritures concurrentes sensibles |

| Correlation-ID | Accepté/généré et propagé dans logs/jobs |

| Idempotency-Key | Requis pour calcul, import et opérations répétables |



# 4. Ressources principales

| Ressource | Endpoints indicatifs |

| Organizations | GET/POST /organizations ; GET/PATCH /organizations/{id} |

| Sites | /sites |

| Projects | /projects ; /projects/{id}/members |

| Model versions | /projects/{id}/models ; /models/{id}/clone ; /approve |

| Nodes/edges | /models/{id}/nodes ; /edges ; /validate |

| Catalog | /catalog/pumps ; /valves ; /materials ; /fluids |

| Scenarios | /models/{id}/scenarios ; /scenarios/{id}/compare |

| Calculations | /scenarios/{id}/calculations ; /calculations/{id} |

| Tanks | /models/{id}/tanks ; /tanks/{id}/strapping-table |

| Transfers | /transfer-plans ; /transfer-plans/{id}/simulate |

| Datasets | /datasets ; /datasets/{id}/imports |

| Reports | /reports ; /reports/{id}/download |

| Standards | /standards ; /rule-sets ; /evaluations |

| Audit | /audit-events avec permissions fortes |



# 5. Cycle d’un calcul

| Étape | Appel/Réponse |

| Créer | POST /scenarios/{id}/calculations avec Idempotency-Key |

| Réponse initiale | 202 Accepted, calculation_id, job_id, status=queued |

| Suivre | GET /calculations/{id} ou événement WebSocket/SSE |

| Progression | phase, pourcentage indicatif, messages non sensibles |

| Résultat | GET /calculations/{id}/summary et endpoints de détail |

| Annuler | POST /calculations/{id}/cancel si supporté |

| Rapport | POST /calculations/{id}/reports |

| Rejouer | POST /calculations/{id}/rerun crée une nouvelle exécution |



# 6. Schéma indicatif de demande de calcul

| Champ | Type | Description |

| scenario_id | UUID | Scénario déjà validé |

| engine | string | liquid-steady-v1 |

| solver.method | enum | hybrid-newton-bracket par exemple |

| solver.tolerances | objet | Résidus et itérations max |

| property_model | string | Modèle/version de propriétés |

| rule_set_ids | UUID[] | Contrôles à appliquer |

| outputs.profile_step_m | double | Résolution de sortie, pas de solveur distinct |

| options.store_iterations | bool | Journal détaillé selon droits |

| client_reference | string | Référence externe optionnelle |



# 7. Imports et fichiers

| Endpoint | Fonction |

| POST /files | Téléversement initial, retour file_id et hash |

| POST /datasets | Créer dataset lié au fichier |

| POST /datasets/{id}/preview | Détecter colonnes, unités et erreurs |

| POST /datasets/{id}/mappings | Enregistrer mapping |

| POST /datasets/{id}/imports | Lancer import asynchrone |

| GET /imports/{id}/errors | Rapport ligne/colonne/code |

| POST /imports/{id}/retry | Reprise idempotente |

| GET /files/{id}/download | Téléchargement autorisé et audité |



# 8. Rapports

| Requête | Paramètres |

| POST /reports | type, source_id, template_version, format, locale |

| GET /reports/{id} | statut, hash, date, signataires |

| GET /reports/{id}/download | URL temporaire ou streaming |

| POST /reports/{id}/approve | décision, commentaire, version objet |

| POST /report-templates | administration, versionnement et test |



# 9. Format des erreurs

| Champ | Description |

| type | URI/code stable du problème |

| title | Résumé utilisateur |

| status | Code HTTP |

| detail | Explication sûre |

| instance | Ressource/requête |

| code | Code métier stable |

| correlation_id | Lien support/logs |

| errors[] | Champ, valeur rejetée, unité, règle et action corrective |

| retryable | Indique si une reprise est possible |



| Exemple de règle Une non-convergence du solveur n’est pas une erreur HTTP du serveur. Le job termine avec status=failed et un diagnostic scientifique structuré. |



# 10. Idempotence et concurrence

- Idempotency-Key + organization + endpoint identifie une création répétée pendant une fenêtre définie.

- Les mises à jour utilisent un numéro de version et retournent 409 en cas de conflit.

- Un modèle approuvé est en lecture seule ; la modification passe par un clone.

- Les imports dédupliquent par hash de fichier et mapping/version.

- Les connecteurs futurs utilisent checkpoints et sequence numbers.

- Un calcul déjà en cours pour le même input_hash peut être réutilisé selon politique.

# 11. Événements et progression

| Canal | Usage |

| SSE/WebSocket | Progression des jobs et notifications applicatives |

| Outbox database | Événements fiables après transaction |

| Event types | calculation.started/progress/completed/failed, import.*, report.* |

| Payload | event_id, type, timestamp, organization_id, resource_id, correlation_id |

| Rétention | Courte pour notifications ; événements métier importants dans audit |



# 12. Intégrations industrielles futures

| Intégration | Contrat |

| OPC UA | Configuration endpoint, certificats, NodeId, sampling, qualité ; lecture seule |

| Modbus/PLC4X | Mapping adresse/tag, type, endian, unité ; passerelle isolée |

| MQTT/Sparkplug | Topics, birth/death certificates, métriques et qualité |

| Historian | Requêtes par tag/intervalle, agrégation et qualité |

| GIS | GeoJSON/WFS ou imports contrôlés |

| CMMS/ERP | Équipements, maintenance, coûts ; API spécifique |

| Moteur GasModels | Paquet de réseau versionné et résultat typé |

| FMU/OpenModelica | Fichier de modèle, paramètres, signaux et série de sortie |



# 13. Versionnement et compatibilité

- Version majeure dans l’URL pour changements incompatibles.

- Schéma JSON et OpenAPI publiés avec changelog.

- Dépréciation annoncée et télémétrie d’usage avant suppression.

- Les moteurs ont leur propre engine_version et input_schema_version.

- Les exports de projet indiquent version minimale et stratégie de migration.

- Tests contractuels entre frontend, API, worker et services spécialisés.

# 14. Critères de recette API

| Critère | Preuve |

| Documentation | OpenAPI complète et exemples valides |

| Sécurité | Endpoints refusés hors permissions |

| Validation | Erreurs de champs/unités structurées |

| Asynchrone | Calcul suivi de queued à completed/failed |

| Idempotence | Deux appels identiques ne créent pas de doublon |

| Concurrence | Conflit détecté sur version obsolète |

| Round-trip | Export/import JSON sans perte fonctionnelle |

| Performance | P95 des endpoints non calcul < 2 s |



# Sources et références

- D04/D05 - Exigences.

- D09/D12 - Dictionnaire et modèle de données.

- D11 - Architecture.

- OpenAPI et bonnes pratiques HTTP comme base technique.

Fin du document