Plateforme de transport et de stockage des hydrocarbures

D04

Cahier des charges fonctionnel complet

Exigences fonctionnelles de la plateforme, du MVP à la cible

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D04 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Objet et périmètre

- Principes fonctionnels

- Gestion des projets

- Modélisation

- Calcul liquide

- Pompes

- Réservoirs et transferts

- Scénarios

- Données

- Rapports

- Administration

- Fonctions futures

- Critères de recette

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Objet et périmètre

Le présent cahier des charges définit les fonctions attendues de la plateforme. Les exigences sont identifiées, priorisées et assorties d’un critère d’acceptation. Les priorités sont : MUST pour le MVP, SHOULD pour une version proche, LATER pour la feuille de route.

| Périmètre MVP Pipeline liquide en régime permanent, stations multiples, pompes principales et de secours, réservoirs, transfert bac-à-bac, scénarios, optimisation simple, import de données, graphiques et rapports. |



# 2. Principes fonctionnels

| ID | Exigence | Priorité | Critère d’acceptation |

| FR-GEN-001 | La plateforme doit être paramétrable et ne contenir aucun nombre fixe de tronçons, stations, pompes ou bacs. | MUST | Créer et calculer deux projets de topologies différentes sans modifier le code. |

| FR-GEN-002 | Chaque résultat doit être rattaché à une version de données, de modèle, de méthode et de scénario. | MUST | Le rapport restitue les quatre identifiants. |

| FR-GEN-003 | Les unités saisies doivent être converties vers un système interne SI tout en conservant la valeur d’origine. | MUST | Conversion vérifiée sur un jeu d’essai. |

| FR-GEN-004 | Les calculs normatifs doivent être séparés des équations physiques et sélectionnables par projet. | MUST | Changer un jeu de règles sans modifier le solveur. |

| FR-GEN-005 | Les erreurs et non-convergences doivent être explicites et exploitables. | MUST | Aucun résultat silencieux ou valeur sentinelle non documentée. |



# 3. Gestion des organisations, projets et versions

| ID | Exigence | Priorité | Critère d’acceptation |

| FR-PRJ-001 | Créer une organisation, un site et plusieurs projets. | MUST | Les données sont isolées par organisation. |

| FR-PRJ-002 | Définir le type de projet, le pays, les normes, les unités et les responsables. | MUST | Fiche projet enregistrée et exportable. |

| FR-PRJ-003 | Cloner un projet ou une version pour créer une variante. | MUST | Le clone conserve la filiation. |

| FR-PRJ-004 | Geler une version approuvée en lecture seule. | SHOULD | Modification impossible hors nouveau clone. |

| FR-PRJ-005 | Comparer les différences entre deux versions. | SHOULD | Liste des paramètres et équipements modifiés. |

| FR-PRJ-006 | Archiver et restaurer un projet avec audit. | MUST | Projet masqué puis restauré par un administrateur. |



# 4. Modélisation du réseau et des équipements

| ID | Exigence | Priorité | Critère d’acceptation |

| FR-MOD-001 | Créer des nœuds et tronçons reliés en graphe. | MUST | Contrôle de connexité et orientation. |

| FR-MOD-002 | Importer un profil altimétrique depuis CSV/Excel et l’interpoler. | MUST | Aperçu, validation et rapport d’erreurs. |

| FR-MOD-003 | Définir longueur, diamètre, épaisseur, rugosité, matériau, pression admissible et état par tronçon. | MUST | Tous les champs obligatoires validés. |

| FR-MOD-004 | Ajouter pompes, vannes, clapets, filtres, débitmètres, réservoirs, sources, puits et bypass. | MUST | Équipements visibles sur le schéma. |

| FR-MOD-005 | Créer une bibliothèque d’équipements réutilisables. | MUST | Instanciation d’un modèle de pompe dans plusieurs stations. |

| FR-MOD-006 | Importer/exporter la topologie au format JSON documenté. | MUST | Round-trip sans perte. |

| FR-MOD-007 | Visualiser le réseau en schéma et sur carte. | SHOULD | Sélection synchronisée carte/schéma. |

| FR-MOD-008 | Détecter les nœuds isolés, doublons, sens incohérents et paramètres manquants. | MUST | Rapport de validation avant calcul. |



# 5. Produits et propriétés physiques

| ID | Exigence | Priorité | Critère d’acceptation |

| FR-FLD-001 | Créer une fiche produit avec densité, viscosité, pression de vapeur et température. | MUST | Fiche validée avec unités et source. |

| FR-FLD-002 | Définir des courbes ou corrélations de propriétés en fonction de la température et de la pression. | MUST | Interpolation et domaine de validité visibles. |

