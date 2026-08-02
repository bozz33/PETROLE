|  |  |  |



Plateforme de transport et de stockage des hydrocarbures

Document de cadrage officiel et plan directeur du projet

Modélisation  •  Calcul  •  Simulation  •  Analyse de données  •  Optimisation

| BACS | → | POMPES | → | PIPELINE | → | TERMINAL |



| Référence | HTP-CAD-001 |

| Version | 0.1 - cadrage initial |

| Date | 2 août 2026 |

| Équipe | 2 développeurs, appuyés par des assistants IA |

| Statut | Base officielle pour la conception et le cahier des charges |



Document de travail structurant - diffusion contrôlée

# Fiche de contrôle du document

| Champ | Valeur |

| Titre | Document de cadrage officiel et plan directeur du projet |

| Référence | HTP-CAD-001 |

| Version | 0.1 |

| Responsables | Équipe projet : 2 développeurs avec assistants IA |

| Objet | Fixer la vision, le périmètre, les principes, les modules, les phases et les décisions structurantes. |

| Documents suivants | Cahier des charges fonctionnel, référentiel scientifique, architecture technique, modèle de données, plan de développement et plan de validation. |

| Base documentaire | Supports transmis sur pipelines, pompes, dépôts pétroliers, stockage, transferts, gazoducs et simulation numérique. |



|  | Décision de référence La plateforme sera fondée sur les normes internationales reconnues et sur les exigences réglementaires du pays d’installation. Les documents russes transmis sont conservés comme références scientifiques, algorithmiques et comparatives, sans constituer la base normative principale. |



## Historique des versions

| Version | Date | Évolution | Statut |

| 0.1 | 02/08/2026 | Création du cadrage initial à l’issue de la phase de recherche. | En revue |



# Table des matières

| Sections 1 à 11 | Sections 12 à annexes |

| 1. Résumé exécutif | 12. Orientation technologique |

| 2. Contexte et justification | 13. Stratégie open source |

| 3. Vision, mission et finalité | 14. Périmètre du MVP |

| 4. Problèmes auxquels la plateforme répond | 15. Feuille de route jusqu’au produit final |

| 5. Objectifs stratégiques et opérationnels | 16. Organisation de l’équipe et méthode de réalisation |

| 6. Périmètre fonctionnel cible | 17. Exigences non fonctionnelles de haut niveau |

| 7. Principes de paramétrage et d’adaptabilité | 18. Risques majeurs et mesures de maîtrise |

| 8. Utilisateurs et acteurs | 19. Critères de succès |

| 9. Cas d’usage prioritaires | 20. Plan documentaire complet |

| 10. Référentiel normatif et réglementaire | 21. Décisions actées et points à confirmer |

| 11. Principes scientifiques et de sûreté | Annexes : glossaire, références et synthèse des modules |



# 1. Résumé exécutif

Le projet vise à développer une plateforme paramétrable de modélisation, de calcul, de simulation, d’analyse de données et d’optimisation des systèmes de transport et de stockage des hydrocarbures. Elle couvrira progressivement les pipelines liquides, les stations de pompage, les dépôts pétroliers, les transferts entre réservoirs, les pipelines multiproduits, les régimes transitoires, les gazoducs, les stations de compression, l’analyse des données industrielles et la détection des anomalies.

La plateforme ne sera pas limitée à un cas académique fixe. L’utilisateur pourra construire ou importer son installation, définir les équipements, les propriétés des produits, les conditions d’exploitation, les règles normatives et les scénarios de fonctionnement. Les résultats devront être explicables, traçables, reproductibles et accompagnés de contrôles de validité.

|  | Finalité du produit Aider les ingénieurs, exploitants et analystes à comprendre une installation, vérifier sa faisabilité, calculer ses régimes de fonctionnement, comparer des scénarios, réduire les risques et optimiser l’énergie, les stocks et la disponibilité des équipements. |



Le développement sera réalisé par une équipe de deux développeurs assistés par des outils d’intelligence artificielle. Cette taille d’équipe impose une stratégie de livraison progressive, un monolithe modulaire au départ, une forte automatisation des tests et une sélection prudente des composants open source.

# 2. Contexte et justification

