| DOCUMENTATION COMPLÈTE DU MVP Plateforme de transport et de stockage des hydrocarbures Pipelines liquides • Stations de pompage • Réservoirs • Transferts • Scénarios • Optimisation   Version 2.0 — 2 août 2026 Statut : BASE APPROUVÉE POUR LE DÉMARRAGE DU DÉVELOPPEMENT |



|  | Décision structurante Le backend permanent sera Python/FastAPI. Le cœur du MVP sera HydroLiquid Core, un moteur liquide hybride construit avec NumPy, SciPy, fluids, CoolProp, Pint, une base produits interne et un adaptateur pandapipes. Le frontend partira de Shadcn Admin et sera spécialisé avec React Flow et des graphiques scientifiques. |



Équipe de réalisation : 2 développeurs, avec validation métier et scientifique

Déploiement cible : local, serveur privé et cloud

# 0. Contrôle du document

| Champ | Valeur |

| Titre | Documentation complète du MVP — Plateforme de transport et stockage des hydrocarbures |

| Version | 2.0 |

| Date | 2 août 2026 |

| Statut | Base fonctionnelle, scientifique et technique pour démarrer le développement |

| Périmètre | MVP liquide en régime permanent : pipelines, pompes, stations, réservoirs, transferts, scénarios et optimisation initiale |

| Équipe | 2 développeurs + experts ponctuels + validation métier/scientifique |

| Backend final | Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL et PostGIS |

| Frontend retenu | Shadcn Admin, React, TypeScript, Vite, React Flow, ECharts/Plotly et MapLibre |

| Moteur principal | HydroLiquid Core |

| Références normatives | Normes internationales et exigences locales applicables; les documents russes sont techniques et comparatifs, non normatifs |



## 0.1 Historique des décisions

| ID | Décision | Application |

| DEC-ARCH-001 | Backend central Python/FastAPI conservé du MVP au produit final | Monolithe modulaire au MVP, services spécialisés ensuite |

| DEC-ENGINE-001 | HydroLiquid Core est le moteur liquide principal | Il assemble des briques existantes et nos extensions métiers |

| DEC-ENGINE-002 | pandapipes est intégré par adaptateur après preuve de concept | Il ne devient pas une dépendance unique ni irréversible |

| DEC-ENGINE-003 | Pyomo est le moteur d’optimisation | Énumération intelligente possible pour les petits cas |

| DEC-UI-001 | Shadcn Admin sert de base visuelle | Les pages de démonstration et l’authentification partielle sont remplacées |

| DEC-SRC-001 | Les documents fournis alimentent équations, hypothèses et cas de validation | Ils ne remplacent pas les normes internationales |

| DEC-SAFETY-001 | Le MVP est un outil d’analyse et d’aide à la décision | Aucune commande directe des automates, PLC ou SIS |



## 0.2 Sommaire

- 1. Résumé exécutif

- 2. Vision, objectifs et périmètre

- 3. Utilisateurs, rôles et parcours

- 4. Spécifications fonctionnelles détaillées

- 5. Référentiel scientifique du MVP

- 6. Sources documentaires et référentiel normatif

- 7. Cœurs logiciels et composants open source

- 8. Architecture technique du MVP

- 9. Modèle de données et traçabilité

- 10. API et contrats d’intégration

- 11. Spécification du frontend Shadcn Admin

- 12. Exigences non fonctionnelles et sécurité

- 13. Validation scientifique et stratégie de tests

- 14. Plan de développement pour deux développeurs

- 15. Critères de réception et définition de fin du MVP

- 16. Risques, limites et mesures de maîtrise

- 17. Évolution vers le produit final

- Annexes : backlog, formats d’import, statuts, erreurs, glossaire et sources

# 1. Résumé exécutif

Le MVP est une application web d’ingénierie destinée à modéliser et simuler le transport stationnaire de produits pétroliers liquides dans des pipelines comprenant plusieurs tronçons, plusieurs stations de pompage et plusieurs réservoirs. Elle doit également permettre de simuler des transferts, d’étudier des modes dégradés et de proposer une configuration d’exploitation techniquement réalisable et énergétiquement intéressante.

|  | Positionnement du MVP Le MVP n’est ni un simple prototype graphique, ni un SCADA, ni un logiciel de commande. Il s’agit d’un premier produit utilisable de bout en bout, avec moteur scientifique validé, traçabilité, interface métier et rapports. |



## 1.1 Résultat attendu

1. Créer une organisation, des utilisateurs, un projet et une installation.

2. Définir ou importer les propriétés d’un produit liquide.

3. Construire un pipeline par tronçons, importer son profil altimétrique et ajouter ses accessoires.

4. Configurer plusieurs stations et plusieurs pompes en série, en parallèle, principales ou de secours.

5. Ajouter des réservoirs avec table de barémage et niveaux d’exploitation.

6. Créer un scénario normal ou dégradé et lancer une simulation stationnaire.

7. Obtenir les débits, pressions, vitesses, pertes, consommations, contraintes et avertissements.

8. Simuler un transfert bac-à-bac et suivre les niveaux dans le temps.

9. Comparer plusieurs scénarios et classer les configurations.

10. Exporter une note de calcul et des résultats en PDF, Excel, CSV et JSON.

## 1.2 Limites fondamentales du MVP

- Écoulement monophasique liquide, conduite pleine et régime principalement permanent.

- Pas de gazoduc complet, pas de line-pack, pas de compresseurs avancés.

- Pas de coup de bélier industriel ni de simulation transitoire détaillée.

- Pas de connexion temps réel au SCADA et aucune commande directe d’équipement.

- Pas de détection de fuite certifiée ni de conformité réglementaire automatique complète.

- Pas de calcul structurel complet des conduites ou des réservoirs dans le moteur MVP.

# 2. Vision, objectifs et périmètre

## 2.1 Vision produit

La plateforme doit devenir un environnement unifié pour l’étude, l’exploitation assistée, la comparaison de scénarios et, à terme, le jumeau numérique des installations de transport et de stockage des hydrocarbures. Le MVP constitue le premier noyau industriel : le liquide stationnaire.

## 2.2 Objectifs mesurables du MVP

| Objectif | Indicateur de réussite |

| Exactitude scientifique | Cas de référence validés dans les tolérances documentées; conservation de masse et cohérence énergétique contrôlées. |

| Utilisabilité | Un ingénieur peut réaliser le parcours complet sans manipuler du code. |

| Traçabilité | Chaque résultat conserve entrées, versions, méthodes, tolérances, avertissements et utilisateur. |

| Déploiement | Installation reproductible par Docker sur poste, serveur privé ou cloud. |

| Extensibilité | Les moteurs sont appelés derrière des interfaces communes; le backend ne doit pas être réécrit après le MVP. |

| Performance | Une simulation stationnaire standard doit viser moins de 10 s; une comparaison simple moins de 60 s. |

| Sécurité | Isolation des organisations, rôles, audit, TLS et validation stricte des imports. |



## 2.3 Périmètre inclus

| Domaine | Fonctions incluses |

| Gestion | Organisations, utilisateurs, projets, versions, pièces jointes, audit. |

| Produits | Bibliothèque, densité, viscosité, température, pression de vapeur, tables de propriétés. |

| Pipeline | Tronçons, diamètres, rugosité, matériaux, accessoires, profil altimétrique, pressions limites. |

| Stations | Pompes multiples, série, parallèle, secours, vitesse variable simple, bypass et indisponibilité. |

| Hydraulique | Débit direct/inverse, pression le long du tracé, pertes, courbe réseau, point de fonctionnement. |