| FR-FLD-003 | Conserver les données de laboratoire avec date, méthode et incertitude. | SHOULD | Traçabilité complète d’un point de propriété. |

| FR-FLD-004 | Signaler toute extrapolation hors domaine. | MUST | Avertissement dans résultat et rapport. |

| FR-FLD-005 | Permettre l’utilisation d’une bibliothèque interne ou de CoolProp lorsqu’applicable. | SHOULD | Source de propriété indiquée. |



# 6. Moteur hydraulique liquide

| ID | Exigence | Priorité | Critère d’acceptation |

| FR-LIQ-001 | Calculer vitesse, Reynolds, facteur de frottement et pertes par tronçon. | MUST | Résultats disponibles par segment. |

| FR-LIQ-002 | Résoudre un réseau stationnaire avec conditions de débit, pression ou niveau. | MUST | Convergence démontrée sur cas de référence. |

| FR-LIQ-003 | Calculer pression, charge totale et ligne hydraulique le long du profil. | MUST | Graphique et export tabulaire. |

| FR-LIQ-004 | Prendre en compte pertes singulières et équipements. | MUST | Somme détaillée par composant. |

| FR-LIQ-005 | Détecter pression inférieure à la vapeur, cavitation et zones gravitaires selon le modèle sélectionné. | MUST | Localisation et avertissement. |

| FR-LIQ-006 | Gérer les injections, soutirages et changements de diamètre. | SHOULD | Conservation de masse contrôlée. |

| FR-LIQ-007 | Calculer la pression maximale et la comparer à la limite de projet. | MUST | Marge affichée par tronçon. |

| FR-LIQ-008 | Fournir résidus, itérations, tolérances et diagnostic de convergence. | MUST | Journal de solveur accessible. |

| FR-LIQ-009 | Permettre plusieurs corrélations de frottement validées. | SHOULD | Méthode sélectionnée dans le scénario. |



# 7. Stations et pompes

| ID | Exigence | Priorité | Critère d’acceptation |

| FR-PMP-001 | Importer les courbes H(Q), rendement, puissance et NPSHr. | MUST | Courbes contrôlées et tracées. |

| FR-PMP-002 | Approximer les courbes selon une méthode documentée sans perdre les points d’origine. | MUST | Erreur d’ajustement calculée. |

| FR-PMP-003 | Modéliser pompes en série, parallèle, vitesse fixe et variable. | MUST | Courbe combinée correcte sur cas test. |

| FR-PMP-004 | Définir rôles principal, secours, maintenance et indisponible. | MUST | Scénario respecte l’état. |

| FR-PMP-005 | Calculer pression d’aspiration/refoulement, puissance, rendement et marge NPSH. | MUST | Tableau station complet. |

| FR-PMP-006 | Signaler fonctionnement hors plage, débit minimal ou puissance moteur. | MUST | Violation bloquante ou avertissement paramétrable. |

| FR-PMP-007 | Tester automatiquement les combinaisons admissibles. | MUST | Classement des configurations. |

| FR-PMP-008 | Évaluer la consommation et le coût selon un tarif horaire. | SHOULD | Coût du scénario calculé. |



# 8. Réservoirs, stocks et transferts

| ID | Exigence | Priorité | Critère d’acceptation |

| FR-TNK-001 | Créer des réservoirs avec géométrie, produit, niveaux et capacité. | MUST | Fiche bac complète. |

| FR-TNK-002 | Importer une table de barémage hauteur-volume et vérifier sa monotonie. | MUST | Erreur signalée si incohérence. |

| FR-TNK-003 | Calculer volume, masse, capacité disponible et niveaux projetés. | MUST | Valeurs à un instant donné. |

| FR-TNK-004 | Simuler un transfert source-destination avec niveaux variables. | MUST | Courbes h(t), Q(t), P(t) et heure de fin. |

| FR-TNK-005 | Vérifier niveau haut/haut-haut, débit maximal et compatibilité produit. | MUST | Transfert impossible ou averti selon règle. |

| FR-TNK-006 | Calculer le bilan matière et les écarts compteur/jaugeage. | MUST | Rapport avec incertitude disponible. |

| FR-TNK-007 | Gérer plusieurs chemins hydrauliques et choisir un chemin. | SHOULD | Chemin sélectionné et vannes listées. |

| FR-TNK-008 | Planifier plusieurs mouvements sans conflit de ressource. | LATER | Planning sans double usage de pompe/ligne/bac. |



# 9. Scénarios, pannes et optimisation

| ID | Exigence | Priorité | Critère d’acceptation |

| FR-SCN-001 | Créer un scénario depuis une baseline et modifier les états sans altérer la baseline. | MUST | Filiation visible. |

