Plateforme de transport et de stockage des hydrocarbures

D16

Plan de développement du MVP

Organisation de deux développeurs, backlog, sprints, charges et jalons

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D16 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Hypothèses

- Équipe

- Périmètre MVP

- Stratégie

- Lots

- Plan 24 sprints

- Répartition

- Jalons

- Charges

- Rituels

- Outils IA

- Critères de fin

- Risques

- Après MVP

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Hypothèses de planification

| Hypothèse | Valeur de travail |

| Équipe | 2 développeurs à temps plein, assistés par des outils IA |

| Cadence | Sprints de 2 semaines |

| Durée cible MVP | 48 semaines de développement + marge de stabilisation selon disponibilité |

| Capacité brute | Environ 96 semaines-personnes sur 48 semaines |

| Capacité utile | 70 à 80 % après coordination, support, recherche, documentation et imprévus |

| Mode de travail | Monolithe modulaire, livraison incrémentale et déploiement continu de test |

| Accès métier | Revue régulière par l’ingénieur mine/pétrole et experts à identifier |

| Site pilote | Non requis pour le premier prototype, requis avant validation industrielle |



| Engagement réaliste Le calendrier suppose un gel strict du MVP. L’ajout précoce du gaz complet, des transitoires, du SCADA temps réel ou d’une détection de fuite certifiée rendrait le planning irréaliste pour deux développeurs. |



# 2. Organisation de l’équipe

| Rôle | Responsabilités principales | Responsabilités secondaires |

| Développeur A - Science/Backend | Noyau physique, solveurs, optimisation, API calcul, validation | Base de données, rapports, revue frontend |

| Développeur B - Produit/Frontend/Data | Frontend, éditeur, imports, données, déploiement | API métier, tests E2E, observabilité |

| Assistants IA | Génération de tests, documentation, revue, prototypes, recherche | Migration, analyse d’erreurs, exemples |

| Référent métier | Validation des cas, données, terminologie et scénarios | Priorisation et recette |

| Expert externe ponctuel | Revue scientifique/normative et sécurité | Validation avant pilote |



# 3. Périmètre fonctionnel du MVP

| Inclus | Exclus du MVP |

| Projet, organisations, utilisateurs et versions | Commande directe de pompes/vannes |

| Réseau liquide paramétrable et profil altimétrique | Certification ou conformité automatique complète |

| Produits et propriétés par tables/corrélations | Gazoduc complet et cartes de compresseurs |

| Pompes série/parallèle, secours, courbes et NPSH | Transitoires détaillés et coup de bélier industriel |

| Calcul stationnaire, pressions, pertes et diagnostics | Pipeline multiphasique pétrole-gaz-eau |

| Réservoirs, barémages et transfert bac-à-bac | Détection de fuite temps réel |

| Scénarios et optimisation par énumération/Pyomo simple | Historian industriel haute disponibilité |

| CSV/XLSX, graphiques, comparaisons et rapports | Application mobile native |



# 4. Stratégie de livraison

- Construire d’abord un noyau scientifique testable en ligne de commande.

- Mettre en place tôt la base, l’API, l’authentification et le déploiement pour éviter un prototype jetable.

- Livrer une première verticale : projet → réseau simple → calcul → graphique → rapport.

- Ajouter les stations et pompes avant les réservoirs.

- Ajouter les scénarios et l’optimisation seulement après stabilisation du solveur.

- Conserver un backlog séparé de recherche pour les éléments non validés.

- Effectuer une revue de périmètre à chaque jalon et reporter les demandes non critiques.

# 5. Lots de travail

| Lot | Contenu | Charge indicative |

| L0 - Fondations | Repo, CI, qualité, architecture, Docker, conventions | 6 sem.-pers. |

| L1 - Plateforme | Auth, organisations, projets, versions, audit | 10 sem.-pers. |

| L2 - Modélisation | Réseau, profil, catalogues, validation | 14 sem.-pers. |

| L3 - Noyau liquide | Propriétés, pertes, réseau, solveur, diagnostics | 18 sem.-pers. |

| L4 - Pompes/stations | Courbes, série/parallèle, NPSH, puissance | 12 sem.-pers. |

