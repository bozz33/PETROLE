Plateforme de transport et de stockage des hydrocarbures

D00

Index du dossier documentaire complet

Guide de lecture et registre des livrables D01 à D20

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D00 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Objet du dossier

- Registre des documents

- Ordre de lecture

- Décisions consolidées

- Hypothèses

- Utilisation des documents

- Éléments à confirmer

- Gestion des versions

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Objet du dossier

Ce dossier rassemble les documents nécessaires pour cadrer, spécifier, concevoir, développer, tester et préparer le pilote de la plateforme paramétrable de transport et de stockage des hydrocarbures. Il constitue la baseline documentaire version 1.0 du projet.

| État du projet La recherche générale est suffisamment avancée pour lancer la conception et le développement du MVP. Les validations réglementaires locales, les données réelles d’équipements et le site pilote seront ajoutés au moment approprié. |



# 2. Registre des documents

| Réf. | Document | Finalité |

| D01 | Document de cadrage officiel et plan directeur | Vision, périmètre, décisions et organisation |

| D02 | Vision produit et proposition de valeur | But, utilisateurs, bénéfices et différenciation |

| D03 | Cartographie des acteurs et processus métier | Rôles, flux, documents et contrôles |

| D04 | Cahier des charges fonctionnel complet | Exigences fonctionnelles identifiées et priorisées |

| D05 | Exigences non fonctionnelles | Performance, sécurité, qualité et maintenabilité |

| D06 | Catalogue des cas d’usage et scénarios | Modes normal, dégradé, secours et futurs |

| D07 | Référentiel scientifique et mathématique | Équations, hypothèses, méthodes et limites |

| D08 | Référentiel normatif international | ASME, API, ISO, IEC, ISA et cadre local |

| D09 | Dictionnaire des données | Entités, champs, unités, qualité et formats |

| D10 | Plan de validation scientifique | Cas tests, tolérances et dossier de preuve |

| D11 | Architecture logicielle détaillée | Composants, domaines, déploiement et ADR |

| D12 | Modèle conceptuel et logique des données | Schéma relationnel, versions et persistance |

| D13 | Spécification des API et intégrations | REST, jobs, fichiers et connecteurs |

| D14 | Stratégie open source et licences | Composants, décisions, audits et alternatives |

| D15 | Sécurité, SCADA et historisation | OT/IT, OPC UA, historian et continuité |

| D16 | Plan de développement du MVP | 24 sprints, équipe, charges, jalons et risques |

| D17 | Roadmap complète jusqu’au produit final | Évolution sur plusieurs phases et partenaires |

| D18 | Plan de tests, qualité et CI/CD | Validation, automatisation, releases et métriques |

| D19 | Modèles de rapports et interfaces | Écrans, graphiques, rapports et UX |

| D20 | Dossier pilote et protocole de validation industrielle | Trame d’un pilote réel, critères et Go/No-Go |



# 3. Ordre de lecture recommandé

| Étape | Documents | Décision |

| 1. Comprendre | D01-D03 | Pourquoi, pour qui, avec quels processus |

| 2. Spécifier | D04-D06 | Ce que le système doit faire |

| 3. Fonder | D07-D10 | Comment calculer, selon quelles règles et comment prouver |

| 4. Concevoir | D11-D15 | Comment construire, stocker, intégrer et sécuriser |

| 5. Exécuter | D16-D19 | Comment développer, tester et livrer |

| 6. Industrialiser | D20 | Comment valider sur une installation réelle |



# 4. Décisions consolidées

- Équipe : deux développeurs appuyés par des assistants IA et des experts ponctuels.

- Socle : Python, FastAPI, PostgreSQL/PostGIS, React/TypeScript, NumPy/SciPy, fluids, CoolProp et Pyomo.

- Architecture : monolithe modulaire pour le MVP, services spécialisés ultérieurement.

- MVP : pipeline liquide stationnaire, stations et pompes, scénarios, réservoirs, transferts, données et rapports.

- Normes : standards internationaux et exigences locales ; les documents russes servent uniquement de référence académique.

- SCADA : lecture seule dans les premières versions ; aucune commande ou fonction de sécurité.

- Validation : cas analytiques, benchmarks, cas académique fourni, puis site pilote.

- Calendrier : environ 12 à 14 mois recommandé pour le MVP avec périmètre gelé.

# 5. Hypothèses de baseline

| Hypothèse | Traitement |

| Nom commercial | Nom générique temporaire utilisé dans les documents |

| Client prioritaire | Bureaux d’études, exploitants de pipelines liquides et dépôts |

| Déploiement | Local et cloud privé avec le même produit |

| Unité interne | SI |

| Langue | Français, architecture internationalisable |

| Site pilote | À sélectionner après MVP/RC |

| Budget | Non chiffré faute de coûts salariaux et d’infrastructure |

| Normes locales | À confirmer officiellement par projet |

| Données fabricant | À importer pour chaque cas réel |



# 6. Utilisation des documents

- D04 et D05 alimentent le backlog et les critères d’acceptation.

- D07 et D10 gouvernent toute modification du noyau scientifique.

- D08 gouverne le moteur de règles ; les textes officiels doivent être acquis légalement.

- D09 à D13 servent à la conception détaillée et aux contrats techniques.

- D14 conditionne l’adoption des dépendances et licences.

- D15 est obligatoire avant toute intégration OT.

- D16 est le plan opérationnel du MVP et doit être révisé à chaque jalon.

- D20 n’est exécutable qu’après accord d’un opérateur et disponibilité des données.

# 7. Éléments à confirmer pendant le projet

- Nom du produit et identité visuelle.

- Tarification, licence et modèle commercial.

- Expert métier/normatif responsable des approbations.

- Normes achetées et éditions contractuelles par projet.

- Données réelles de pompes, compresseurs, produits et réservoirs.

- Volumétrie SCADA et politique de rétention.

- Opérateur et installation du site pilote.

- Budget d’hébergement, de normes, de sécurité et de support.

- Calendrier selon disponibilité réelle des deux développeurs.

# 8. Gestion des versions

| Version | Statut | Règle |

| 1.0 | Baseline initiale | Tous les documents D01-D20 livrés |

| 1.x | Révisions mineures | Clarifications sans changement majeur de périmètre |

| 2.0 | Après POC/architecture | Décisions techniques et exigences ajustées |

| 3.0 | Après MVP | Documentation alignée sur le produit réel |

| 4.0 | Après pilote | Référentiel industriel et critères validés |



# Sources et références

- Documents D01 à D20 contenus dans le même dossier.

- Sources techniques et normatives citées dans D07, D08 et D14.

Fin de l’index - baseline documentaire v1.0