| FR-SCN-002 | Bibliothèque de modes : normal, pompe arrêtée, secours, station bypassée, débit réduit. | MUST | Scénarios instanciables. |

| FR-SCN-003 | Comparer plusieurs scénarios sur débit, pressions, énergie, violations et coût. | MUST | Tableau comparatif et classement. |

| FR-SCN-004 | Rechercher automatiquement une configuration faisable. | MUST | Au moins une stratégie d’énumération contrôlée. |

| FR-SCN-005 | Optimiser une fonction objectif avec contraintes paramétrables. | SHOULD | Résultat reproductible et solveur identifié. |

| FR-SCN-006 | Expliquer pourquoi un scénario est non réalisable. | MUST | Liste de contraintes violées. |

| FR-SCN-007 | Simuler les transitoires et coups de bélier. | LATER | Cas de validation MOC. |

| FR-SCN-008 | Simuler gazoducs et compresseurs. | LATER | Cas réseau gaz validé. |



# 10. Données, analyses et tableaux de bord

| ID | Exigence | Priorité | Critère d’acceptation |

| FR-DAT-001 | Importer CSV et Excel avec mapping des colonnes et unités. | MUST | Aperçu et validation avant import. |

| FR-DAT-002 | Conserver données brutes, normalisées et corrigées séparément. | MUST | Lignage vérifiable. |

| FR-DAT-003 | Gérer horodatage, unité, qualité et source de chaque mesure. | MUST | Schéma conforme D09. |

| FR-DAT-004 | Afficher séries temporelles, statistiques et détection de valeurs aberrantes. | SHOULD | Tableau de bord configurable. |

| FR-DAT-005 | Comparer mesures et simulation et calculer résidus. | SHOULD | KPI RMSE, biais, bilan. |

| FR-DAT-006 | Connecter un historian/SCADA en lecture seule. | LATER | Connecteur certifié sur site pilote. |

| FR-DAT-007 | Détecter et localiser une fuite avec méthodes hybrides. | LATER | Performance validée selon D20. |



# 11. Rapports et collaboration

| ID | Exigence | Priorité | Critère d’acceptation |

| FR-RPT-001 | Générer une note de calcul avec entrées, méthodes, résultats et avertissements. | MUST | Export Word/PDF conforme au modèle. |

| FR-RPT-002 | Exporter résultats en CSV/Excel et graphiques en image. | MUST | Export réutilisable. |

| FR-RPT-003 | Ajouter commentaires, statut et approbation. | SHOULD | Workflow brouillon/revu/approuvé. |

| FR-RPT-004 | Inclure la liste des normes et versions sélectionnées. | MUST | Références affichées. |

| FR-RPT-005 | Générer rapport de transfert, scénario, bilan matière et validation. | MUST | Quatre modèles disponibles. |

| FR-RPT-006 | Personnaliser logo, entête et langue. | SHOULD | Modèle par organisation. |



# 12. Administration et sécurité fonctionnelle

| ID | Exigence | Priorité | Critère d’acceptation |

| FR-ADM-001 | Gérer utilisateurs, rôles et permissions par organisation/projet. | MUST | Tests RBAC réussis. |

| FR-ADM-002 | Journaliser connexions, changements, calculs, exports et approbations. | MUST | Audit filtrable. |

| FR-ADM-003 | Sauvegarder et restaurer la base et les fichiers. | MUST | Test de restauration réussi. |

| FR-ADM-004 | Paramétrer les limites et règles sans accès direct au code. | MUST | Édition contrôlée et versionnée. |

| FR-ADM-005 | Séparer environnement de calcul, production et intégration industrielle. | MUST | Déploiements distincts. |

| FR-ADM-006 | Interdire toute commande SCADA dans le MVP. | MUST | Connecteurs en lecture seule. |



# 13. Critères de recette fonctionnelle du MVP

- Créer un projet complet avec au moins 100 tronçons, 5 stations, 15 pompes et 10 réservoirs.

- Importer profil, propriétés, courbes de pompe et barémages sans modifier le code.

- Calculer une baseline convergente et afficher les profils de pression et charge.

- Créer cinq scénarios dont un avec pompe de secours et un non réalisable.

- Simuler un transfert bac-à-bac et produire l’évolution des niveaux.

- Comparer les scénarios et recommander une configuration selon énergie et contraintes.

- Générer la note de calcul et les exports avec traçabilité complète.

- Déployer la même version sur un poste local et un serveur de test.

# Sources et références

- D01 à D03 pour le cadrage, les acteurs et les processus.

- Documents techniques transmis pour les méthodes de pipeline, pompes, réservoirs et gaz.

- D07 à D10 pour les équations, normes, données et validation.

- D11 à D18 pour l’architecture, les API, la sécurité et la qualité.

Fin du document