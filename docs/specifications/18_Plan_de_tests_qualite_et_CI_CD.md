Plateforme de transport et de stockage des hydrocarbures

D18

Plan de tests, qualité et CI/CD

Stratégie de tests, revues, automatisation, releases et exploitation

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec validation métier et scientifique |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D18 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Objectifs qualité

- Pyramide de tests

- Tests scientifiques

- Tests backend

- Tests frontend

- Tests données

- Sécurité

- Performance

- CI

- CD

- Releases

- Environnements

- Gestion anomalies

- Métriques

- Checklists

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Objectifs qualité

- Empêcher les régressions scientifiques et fonctionnelles.

- Rendre chaque release reproductible et installable.

- Détecter tôt les erreurs d’unités, de données et de topologie.

- Sécuriser les migrations et les dépendances.

- Fournir des preuves de validation adaptées à un logiciel d’ingénierie.

- Maintenir une qualité réaliste pour une équipe de deux développeurs.

# 2. Pyramide de tests

| Niveau | Part cible | Contenu |

| Unitaires | 55-65 % | Formules, unités, propriétés, règles et utilitaires |

| Composants | 15-20 % | Conduite, pompe, réseau, bac et repositories |

| Intégration | 10-15 % | API + DB + worker + stockage |

| E2E | 5-10 % | Parcours utilisateur critiques |

| Scientifiques/benchmarks | Transversal | Cas D10 figés et rapports |

| Manuels ciblés | Transversal | UX, graphiques, installation et métier |



# 3. Tests du noyau scientifique

| Famille | Exemples |

| Unités | Conversions, dimension, absolu/manométrique, température |

| Propriétés | Interpolation, extrapolation, limites et sources |

| Hydraulique | Re, λ, pertes, signes et extrêmes |

| Pompes | Fit, série/parallèle, affinité, NPSH, enveloppes |

| Réseau | Conservation, conditions limites, jacobienne, convergence |

| Réservoirs | Barémage, inversion, intégration et événements de niveau |

| Optimisation | Faisabilité, objectif, énumération exhaustive de contrôle |

| Résilience | NaN, infini, valeur négative, plage impossible |

| Régression | Golden cases versionnés de D10 |

| Propriété-based | Invariants de masse, monotonie et symétrie |



# 4. Backend et API

| Test | Outil/cible |

| Services métier | pytest, fixtures et DB transactionnelle |

| API | TestClient/httpx, schémas et permissions |

| Migrations | Upgrade depuis version N-1 et base vide |

| Concurrence | Version optimiste, idempotence et jobs |

| Fichiers | Upload, hash, limites, types et reprise |

| Worker | Succès, échec, annulation, retry et timeout |

| Rapports | Contenu, hash, permissions et rendu visuel |

| Audit | Événement présent pour actions sensibles |



# 5. Frontend

| Niveau | Contenu |

| Unitaire | Formatage unités, composants critiques, validation |

| Composant | Formulaires, tableaux, graphiques et états erreur |

| Contrat | Types générés/OpenAPI et mocks réalistes |

| E2E | Créer projet, importer réseau, calculer, comparer, rapport |

| Visuel | Captures de régression des pages principales |

| Accessibilité | Navigation clavier, labels, contraste et lecteurs |

| Navigateurs | Chrome/Edge/Firefox récents |

| Performance | Taille bundle et rendu de grands tableaux/graphes |



# 6. Tests des imports et données

- Encodages, séparateurs, point/virgule décimal et lignes vides.

- Colonnes manquantes, supplémentaires, ambiguës et doublonnées.

- Unités incompatibles ou inconnues.

- Très gros fichier, interruption et reprise.

- Horodatages, fuseaux, doublons et ordre.

- Barémage non monotone et profil non ordonné.

- Round-trip export/import JSON et GeoJSON.

- Protection contre formules dangereuses dans CSV/XLSX exportés.

# 7. Sécurité

| Contrôle | Fréquence |

| SAST Python/TypeScript | Chaque pull request |

| Scan dépendances/CVE | Chaque pull request + quotidien |

| Scan licences/SBOM | Chaque release |

| Scan images conteneur | Chaque build |

| Secrets | Pré-commit et CI |

| DAST API/web | Release candidate et périodique |

| Tests RBAC | Automatiques |

| Pentest externe | Avant pilote industriel ou selon contrat |

| Revue architecture OT | Avant toute connexion |