Les systèmes de transport et de stockage des hydrocarbures réunissent des pipelines de longue distance, des stations de pompage ou de compression, des réseaux technologiques de dépôts, des réservoirs, des vannes, des instruments et des systèmes de contrôle. Leur fonctionnement dépend simultanément de l’hydraulique, de la thermodynamique, de la topographie, des propriétés des produits, des caractéristiques des machines et des contraintes de sécurité.

Les documents étudiés décrivent les méthodes de calcul des régimes stationnaires, des pertes de charge, des courbes de pompes, des zones gravitaires, des transferts entre réservoirs, des parcs de stockage, des mélanges multiproduits, des coups de bélier et des systèmes gaziers. Ils constituent une base scientifique utile pour la conception des moteurs de calcul, sous réserve de validation et d’alignement sur les normes internationales retenues.

- Les outils spécialisés existants sont souvent coûteux, cloisonnés ou centrés sur une seule famille de problèmes.

- Les calculs sont fréquemment répartis entre feuilles Excel, scripts, logiciels métiers et données SCADA non réconciliées.

- La comparaison systématique des modes normal, dégradé et secours reste difficile sans modèle unifié.

- Les entreprises ont besoin d’une solution adaptable à leur installation, à leurs produits, à leurs règles et à leurs données.

- La plateforme peut aussi constituer un environnement de formation, de validation et de capitalisation du savoir métier.

# 3. Vision, mission et finalité

## 3.1 Vision

Devenir une plateforme d’ingénierie numérique et d’aide à l’exploitation capable de représenter, simuler et optimiser les chaînes de transport et de stockage des hydrocarbures, depuis le réservoir source jusqu’au terminal ou au client final.

## 3.2 Mission

Transformer des données techniques et industrielles hétérogènes en un modèle cohérent, calculable et vérifiable, puis fournir des résultats compréhensibles : débits, pressions, puissances, niveaux, marges de sécurité, consommations, anomalies, scénarios et recommandations.

## 3.3 Proposition de valeur

| Valeur apportée | Description |

| Unification | Un seul environnement pour les pipelines, stations, réservoirs, scénarios, données et rapports. |

| Paramétrage | Adaptation à des installations, produits, normes et contraintes différents sans recoder le cœur. |

| Traçabilité | Conservation des données d’entrée, hypothèses, versions de calcul, règles et résultats. |

| Explicabilité | Présentation des équations, contrôles, marges et causes de non-faisabilité. |

| Optimisation | Recherche de configurations réduisant l’énergie, les coûts, les risques et les indisponibilités. |

| Évolutivité | Passage progressif du calcul hors ligne au jumeau numérique en lecture seule. |



# 4. Problèmes auxquels la plateforme répond

| Problème métier | Réponse attendue de la plateforme |

| Dimensionnement et vérification dispersés | Centraliser les données, méthodes, résultats et rapports. |

| Nombreuses configurations possibles | Générer et comparer automatiquement les modes d’exploitation. |

| Difficulté à prévoir les conséquences d’une panne | Simuler les modes dégradés et les séquences de secours. |

| Écarts entre calcul et exploitation réelle | Comparer le modèle aux données historiques et réconcilier les mesures. |

| Risque de surpression, cavitation ou débordement | Calculer les marges et signaler les contraintes violées. |

| Consommation énergétique élevée | Optimiser les pompes, compresseurs, consignes et horaires. |

| Données SCADA difficiles à exploiter | Historiser, qualifier, nettoyer, visualiser et analyser les séries temporelles. |

| Dépendance à des outils propriétaires | S’appuyer sur un cœur maîtrisé et des briques open source auditées. |



# 5. Objectifs stratégiques et opérationnels

## 5.1 Objectifs stratégiques

- Créer un actif logiciel scientifique maîtrisé par l’équipe projet.

- Proposer une solution adaptée aux besoins africains tout en restant utilisable à l’international.

- Réduire la dépendance à un logiciel unique ou à un fournisseur unique.

- Construire progressivement un jumeau numérique en lecture seule et un outil de formation opérateur.

- Permettre une offre locale, cloud ou hybride selon les contraintes de l’opérateur.

## 5.2 Objectifs opérationnels

- Calculer les régimes hydrauliques stationnaires des pipelines liquides.

- Modéliser des stations comportant plusieurs pompes principales, parallèles, en série et de secours.

