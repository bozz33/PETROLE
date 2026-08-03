Plateforme de transport et de stockage des hydrocarbures

D19

Modèles de rapports et interfaces

Catalogue des écrans, graphiques, rapports et règles de présentation

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec validation métier et scientifique |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D19 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Principes UX

- Navigation

- Écrans MVP

- Éditeur réseau

- Calcul et résultats

- Scénarios

- Bacs/transferts

- Données

- Administration

- Graphiques

- Rapports

- Modèle note de calcul

- Modèle transfert

- Alertes et erreurs

- Accessibilité

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Principes d’interface

- Interface destinée à des ingénieurs : dense mais structurée, unités toujours visibles.

- Séparer saisie, validation, calcul et approbation.

- Montrer les hypothèses et avertissements avant les indicateurs de performance.

- Permettre de revenir de chaque résultat à l’équipement et à la donnée source.

- Utiliser des couleurs comme complément et non comme seul code.

- Conserver le contexte projet/scénario dans toutes les pages.

- Ne pas imiter un HMI/SCADA de contrôle ; la plateforme est analytique.

# 2. Navigation principale

| Zone | Contenu |

| Accueil | Organisations, projets récents, jobs, alertes de qualité |

| Projet | Résumé, versions, membres, normes et fichiers |

| Modèle | Carte, schéma, actifs, produits et validation |

| Scénarios | Liste, overrides, comparaison et statut |

| Calculs | Jobs, résultats, diagnostics et historique |

| Stockage | Bacs, inventaires, transferts et bilans |

| Données | Imports, datasets, séries et qualité |

| Rapports | Documents générés, modèles et approbations |

| Administration | Utilisateurs, catalogues, règles, audit et sauvegardes |



# 3. Écrans MVP

| Écran | Éléments clés | Actions |

| Liste projets | Nom, type, site, statut, dernière activité | Créer, ouvrir, cloner, archiver |

| Fiche projet | Référentiel, unités, pays, responsables | Modifier, valider, exporter |

| Validateur modèle | Erreurs bloquantes et avertissements | Naviguer vers objet et corriger |

| Catalogue pompe | Points, fit, courbes, limites | Importer, approuver, versionner |

| Scénario | Conditions, états, objectifs | Calculer, comparer, cloner |

| Résultat | KPI, profil, stations, violations | Exporter, rapport, approuver |

| Parc de bacs | Niveaux, produits, capacité disponible | Créer mouvement |

| Transfert | Chemin, pompe, volume, courbes | Simuler et rapport |

| Import | Aperçu, mapping, unités, erreurs | Valider et lancer |

| Audit | Acteur, action, objet, date | Filtrer/exporter selon droits |



# 4. Éditeur réseau

- Panneau gauche : bibliothèque de composants et couches.

- Centre : schéma ou carte avec sélection, zoom et filtres.

- Panneau droit : propriétés de l’objet sélectionné avec unités et source.

- Bandeau validation : nombre d’erreurs, avertissements et statut calculable.

- Vue profil : chainage, altitude, stations et points remarquables.

- Mode tableau : édition en masse et copier-coller contrôlé.

- Historique : diff de version et auteur.

| MVP pragmatique L’éditeur graphique peut commencer comme une vue contrôlée complétée par des tableaux et formulaires. Un outil CAD/P&ID complet n’est pas nécessaire au MVP. |



# 5. Page de calcul et résultats

| Bloc | Contenu |

| Résumé | Statut, durée, débit, énergie, pression min/max, violations |

| Hypothèses | Produit, propriétés, corrélations, conditions et normes |

| Profil hydraulique | Altitude, charge, pression, limites et stations |

| Stations | Aspiration/refoulement, pompes, point, puissance, NPSH |

| Tronçons | Q, v, Re, λ, pertes, pression et marge |

| Diagnostics | Résidu, itérations, bilan de masse, extrapolations |

| Contrôles | Règles conformes/non conformes/non applicables |

| Fichiers | Entrées canoniques, exports et rapport |



# 6. Comparateur de scénarios

| Dimension | Présentation |

| Faisabilité | Badge et raisons principales |

| Débit/production | Valeur et écart baseline |

| Pressions | Min/max, emplacements et marges |

| Énergie/coût | Total et par station |

| Équipements | Actifs, secours, indisponibles et vitesse |

| Contraintes | Nombre par sévérité et détail |

| Objectif | Score, rang et méthode d’optimisation |

| Décision | Recommandé, retenu, rejeté et commentaire |



# 7. Interface réservoirs et transferts

| Vue | Éléments |

| Parc | Bac, produit, niveau, volume, capacité disponible, alarmes |

| Fiche bac | Géométrie, barémage, limites, équipements, historique |

| Assistant transfert | Source, destination, volume, produit, chemin, pompe |

| Simulation | Q(t), niveaux, pressions, énergie et événements |

| Ordre de mouvement | Vannes, pompes, limites, heure et responsable |

| Bilan | Compteurs, stocks, densité, écart, incertitude et commentaires |