| Réservoirs | Types simples, table de barémage, niveaux, capacité disponible, transferts et bilan matière. |

| Scénarios | Normal, panne de pompe, secours, station indisponible, bypass, vanne partielle, filtre colmaté simplifié. |

| Optimisation | Classement de configurations, énergie, nombre de pompes, contraintes de débit et de pression. |

| Résultats | Graphiques, tableaux, contraintes, explication, PDF, Excel, CSV et JSON. |



## 2.4 Périmètre explicitement exclu

| Exclusion | Motif / phase prévue |

| Gazoducs et stations de compression | Gas Network Core après le MVP; GasModels.jl pour l’optimisation gaz. |

| Transitoires et coups de bélier | Transient Core après le MVP; OpenModelica/Modelica.Fluid et éventuellement un solveur MOC. |

| SCADA temps réel et automates | Passerelle OPC UA/PLC4X dans une phase industrielle ultérieure. |

| Détection de fuite certifiée | Nécessite données opérationnelles, validation terrain et processus de certification. |

| Optimisation multi-périodes avancée | Après stabilisation du moteur et acquisition de données réelles. |

| Calcul mécanique complet | À traiter par modules spécialisés et vérifications normatives futures. |

| Commande automatique | Le produit reste d’abord en lecture seule et recommandation. |



# 3. Utilisateurs, rôles et parcours

## 3.1 Rôles applicatifs

| Rôle | Droits principaux | Restrictions |

| Administrateur organisation | Utilisateurs, rôles, bibliothèques partagées, paramètres et audit. | Ne valide pas automatiquement les calculs. |

| Ingénieur | Créer, modifier, importer, simuler, optimiser et exporter. | Ne modifie pas une simulation validée; crée une nouvelle version. |

| Validateur | Consulter, commenter, approuver ou rejeter une simulation. | Pas de modification silencieuse des entrées. |

| Lecteur | Consulter les projets, résultats et rapports. | Aucune modification ni lancement de calcul selon la politique. |

| Administrateur plateforme | Maintenance technique, supervision et support. | Accès aux données encadré et audité. |



## 3.2 Parcours principal de bout en bout

| Organisation → Projet → Produit → Pipeline → Stations/Pompes → Réservoirs       ↓ Scénario → Validation des données → Simulation → Contrôles physiques       ↓ Résultats/Graphiques → Comparaison/Optimisation → Validation → Rapport |



## 3.3 Principaux cas d’usage

| ID | Cas d’usage | Acteur principal |

| UC-01 | Créer un projet et une installation versionnée | Ingénieur |

| UC-02 | Importer un profil altimétrique CSV/XLSX | Ingénieur |

| UC-03 | Importer une courbe de pompe | Ingénieur |

| UC-04 | Configurer plusieurs stations et pompes | Ingénieur |

| UC-05 | Lancer un calcul à débit imposé | Ingénieur |

| UC-06 | Calculer le débit compatible avec les limites | Ingénieur |

| UC-07 | Vérifier NPSH, cavitation et pression maximale | Ingénieur |

| UC-08 | Simuler la panne d’une pompe et l’activation du secours | Ingénieur |

| UC-09 | Simuler un transfert entre deux réservoirs | Ingénieur |

| UC-10 | Comparer des scénarios | Ingénieur/Validateur |

| UC-11 | Optimiser une configuration de pompage | Ingénieur |

| UC-12 | Approuver une simulation et figer sa version | Validateur |

| UC-13 | Générer un rapport technique | Ingénieur/Validateur |

| UC-14 | Consulter l’historique et l’audit | Administrateur/Validateur |



# 4. Spécifications fonctionnelles détaillées

## 4.1 Comptes, organisations et sécurité fonctionnelle

- Création d’une organisation et d’utilisateurs avec rôles configurables.

- Connexion, déconnexion, expiration de session et réinitialisation de mot de passe.

- Isolation stricte des données par organisation.

- Activation/désactivation de comptes et journal d’audit des actions sensibles.

- Gestion des préférences d’unités, langue, fuseau horaire et formats de nombres.

|  | Critère d’acceptation Un utilisateur d’une organisation ne doit jamais voir ni modifier les objets d’une autre organisation, y compris par manipulation directe des identifiants API. |



## 4.2 Projets, installations et versions

- Créer, dupliquer, archiver et restaurer un projet.

- Créer plusieurs installations dans un même projet.

- Gérer les états Brouillon, Prêt pour calcul, Calculé, À valider, Validé et Archivé.

- Associer des fichiers : courbes constructeur, profils, fiches produit et notes techniques.

- Créer une nouvelle version lorsqu’un objet validé est modifié.

- Associer les références normatives et leur édition au niveau du projet.

## 4.3 Bibliothèque de produits

| Catégorie de donnée | Champs minimaux |

| Identification | Nom, code, catégorie, description, source des données. |

| État de calcul | Température, pression de référence, phase liquide, plage de validité. |

| Propriétés | Densité, viscosité cinématique/dynamique, pression de vapeur, compressibilité. |

| Tables | Température–densité, température–viscosité, pression–densité si disponible. |

| Traçabilité | Origine laboratoire, fournisseur, document, date, version et incertitude. |

| Fournisseur de propriétés | Valeur saisie, table interne, CoolProp ou corrélation validée. |



Produits génériques initiaux : pétrole brut, essence, gasoil, kérosène, fuel léger, fuel lourd, condensat, eau et produit personnalisé.

## 4.4 Pipeline, tronçons et profil altimétrique

| Objet | Fonctions et champs |

| Pipeline | Nom, origine, destination, produit, condition de départ, condition d’arrivée, débit imposé ou à calculer. |

| Tronçon | Longueur, diamètre intérieur/extérieur, épaisseur, matériau, rugosité, pression maximale admissible, état. |

| Profil | Points distance–altitude, interpolation, correction, visualisation, positionnement des équipements. |

| Accessoire | Type, position, quantité, coefficient K, diamètre, état ouvert/fermé/partiel. |

| Points spéciaux | Injection, soutirage, station, vanne de sectionnement, réservoir, instrumentation déclarative. |

| Contrôles | Distances croissantes, diamètres positifs, cohérence de longueur, absence de doublons, unités connues. |



## 4.5 Stations de pompage et pompes

- Nombre configurable de stations et de pompes par station.

- Pompes identiques ou différentes; fonctionnement en série, parallèle ou groupe simple série-parallèle.

- Statut principal, secours, maintenance ou indisponible.

- Vitesse fixe ou variable avec limites de vitesse.

- Courbes H(Q), η(Q), P(Q) et NPSHr(Q) saisies, importées ou interpolées.

- Pressions minimale d’aspiration et maximale de refoulement; bypass de station.

- Calcul du débit par pompe, hauteur fournie, rendement, puissance et marge NPSH.

| Contrôle | Résultat attendu |

| Pompe hors domaine de courbe | Avertissement ou invalidation selon la sévérité. |

| Débit inférieur au minimum | Avertissement de fonctionnement non recommandé. |

| Débit supérieur au maximum | Scénario non conforme. |

| Puissance absorbée supérieure au moteur | Violation critique. |

| NPSHa < NPSHr + marge | Risque de cavitation, scénario non conforme. |

| Pression de refoulement > limite | Violation critique et localisation du point. |



## 4.6 Réservoirs et tables de barémage

| Fonction | Spécification MVP |

| Types | Vertical cylindrique, horizontal cylindrique, générique par table de barémage. |

| Niveaux | Minimum, bas, normal, haut, haut-haut et niveau actuel. |

