Plateforme de transport et de stockage des hydrocarbures

D05

Exigences non fonctionnelles

Performance, sécurité, fiabilité, maintenabilité et qualité

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec validation métier et scientifique |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D05 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Principes

- Performance

- Disponibilité

- Sécurité

- Intégrité scientifique

- Utilisabilité

- Portabilité

- Maintenabilité

- Observabilité

- Données

- Conformité

- Critères de recette

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Principes

Les exigences non fonctionnelles définissent la qualité attendue du système. Elles sont mesurables, testables et adaptées à une équipe de deux développeurs. Les cibles du MVP privilégient la robustesse, la traçabilité et la simplicité d’exploitation plutôt qu’une architecture distribuée prématurée.

# 2. Performance et capacité

| ID | Exigence | Priorité | Critère d’acceptation |

| NFR-PERF-001 | Le calcul stationnaire d’un cas de 1 000 tronçons doit terminer en moins de 10 secondes sur le serveur de référence. | MUST | Percentile 95 mesuré. |

| NFR-PERF-002 | Une comparaison de 100 configurations simples doit terminer en moins de 120 secondes. | MUST | Benchmark automatisé. |

| NFR-PERF-003 | L’interface doit répondre en moins de 2 secondes pour les opérations courantes hors calcul. | MUST | Tests navigateur. |

| NFR-PERF-004 | Les calculs longs doivent s’exécuter en tâche de fond sans bloquer l’API. | MUST | File de tâches et statut. |

| NFR-PERF-005 | Le système doit supporter au moins 25 utilisateurs simultanés au MVP. | SHOULD | Test de charge. |



# 3. Disponibilité, continuité et sauvegarde

| ID | Exigence | Priorité | Critère d’acceptation |

| NFR-AVL-001 | Le MVP doit viser 99 % de disponibilité hors maintenance planifiée. | SHOULD | Suivi mensuel. |

| NFR-AVL-002 | Les données validées doivent être sauvegardées quotidiennement et avant migration. | MUST | Journal et test de sauvegarde. |

| NFR-AVL-003 | RPO cible : 24 h au MVP ; RTO cible : 8 h. | MUST | Exercice de restauration. |

| NFR-AVL-004 | Un calcul interrompu ne doit pas corrompre le projet ou les résultats précédents. | MUST | Test d’arrêt forcé. |

| NFR-AVL-005 | Les exports doivent être régénérables depuis les données versionnées. | MUST | Reproduction bit-à-bit lorsque possible. |



# 4. Sécurité et contrôle d’accès

| ID | Exigence | Priorité | Critère d’acceptation |

| NFR-SEC-001 | Authentification robuste et mots de passe hachés avec algorithme moderne. | MUST | Audit technique. |

| NFR-SEC-002 | RBAC par organisation, site, projet et action. | MUST | Tests d’accès négatifs. |

| NFR-SEC-003 | Chiffrement TLS en transit et chiffrement des secrets au repos. | MUST | Configuration vérifiée. |

| NFR-SEC-004 | Aucun secret ne doit être stocké dans le dépôt de code. | MUST | Scan CI. |

| NFR-SEC-005 | Les connexions SCADA futures doivent être en lecture seule et isolées. | MUST | Architecture et test. |

| NFR-SEC-006 | Les journaux ne doivent pas contenir de secrets ni de données sensibles inutiles. | MUST | Revue des logs. |

| NFR-SEC-007 | Les dépendances doivent être scannées et mises à jour selon une politique documentée. | MUST | Rapport automatique. |



# 5. Intégrité scientifique et reproductibilité

| ID | Exigence | Priorité | Critère d’acceptation |

| NFR-SCI-001 | Chaque calcul doit enregistrer les entrées, tolérances, version du moteur et méthode. | MUST | Trace complète. |

| NFR-SCI-002 | Les calculs doivent être déterministes à entrées identiques, sauf algorithme explicitement stochastique. | MUST | Test de répétabilité. |

| NFR-SCI-003 | Les équations et corrélations doivent avoir une source, un domaine de validité et des tests. | MUST | Registre scientifique. |

| NFR-SCI-004 | Les extrapolations, approximations et valeurs par défaut doivent être signalées. | MUST | Avertissements dans rapport. |

| NFR-SCI-005 | Aucun résultat ne doit être déclaré valide si le bilan de masse ou la convergence dépasse la tolérance. | MUST | Blocage documenté. |



# 6. Utilisabilité et accessibilité

| ID | Exigence | Priorité | Critère d’acceptation |

| NFR-UX-001 | L’interface doit être disponible en français et préparée pour l’internationalisation. | MUST | Catalogue de traductions. |

| NFR-UX-002 | Les unités doivent toujours être visibles avec les valeurs. | MUST | Audit écran/rapport. |

| NFR-UX-003 | Les erreurs doivent expliquer la cause et l’action corrective. | MUST | Revue de messages. |