# 8. Données et qualité

- Aperçu des lignes et détection automatique des types.

- Mapping colonne → grandeur → unité → actif/tag.

- Histogrammes, trous, doublons, qualité et plages.

- Séparation visuelle brute/normalisée/réconciliée.

- Chronologie avec événements et états d’équipement.

- Comparaison mesure/modèle et résidus.

- Export des anomalies et décisions de correction.

# 9. Administration

| Écran | Fonctions |

| Utilisateurs/rôles | Inviter, désactiver, scopes et MFA |

| Catalogues | Pompes, matériaux, fluides et modèles approuvés |

| Standards/règles | Éditions, paramètres, validation et activation |

| Templates | Rapports, logos, langues et versions |

| Jobs | Files, erreurs, retry et quotas |

| Audit | Actions, sécurité, exports et approbations |

| Sauvegardes | État, historique et test de restauration |

| Connecteurs futurs | Endpoints, certificats, tags et santé |



# 10. Catalogue des graphiques

| Graphique | Axes/couches | Usage |

| Profil hydraulique | x : chainage ; y : altitude/charge ; pression secondaire | Pipeline |

| Pression vs distance | pression, MAOP/minimum, zones et stations | Vérification |

| Courbe pompe-réseau | Q-H, points fabricant, operating point | Sélection |

| Rendement/puissance/NPSH | Q vs courbes multiples | Enveloppe pompe |

| Comparaison scénarios | barres/radar contrôlé/table | Décision |

| Niveaux de bacs | temps vs niveaux et seuils | Transfert |

| Débit/pression transfert | temps vs variables | Dynamique |

| Bilan matière | entrées/sorties/stock/écart | Comptage |

| Séries SCADA futures | temps, qualité, événements | Analyse |

| Carte compresseur future | débit corrigé/rapport, surge/choke | Gaz |



# 11. Catalogue des rapports

| Code | Rapport | Phase |

| RPT-01 | Fiche projet et hypothèses | MVP |

| RPT-02 | Note de calcul hydraulique | MVP |

| RPT-03 | Comparaison de scénarios | MVP |

| RPT-04 | Rapport station/pompes | MVP |

| RPT-05 | Simulation de transfert | MVP |

| RPT-06 | Bilan matière | MVP |

| RPT-07 | Qualité des données | V1 |

| RPT-08 | Calibration mesure-modèle | V1 |

| RPT-09 | Transitoire/coup de bélier | V2 |

| RPT-10 | Transport multiproduit | V2 |

| RPT-11 | Gazoduc/compresseurs | V4 |

| RPT-12 | Alerte et enquête fuite | V5 |

| RPT-13 | Validation scientifique | Toutes |

| RPT-14 | Audit et configuration | Toutes |



# 12. Structure de la note de calcul hydraulique

- Page de garde, contrôle du document et approbations.

- Objet, périmètre, limites et référentiels.

- Description du système et schéma.

- Données d’entrée, unités, sources et qualité.

- Hypothèses et modèles scientifiques.

- Méthode numérique, tolérances et convergence.

- Résultats globaux et détaillés.

- Stations et pompes.

- Profils et graphiques.

- Contrôles, violations, avertissements et marges.

- Conclusion et recommandations.

- Annexes : tables, empreintes, versions et logs résumés.

# 13. Structure du rapport de transfert

- Bac source/destination, produit, volume et responsables.

- État initial : niveaux, volumes, températures et disponibilités.

- Chemin : lignes, vannes, filtres, pompe et compteurs.

- Calcul : débit, pression, NPSH, énergie et durée.

- Chronologie projetée et seuils de niveau.

- Positions/états requis, présentés comme aide et non commande.

- Risques et conditions d’arrêt.

- Bilan prévu puis bilan réel si données importées.

- Écarts, commentaires et approbation.

# 14. Alertes, avertissements et erreurs

| Niveau | Présentation | Exemple |

| Info | Ne bloque pas | Interpolation utilisée |

| Avertissement | Résultat disponible mais à examiner | Propriété extrapolée |

| Critique | Scénario non approuvable | NPSH insuffisant ou pression dépassée |

| Erreur données | Calcul non lancé | Diamètre absent |

| Échec numérique | Pas de résultat valide | Non-convergence |

| Sécurité | Action interdite | Permission ou connecteur write |



# 15. Accessibilité et impression

- Contraste suffisant, focus visible et navigation clavier.

- Texte alternatif pour figures et descriptions tabulaires.

- Unités et symboles lisibles sans dépendre de la couleur.

- Tables avec en-têtes et pagination correcte.

- Rapports A4, marges stables, graphiques vectoriels ou haute résolution.

- Numérotation, titres et références cohérents.

- Langage clair en français et glossaire technique.

- Version sombre éventuelle uniquement si elle ne compromet pas l’impression.

# Sources et références

- D03/D04 - Processus et fonctions.

- D05 - Qualité et accessibilité.

- D09 - Données.

- D19 sert de base aux maquettes UX et templates de rapports.

Fin du document