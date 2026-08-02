Plateforme de transport et de stockage des hydrocarbures

D03

Cartographie des acteurs et processus métier

Rôles, responsabilités, flux de travail et documents métier

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D03 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Acteurs

- Cycle de vie d’un projet

- Processus pipeline

- Processus dépôt et stockage

- Processus données

- Processus incidents

- RACI

- Documents métier

- Points de contrôle

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Acteurs de l’écosystème

| Acteur | Responsabilités | Besoins dans la plateforme |

| Ingénieur pipeline | Modélisation, calcul, vérification et dimensionnement | Éditeur réseau, solveur, profils, rapports |

| Ingénieur exploitation | Définition des modes et consignes | Scénarios, contraintes, prévisions |

| Opérateur/dispatcher | Conduite opérationnelle et suivi des mouvements | Tableaux de bord, alertes, chronologie |

| Ingénieur dépôt | Réservoirs, transferts, réception/expédition | Barémage, stocks, chemins de transfert |

| Maintenance | Disponibilité et fiabilité des équipements | Historique, heures de marche, pannes |

| HSE/Process safety | Analyse des risques et préparation aux incidents | Scénarios, limites, rapports |

| Analyste de données | Qualité, rapprochement, anomalies | Historique, notebooks, modèles |

| Administrateur | Comptes, référentiels, sécurité | RBAC, audit, sauvegardes |

| Direction | Pilotage et arbitrage | KPI et synthèses |

| Auditeur/autorité | Contrôle et justification | Accès en lecture, traçabilité, exports |



# 2. Cycle de vie d’un projet dans la plateforme

| Étape | Entrées | Activités | Sorties |

| 1. Cadrage | Objectifs, site, produit, référentiel | Définir périmètre et hypothèses | Fiche projet |

| 2. Collecte | Plans, profils, fiches équipements | Importer, nettoyer, qualifier | Jeu de données versionné |

| 3. Modélisation | Réseau et équipements | Construire topologie et paramètres | Modèle calculable |

| 4. Validation des données | Unités, plages, cohérence | Contrôles automatiques et métier | Rapport de qualité |

| 5. Calcul de base | Conditions aux limites | Résoudre le régime de référence | Résultats et diagnostics |

| 6. Scénarios | Indisponibilités, objectifs | Cloner et modifier le modèle | Comparatif de scénarios |

| 7. Optimisation | Coûts et contraintes | Rechercher configuration admissible | Recommandation |

| 8. Revue | Résultats, normes, avertissements | Validation humaine | Scénario approuvé |

| 9. Rapport | Modèle et décisions | Générer et signer | Note de calcul/rapport |

| 10. Capitalisation | Mesures réelles | Comparer et réviser | Nouveau modèle calibré |



# 3. Processus métier : pipeline liquide

- Définir le tracé, les altitudes, diamètres, rugosités, matériaux et limites de pression.

- Définir les produits, températures, densités, viscosités, pression de vapeur et règles de propriétés.

- Configurer les stations, pompes, montages série/parallèle, variateurs, bypass et équipements de secours.

- Définir les conditions aux limites : pression, débit, niveau de bac ou demande terminale.

- Calculer le point de fonctionnement, les pressions, vitesses, pertes et marges de cavitation.

- Identifier les surpressions, sous-pressions, écoulements gravitaires, non-convergences et équipements hors enveloppe.

- Comparer les configurations et valider un mode avec commentaires et approbation.

# 4. Processus métier : dépôt, stockage et transferts

- Créer les réservoirs et importer leurs tables de barémage.

- Définir les niveaux bas, haut, haut-haut, capacité utile et contraintes de produit.

- Construire le réseau de collecteurs, pompes, filtres, vannes, compteurs et points de réception/expédition.

- Choisir un bac source, un bac destinataire, un chemin hydraulique et une pompe.

- Calculer débit, pressions, NPSH, évolution des niveaux, durée, énergie et risques de débordement.

- Établir le bilan matière et comparer jaugeage, débitmètre et quantité calculée.

- Produire un ordre de mouvement et un rapport de fin de transfert.

# 5. Processus métier : données et calibration

| Processus | Règles essentielles | Sortie |

| Ingestion | Conserver source, horodatage, unité et qualité | Données brutes immuables |

| Normalisation | Convertir vers SI sans supprimer la valeur d’origine | Données harmonisées |

| Validation | Plages, doublons, trous, dérives, cohérence de masse | Score de qualité |

| Réconciliation | Ajuster dans les incertitudes sous contraintes physiques | Valeurs réconciliées |

| Calibration | Estimer rugosité, coefficients ou biais documentés | Paramètres calibrés |

| Comparaison | Mesuré contre simulé | Résidus et indicateurs |

| Publication | Approuver une version de modèle | Baseline exploitable |



# 6. Processus métier : incident et mode de secours

- Déclarer l’équipement indisponible ou l’événement hypothétique.

- Créer un scénario dérivé sans altérer le modèle de référence.

- Recalculer la faisabilité, les pressions extrêmes, les temps avant limite et la capacité de secours.

- Proposer plusieurs stratégies de récupération classées par sécurité, délai et coût.

- Soumettre la recommandation à une validation humaine.

- Conserver l’événement, la décision et le résultat réel pour retour d’expérience.

# 7. Matrice RACI simplifiée

| Activité | Dev/administrateur | Ingénieur calcul | Exploitant | HSE | Responsable |

| Créer référentiel équipement | R | C | C | I | A |

| Construire modèle | C | R | C | I | A |

| Valider données | C | R | R | I | A |

| Lancer scénario | I | R | R | C | A |

| Approuver résultat | I | R | C | C | A |

| Définir limites sécurité | I | C | C | R | A |

| Administrer utilisateurs | R | I | I | I | A |

| Modifier méthode scientifique | R | C | I | C | A |

| Autoriser connexion SCADA | R | I | C | C | A |



# 8. Documents métier produits

| Document | Contenu | Responsable de validation |

| Fiche projet | Objectifs, périmètre, référentiels, unités | Chef de projet |

| Dossier de données | Sources, qualité, versions, hypothèses | Ingénieur calcul |

| Note de calcul | Équations, entrées, résultats, vérifications | Ingénieur habilité |

| Rapport de scénario | Écarts, contraintes et recommandation | Exploitation |

| Ordre de transfert | Source, destination, chemin, volumes et limites | Responsable dépôt |

| Rapport de bilan matière | Entrées, sorties, stock, écart, incertitude | Comptage/Exploitation |

| Rapport incident | Chronologie, simulations, décision, retour | HSE/Direction |

| Rapport de validation | Cas tests, écarts, couverture, anomalies | Responsable technique |



# 9. Points de contrôle obligatoires

| Gates de validation Aucun scénario ne peut être présenté comme approuvé sans données valides, convergence du solveur, contrôle des limites, identification de la méthode et validation humaine. |



- Validation du système d’unités et des conversions.

- Contrôle de conservation de masse et cohérence énergétique.

- Vérification des enveloppes de pompes ou compresseurs.

- Vérification des limites de pression, niveau, température et cavitation.

- Journalisation de toute modification de modèle ou de règle.

- Séparation des données brutes, corrigées et réconciliées.

- Confirmation explicite avant export d’un rapport marqué « approuvé ».

# Sources et références

- Manuels fournis sur les dépôts, réservoirs, équipements, transferts et systèmes gaziers.

- Support de modélisation de pipeline et programme Python pour les processus de calcul stationnaire.

- Pratiques de gestion des scénarios, de validation et de sécurité définies par le projet.

Fin du document