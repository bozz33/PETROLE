Plateforme de transport et de stockage des hydrocarbures

D14

Stratégie open source et licences

Composants retenus, usages, limites, licences et plan d’audit

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D14 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Principes

- Stack cœur

- Moteurs scientifiques

- Gaz et transitoires

- Données industrielles

- Comparaison

- Matrice licences

- Critères d’adoption

- POC

- Gouvernance

- Plan de sortie

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Principes

- Ne pas repartir de zéro pour les fonctions mathématiques génériques, mais conserver la maîtrise du modèle métier.

- Aucun projet open source unique ne couvre tout le produit ; l’architecture est fédérée et modulaire.

- Privilégier licences permissives pour les bibliothèques embarquées.

- Isoler les composants copyleft ou à licence complexe dans des processus/services après audit.

- Geler les versions, vérifier les CVE et maintenir des cas de non-régression.

- Prévoir une abstraction pour remplacer une dépendance critique.

- Ne pas confondre code open source et validation industrielle.

# 2. Stack cœur recommandée

| Projet | Usage | Licence connue | Décision |

| Python | Langage principal | PSF | Retenu |

| NumPy | Calcul vectoriel | BSD-3-Clause | Retenu |

| SciPy | Solveurs et optimisation numérique | BSD-3-Clause | Retenu |

| fluids | Corrélations et composants de mécanique des fluides | MIT | Retenu avec tests |

| CoolProp | Propriétés thermophysiques de fluides couverts | MIT | Retenu via adapter |

| Pyomo | Modélisation d’optimisation | BSD-3-Clause | Retenu |

| FastAPI | API web | MIT | Retenu |

| Pydantic | Validation de données | MIT | Retenu |

| SQLAlchemy/Alembic | Persistance et migrations | MIT | Retenu |

| PostgreSQL | Base relationnelle | PostgreSQL License | Retenu |

| PostGIS | Données géospatiales | GPL-2.0 ou ultérieure pour le projet serveur | Retenu comme service base |

| React | Frontend | MIT | Retenu |

| MapLibre GL JS | Cartographie | BSD-3-Clause | Retenu |

| Apache ECharts | Graphiques | Apache-2.0 | Retenu |



# 3. Moteurs et bibliothèques scientifiques

| Composant | Apport | Ce qui reste à développer |

| fluids | Frottement, raccords, vannes, écoulement compressible et utilitaires | Solveur réseau, stations, scénarios, traçabilité, validation |

| CoolProp | Propriétés de fluides normalisés et équations d’état | Base de produits pétroliers réels et données laboratoire |

| SciPy | Racines, optimisation, interpolation, intégration | Formulation physique et diagnostics métier |

| Pyomo | NLP/MILP/MINLP et interface solveurs | Modèles, linéarisation, contraintes et stratégie |

| NetworkX optionnel | Algorithmes de graphe | Ne pas l’utiliser comme modèle persistant principal |

| Polars/pandas | Traitement tabulaire | Gouvernance, mapping, qualité et volumétrie |



# 4. Projets spécialisés gaz et réseau

| Projet | Licence | Usage proposé | Décision |

| GasModels.jl | BSD | Optimisation de réseaux de gaz et formulations de recherche | Service futur/benchmark |

| JuMP | MPL-2.0 | Modélisation optimisation Julia | Dépendance de GasModels |

| pandapipes | BSD | Réseaux gaz/liquide simples et comparaison | Benchmark, pas cœur universel |

| IDAES-PSE | BSD-3-Clause | Procédés, propriétés et optimisation Pyomo | À évaluer pour terminaux |

| DWSIM | GPLv3 | Thermodynamique et procédés | Outil externe ou service après audit, pas embarqué au MVP |



# 5. Transitoires et Modelica

| Projet | Licence/point d’attention | Usage |

| Modelica Standard Library | BSD-3-Clause | Composants fluides et thermiques |

| OpenModelica | OSMC Public License et composants sous GPL ; usage à auditer | Environnement de simulation et génération FMU |

| FMI/FMU | Standard ouvert ; implémentations diverses | Échange de modèles compilés |

| Assimulo/SUNDIALS candidats | Licences à vérifier par version | Solveurs DAE/ODE |

| Moteur MOC interne | Propriété du projet | Coup de bélier liquide ciblé |



| Décision licence OpenModelica et DWSIM ne doivent pas être incorporés aveuglément dans un produit propriétaire. La preuve de concept peut les utiliser comme outils externes ; toute distribution ou intégration fait l’objet d’un audit juridique. |



# 6. Connectivité industrielle et historiques

| Projet | Licence | Usage proposé |

| open62541 | MPL-2.0 | Client/serveur OPC UA C/C++ dans une passerelle dédiée |