| Volumes | Nominal, utile, mort, actuel et disponible. |

| Barémage | Import niveau–volume, interpolation monotone, conversion dans les deux sens. |

| État | Disponible, maintenance, indisponible. |

| Contrôles | Table croissante, niveau ≤ hauteur, volume ≤ capacité, produit compatible. |



## 4.7 Transferts bac-à-bac

- Sélection du bac source, du bac destination, du chemin hydraulique et du groupe de pompage.

- Objectif exprimé par volume cible, niveau cible, durée cible ou débit souhaité.

- Calcul du débit réel, des pressions, des pertes, de l’énergie et de l’heure estimée de fin.

- Évolution discrétisée des niveaux et volumes pendant le transfert.

- Arrêt théorique sur niveau bas source, niveau haut destination, volume atteint ou contrainte hydraulique.

- Bilan matière avec volume initial, final, transféré, mesuré et écart.

## 4.8 Scénarios d’exploitation

| Scénario obligatoire | Description |

| Normal | Tous les équipements prévus sont disponibles. |

| Pompe indisponible | Une pompe principale est retirée du service. |

| Secours | La pompe de secours remplace une pompe indisponible. |

| Station indisponible | Toutes les pompes d’une station sont arrêtées. |

| Bypass | Le fluide contourne la station avec les pertes du chemin de bypass. |

| Débit réduit | Le débit cible est abaissé. |

| Réservoir alternatif | La destination ou la source change. |

| Température différente | Les propriétés sont recalculées ou lues dans les tables. |

| Filtre colmaté simplifié | Le coefficient de perte augmente. |

| Vanne partiellement fermée | Le coefficient K ou la perte équivalente augmente. |



## 4.9 Simulation, résultats et explication

| Groupe de résultats | Contenu minimal |

| Statut | Convergé, convergé avec avertissements, non convergé, invalide, annulé. |

| Hydraulique | Débit, vitesse, Reynolds, facteur de frottement, pertes, pression et charge. |

| Stations | Pressions d’aspiration/refoulement, débit par pompe, rendement, puissance, NPSH. |

| Réservoirs | Niveaux, volumes, temps de transfert et capacité restante. |

| Contraintes | Type, sévérité, position, valeur, limite, écart et recommandation. |

| Numérique | Solveur, tolérance, résidu, itérations, durée et version du moteur. |

| Traçabilité | Entrées figées, modèle, corrélations, références, utilisateur et date. |



## 4.10 Comparaison et optimisation

- Comparer jusqu’à plusieurs scénarios sur débit, énergie, pressions, nombre de pompes, temps de transfert et violations.

- Générer les configurations combinatoires admissibles pour les petits réseaux.

- Utiliser Pyomo pour les problèmes continus/discrets lorsque le modèle est stable et résoluble.

- Classer les alternatives selon un objectif choisi : énergie, coût, disponibilité ou nombre de démarrages.

- Conserver les configurations rejetées et leur motif de rejet.

## 4.11 Import, export et rapports

| Flux | Formats | Contrôles |

| Import | CSV, XLSX, JSON | Colonnes, unités, types, monotonicité, doublons, plages. |

| Export données | CSV, XLSX, JSON | Version, unités et métadonnées incluses. |

| Rapports | PDF et XLSX | Projet, hypothèses, méthodes, résultats, graphiques, limites et avertissements. |

| Pièces jointes | PDF, images, feuilles constructeur | Taille, type MIME, antivirus selon environnement. |



# 5. Référentiel scientifique du MVP

|  | Règle scientifique Les équations physiques, les corrélations, les règles normatives et les données constructeur sont séparées. Un calcul ne doit jamais masquer son domaine de validité, sa source ou une non-convergence. |



## 5.1 Domaine physique

- Liquide newtonien ou traité par une corrélation explicitement sélectionnée.

- Écoulement monophasique, conduite pleine, stationnaire.

- Régimes laminaire, transition et turbulent.

- Variation de propriétés selon la température par table ou corrélation.

- Réseau linéaire longue distance et réseaux internes simples nœuds–branches.

- Zones gravitaires détectées selon les hypothèses du moteur; aucune affirmation de conduite partiellement remplie sans modèle dédié.

## 5.2 Équations minimales

| Calcul | Relation de référence |

| Section | A = πD² / 4 |

| Vitesse | v = Q / A |

| Reynolds | Re = ρvD / μ = vD / ν |

| Perte linéaire | h_f = λ(L/D)(v²/2g) |

| Perte singulière | h_m = ΣK(v²/2g) |

| Bernoulli étendu | p₁/(ρg)+z₁+v₁²/(2g)+H_p = p₂/(ρg)+z₂+v₂²/(2g)+h_L |

| Puissance hydraulique | P_h = ρgQH |

| Puissance absorbée | P_abs = P_h / η |

| NPSH disponible | NPSHa = p_abs/(ρg) + z - p_v/(ρg) - pertes aspiration, selon convention du modèle |

| Bilan matière | dV/dt = Q_entrant - Q_sortant |



Les expressions exactes, les conventions de signe et les conditions aux limites seront documentées dans le code et dans la fiche de chaque modèle. Les équations ci-dessus servent de socle fonctionnel, pas de spécification numérique exhaustive.

## 5.3 Facteur de frottement

| Régime / option | Méthode |

| Laminaire | λ = 64/Re. |

| Turbulent implicite | Colebrook–White. |

| Turbulent explicite | Haaland ou Swamee–Jain. |

| Transition | Stratégie documentée, continue et testée; avertissement possible. |

| Comparaison | Le moteur peut comparer plusieurs corrélations pour l’analyse de sensibilité. |



## 5.4 Courbes de pompe

Les courbes constructeur restent prioritaires. Le MVP accepte des points expérimentaux et peut ajuster une courbe de forme H = a − bQ² lorsque cette approximation est pertinente. Les documents fournis présentent cette méthode d’approximation par moindres carrés; elle sera utilisée comme option, non comme modèle universel.

- Interpolation monotone ou spline contrôlée pour H(Q), η(Q), P(Q) et NPSHr(Q).

- Pompes en série : addition des hauteurs pour un débit commun.

- Pompes en parallèle : addition des débits pour une hauteur commune, avec résolution du partage.

- Lois d’affinité pour vitesse variable, uniquement dans le domaine validé par le fabricant.

- Détection des extrapolations et affichage d’un avertissement explicite.

## 5.5 Propriétés des produits

| Fournisseur | Usage | Limite |

| Valeur utilisateur / laboratoire | Produit réel et conditions connues. | Nécessite source, date, température et incertitude. |

| Table interne | Densité et viscosité selon la température. | Interpolation limitée au domaine de la table. |

| CoolProp | Fluides, mélanges et incompressibles couverts. | Ne représente pas automatiquement tous les bruts et produits commerciaux. |

| Corrélation interne | Produit spécifique validé. | Version, domaine et erreur doivent être tracés. |



## 5.6 Méthodes numériques

- Recherche de racine par Brent ou dichotomie pour les équations à une inconnue.

- Newton sécurisé avec repli lorsque les dérivées et l’initialisation sont fiables.

- Solveurs non linéaires SciPy pour les réseaux plus complexes.

- Interpolation des profils, courbes de pompe et tables de barémage.

- Critères de convergence basés sur résidus de pression, débit et conservation de masse.

- Arrêt contrôlé et message explicite en cas d’absence de solution physique.

## 5.7 Interface de moteur