- Calculer et planifier les transferts entre réservoirs et les opérations de dépôt.

- Comparer des scénarios normaux, dégradés, de maintenance et d’urgence.

- Importer et analyser des données Excel, CSV, historian et SCADA.

- Étendre le moteur aux transitoires, multiproduits, gazoducs et stations de compression.

- Produire des graphiques, tableaux, notes de calcul et rapports d’exploitation.

# 6. Périmètre fonctionnel cible

| Code | Module | Portée |

| M1 | Modélisation des installations | Pipelines, tronçons, stations, réservoirs, vannes, collecteurs, instruments et topologie. |

| M2 | Hydraulique des liquides | Débit, pression, pertes de charge, profil hydraulique, cavitation et zones gravitaires. |

| M3 | Stations de pompage | Courbes, série/parallèle, vitesse variable, secours, puissance, rendement et NPSH. |

| M4 | Stockage et dépôts | Réservoirs, barémage, stocks, réception, expédition, pertes et bilan matière. |

| M5 | Transferts technologiques | Chemins de transfert, niveaux dynamiques, temps, énergie, débordement et sélection de pompe. |

| M6 | Scénarios et optimisation | Modes normal/dégradé/secours, comparaison multicritère et configuration recommandée. |

| M7 | Analyse de données | Import, nettoyage, qualité, KPI, comparaison modèle-mesures et détection de dérive. |

| M8 | Multiproduits | Lots, interfaces, mélanges, ordonnancement, capacité de stockage et qualité. |

| M9 | Régimes transitoires | Démarrages, arrêts, fermeture de vanne, coup de bélier et séparation de colonne. |

| M10 | Gazoducs et compression | Gaz réel, line-pack, cartes de compresseurs, anti-surge et optimisation. |

| M11 | Surveillance et fuite | Bilan massique, modèles en temps réel, statistiques et localisation probable. |

| M12 | Rapports et collaboration | Versions, validation, commentaires, exports PDF/Excel/CSV et audit. |



|  | Limite structurante La plateforme d’analyse ne remplacera pas les automates, les systèmes instrumentés de sécurité ni les procédures d’urgence. Les premières versions seront en saisie manuelle ou en lecture seule des données industrielles. |



# 7. Principes de paramétrage et d’adaptabilité

L’adaptabilité ne signifie pas qu’une seule équation convient à toutes les situations. Elle repose sur un modèle de données commun, des équipements configurables et plusieurs moteurs scientifiques spécialisés.

| Dimension paramétrable | Exemples |

| Topologie | Nombre de tronçons, stations, réservoirs, branches, bypass et points d’injection/soutirage. |

| Conduites | Longueur, diamètre, épaisseur, matériau, rugosité, pression admissible, profil et isolation. |

| Produits | Densité, viscosité, pression de vapeur, compressibilité, température et données laboratoire. |

| Machines | Courbes H(Q), rendement, puissance, NPSH, vitesse, cartes compresseur et disponibilité. |

| Exploitation | Débit demandé, pressions limites, niveaux, équipements indisponibles et tarifs énergétiques. |

| Normes et règles | Référentiel choisi, édition, pays, opérateur, limites particulières et unités. |

| Calculs | Tolérances, corrélations, modèles thermiques, hypothèses stationnaires ou dynamiques. |

| Données | Saisie manuelle, import Excel/CSV, API, historian, OPC UA ou MQTT. |



# 8. Utilisateurs et acteurs

| Acteur | Besoins principaux |

| Ingénieur pipeline | Modéliser, calculer, vérifier les pressions, débits, pertes et scénarios. |

| Ingénieur exploitation | Choisir le mode de fonctionnement et anticiper les contraintes. |

| Ingénieur dépôt | Gérer les stocks, transferts, capacités et bilans. |

| Ingénieur gaz | Analyser les gazoducs, compresseurs, line-pack et consommations. |

| Analyste de données | Nettoyer, croiser, visualiser et modéliser les données historiques. |

| Maintenance | Suivre disponibilité, dérives, heures de marche et événements. |

| HSE / intégrité | Étudier les scénarios, alarmes, limites, fuites et risques. |

| Dispatcher / planificateur | Programmer lots, mouvements, bacs et horaires. |

| Direction | Consulter KPI, énergie, disponibilité, capacité et coûts. |

