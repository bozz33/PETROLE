Plateforme de transport et de stockage des hydrocarbures

D02

Vision produit et proposition de valeur

Positionnement, objectifs et différenciation de la plateforme

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D02 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Résumé de la vision

- Problèmes à résoudre

- Proposition de valeur

- Utilisateurs cibles

- Capacités du produit

- Différenciation

- Modèle de déploiement

- Indicateurs de succès

- Hypothèses et limites

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Résumé de la vision

| Vision produit Créer une plateforme paramétrable capable de représenter une installation réelle de transport et de stockage des hydrocarbures, d’en calculer les modes de fonctionnement, d’analyser ses données et de comparer des décisions d’exploitation avant leur application sur le terrain. |



La plateforme vise les pipelines de liquides, les stations de pompage, les réseaux technologiques de dépôts, les réservoirs et, dans les versions ultérieures, les gazoducs et stations de compression. Elle associe un moteur physique déterministe, des outils d’analyse de données et des fonctions d’optimisation. L’intelligence artificielle assiste l’utilisateur mais ne remplace pas les équations, les règles normatives ni la validation humaine.

# 2. Problèmes à résoudre

- Calculs dispersés entre feuilles de calcul, scripts académiques, logiciels propriétaires et documents papier.

- Difficulté à représenter une installation complète avec ses variantes, équipements de secours et contraintes réelles.

- Comparaison lente des modes normal, dégradé, maintenance et urgence.

- Faible traçabilité des hypothèses, unités, corrélations et normes utilisées.

- Exploitation insuffisante des historiques de pression, débit, température, niveau et énergie.

- Coût élevé et dépendance à des logiciels fermés spécialisés.

- Manque d’outils adaptés au contexte africain, à l’installation locale et aux besoins de formation.

# 3. Proposition de valeur

| Bénéficiaire | Valeur apportée | Résultat concret |

| Ingénieur étude | Modèle paramétrable et calcul reproductible | Notes de calcul, profils hydrauliques, vérifications et scénarios |

| Exploitant pipeline | Comparaison des configurations de stations | Débit réalisable, pressions, consommation et marges de sécurité |

| Exploitant dépôt | Simulation des mouvements de produits | Temps de transfert, choix de pompe, capacité disponible, risque de débordement |

| Maintenance | Analyse des indisponibilités et dérives | Modes de secours, priorités de maintenance, historique des équipements |

| HSE | Étude des situations dangereuses | Scénarios, limites, alarmes et rapports d’aide à la décision |

| Direction | Vue consolidée des performances | KPI énergie, disponibilité, production, stocks et pertes |

| Formation | Cas reproductibles et simulateur | Apprentissage des régimes normaux et incidents sans agir sur le site |



# 4. Utilisateurs cibles

- Exploitants d’oléoducs et de pipelines multiproduits.

- Dépôts pétroliers, terminaux, raffineries et sociétés de distribution.

- Bureaux d’études, intégrateurs et consultants.

- Compagnies de transport et distribution de gaz dans les phases ultérieures.

- Universités, centres de formation et laboratoires.

- Autorités, inspecteurs et auditeurs, selon les droits accordés.

# 5. Capacités du produit

| Domaine | Capacités prévues au MVP | Évolutions |

| Modélisation | Réseau liquide, tronçons, stations, pompes, vannes, réservoirs | Gaz, compresseurs, terminaux complexes, SIG avancé |

| Calcul | Régime permanent, pertes, pression, cavitation, zones gravitaires | Transitoires, multiphase ciblé, thermique avancée |

| Scénarios | Équipements disponibles/indisponibles, secours, bypass | Bibliothèque HAZOP/FMEA, simulateur opérateur |

| Optimisation | Sélection de configurations et énergie simple | MILP/MINLP, MPC économique, ordonnancement multiproduit |

| Données | Saisie, Excel/CSV, historique limité | OPC UA, historian, estimation d’état, temps réel |

| Rapports | PDF/Word/Excel, tableaux et graphiques | Rapports réglementaires personnalisés, signature et workflow |



# 6. Différenciation

- Paramétrage sans nombre fixe de stations, pompes, tronçons ou réservoirs.

- Séparation explicite entre moteur physique, règles normatives, données et interface.

- Déploiement local, cloud privé ou hybride, adapté aux sites à connectivité limitée.

- Traçabilité de chaque résultat : entrées, version du modèle, méthode numérique et avertissements.

- Architecture ouverte permettant d’intégrer des moteurs spécialisés sans dépendre d’un seul logiciel.

- Conception bilingue et extensible, avec priorité au français et aux unités SI.

- Positionnement progressif : outil d’ingénierie d’abord, jumeau numérique ensuite.

# 7. Modèle de déploiement

| Mode | Description | Usage |

| Local autonome | Serveur installé chez le client, sans dépendance Internet | Sites sensibles ou isolés |

| Client/serveur local | Application web sur réseau interne | Dépôt, station ou bureau d’études |

| Cloud privé | Instance dédiée par organisation | Accès multi-sites et administration centralisée |

| Hybride | Calcul et collecte locale, synchronisation contrôlée | Sites distants et consolidation groupe |

| SaaS futur | Service multi-tenant avec isolation forte | PME, formation et bureaux d’études |



# 8. Indicateurs de succès

| Indicateur | Cible MVP | Mesure |

| Exactitude hydraulique | Écart conforme aux tolérances définies dans D10 | Comparaison aux cas analytiques et de référence |

| Traçabilité | 100 % des calculs versionnés | Journal de calcul et empreinte des données |

| Temps de calcul | Cas stationnaire courant en moins de 10 s | Tests de performance |

| Utilisabilité | Un scénario complet sans modifier le code | Test utilisateur guidé |

| Robustesse | Échec explicite et diagnostiqué en cas de non-convergence | Tests négatifs |

| Couverture | Pipeline liquide et transfert bac-à-bac opérationnels | Recette fonctionnelle |

| Déploiement | Installation reproductible local/cloud | Docker et procédure documentée |



# 9. Hypothèses et limites

| Limite de responsabilité La plateforme fournit des calculs et recommandations d’aide à la décision. Elle ne certifie pas une installation, ne remplace pas une étude réglementaire et ne commande pas les équipements de sécurité dans le MVP. |



- Le MVP traite principalement des liquides monophasés en régime permanent.

- Les propriétés d’un produit réel doivent provenir de données fiables ou de mesures de laboratoire.

- La conformité dépend du pays, du contrat et de l’édition de norme sélectionnée.

- Les résultats industriels nécessitent une validation par un ingénieur compétent et un site pilote.

- Les fonctions IA doivent citer les données et ne peuvent modifier les résultats physiques validés.

# Sources et références

| Règle d’utilisation Les documents académiques russes soutiennent la compréhension et les cas de test, mais ne constituent pas la base normative principale. |



- Documents fournis : modélisation hydraulique de pipeline, programme Python multi-stations, stockage et équipements des dépôts, calcul des systèmes de transport pétrolier, systèmes gaziers.

- Référentiels internationaux retenus : ASME, API, ISO, IEC et ISA, selon le module et le pays.

- Sources industrielles et open source détaillées dans D08 et D14.

Fin du document