| class HydraulicEngine:     def validate(network, scenario) -> ValidationReport: ...     def simulate(network, scenario) -> SimulationResult: ...     def explain(result) -> Explanation: ...  Implémentations MVP : - LongDistanceLiquidEngine  # moteur principal oléoduc - PandapipesEngine          # adaptateur pour cas compatibles et comparaison |



## 5.8 Contrôles physiques et numériques obligatoires

| ID | Contrôle | Sévérité |

| C-001 | Conservation de masse | Critique |

| C-002 | Pression inférieure à la pression de vapeur | Critique |

| C-003 | NPSH insuffisant | Critique |

| C-004 | Pression supérieure à la limite admissible | Critique |

| C-005 | Vitesse hors plage configurée | Avertissement ou critique |

| C-006 | Pompe hors courbe | Avertissement ou critique |

| C-007 | Puissance moteur dépassée | Critique |

| C-008 | Réservoir sous niveau minimal | Critique |

| C-009 | Réservoir au-dessus du niveau haut-haut | Critique |

| C-010 | Non-convergence | Erreur explicite |

| C-011 | Extrapolation de propriété | Avertissement |

| C-012 | Résidu supérieur à la tolérance | Erreur ou avertissement selon règle |



# 6. Sources documentaires et référentiel normatif

## 6.1 Utilisation des documents fournis

Les documents fournis sont une base technique, académique et comparative. Ils sont utilisés pour identifier les équations, les méthodes d’approximation, les cas d’exercice, les équipements, les transferts et les méthodes de barémage. Ils ne deviennent pas automatiquement des exigences réglementaires du produit.

| Source | Apport | Statut dans le produit |

| « Компьютерное моделирование… » | Moindres carrés, courbes de pompe, résolution non linéaire et exercices de programmation. | Extraction de modèles et cas de test. |

| Programme Python fourni | Pipeline de 460 km, stations multiples, pompes, profil et contrôles. | Base de comparaison à corriger et tester; règles russes isolées. |

| « Нефтебазы и АЗС » | Dépôts, équipements, pertes de charge, réservoirs, exploitation et mesure. | Référence technique et métier. |

| « Хранение 2020 » | Stockage, réception/expédition, calibration des réservoirs et pertes. | Barémage, opérations et contrôles. |

| « Пособие Хранение_КНИТУ » | Propriétés des produits, influence de la pression et de la température, stockage. | Modèles de propriétés et cas de validation. |

| « ГТС 2020 » | Transport gazier, propriétés du gaz, équipements et traitement. | Réservé à la préparation du futur module gaz. |



## 6.2 Hiérarchie de référence

1. Lois physiques et méthodes reconnues.

2. Normes internationales applicables : ASME, API, ISO, IEC, ISA, etc.

3. Réglementation locale et exigences de l’opérateur.

4. Données des fabricants et données de laboratoire.

5. Documents techniques fournis et littérature académique.

6. Bibliothèques open source et logiciels de comparaison, après validation.

## 6.3 Référentiels à enregistrer dans le MVP

| Domaine | Références principales — édition applicable à confirmer |

| Pipelines liquides | ASME B31.4, ISO 13623, API RP 1160. |

| Pompes | API 610, ISO 9906, API 682 selon le besoin. |

| Réservoirs et dépôts | API 650, API 653, API 2000, API 2350, API 2610, API MPMS. |

| Fuite future | API RP 1130, API RP 1175, API TR 1149. |

| Sécurité fonctionnelle future | IEC 61511. |

| Cybersécurité industrielle future | IEC 62443. |

| Alarmes futures | ISA-18.2. |

| Interopérabilité future | IEC 62541 / OPC UA. |



|  | Important Le MVP conserve les références et implémente uniquement les contrôles effectivement codés et validés. Il ne doit jamais afficher une « conformité complète » lorsqu’il n’a vérifié qu’un sous-ensemble. |



# 7. Cœurs logiciels et composants open source

## 7.1 Cœurs retenus

| Cœur | Technologies | Rôle |

| Cœur applicatif | Python, FastAPI, Pydantic, SQLAlchemy, Alembic | Projets, équipements, scénarios, orchestration, droits, traçabilité et rapports. |

| HydroLiquid Core | NumPy, SciPy, fluids, CoolProp, Pint, adaptateur pandapipes | Calcul stationnaire des pipelines liquides et stations. |

| Tank & Transfer Core | HydroLiquid Core + modèles de réservoirs | Niveau-volume, transfert, évolution temporelle et bilan matière. |

| Operations Optimizer | Pyomo + solveurs + énumération | Sélection de pompes, vitesses, secours, stations et objectifs énergétiques. |

| Frontend métier | Shadcn Admin, React Flow, ECharts/Plotly, MapLibre | Navigation, édition du réseau, graphiques et cartes. |



## 7.2 Matrice de composants

| Projet | MVP | Statut | Rôle / condition |

| FastAPI | Oui | Backend final | API typées et OpenAPI; cœur central. |

| PostgreSQL/PostGIS | Oui | Données finales | Source de vérité et géospatial. |

| Shadcn Admin | Oui | Base frontend | UI à adapter; ce n’est pas une application métier prête. |

| React Flow | Oui | Éditeur réseau | Nœuds et connexions personnalisés. |

| NumPy/SciPy | Oui | Calcul | Solveurs, interpolation et algèbre. |

| fluids | Oui | Calcul | Corrélations et fonctions de mécanique des fluides. |

| CoolProp | Oui | Propriétés | Fournisseur parmi plusieurs. |

| Pint | Oui | Unités | Conversions et cohérence dimensionnelle. |

| Pyomo | Oui | Optimisation | Formulation; solveur séparé requis. |

| pandapipes | POC puis adaptateur | Moteur secondaire | Validation obligatoire sur nos cas. |

| DWSIM | Externe | Validation | Comparaison; pas de cœur intégré au MVP. |

| IDAES | Non requis | Après MVP | Procédés, réconciliation et optimisation avancée. |

| OpenModelica | Non | Après MVP | Transitoires via Modelica/FMU. |

| GasModels.jl | Non | Après MVP | Optimisation des réseaux gaziers. |

| open62541/PLC4X | Non | Après MVP | Connectivité industrielle. |

| TimescaleDB | Optionnel | Après volume réel | Séries temporelles SCADA. |



## 7.3 Preuve de concept pandapipes

pandapipes ne sera figé comme moteur par défaut qu’après une preuve de concept comparative. La plateforme conservera une abstraction de moteur pour éviter une dépendance irréversible.

| Cas de POC | Comparaisons obligatoires |

| Conduite simple | Calcul manuel, fluids/SciPy, pandapipes. |

| Profil avec dénivelé | Moteur longue distance, programme corrigé, pandapipes. |

| Pompe unique | Courbe constructeur et intersection réseau. |

| Série et parallèle | Calcul analytique/numérique indépendant. |

| Plusieurs stations | Programme fourni corrigé et moteur propre. |

| Cavitation / NPSH | Calcul manuel et données constructeur. |

| Bypass et panne | Vérification des états et contraintes. |

| Transfert bac-à-bac | Bilan matière et évolution temporelle. |

| Cas sans solution | Messages et résidus explicites. |

| Performance | Temps de calcul et stabilité jusqu’aux tailles cibles. |



# 8. Architecture technique du MVP

## 8.1 Architecture d’exécution

Le MVP adopte un monolithe modulaire. Les modules partagent un déploiement et une base, tout en respectant des frontières internes strictes. Les calculs lourds sont exécutés par des workers séparés afin de ne pas bloquer l’API.