| Formateur / étudiant | Utiliser des cas pédagogiques et un simulateur hors ligne. |



# 9. Cas d’usage prioritaires

| Identifiant | Cas d’usage |

| UC-01 | Créer un modèle de pipeline à partir de données manuelles ou importées. |

| UC-02 | Calculer le débit et la distribution de pression pour une configuration donnée. |

| UC-03 | Déterminer les pressions d’aspiration et de refoulement de chaque station. |

| UC-04 | Identifier les zones gravitaires, la cavitation et les dépassements de pression. |

| UC-05 | Tester les combinaisons de pompes principales et de secours. |

| UC-06 | Simuler un transfert entre deux ou plusieurs réservoirs. |

| UC-07 | Calculer les niveaux, le temps de transfert, l’énergie et le risque de débordement. |

| UC-08 | Comparer le mode normal à une station indisponible ou une pompe en panne. |

| UC-09 | Optimiser la configuration pour un débit demandé et un coût énergétique minimal. |

| UC-10 | Importer des données historiques et comparer mesures et simulation. |

| UC-11 | Générer un rapport de calcul et un dossier de scénario traçable. |

| UC-12 | Étendre ultérieurement le projet aux transitoires et aux gazoducs. |



# 10. Référentiel normatif et réglementaire

Le logiciel sera conçu pour sélectionner et versionner les référentiels applicables. Les normes seront des règles de projet, et non des valeurs figées dans le code. L’édition en vigueur devra être vérifiée et enregistrée au moment de chaque projet ou déploiement.

| Domaine | Familles de références prévues |

| Pipelines liquides | ASME B31.4, ISO 13623, API RP 1160 et exigences de l’opérateur. |

| Gazoducs | ASME B31.8, ASME B31.8S, ISO 13623 et prescriptions nationales. |

| Pompes | API 610, ISO 9906, API 682 et exigences fabricants. |

| Compresseurs | API 617, API 618, API 614, API 670 et cartes fabricants. |

| Réservoirs | API 650, API 653, API 2000, API 2350 et API 2610. |

| Mesure et stocks | API MPMS, exigences de métrologie et procédures de l’opérateur. |

| Détection de fuite | API RP 1130, API RP 1175 et objectifs de performance du site. |

| Sécurité fonctionnelle | IEC 61511 et étude de risques du projet. |

| Cybersécurité industrielle | IEC 62443 et politiques de l’opérateur. |

| Alarmes et interopérabilité | ISA-18.2, OPC UA / IEC 62541 et protocoles approuvés. |

| Côte d’Ivoire / sous-région | Lois, décrets, environnement, installations classées, métrologie et qualité des produits. |



|  | Hiérarchie d’application 1) loi et autorité du pays ; 2) exigences du contrat et de l’opérateur ; 3) normes internationales sélectionnées ; 4) méthodes internes validées ; 5) sources académiques et comparatives. |



# 11. Principes scientifiques et de sûreté

- Séparer strictement les données d’entrée, le moteur de calcul, les règles normatives, l’interface et les rapports.

- Associer à chaque résultat les hypothèses, la méthode, les unités, la tolérance et le statut de convergence.

- Contrôler la conservation de la masse et, lorsque pertinent, de l’énergie.

- Refuser ou signaler explicitement les scénarios non réalisables au lieu de produire des valeurs artificielles.

- Maintenir une bibliothèque de cas de validation manuels, académiques, publiés et industriels.

- Comparer les moteurs internes à des outils indépendants lorsque cela est possible.

- Ne pas confier à un modèle de langage la réalisation des calculs déterministes ou des décisions de sécurité.

- Conserver une validation humaine obligatoire pour les recommandations et les rapports officiels.

## 11.1 Statuts de résultat

| Statut | Signification |

| VALIDE | Calcul convergé, contrôles réussis et données suffisantes. |

| VALIDE AVEC AVERTISSEMENTS | Résultat exploitable avec hypothèses ou marges faibles. |

| NON RÉALISABLE | Contraintes physiques ou d’exploitation incompatibles. |

| NON CONVERGÉ | Le solveur n’a pas atteint la tolérance définie. |

| DONNÉES INSUFFISANTES | Paramètres obligatoires absents ou incohérents. |

| HORS DOMAINE | Le modèle choisi n’est pas valable pour le cas. |