| L5 - Scénarios/optimisation | Overrides, comparaison, recherche de configuration | 10 sem.-pers. |

| L6 - Réservoirs/transferts | Barémage, inventaire, simulation et bilan | 14 sem.-pers. |

| L7 - Données/rapports | CSV/XLSX, graphiques, rapports et exports | 10 sem.-pers. |

| L8 - Stabilisation | Performance, sécurité, recette, documentation | 10 sem.-pers. |



# 6. Plan détaillé des 24 sprints

| Sprint | Objectif | Travaux | Livrable |

| S01 | Vision exécutable | Repo, ADR, CI, Docker, conventions, squelette API/UI | Architecture exécutable |

| S02 | Qualité et données de base | PostgreSQL/PostGIS, migrations, unités, erreurs | Base et pipeline CI |

| S03 | Identité et organisations | Auth, utilisateurs, rôles, organisation | Connexion et RBAC initial |

| S04 | Projets et versions | Sites, projets, modèle/version, audit | Créer/cloner/archiver |

| S05 | Catalogues | Matériaux, fluides, équipements génériques | CRUD et imports simples |

| S06 | Réseau v1 | Nœuds, tronçons, validation topologique | Réseau simple calculable |

| S07 | Profil et carte | Import profil, interpolation, PostGIS, aperçu | Tracé et profil validés |

| S08 | Hydraulique composants | Re, λ, pertes, unités, tests analytiques | Bibliothèque validée V1 |

| S09 | Solveur linéaire v1 | Conduite série, conditions limites, diagnostics | Cas simple de bout en bout |

| S10 | Solveur réseau v2 | Assemblage non linéaire, Newton/hybride | Réseau ramifié simple |

| S11 | Résultats et graphiques | Persistance, profil pression/charge, exports | Verticale complète V1 |

| S12 | Produits avancés | Tables ρ/ν/pv, interpolation, avertissements | Propriétés versionnées |

| S13 | Courbes de pompe | Import H/η/P/NPSHr, fit et visualisation | Catalogue pompe |

| S14 | Stations | Pompes en série, aspiration/refoulement, puissance | Station calculée |

| S15 | Pompes parallèle/VSD | Partage, affinité, limites, secours | Configurations multiples |

| S16 | Scénarios | Overrides, clone, indisponibilité, comparaison | Modes normal/dégradé |

| S17 | Recherche configuration | Énumération filtrée, classement, coût énergie | Recommandation MVP |

| S18 | Réservoirs | Fiches, barémages, inventaires, niveaux | Parc de bacs |

| S19 | Transfert v1 | Chemin source-pompe-destination, point initial | Calcul transfert statique |

| S20 | Transfert dynamique | Évolution niveaux, événements, durée, énergie | Simulation bac-à-bac |

| S21 | Bilan matière | Entrées/sorties/stocks, écart et incertitude simple | Rapport de mouvement |

| S22 | Imports et rapports | XLSX/CSV robuste, modèles de notes/rapports | Livrables utilisateurs |

| S23 | Recette et performance | Cas D10, charge, sécurité, restauration | Release candidate |

| S24 | Stabilisation et démonstration | Correction, documentation, installation, formation | MVP 1.0 |



# 7. Répartition indicative par sprint

| Période | Développeur A | Développeur B | Travail commun |

| S01-S04 | Architecture backend, unités, auth services | Frontend shell, design, auth UI, projets | ADR, CI, code review |

| S05-S08 | Catalogues scientifiques, hydraulique | CRUD, imports, réseau UI, profil | Schémas, tests |

| S09-S12 | Solveurs, diagnostics, propriétés | Visualisation, résultats, workflow | Validation D10 |

| S13-S17 | Pompes, stations, optimisation | Écrans courbes/scénarios/comparaison | Recette métier |

| S18-S21 | Calculs réservoir/transfert/bilan | UI bacs, mouvements, graphiques | Cas de validation |

| S22-S24 | Rapports, performance scientifique | Imports, déploiement, UX, docs | Sécurité, release |



# 8. Jalons et décisions Go/No-Go

| Jalon | Fin estimée | Conditions |

| M0 - Fondations | S04 | Déploiement reproductible, RBAC et migrations |

| M1 - Première hydraulique | S11 | Conduite/réseau simple validé et graphique |