| hydro-platform/ ├── apps/ │   ├── api/                 # FastAPI │   └── web/                 # Shadcn Admin / React ├── packages/ │   ├── domain/              # modèle métier pur │   ├── hydroliquid/         # moteur liquide │   ├── tank_transfer/       # stockage et transferts │   ├── optimization/        # Pyomo et énumération │   ├── reporting/           # PDF / Excel │   └── shared/              # unités, erreurs, observabilité ├── database/migrations/ ├── datasets/reference_cases/ ├── deployment/ └── tests/ |



## 8.2 Modules backend

| Module | Responsabilité |

| identity | Organisations, utilisateurs, rôles, sessions. |

| projects | Projets, installations, versions, pièces jointes. |

| catalog | Produits, pompes, accessoires, référentiels. |

| network | Pipelines, tronçons, profil, stations, réservoirs et topologie. |

| scenarios | États d’équipement, conditions limites et duplication. |

| simulations | Validation, lancement, orchestration, statut et résultats. |

| optimization | Configurations, objectifs, contraintes et classement. |

| reporting | Notes de calcul, exports et modèles. |

| audit | Événements, modifications et accès. |

| standards | Références et règles effectivement implémentées. |



## 8.3 Déploiements supportés

| Mode | Topologie | Particularités |

| Développement | Docker Compose local | API, web, PostgreSQL/PostGIS, MinIO et worker. |

| Entreprise locale | Serveur privé sur LAN | Fonctionnement sans dépendance obligatoire à Internet. |

| Cloud privé/public | Conteneurs + reverse proxy | TLS, sauvegardes, supervision et stockage objet. |

| Futur haute disponibilité | Plusieurs instances API/workers | Réplication PostgreSQL et orchestrateur si nécessaire. |



# 9. Modèle de données et traçabilité

## 9.1 Entités principales

| Entité | Responsabilité |

| Organisation | Tenant, paramètres, unités par défaut. |

| Utilisateur / rôle | Identité, permissions et statut. |

| Projet / version | Contexte, pays, normes, état et historique. |

| Installation | Réseau physique versionné. |

| Produit | Propriétés et sources. |

| Pipeline / tronçon | Géométrie, matériau, rugosité et limites. |

| Point d’altitude | Distance, altitude, coordonnées optionnelles. |

| Station / pompe | Configuration, courbes et états. |

| Réservoir / barémage | Capacité, niveaux et table niveau-volume. |

| Scénario | Conditions, états d’équipement et objectif. |

| Simulation | Snapshot d’entrée, statut et moteur. |

| Résultat | Profils, stations, contraintes et métriques. |

| Optimisation | Objectif, candidats, classement et solution. |

| Rapport | Type, version, fichier et empreinte. |

| AuditLog | Acteur, action, objet, avant/après et date. |

| StandardReference | Référentiel, édition, règle, applicabilité et source. |



## 9.2 Principes de versionnement

- Une simulation conserve un snapshot immuable de toutes ses entrées.

- Une simulation validée ne peut pas être modifiée; une nouvelle version est créée.

- Les courbes et propriétés utilisées sont référencées par version.

- La version du moteur, le commit applicatif et les dépendances scientifiques sont enregistrés.

- Les rapports contiennent l’identifiant et l’empreinte de la simulation source.

## 9.3 Unités

Le stockage et le calcul utilisent un système SI cohérent. Les unités d’affichage sont configurables. Pint est utilisé aux frontières de l’application et dans les tests; les types métier internes doivent éviter le mélange de grandeurs.

| Grandeur | Unité interne | Exemples d’affichage |

| Pression | Pa | bar, MPa, psi |

| Débit volumique | m³/s | m³/h, bbl/h |

| Longueur | m | mm, km |

| Température | K | °C |

| Viscosité dynamique | Pa·s | mPa·s |

| Viscosité cinématique | m²/s | cSt |

| Puissance | W | kW, MW |

| Énergie | J | kWh, MWh |



# 10. API et contrats d’intégration

## 10.1 Principes

- API REST versionnée sous /api/v1 avec schéma OpenAPI généré par FastAPI.

- Entrées et sorties validées par Pydantic; champs inconnus refusés pour les objets critiques.

- Identifiants UUID et contrôle d’accès au niveau service et requête.

- Idempotence pour les imports et les commandes longues lorsque pertinent.

- Simulations longues asynchrones : création d’un job puis consultation du statut.

- Erreurs structurées avec code, message, champ, sévérité et contexte.

## 10.2 Endpoints minimaux

| Méthode | Route | Objet |

| POST | /organizations | Créer une organisation. |

| POST | /projects | Créer un projet. |

| POST | /projects/{id}/versions | Créer une version. |

| POST | /products | Créer un produit. |

| POST | /pipelines | Créer un pipeline. |

| POST | /pipelines/{id}/profile/import | Importer un profil. |

| POST | /stations/{id}/pumps | Ajouter une pompe. |

| POST | /pumps/{id}/curves/import | Importer des courbes. |

| POST | /tanks/{id}/calibration/import | Importer un barémage. |

| POST | /scenarios | Créer un scénario. |

| POST | /simulations | Lancer une simulation. |

| GET | /simulations/{id} | Lire statut et synthèse. |

| GET | /simulations/{id}/results | Lire les résultats complets. |

| POST | /optimizations | Lancer une optimisation. |

| POST | /reports | Générer un rapport. |



## 10.3 Exemple de demande de simulation

| POST /api/v1/simulations {   "project_version_id": "uuid",   "scenario_id": "uuid",   "engine": "long_distance_liquid",   "options": {     "friction_model": "colebrook_white",     "tolerance": 1e-6,     "max_iterations": 100   } } |



## 10.4 Exemple de réponse synthétique

| {   "status": "converged_with_warnings",   "flow_m3_s": 1.42,   "min_pressure_pa": 410000,   "max_pressure_pa": 7240000,   "total_power_w": 6140000,   "violations": [],   "warnings": ["PUMP_EXTRAPOLATION_NEAR_LIMIT"],   "engine_version": "hydroliquid-0.4.0",   "iterations": 18,   "residual": 2.1e-7 } |



# 11. Spécification du frontend Shadcn Admin

Shadcn Admin est retenu comme base visuelle et structurelle. Le dépôt officiel précise qu’il s’agit d’une collection d’interface d’administration construite avec Shadcn et Vite, avec navigation, mode clair/sombre, responsive, accessibilité, recherche et pages d’exemple. Il indique également que ce n’est pas une application métier prête à brancher; notre équipe doit donc remplacer les données de démonstration et l’authentification partielle.

## 11.1 Stack frontend

| Brique | Choix |

| Socle | React + TypeScript + Vite. |

| Composants | Shadcn Admin + shadcn/ui + Tailwind CSS + Radix UI. |

| Routage | TanStack Router. |

| Données serveur | TanStack Query. |

| Formulaires | React Hook Form + Zod. |

| État local | Zustand lorsque nécessaire. |

| Tables | TanStack Table. |

| Éditeur réseau | React Flow. |

| Graphiques | Apache ECharts ou Plotly. |

| Cartographie | MapLibre. |

| Tests | Vitest + Playwright. |



## 11.2 Navigation cible

| Menu | Pages |

| Tableau de bord | Projets récents, simulations, alertes et indicateurs. |

| Projets | Liste, création, versions, membres et documents. |

| Modélisation | Installation, pipeline, stations, pompes, réservoirs et accessoires. |

| Bibliothèques | Produits, pompes, équipements et références normatives. |

| Scénarios | Création, duplication, états et comparaison. |

| Simulations | Lancement, progression, historique et détails. |

| Optimisation | Objectifs, contraintes, candidats et classement. |