# 12. Orientation technologique

|  | Choix recommandé Python sera le langage principal du backend scientifique et PostgreSQL avec PostGIS sera la base centrale. Les moteurs spécialisés pourront être intégrés comme bibliothèques ou services isolés. |



| Couche | Technologies recommandées | Rôle |

| Frontend | React + TypeScript | Éditeur, tableaux, cartes, graphiques et workflows. |

| API | Python + FastAPI + Pydantic | Services métier, validation et exposition OpenAPI. |

| Calcul scientifique | NumPy, SciPy, moteur interne | Solveurs, interpolation, équations et validation. |

| Hydraulique | fluids + fonctions internes | Corrélations, pertes, composants et calculs contrôlés. |

| Propriétés | Base interne + CoolProp | Propriétés génériques et données réelles de laboratoire. |

| Optimisation | Pyomo + solveurs adaptés | NLP, MILP et MINLP selon les problèmes. |

| Données métier | PostgreSQL | Projets, équipements, versions, scénarios et résultats. |

| SIG | PostGIS | Tracés, profils, stations, zones et géométries. |

| Séries temporelles | PostgreSQL partitionné puis TimescaleDB/IoTDB | Historique de capteurs et agrégations. |

| Tâches longues | Workers Python + file de tâches | Calculs asynchrones, optimisation et rapports. |

| Fichiers | Stockage objet compatible S3 | Imports, modèles, pièces jointes et rapports. |

| Déploiement | Docker/Podman | Installation locale, cloud ou hybride. |



## 12.1 Principe d’architecture

Le projet débutera par un monolithe modulaire pour limiter la complexité opérationnelle. Les modules conserveront des frontières claires afin d’extraire ultérieurement les moteurs gaz, transitoire, optimisation ou SCADA en services séparés lorsque leur charge ou leur technologie l’exigera.

# 13. Stratégie open source

| Composant | Usage prévu | Position |

| NumPy / SciPy | Calcul numérique et solveurs. | Cœur MVP |

| fluids | Corrélations hydrauliques et composants. | Cœur MVP, sous contrôle |

| CoolProp | Propriétés thermophysiques génériques. | Cœur complémentaire |

| Pyomo | Optimisation des modes et planification. | Cœur optimisation |

| PostgreSQL / PostGIS | Données métier et géographiques. | Cœur données |

| pandapipes | Comparaison de réseaux simples. | Benchmark, pas cœur unique |

| GasModels.jl | Optimisation future des réseaux gaziers. | Service spécialisé futur |

| OpenModelica / Modelica.Fluid | Prototypes dynamiques et validation. | Service ou FMU futur |

| DWSIM | Comparaison de procédés et terminaux. | Outil externe sous audit de licence |

| open62541 / PLC4X | Connectivité OPC UA et protocoles industriels. | Passerelle future |

| TimescaleDB / Apache IoTDB | Historisation industrielle. | Selon volumes |



- Réaliser un audit de licence avant toute intégration commerciale.

- Éviter qu’un projet externe devienne un point de défaillance unique.

- Encapsuler chaque composant derrière une interface contrôlée par l’équipe.

- Créer des tests de non-régression indépendants des bibliothèques utilisées.

- Conserver la propriété du modèle métier, des scénarios, des règles et des données.

# 14. Périmètre du MVP

Le MVP doit être suffisamment utile pour un ingénieur, tout en restant réalisable par deux développeurs. Il ciblera en priorité les pipelines liquides, les stations de pompage et les transferts de dépôt.

| Inclus dans le MVP | Reporté après le MVP |

| Création de projets et gestion des versions | Commande directe des automates et vannes |

| Pipelines et profils altimétriques paramétrables | Certification d’un système de détection de fuite |

| Nombre configurable de stations et pompes | Gazoducs industriels complets |

| Pompes en série, parallèle, principale et secours | Écoulements multiphasiques pétrole-gaz-eau |

| Calcul hydraulique stationnaire des liquides | Jumeau numérique temps réel |

| Pressions, débits, pertes, cavitation et zones gravitaires | Simulateur opérateur complet |

| Réservoirs, tables de barémage et transferts bac-à-bac | Optimisation MINLP à grande échelle |

| Scénarios normal, dégradé, maintenance et secours | Haute disponibilité multi-site certifiée |