| M2 - Stations | S15 | Pompes série/parallèle, puissance et NPSH validés |

| M3 - Scénarios | S17 | Comparaison et recherche de configuration |

| M4 - Stockage | S21 | Transfert dynamique et bilan matière |

| M5 - RC | S23 | Cas D10, sécurité et performance |

| M6 - MVP 1.0 | S24 | Documentation, installation et démonstration acceptées |



# 9. Estimation de charge et marge

La charge fonctionnelle estimée représente environ 90 à 100 semaines-personnes. La capacité brute de deux personnes pendant 48 semaines est de 96 semaines-personnes ; le plan est donc tendu. Il nécessite l’usage efficace des assistants IA, une forte automatisation et une marge obtenue par réduction de périmètre ou prolongation de quelques semaines.

| Scénario | Durée calendaire | Hypothèses |

| Optimiste | 10-11 mois | Peu d’imprévus, expert disponible, composants stables |

| Recommandé | 12-14 mois | Marge qualité, recherche et corrections |

| Prudent | 15-18 mois | Temps partiel, données difficiles, refonte du solveur |

| Avec gaz/transitoires ajoutés | Non recommandé | Au moins 12-24 mois supplémentaires |



# 10. Rituels et gestion

- Planification de sprint : 2 heures toutes les deux semaines.

- Synchronisation quotidienne courte ou asynchrone structurée.

- Revue de code obligatoire pour tout changement critique.

- Démonstration et revue métier à chaque sprint ou au minimum mensuelle.

- Rétrospective et mise à jour du registre de risques.

- Revue scientifique formelle aux jalons M1, M2 et M4.

- Release notes et migration testée à chaque version candidate.

# 11. Utilisation encadrée des assistants IA

| Usage autorisé | Contrôle humain |

| Génération de squelette, tests et fixtures | Revue de code et exécution |

| Documentation et exemples | Validation technique et métier |

| Recherche de bibliothèques/algorithmes | Vérification de sources primaires |

| Analyse d’erreurs et refactoring | Benchmarks et tests de non-régression |

| Génération de migrations simples | Revue SQL et restauration testée |

| Création de cas synthétiques | Comparaison à une solution indépendante |

| Traduction/terminologie | Validation par expert francophone/anglophone |



| Interdictions Les assistants IA ne valident pas seuls une équation, une règle normative, une migration destructive, une sécurité OT ou un résultat industriel. |



# 12. Definition of Done

- Exigence et critères d’acceptation identifiés.

- Code typé, revu et formaté.

- Tests unitaires/intégration/E2E pertinents réussis.

- Documentation et migration mises à jour.

- Aucune vulnérabilité critique connue introduite.

- Cas scientifique associé lorsqu’une formule change.

- Observabilité et message d’erreur ajoutés.

- Démonstration effectuée et acceptation enregistrée.

- Déployé sur l’environnement de test.

# 13. Principaux risques de planning

| Risque | Impact | Réponse |

| Solveur plus complexe que prévu | Fort | POC tôt, cas simples, expert ponctuel |

| Éditeur graphique trop ambitieux | Fort | Formulaires + vue graphe contrôlée au MVP |

| Périmètre qui s’étend | Fort | Comité de changement et backlog LATER |

| Absence de données fabricant | Moyen | Bibliothèque synthétique et import configurable |

| Un développeur indisponible | Fort | Documentation, pair programming, tâches critiques partagées |

| Dépendance open source instable | Moyen | Versions verrouillées et adapters |

| Normes inaccessibles | Moyen | Budget d’acquisition et expert |

| Manque de relecture métier | Fort | Planifier des revues et ne pas déclarer validé |



# 14. Après le MVP

- Pilote avec données réelles et calibration.

- Analyse historique avancée et réconciliation.

- Multiproduits et interfaces.

- Régimes transitoires liquides.

- Passerelle SCADA en lecture seule.

- Module gaz et compression.

- Détection de fuite et jumeau numérique.

- Industrialisation, haute disponibilité et certifications par site.

# Sources et références

- D04/D05 - Périmètre et qualité.

- D10 - Validation.

- D11-D15 - Architecture, API, open source et sécurité.

- D18 - Tests et CI/CD.

Fin du document