| NFR-UX-004 | Les tableaux et graphiques doivent être lisibles sur écran 1366x768 minimum. | MUST | Test responsive. |

| NFR-UX-005 | Les écrans principaux doivent respecter les principes WCAG 2.2 AA autant que possible. | SHOULD | Audit accessibilité. |

| NFR-UX-006 | Un utilisateur formé doit créer et calculer un cas simple en moins de 30 minutes. | SHOULD | Test utilisateur. |



# 7. Portabilité et déploiement

| ID | Exigence | Priorité | Critère d’acceptation |

| NFR-DEP-001 | Déploiement conteneurisé sur Linux, local ou cloud privé. | MUST | Procédure automatisée. |

| NFR-DEP-002 | Le navigateur doit être le client principal, sans installation lourde. | MUST | Test Chrome/Edge/Firefox récents. |

| NFR-DEP-003 | Le système doit fonctionner sans Internet après installation locale. | MUST | Test réseau isolé. |

| NFR-DEP-004 | Les migrations de base doivent être versionnées et réversibles lorsque possible. | MUST | Test upgrade/downgrade. |

| NFR-DEP-005 | Les configurations doivent être externalisées par environnement. | MUST | Aucun changement de code. |



# 8. Maintenabilité et architecture

| ID | Exigence | Priorité | Critère d’acceptation |

| NFR-MNT-001 | Architecture monolithe modulaire au MVP, avec frontières de domaine explicites. | MUST | Analyse des dépendances. |

| NFR-MNT-002 | Couverture minimale de tests : 80 % pour le noyau de calcul, 65 % global. | MUST | Rapport CI. |

| NFR-MNT-003 | Typage statique Python et TypeScript sans erreurs critiques. | MUST | mypy/pyright et tsc. |

| NFR-MNT-004 | Documentation API générée et exemples exécutables. | MUST | OpenAPI disponible. |

| NFR-MNT-005 | Les modules scientifiques doivent être utilisables sans l’interface web. | MUST | Tests de bibliothèque. |

| NFR-MNT-006 | La complexité et les dettes techniques doivent être revues à chaque version. | SHOULD | Registre de dette. |



# 9. Observabilité

| ID | Exigence | Priorité | Critère d’acceptation |

| NFR-OBS-001 | Logs structurés avec corrélation par requête et calcul. | MUST | Recherche d’un incident de bout en bout. |

| NFR-OBS-002 | Mesures de durée, erreurs, files de calcul, CPU, mémoire et base. | MUST | Tableau de bord technique. |

| NFR-OBS-003 | Journal scientifique distinct du journal applicatif. | MUST | Trace des itérations et résidus. |

| NFR-OBS-004 | Alertes sur échec de sauvegarde, saturation et erreurs répétées. | SHOULD | Test d’alerte. |



# 10. Données, confidentialité et rétention

| ID | Exigence | Priorité | Critère d’acceptation |

| NFR-DATA-001 | Les données d’une organisation doivent être isolées logiquement et contrôlées. | MUST | Tests multi-tenant logiques. |

| NFR-DATA-002 | Les suppressions doivent être logiques avant purge contrôlée. | MUST | Restauration pendant délai. |

| NFR-DATA-003 | Les politiques de rétention doivent être configurables par type de donnée. | SHOULD | Règle appliquée en test. |

| NFR-DATA-004 | Les données historiques doivent conserver horodatage source et qualité. | MUST | Schéma D09 respecté. |

| NFR-DATA-005 | Les exports doivent respecter les permissions et être journalisés. | MUST | Audit export. |



# 11. Conformité et normes

- Le logiciel doit permettre de sélectionner et versionner le référentiel applicable.

- L’équipe ne doit pas recopier intégralement les normes protégées ; elle implémente des règles issues de textes acquis légalement.

- Toute règle normative doit être approuvée par un expert avant activation en production.

- Les éditions et interprétations doivent être revues au début de chaque projet réel.

- La conformité locale et l’évaluation environnementale restent sous responsabilité du maître d’ouvrage et des autorités.

# 12. Recette non fonctionnelle

| Domaine | Test de sortie MVP | Seuil de réussite |

| Performance | Benchmark 1 000 tronçons | P95 < 10 s |

| Robustesse | 100 cas invalides/non convergents | 100 % diagnostiqués sans corruption |

| Sécurité | Scan SAST, dépendances et RBAC | Aucune vulnérabilité critique ouverte |

| Restauration | Restauration d’une sauvegarde complète | RPO/RTO respectés |

| Reproductibilité | 10 répétitions de cas de référence | Résultats identiques aux tolérances |

| Portabilité | Installation sur deux environnements | Procédure sans modification de code |

| Qualité | Tests automatiques | Seuils de couverture atteints |



# Sources et références

- D04 - Cahier des charges fonctionnel.

- D11 à D18 - Architecture, sécurité, développement et qualité.

- IEC 62443, IEC 61511 et bonnes pratiques OWASP utilisées comme guides, selon périmètre.

Fin du document