| Optimisation simple et comparaison multicritère | Intégrations SCADA en écriture |

| Import Excel/CSV, graphiques et rapports | Détection de fuite externe par fibre optique |



## 14.1 Critères de sortie du MVP

- Les cas de validation stationnaires atteignent les tolérances fixées.

- La conservation de masse est contrôlée et documentée.

- Un ingénieur peut créer un réseau, lancer un calcul et comprendre les résultats sans modifier le code.

- Les scénarios non réalisables sont identifiés avec une cause exploitable.

- Les rapports conservent les entrées, hypothèses, règles, résultats et avertissements.

- L’installation locale est reproductible à l’aide de conteneurs.

# 15. Feuille de route jusqu’au produit final

| Phase | Lot | Résultat principal |

| Phase 0 | Fondations scientifiques | Audit open source, refonte du script existant, unités, cas tests et architecture de base. |

| Phase 1 | MVP pipeline liquide | Modèle réseau, stations, pompes, calcul stationnaire, scénarios, graphiques et rapports. |

| Phase 2 | Stockage et transferts | Réservoirs, barémage, bilan matière, mouvements, sélection de pompe et débordement. |

| Phase 3 | Analyse de données | Imports, qualité, KPI, comparaison mesure-modèle et tableaux de bord. |

| Phase 4 | Multiproduits et transitoires | Lots, interfaces, mélange, coup de bélier et événements temporels. |

| Phase 5 | Connexion industrielle | Historian, OPC UA, MQTT, qualité des tags et lecture seule SCADA. |

| Phase 6 | Gazoducs et compression | Gaz réel, line-pack, compresseurs, anti-surge et optimisation. |

| Phase 7 | Fuite et jumeau numérique | Bilan massique, RTTM, statistiques, estimation d’état et prévision. |

| Phase 8 | Industrialisation | Haute disponibilité, cybersécurité, multi-sites, formation et validation par opérateur. |



|  | Règle de progression Chaque phase doit produire un incrément utilisable et validé. Le gaz, le temps réel et la détection de fuite ne doivent pas retarder la livraison d’un moteur liquide et stockage robuste. |



# 16. Organisation de l’équipe et méthode de réalisation

L’équipe comprend deux développeurs et des assistants IA. Les assistants IA accélèrent la recherche, le prototypage, la documentation et les tests, mais ne remplacent ni la validation métier ni la revue de code.

| Rôle | Responsabilités recommandées |

| Développeur A - moteur scientifique | Équations, solveurs, modèles physiques, optimisation, tests numériques et validation. |

| Développeur B - plateforme | API, base de données, frontend, imports, rapports, sécurité et déploiement. |

| Responsabilité partagée | Architecture, modèle métier, revue croisée, CI/CD, performances et documentation. |

| Assistants IA | Recherche guidée, génération de tests, revue, documentation, prototypes et analyse de données. |

| Référent métier | Validation des hypothèses, cas d’usage, données, unités, résultats et critères d’acceptation. |



## 16.1 Méthode de travail

1. Spécifier un cas d’usage et ses critères d’acceptation.

2. Formaliser les données, équations, hypothèses et limites.

3. Écrire les tests de référence avant ou avec le code.

4. Implémenter le moteur et exposer une API stable.

5. Comparer à un calcul manuel ou un outil indépendant.

6. Faire une revue croisée entre les deux développeurs.

7. Documenter la version, les écarts et les décisions.

8. Livrer un incrément démontrable à fréquence régulière.

## 16.2 Règles d’usage de l’IA

- Aucun calcul critique généré par IA ne sera accepté sans test et revue humaine.

- Les sources, hypothèses et formules utilisées devront être identifiables.

- Le code généré devra respecter les conventions, types, tests et analyses statiques du projet.

- Les données industrielles confidentielles ne seront pas envoyées à un service non autorisé.

- Les décisions normatives et HSE resteront sous responsabilité humaine.

# 17. Exigences non fonctionnelles de haut niveau

| Qualité | Exigence |

| Fiabilité | Résultats déterministes, contrôles de convergence et absence de valeur silencieusement inventée. |

| Traçabilité | Historique des versions, données, paramètres, règles, calculs et validations. |

| Performance | Calcul stationnaire interactif et calculs longs exécutés en tâche de fond. |