| Eclipse Milo | EPL-2.0 | Alternative OPC UA Java |

| Apache PLC4X | Apache-2.0 | Accès commun à Modbus, S7, EtherNet/IP et autres protocoles |

| Eclipse Paho | EPL/EDL selon composant | Client MQTT |

| Apache IoTDB | Apache-2.0 | Historian industriel haute volumétrie futur |

| TimescaleDB | Apache-2.0 pour certaines parties + licence communautaire pour d’autres | Extension PostgreSQL après vérification des fonctionnalités utilisées |

| Grafana | AGPLv3 | Observabilité interne/externe ; implications de service à examiner |



# 7. Matrice de décision

| Projet | Cœur MVP | Benchmark | Service futur | À éviter sans audit |

| NumPy/SciPy | Oui | Oui | Non | Non |

| fluids | Oui | Oui | Non | Non |

| CoolProp | Oui | Oui | Non | Non |

| Pyomo | Oui | Oui | Non | Solveur commercial à licencier séparément |

| pandapipes | Non | Oui | Possible | Non |

| GasModels.jl | Non | Oui | Oui | Non |

| OpenModelica | Non | Oui | Oui/FMU | Oui pour intégration directe |

| DWSIM | Non | Oui | Possible | Oui pour incorporation |

| open62541/PLC4X | Non | POC | Oui | Non |

| IoTDB/TimescaleDB | Non | POC | Oui | Fonctions sous licence non compatible |



# 8. Critères d’adoption d’une dépendance

| Critère | Questions |

| Couverture | La fonction est-elle réellement requise et validée ? |

| Licence | Distribution, SaaS, modification et liens sont-ils compatibles ? |

| Activité | Mainteneurs, releases, issues et bus factor ? |

| Qualité | Tests, documentation, typing, benchmarks ? |

| Sécurité | CVE, politique de divulgation, dépendances transitives ? |

| Performance | Temps, mémoire, parallélisme et stabilité ? |

| Portabilité | Linux, Windows dev, architecture CPU, conteneur ? |

| Remplacement | Adapter défini et alternative disponible ? |

| Validation | Cas de référence et limites connues ? |

| Gouvernance | Qui dans l’équipe maîtrise et met à jour ? |



# 9. Preuves de concept obligatoires

| POC | Objectif | Décision attendue |

| POC-OS-01 | fluids vs formules internes sur 30 cas | Fonctions réutilisées et wrappers |

| POC-OS-02 | CoolProp sur fluides couverts et données pétrolières | Périmètre exact et fallback |

| POC-OS-03 | Pyomo + solveurs open source | Performance de l’optimisation MVP |

| POC-OS-04 | pandapipes vs moteur sur réseau simple | Valeur comme benchmark |

| POC-OS-05 | GasModels.jl sur cas gaz | Contrat de service futur |

| POC-OS-06 | OpenModelica/FMU sur pompe-vanne-réservoir | Stratégie transitoires |

| POC-OS-07 | PostgreSQL partitionné vs TimescaleDB | Seuil de migration |

| POC-OS-08 | open62541/PLC4X en lecture seule | Passerelle et sécurité |



# 10. Gouvernance des dépendances

- Fichier SBOM généré à chaque release.

- Versions verrouillées et mises à jour planifiées.

- Scan de vulnérabilités et licences en CI.

- Registre avec propriétaire interne, justification et alternative.

- Test de non-régression avant toute montée de version scientifique.

- Conservation du code source et des licences conformément aux obligations.

- Aucune dépendance téléchargée dynamiquement en production sans contrôle.

# 11. Plan de sortie et réduction de dépendance

| Dépendance | Abstraction/solution de repli |

| fluids | Interface correlations ; implémentations internes pour fonctions critiques |

| CoolProp | PropertyProvider ; tables et corrélations internes |

| Pyomo | OptimizationModel ; énumération ou autre framework |

| PostGIS | Geometry repository ; GeoJSON et calculs applicatifs limités |

| TimescaleDB | SQL PostgreSQL standard + export Parquet |

| OpenModelica | FMU standard ou moteur interne |

| GasModels.jl | Contrat JSON indépendant et solveur gaz alternatif |

| ECharts/MapLibre | Composants UI encapsulés |



# Sources et références

| Règle d’utilisation Les licences peuvent évoluer selon les versions et les modules. Le registre de dépendances doit conserver la licence exacte du paquet distribué. |



- Dépôts officiels et fichiers de licence des projets cités, vérifiés au moment de la recherche 2026.

- D11 - Architecture et D16 - Plan de développement.

- Un audit juridique formel reste nécessaire avant distribution commerciale.

Fin du document