# 8. Performance et robustesse

| Benchmark | Mesure |

| Réseau 100/1 000/10 000 tronçons | Temps, mémoire, itérations |

| 100 configurations de pompes | Temps total et parallélisme |

| Import 1M échantillons | Débit, mémoire et reprise |

| 25 utilisateurs | P95 API et erreurs |

| Rapport volumineux | Durée et taille |

| Longue tâche interrompue | Intégrité et reprise |

| Base restaurée | RTO/RPO et cohérence |

| Dégradation dépendance externe | Timeout et message |



# 9. Pipeline CI

| Étape | Actions |

| 1. Checkout | Version et sous-modules contrôlés |

| 2. Lint/format | Ruff/Black ou équivalent, ESLint/Prettier |

| 3. Typage | mypy/pyright, TypeScript |

| 4. Unit tests | Python et frontend en parallèle |

| 5. Integration | PostgreSQL/PostGIS, worker, stockage |

| 6. Scientific | Golden cases rapides |

| 7. Security | Secrets, SAST, CVE, licences |

| 8. Build | Images conteneur avec tags immuables |

| 9. SBOM/signature | Inventaire et signature du build |

| 10. Publish | Registry après branche protégée |

| 11. Deploy test | Migration + smoke tests |

| 12. Report | Couverture, qualité, artefacts |



# 10. Livraison continue

| Environnement | Déclencheur | Contrôles |

| dev partagé | Merge branche principale | Migration automatique + smoke |

| staging | Tag release candidate | Tests E2E, sécurité et données |

| pilot | Approbation manuelle | Sauvegarde, fenêtre, rollback |

| production futur | Change approuvé | Runbook, monitoring et validation post-déploiement |



# 11. Stratégie de release

- Versionnement sémantique de l’application et version indépendante du moteur scientifique.

- Release notes avec changements, migrations, risques et cas de validation.

- Tags Git signés et images immuables.

- Support d’au moins la version courante et précédente pendant la phase pilote.

- Hotfix avec test ciblé et réintégration sur la branche principale.

- Aucune modification manuelle en production non reproduite dans le code/configuration.

- Possibilité de rollback applicatif ; migrations destructives différées.

# 12. Données de test et environnements

| Jeu | Usage | Confidentialité |

| Synthétique simple | Unitaires et E2E | Public interne |

| Cas académiques fournis | Validation scientifique | Droits et sources conservés |

| Cas anonymisé pilote | Staging et calibration | Accès restreint |

| Données réelles | Pilote/production | Politique opérateur |

| Cas sécurité | Tests attaques/erreurs | Aucune donnée réelle |

| Golden reports | Régression documentaire | Données synthétiques |



# 13. Gestion des anomalies

| Sévérité | Définition | SLA interne indicatif |

| S0 | Risque sécurité/personnes ou corruption critique | Arrêt release, traitement immédiat |

| S1 | Résultat scientifique faux ou accès non autorisé | Priorité maximale avant usage |

| S2 | Fonction majeure indisponible sans contournement | Sprint courant/prochain |

| S3 | Défaut avec contournement ou UX importante | Planifié |

| S4 | Mineur/cosmétique | Backlog |



# 14. Métriques qualité

| Métrique | Cible MVP |

| Couverture noyau scientifique | ≥ 80 % + cas D10 |

| Couverture globale | ≥ 65 % utile, sans jeu artificiel |

| Défauts S0/S1 ouverts à release | 0 |

| Vulnérabilités critiques | 0 |

| Tests instables | < 1 % ; correction prioritaire |

| Temps CI principal | < 15 min idéal, suite complète nocturne |

| Réussite restauration | 100 % des exercices |

| Régression golden cases | 0 non expliquée |

| Dette technique | Revue à chaque jalon |



# 15. Checklist release MVP

- Toutes les exigences MUST acceptées ou dérogations signées.

- Cas D10 réussis et rapport archivé.

- Migration depuis la version précédente testée.

- Sauvegarde/restauration testées.

- Scan sécurité et licences sans blocant.

- Guide installation, administration et utilisateur à jour.

- Images et artefacts signés/versionnés.

- Rapports Word/PDF rendus et inspectés.

- Démonstration de recette réalisée.

- Plan de support et rollback disponible.

# Sources et références

- D05 - Exigences non fonctionnelles.

- D10 - Validation scientifique.

- D15 - Sécurité.

- D16 - Plan MVP.

Fin du document