| Sécurité | Authentification, rôles, audit, chiffrement et segmentation des connecteurs industriels. |

| Portabilité | Déploiement local, cloud ou hybride avec conteneurs. |

| Interopérabilité | CSV, Excel, API, SIG et protocoles industriels via passerelles. |

| Maintenabilité | Monolithe modulaire, typage, tests, documentation et interfaces internes stables. |

| Évolutivité | Possibilité de séparer les moteurs spécialisés et l’historian. |

| Utilisabilité | Interface compréhensible par un ingénieur, unités explicites et avertissements actionnables. |

| Auditabilité scientifique | Chaque résultat peut être relié à une méthode, une version et un jeu d’entrée. |



# 18. Risques majeurs et mesures de maîtrise

| ID | Risque | Niveau | Mesure de maîtrise |

| R1 | Périmètre trop large pour deux développeurs | Élevé | MVP strict, lots indépendants et gel des fonctionnalités. |

| R2 | Résultats scientifiques non validés | Critique | Cas de référence, tests automatisés et revue métier. |

| R3 | Dépendance à une bibliothèque externe | Moyen | Interfaces d’abstraction, audit licence et tests indépendants. |

| R4 | Absence de données industrielles | Élevé | Cas synthétiques, données publiques et recherche d’un site pilote. |

| R5 | Confusion entre conseil et commande | Critique | Lecture seule, avertissements et séparation des systèmes de sécurité. |

| R6 | Dérive normative | Moyen | Référentiels versionnés et mise à jour contrôlée. |

| R7 | Complexité du gaz et des transitoires | Élevé | Report après validation du cœur liquide et services spécialisés. |

| R8 | Utilisation non maîtrisée de l’IA | Élevé | Revue humaine, tests, confidentialité et journal des décisions. |

| R9 | Cybersécurité des connexions SCADA | Critique | Passerelle en DMZ, lecture seule et conformité IEC 62443. |



# 19. Critères de succès

- Le moteur liquide reproduit les cas de référence dans les tolérances approuvées.

- La plateforme accepte des topologies et équipements variables sans modification du code métier.

- Les ingénieurs peuvent comparer rapidement plusieurs modes d’exploitation.

- Les résultats sont accompagnés d’explications, de contrôles et de graphiques lisibles.

- Les données et décisions sont versionnées et auditables.

- Le déploiement local fonctionne sans dépendance obligatoire à Internet.

- L’architecture permet d’ajouter le gaz, les transitoires et le SCADA sans réécriture totale.

- Un site pilote ou un partenaire métier valide l’utilité opérationnelle du MVP.

# 20. Plan documentaire complet

| Réf. | Document | État |

| D01 | Cadrage officiel et plan directeur | Livré - présent document |

| D02 | Vision produit et proposition de valeur | Livré - version 1.0 |

| D03 | Cartographie des acteurs et processus métier | Livré - version 1.0 |

| D04 | Cahier des charges fonctionnel complet | Livré - version 1.0 |

| D05 | Exigences non fonctionnelles | Livré - version 1.0 |

| D06 | Catalogue des cas d’usage et scénarios | Livré - version 1.0 |

| D07 | Référentiel scientifique et mathématique | Livré - version 1.0 |

| D08 | Référentiel normatif international | Livré - version 1.0 |

| D09 | Dictionnaire des données | Livré - version 1.0 |

| D10 | Plan de validation scientifique | Livré - version 1.0 |

| D11 | Architecture logicielle détaillée | Livré - version 1.0 |

| D12 | Modèle de données conceptuel et logique | Livré - version 1.0 |

| D13 | Spécification des API et intégrations | Livré - version 1.0 |

| D14 | Stratégie open source et licences | Livré - version 1.0 |

| D15 | Sécurité, SCADA et historisation | Livré - version 1.0 |

| D16 | Plan de développement du MVP | Livré - version 1.0 |

| D17 | Roadmap complète jusqu’au produit final | Livré - version 1.0 |

| D18 | Plan de tests, qualité et CI/CD | Livré - version 1.0 |

| D19 | Modèles de rapports et interfaces | Livré - version 1.0 |

| D20 | Dossier pilote et protocole de validation industrielle | Trame complète livrée - à compléter avec le site pilote |