| Résultats | Synthèse, profil hydraulique, courbes et contraintes. |

| Rapports | Génération, historique et téléchargement. |

| Administration | Organisations, utilisateurs, rôles, unités et audit. |



## 11.3 Éditeur React Flow

- Nœuds personnalisés : réservoir, pompe, station, vanne, jonction, source, soutirage et terminal.

- Connexions typées empêchant les liaisons impossibles.

- Panneau de propriétés synchronisé avec le formulaire métier.

- Validation visuelle : erreurs rouges, avertissements orange, état calculé vert.

- Zoom, mini-carte, alignement, regroupement par station et raccourcis clavier.

- Le schéma technologique et la géométrie géographique sont séparés mais liés.

## 11.4 Graphiques obligatoires

| Graphique | Contenu |

| Profil hydraulique | Terrain, axe, ligne de charge, stations, réservoirs et points critiques. |

| Pression-distance | Pression calculée, limites min/max et événements. |

| Pompe-réseau | Courbe de pompe/groupe, courbe réseau et point de fonctionnement. |

| Rendement/puissance | Courbes et point d’exploitation. |

| Transfert | Niveaux et volumes en fonction du temps. |

| Comparaison | Débit, énergie, pressions, temps et violations par scénario. |

| Carte | Tracé, stations, réservoirs et informations géographiques. |



# 12. Exigences non fonctionnelles et sécurité

## 12.1 Performance cible

| Exigence | Cible MVP |

| Taille pipeline | Jusqu’à 1 000 tronçons dans les tests de capacité. |

| Stations | Jusqu’à 50 stations. |

| Bibliothèque pompes | Jusqu’à 500 références par organisation. |

| Réservoirs | Jusqu’à 500 par organisation. |

| Simulation standard | Objectif inférieur à 10 secondes. |

| Comparaison simple | Objectif inférieur à 60 secondes. |

| Optimisation initiale | Objectif inférieur à 5 minutes sur taille bornée. |

| Import | Validation et aperçu avant engagement en base. |



## 12.2 Fiabilité et explicabilité

- Aucun résultat silencieux en cas de non-convergence ou d’entrée hors domaine.

- Résultats reproductibles avec même snapshot, version du moteur et paramètres.

- Conservation de masse vérifiée et résidu affiché.

- Localisation et explication de chaque violation.

- Journaux corrélés par identifiant de requête et de simulation.

- Sauvegardes testées et procédure de restauration documentée.

## 12.3 Sécurité applicative

- TLS en production et cookies HttpOnly/SameSite ou stratégie de jetons sécurisée.

- Hachage moderne des mots de passe et secrets hors du code.

- RBAC, isolation tenant et contrôles d’autorisation côté backend.

- Validation stricte des fichiers, taille limitée et stockage isolé.

- Journal d’audit immuable pour les actions sensibles.

- Analyse des dépendances, mises à jour maîtrisées et inventaire SBOM.

- Le futur raccordement industriel sera séparé par une passerelle et un réseau segmenté.

## 12.4 Observabilité

| Signal | Contenu |

| Logs | Requêtes, jobs, erreurs, solveurs et événements de sécurité. |

| Métriques | Latence API, temps de calcul, taux d’échec, files d’attente et ressources. |

| Traces | Corrélation frontend–API–worker–moteur. |

| Santé | Endpoints liveness/readiness et diagnostic des dépendances. |

| Audit scientifique | Version, options, résidus, avertissements et données utilisées. |



# 13. Validation scientifique et stratégie de tests

## 13.1 Niveaux de validation

1. Tests unitaires des équations et conversions.

2. Tests de propriété : monotonie, conservation, invariance dimensionnelle et bornes.

3. Tests de composants : pompe, conduite, réservoir et accessoire.

4. Tests de réseau : stations multiples, états dégradés et conditions aux limites.

5. Comparaison avec calcul manuel et cas issus des documents fournis.

6. Comparaison avec pandapipes lorsque le cas est compatible.

7. Validation externe avec DWSIM pour les cas de procédés compatibles.

8. Tests d’intégration API/base/worker et tests E2E frontend.

9. Tests de non-régression à chaque changement de moteur.

## 13.2 Cas scientifiques obligatoires

| ID | Cas | Attendu |

| V-001 | Conduite horizontale simple | Pression et perte connues. |

| V-002 | Dénivelé positif/négatif | Influence correcte de la charge statique. |

| V-003 | Régime laminaire | λ = 64/Re. |

| V-004 | Régime turbulent | Colebrook et approximation explicite comparées. |

| V-005 | Débit imposé | Profil de pression complet. |

| V-006 | Pressions imposées | Débit résolu. |

| V-007 | Pompe unique | Point pompe-réseau. |

| V-008 | Pompes en série | Hauteurs cumulées. |

| V-009 | Pompes en parallèle | Partage du débit. |

| V-010 | Stations multiples | Pressions d’aspiration/refoulement. |

| V-011 | NPSH insuffisant | Violation détectée. |

| V-012 | Surpression | Localisation et limite. |

| V-013 | Station bypassée | Chemin et pertes modifiés. |

| V-014 | Pompe de secours | Substitution et nouvelle performance. |

| V-015 | Transfert bac-à-bac | Bilan matière et temps. |

| V-016 | Bac presque vide | Arrêt sur niveau bas. |

| V-017 | Bac presque plein | Arrêt sur niveau haut. |

| V-018 | Absence de solution | Erreur explicite. |

| V-019 | Non-convergence forcée | Résidu et itérations conservés. |

| V-020 | Grande longueur / profil complexe | Stabilité et performance. |



## 13.3 Tolérances et gouvernance

- Chaque cas possède entrées, résultat attendu, méthode de référence, tolérance et version.

- Les tolérances sont spécifiques à la grandeur et au modèle; aucune tolérance globale arbitraire.

- Les changements de résultat exigent une revue scientifique et une note de migration.

- Les jeux de données de référence sont versionnés dans le dépôt.

- Les tests automatisés sont revus ; les résultats attendus sont validés par un référent compétent.

# 14. Plan de développement pour deux développeurs

## 14.1 Répartition des responsabilités

| Développeur 1 — scientifique/backend | Développeur 2 — frontend/données/infrastructure | Travail commun |

| • HydroLiquid Core • Pompes, stations, réservoirs • API de simulation • Optimisation Pyomo • Tests scientifiques | • PostgreSQL/PostGIS • Shadcn Admin • React Flow et graphiques • Imports/exports • Docker et CI/CD | • Modèle métier • Contrats API • Revues de code • Tests d’intégration • Documentation et validation |



## 14.2 Phases et livrables

| Phase | Contenu | Livrable |

| P0 — 4 sem. | Fondations, architecture, unités, POC pandapipes, pipeline simple. | Prototype scientifique calculable. |

| P1 — 4 à 6 sem. | Projets, produits, tronçons, profil, accessoires, imports. | Pipeline paramétrable. |

| P2 — 5 à 7 sem. | Stations, courbes, série/parallèle, secours, NPSH, puissance. | Oléoduc multi-stations. |

| P3 — 4 à 6 sem. | Réservoirs, barémage, transferts, niveaux et bilans. | Simulation bac-à-bac. |

| P4 — 4 à 6 sem. | Scénarios, comparaison, optimisation et classement. | Aide à la décision. |

| P5 — 4 à 6 sem. | UI complète, rapports, audit, performance, sécurité. | MVP bêta déployable. |

| P6 — 2 à 4 sem. | Validation indépendante, tests utilisateurs et corrections. | MVP 1.0. |



## 14.3 Règles de réalisation