# 21. Décisions actées et points à confirmer

## 21.1 Décisions actées

- Le produit sera paramétrable, modulaire et multinorme.

- Les normes internationales seront prioritaires ; les sources russes seront comparatives.

- Python sera le langage principal et PostgreSQL/PostGIS la base centrale.

- Le MVP ciblera les liquides, pompes, réservoirs, transferts et scénarios.

- Le projet sera réalisable par incréments avec deux développeurs et des assistants IA.

- Les premières connexions industrielles resteront en lecture seule.

- Les moteurs déterministes seront séparés de l’IA conversationnelle.

## 21.2 Points à confirmer pendant les documents suivants

| Point | Traitement prévu |

| Nom commercial de la plateforme | À décider lors du document vision produit. |

| Client prioritaire du MVP | Hypothèse : pipelines liquides, dépôts et bureaux d’études. |

| Capacités maximales initiales | À définir dans les exigences non fonctionnelles. |

| Calendrier précis | À établir dans le plan de développement selon la disponibilité réelle. |

| Budget | À chiffrer après choix des tarifs, hébergement et outils. |

| Site pilote | À rechercher parallèlement au développement du MVP. |

| Données réelles de pompes et réservoirs | À obtenir auprès de fabricants ou partenaires. |

| Éditions normatives exactes | À vérifier et versionner au début de chaque projet. |



# Annexe A - Glossaire initial

| Terme | Définition |

| HGL / ligne hydraulique | Représentation de la charge hydraulique le long de la conduite. |

| NPSH | Marge de pression liée au risque de cavitation d’une pompe. |

| RTTM | Modèle transitoire en temps réel recalé sur les données industrielles. |

| Line-pack | Quantité de gaz stockée dans un gazoduc sous pression. |

| SCADA | Système de supervision, contrôle et acquisition de données. |

| Historian | Base spécialisée dans la conservation des données temporelles industrielles. |

| OPC UA | Standard d’interopérabilité et de sécurité pour les données industrielles. |

| MVP | Première version utilisable permettant de valider la valeur et le cœur technique. |

| Cas de validation | Jeu d’entrée et résultat attendu servant à vérifier le moteur. |

| Mode dégradé | Fonctionnement avec un équipement indisponible ou une contrainte inhabituelle. |



# Annexe B - Références documentaires de la phase de recherche

| Réf. | Source et contribution |

| R1 | Matériaux de modélisation informatique des procédés de transport par pipeline des hydrocarbures - calcul des régimes stationnaires, profil hydraulique et zones gravitaires. |

| R2 | Programme Python transmis - calcul d’un oléoduc comportant une station de tête et deux stations intermédiaires. |

| R3 | Modélisation informatique des procédés de transport des hydrocarbures - méthodes numériques, pompes, réservoirs, gaz et transitoires. |

| R4 | Neftébases et stations-service - équipements, opérations, comptage, pertes, corrosion et sécurité. |

| R5 | Ouvrages et équipements pour le stockage, le transport et la livraison des produits pétroliers. |

| R6 | Objets de stockage et de réception-expédition des carburants et lubrifiants - calculs technologiques, réservoirs et pompes. |

| R7 | Calcul des systèmes de transport pétrolier - propriétés, multiproduits, résistance et coup de bélier. |

| R8 | Systèmes de transport et de distribution du gaz naturel - gazoducs, stations de compression, diagnostic et stockage. |

| R9 | Formules de calcul hydraulique et sélection de pompe pour une tuyauterie technologique de dépôt. |



Ces références sont utilisées comme base de compréhension et de validation comparative. Les règles réglementaires et normatives du produit seront établies dans le Référentiel normatif international D08.

# Annexe C - Synthèse de l’enchaînement documentaire

| Étape | Documents | Décision obtenue |

| Cadrage | D01 à D03 | Pourquoi, pour qui et avec quel périmètre. |

| Spécification | D04 à D10 | Ce que le produit doit faire et comment valider les calculs. |

| Conception | D11 à D15 | Comment l’architecture, les données et les intégrations seront réalisées. |

| Exécution | D16 à D19 | Backlog, calendrier, qualité, interfaces et livraisons. |

| Industrialisation | D20 | Validation sur installation pilote et préparation du déploiement réel. |



FIN DU DOCUMENT HTP-CAD-001