- Une fonctionnalité scientifique n’est terminée qu’avec tests, tolérances, source et rapport de validation.

- Aucun code critique n’est fusionné sans revue croisée et validation des tests.

- Le frontend ne doit pas contenir de logique scientifique de référence.

- Les migrations de base sont reproductibles et testées à partir d’une base vide.

- Toute dépendance open source est enregistrée avec licence, version et justification.

- Une démonstration intégrée est produite à la fin de chaque phase.

# 15. Critères de réception et définition de fin du MVP

## 15.1 Parcours fonctionnel obligatoire

1. Créer une organisation et attribuer des rôles.

2. Créer un projet et une version d’installation.

3. Définir/importer un produit.

4. Créer/importer un pipeline et son profil.

5. Ajouter plusieurs stations et pompes.

6. Configurer série, parallèle, vitesse et secours.

7. Ajouter des réservoirs et leur barémage.

8. Créer un scénario normal ou dégradé.

9. Lancer et suivre une simulation.

10. Consulter profils, tableaux, contraintes et explications.

11. Simuler un transfert et suivre les niveaux.

12. Comparer et optimiser des configurations.

13. Valider la simulation et générer les rapports.

14. Retrouver toutes les versions et l’audit.

## 15.2 Portes de sortie

| Domaine | Condition de réception |

| Fonctionnel | Tous les parcours principaux et scénarios obligatoires passent. |

| Scientifique | Cas V-001 à V-020 réussis dans les tolérances approuvées. |

| Technique | Docker, migrations, sauvegarde/restauration et CI sont opérationnels. |

| Sécurité | Isolation tenant, RBAC, fichiers et audit testés. |

| Performance | Objectifs mesurés ou écarts documentés et acceptés. |

| Documentation | Installation, exploitation, API, modèles et limites documentés. |

| Validation utilisateur | Essais par au moins un ingénieur métier et corrections critiques closes. |



|  | Définition officielle de fin Le MVP est terminé lorsqu’un utilisateur peut réaliser le parcours complet, obtenir des résultats validés et reproductibles, comparer des scénarios, produire un rapport et installer la solution sans intervention manuelle non documentée. |



# 16. Risques, limites et mesures de maîtrise

| ID | Risque | Niveau | Maîtrise |

| R-01 | pandapipes ne couvre pas les cas oléoduc | Élevé | Adaptateur, POC, moteur longue distance propre et comparaison. |

| R-02 | Données produit insuffisantes | Élevé | Tables internes, données labo, sources et incertitudes. |

| R-03 | Complexité série/parallèle/secours | Élevé | Décomposition par étapes et cas de référence. |

| R-04 | Optimisation MINLP instable | Moyen/élevé | Énumération initiale, modèles simplifiés, solveurs interchangeables. |

| R-05 | Licence incompatible | Élevé | Inventaire licences; DWSIM reste externe; audit avant intégration. |

| R-06 | Équipe de deux développeurs | Élevé | Monolithe modulaire, périmètre strict, automatisation renforcée et jalons. |

| R-07 | Résultats non expliqués | Élevé | Traçabilité, contraintes localisées, rapport des méthodes. |

| R-08 | Confusion conformité / calcul | Élevé | Séparer lois physiques et règles; afficher le périmètre de contrôle. |

| R-09 | Imports de mauvaise qualité | Moyen | Aperçu, mapping, unités, validation et rejet atomique. |

| R-10 | Dérive vers le SCADA trop tôt | Élevé | Lecture seule; connectivité reportée après validation du cœur. |



# 17. Évolution vers le produit final

Le backend et les cœurs du MVP sont conservés. Le produit final ajoute des moteurs spécialisés sous forme de services ou de plugins, sans réécrire la gestion des projets, les données, les droits ou le frontend principal.

| Capacité finale | Fonctions | Technologie cible |

| Moteur liquide avancé | Multiproduit, thermique, produits visqueux, estimation d’état et temps quasi réel. | HydroLiquid Core enrichi. |

| Moteur gaz | Réseaux gaz, compresseurs, line-pack et optimisation. | Gas Network Core + GasModels.jl + modèles propres. |

| Moteur transitoire | Démarrage/arrêt, vannes, coupure et coup de bélier. | OpenModelica/Modelica.Fluid/FMU; solveur MOC si nécessaire. |

| Procédés complexes | Chauffage, séparation, mélange, réconciliation et MPC. | IDAES comme module complémentaire. |

| Connectivité industrielle | Lecture OPC UA et protocoles automate. | open62541 et PLC4X via passerelle isolée. |

| Historisation | Séries temporelles, événements, alarmes et qualité. | PostgreSQL/TimescaleDB; IoTDB si l’échelle l’exige. |

| Détection de fuite | Mass balance, RTTM, statistiques et capteurs externes. | Architecture multicouche après données et pilote. |

| Jumeau numérique | Synchronisation, estimation, prédiction et recommandation. | Orchestration des moteurs et données réelles. |



# Annexe A — Backlog MVP par épopée

| Épopée | Nom | Contenu | Priorité |

| E01 | Fondations | Repo, Docker, CI, conventions, environnements, observabilité. | Must |

| E02 | Identité | Organisations, utilisateurs, rôles, sessions, audit. | Must |

| E03 | Projets | CRUD, versions, états, pièces jointes. | Must |

| E04 | Produits | Bibliothèque, propriétés, tables, sources. | Must |

| E05 | Pipeline | Tronçons, profil, accessoires, PostGIS. | Must |

| E06 | Pompes | Courbes, interpolation, séries, parallèles, vitesse. | Must |

| E07 | Stations | Collecteurs, états, bypass, secours, limites. | Must |

| E08 | Hydraulique | Équations, solveurs, contraintes et explication. | Must |

| E09 | Réservoirs | Types, niveaux, barémage, état. | Must |

| E10 | Transferts | Simulation temporelle, arrêt, bilan. | Must |

| E11 | Scénarios | Normal, panne, secours, bypass, température. | Must |

| E12 | Optimisation | Énumération, Pyomo, objectifs, classement. | Should |

| E13 | Résultats | Tables, profils, graphiques et violations. | Must |

| E14 | Rapports | PDF, Excel, CSV, JSON. | Must |

| E15 | Imports | Mapping, unités, aperçu, validation. | Must |

| E16 | Validation | Cas de référence et non-régression. | Must |

| E17 | Déploiement | Local, serveur privé, cloud, sauvegarde. | Must |

| E18 | Cartographie | Tracé et localisation des équipements. | Should |

| E19 | Approbation | Workflow validateur et gel de version. | Should |

| E20 | Performance | Benchmarks, profiling et limites. | Must |



# Annexe B — Histoires utilisateur prioritaires

| ID | Histoire | Critère principal |

| US-001 | En tant qu’ingénieur, je crée un projet avec unités et référentiels afin de préparer une étude. | Projet versionné et visible uniquement dans mon organisation. |

| US-002 | J’importe un profil distance–altitude afin de modéliser le terrain. | Aperçu, unités, erreurs et import atomique. |

| US-003 | J’importe les courbes H, rendement, puissance et NPSHr d’une pompe. | Points affichés, domaine validé et version conservée. |

| US-004 | Je configure des pompes en série ou parallèle. | Schéma valide et performances de groupe calculées. |

| US-005 | Je lance un calcul à débit imposé. | Profil de pression, pertes et contraintes retournés. |

| US-006 | Je demande le débit compatible avec les limites. | Débit trouvé ou absence de solution expliquée. |

| US-007 | Je rends une pompe indisponible et active le secours. | Nouveau scénario calculé et comparaison produite. |

| US-008 | Je crée un réservoir et importe son barémage. | Conversions niveau-volume cohérentes. |

| US-009 | Je simule un transfert d’un volume cible. | Temps, niveaux, énergie et conditions d’arrêt affichés. |

| US-010 | Je compare plusieurs scénarios. | Tableau et graphiques comparatifs. |

| US-011 | Je demande la configuration minimisant l’énergie. | Candidats, rejets, meilleure solution et hypothèses. |

| US-012 | Je valide une simulation. | Snapshot immuable et rapport identifié. |

| US-013 | Je génère une note de calcul. | PDF avec hypothèses, méthodes, résultats, graphiques et limites. |

| US-014 | Je consulte une non-convergence. | Cause probable, résidu, itérations et données concernées. |

| US-015 | Je duplique un projet ou scénario. | Nouvel objet indépendant avec origine tracée. |



# Annexe C — Formats d’import minimaux

## C.1 Profil altimétrique

| distance_km,elevation_m,latitude,longitude 0.0,125.4,5.3201,-4.0182 5.0,130.2,5.3310,-4.0010 10.0,118.7,5.3422,-3.9850 |



## C.2 Courbe de pompe

| flow_m3_h,head_m,efficiency_pct,power_kw,npshr_m 1000,320,72,1180,4.5 1500,295,81,1490,5.2 2000,250,78,1750,6.8 |



## C.3 Table de barémage

| level_m,volume_m3 0.00,0 0.50,980 1.00,1965 1.50,2952 |



## C.4 Tronçons

| sequence,length_m,inner_diameter_m,roughness_m,mawp_pa,material 1,12000,0.800,0.000045,8000000,carbon_steel 2,18000,0.800,0.000045,8000000,carbon_steel |



# Annexe D — Statuts et codes d’erreur

| Code | Description |

| SIM_QUEUED | Simulation en attente. |

| SIM_RUNNING | Calcul en cours. |

| SIM_CONVERGED | Convergé sans violation critique. |

| SIM_CONVERGED_WARN | Convergé avec avertissements. |

| SIM_INVALID_INPUT | Entrées invalides. |

| SIM_NO_PHYSICAL_SOLUTION | Aucune solution physique trouvée. |

| SIM_NOT_CONVERGED | Tolérance non atteinte. |

| SIM_CANCELLED | Calcul annulé. |
| SIM_TECHNICAL_ERROR | Échec technique du processus après épuisement des reprises. |

| ERR_UNIT_UNKNOWN | Unité inconnue. |

| ERR_PROFILE_NOT_MONOTONIC | Distances non croissantes. |

| ERR_PUMP_CURVE_INVALID | Courbe de pompe incohérente. |

| ERR_TANK_TABLE_INVALID | Barémage non monotone. |

| VIOL_PRESSURE_HIGH | Pression maximale dépassée. |

| VIOL_PRESSURE_LOW | Pression minimale non respectée. |

| VIOL_CAVITATION | NPSH insuffisant. |

| VIOL_POWER | Puissance moteur dépassée. |

| WARN_EXTRAPOLATION | Calcul hors domaine tabulé. |

| WARN_NEAR_LIMIT | Point proche d’une limite configurée. |



# Annexe E — Registre initial des décisions d’architecture

| ADR | Décision | Justification |

| ADR-001 | Monolithe modulaire au MVP | Réduit la complexité d’une équipe de deux développeurs. |

| ADR-002 | Python comme langage principal | Cohérence scientifique, API, optimisation et écosystème. |

| ADR-003 | Moteurs derrière interfaces | Remplacement et comparaison sans couplage du produit. |

| ADR-004 | PostgreSQL/PostGIS comme source de vérité | Données métier, versionnement et géospatial dans un socle unique. |

| ADR-005 | SI en interne | Réduction des erreurs de conversion. |

| ADR-006 | Shadcn Admin comme base UI | Accélération sans figer la logique métier. |

| ADR-007 | DWSIM externe | Validation sans contamination de licence ni couplage. |

| ADR-008 | IDAES après le MVP | Éviter une complexité prématurée. |

| ADR-009 | Lecture seule avant contrôle | Sécurité opérationnelle et validation progressive. |

| ADR-010 | Normes non codées en dur | Version, applicabilité et traçabilité des règles. |



# Annexe F — Glossaire

| Terme | Définition |

| API | Interface de programmation applicative. |

| BEP | Best Efficiency Point, point de meilleur rendement d’une pompe. |

| H(Q) | Hauteur fournie par une pompe selon le débit. |

| HGL | Hydraulic Grade Line, ligne piézométrique. |

| MAWP | Pression maximale admissible de service. |

| MVP | Produit minimum viable, utilisable et validable. |

| NPSHa | NPSH disponible dans l’installation. |

| NPSHr | NPSH requis par la pompe. |

| POC | Preuve de concept. |

| RBAC | Contrôle d’accès basé sur les rôles. |

| RTTM | Real-Time Transient Model, futur modèle de fuite/temps réel. |

| SCADA | Système de supervision et acquisition de données. |

| Snapshot | Copie immuable des données utilisées par une simulation. |

| SIS | Système instrumenté de sécurité. |

| Tenant | Organisation isolée dans une plateforme multi-organisation. |



# Annexe G — Sources et documentation de référence

Sources fournies par le porteur du projet

- « Компьютерное моделирование технологических процессов трубопроводного транспорта углеводородов » — support sur la modélisation, les moindres carrés, les pompes et les méthodes numériques.

- Programme Python fourni — cas d’un oléoduc avec profil, stations multiples et pompes; utilisé comme base comparative, après correction.

- « Нефтебазы и АЗС » — ouvrage technique sur les dépôts, les pipelines, les pompes, les réservoirs, la mesure et l’exploitation.

- « Хранение 2020 » et « Пособие Хранение_КНИТУ » — stockage, propriétés des produits, barémage, réception et expédition.

- « ГТС 2020 » — préparation du futur périmètre gazier.

Sources officielles des projets open source — consultées le 2 août 2026

| Projet | Référence utilisée |

| Shadcn Admin | Dépôt officiel satnaing/shadcn-admin — caractéristiques, stack et licence MIT. |

| FastAPI | Documentation officielle — framework Python, validation typée et OpenAPI. |

| pandapipes | Documentation officielle — composants de réseau et évolutions. |

| CoolProp | Documentation officielle — propriétés de fluides, mélanges et incompressibles. |

| Pyomo | Documentation officielle — langage de modélisation d’optimisation et intégration de solveurs. |

| React Flow | Documentation officielle — éditeurs à nœuds, licence MIT et personnalisation. |

| PostgreSQL | Documentation officielle — base relationnelle, partitionnement et réplication. |

| PostGIS | Documentation officielle — stockage, indexation et requêtes géospatiales. |

| GasModels.jl | Dépôt officiel LANL-ANSI — optimisation stationnaire des réseaux gaziers. |

| OpenModelica | Guide officiel — simulation Modelica et intégration FMI/FMU. |

| IDAES | Documentation officielle — framework orienté équations basé sur Pyomo. |



# Conclusion

|  | Décision de démarrage La documentation est suffisante pour commencer immédiatement la phase P0. Le premier objectif est de produire un cas liquide simple validé, puis d’étendre progressivement le même socle vers les stations multiples, les réservoirs, les scénarios et l’optimisation. |



Le MVP complet est estimé à environ 23 à 35 semaines pour deux développeurs à temps plein, sous réserve de la disponibilité des données, de la validation scientifique et du maintien strict du périmètre.
