Plateforme de transport et de stockage des hydrocarbures

D17

Roadmap complète jusqu’au produit final

Évolution du MVP vers la plateforme industrielle et le jumeau numérique

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec validation métier et scientifique |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D17 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Vision de progression

- Phases

- Calendrier indicatif

- Produits par version

- Capacités organisationnelles

- Données et pilotes

- Partenariats

- Modèle commercial

- Indicateurs

- Décisions de passage

- Risques long terme

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Vision de progression

La plateforme doit évoluer par niveaux de confiance. Chaque nouvelle capacité repose sur les moteurs validés auparavant. Le chemin recommandé va de l’ingénierie hors ligne vers l’analyse de données, puis la simulation dynamique, la connexion en lecture seule, le gaz et enfin le jumeau numérique et la détection de fuite.

| Niveau | Positionnement | Confiance requise |

| N0 | Prototype scientifique | Tests unitaires et cas analytiques |

| N1 | MVP ingénierie liquide | Validation système et rapports |

| N2 | Produit dépôt/pipeline hors ligne | Pilotes utilisateurs et données réelles |

| N3 | Analyse industrielle en lecture seule | Sécurité OT et qualité des données |

| N4 | Gaz et transitoires | Benchmarks spécialisés et experts |

| N5 | Jumeau numérique/LD | Performance opérationnelle mesurée |

| N6 | Plateforme industrielle multi-sites | HA, support, conformité et gouvernance |



# 2. Phases de la roadmap

| Phase | Fenêtre indicative | Objectif | Livrable |

| Phase 0 | 0-3 mois | POC scientifique et fondations | Noyau hydraulique simple, architecture et validation initiale |

| Phase 1 | 3-14 mois | MVP liquide | Pipeline, stations, scénarios, bacs, transferts, rapports |

| Phase 2 | 12-20 mois | Pilote et produit V1 | Calibration, UX, sécurité, première installation |

| Phase 3 | 18-28 mois | Data analytics | Historique, qualité, comparaison, prévisions et maintenance |

| Phase 4 | 24-38 mois | Multiproduits et transitoires | Lots, mélanges, MOC, incidents |

| Phase 5 | 32-44 mois | Intégration SCADA | Passerelle, historian, quasi temps réel |

| Phase 6 | 36-54 mois | Gaz et compression | Réseaux gaz, compresseurs, line-pack, optimisation |

| Phase 7 | 48-66 mois | Fuite et jumeau numérique | RTTM, estimation d’état, détection hybride |

| Phase 8 | 60 mois et + | Industrialisation | Multi-sites, HA, simulateur, support et certification |



| Nature du calendrier Les phases se chevauchent uniquement si l’équipe s’agrandit ou si des partenaires prennent en charge des lots. Avec deux développeurs seulement, la durée séquentielle complète est plutôt de quatre à six ans. |



# 3. Versions produit

| Version | Contenu majeur | Public cible |

| 0.1 | Bibliothèque hydraulique et CLI | Équipe/R&D |

| 0.5 | Première verticale web pipeline simple | Démonstration interne |

| 1.0 MVP | Pipeline liquide, stations, bacs et scénarios | Bureaux d’études et pilotes |

| 1.5 | Calibration, analyses, sécurité pilote | Premier client pilote |

| 2.0 | Multiproduits et transitoires liquides | Exploitants pipeline |

| 2.5 | SCADA read-only et historique | Sites opérationnels |

| 3.0 | Gazoduc et compression | Opérateurs gaz |

| 4.0 | RTTM et détection de fuite | Opérateurs critiques |

| 5.0 | Jumeau numérique multi-sites et formation | Groupes industriels |



# 4. Capacités fonctionnelles par phase

| Capacité | MVP | V2 | V3 | V4+ |

| Liquide stationnaire | Complet ciblé | Amélioré | Temps réel | Multi-sites |

| Réservoir/transfert | Complet ciblé | Planning | Temps réel | Optimisation globale |

| Optimisation pompes | Énumération/simple | MINLP ciblé | MPC | Multi-objectifs |

| Multiproduits | Non | Oui | Temps réel | Planification |

| Transitoires | Non | Oui | Calibration | Formation |

| Historique | Fichiers | Analytics | Historian/SCADA | Data lake |

| Gaz | Non | POC | Oui | Temps réel |

| Fuite | Non | Recherche | Pilote | Programme opérationnel |

| Aide à la décision | Indicateurs explicables | Analyses avancées | Recommandations contrôlées | Explications détaillées |



# 5. Évolution de l’équipe

| Étape | Équipe minimale recommandée |

| MVP | 2 développeurs + référent métier + expert ponctuel |

| Premier pilote | 2 développeurs + ingénieur pipeline/dépôt à temps significatif + DevOps ponctuel |

| Transitoires/gaz | Ajouter 1 ingénieur numérique/thermofluides ou partenaire académique |

| SCADA/OT | Ajouter/intégrer 1 spécialiste automatisme/cybersécurité |

| Produit commercial | Support client, QA, produit et sécurité |

| Détection de fuite | Équipe multidisciplinaire : hydraulique, data, instrumentation et exploitation |



# 6. Données et sites pilotes

| Pilote | But | Données minimales |

| Pilote A - Étude hors ligne | Valider hydraulique et UX | Profil, conduites, pompes, mesures ponctuelles |

| Pilote B - Dépôt | Valider bacs/transferts | Barémages, mouvements, compteurs, niveaux |

| Pilote C - Historique | Analytics et calibration | Plusieurs mois de pression/débit/états |

| Pilote D - Transitoire | Valider dynamique | Événement instrumenté ou test contrôlé |

| Pilote E - Gaz | Réseau et compresseur | Composition, cartes, pression, température, demande |

| Pilote F - Fuite | Performance LDS | Essais contrôlés ou données labellisées |



# 7. Partenariats nécessaires

- Université ou laboratoire pour méthodes transitoires, gaz et validation indépendante.

- Bureau d’études ou opérateur pour cas réels et expertise normative.

- Fabricants de pompes/compresseurs pour courbes et limites.

- Intégrateur SCADA/cybersécurité pour la passerelle industrielle.

- Laboratoire de métrologie pour bilans et incertitudes.

- Autorités et organismes de normalisation pour le cadre local.

- Assureur/auditeur HSE pour la compréhension des attentes de risque.

# 8. Modèles commerciaux possibles

| Modèle | Avantages | Contraintes |

| Licence locale par site | Adapté aux données sensibles | Installation et support |

| Abonnement cloud privé | Mises à jour centralisées | Connectivité et souveraineté |

| SaaS pour bureaux d’études | Accès simple et mutualisé | Isolation et tarification |

| Licence académique | Adoption et formation | Support limité |

| Services d’étude/calibration | Revenus précoces et connaissance métier | Dépendance au temps humain |

| OEM/API | Intégration dans une offre tierce | Contrats, SLA et licences |



# 9. Indicateurs de maturité

| Axe | Indicateurs |

| Science | Nombre de modèles validés, couverture des cas, écarts |

| Produit | Utilisateurs actifs, durée de création d’un cas, adoption |

| Fiabilité | Disponibilité, erreurs, temps de calcul, non-convergences |

| Données | Complétude, qualité, latence, calibration |

| Sécurité | Vulnérabilités, incidents, restauration, conformité |

| Business | Pilotes, conversion, revenus récurrents, coût support |

| Équipe | Bus factor, documentation, dette technique, vélocité |

| Impact | Énergie économisée, temps d’étude réduit, incidents évités |



# 10. Gates de passage

| Passage | Conditions obligatoires |

| POC → MVP | Équations principales validées et architecture stable |

| MVP → Pilote | Recette D04/D05, sécurité, restauration et documentation |

| Pilote → V1 commerciale | Écarts acceptables, support et contrats |

| Historique → SCADA | Architecture OT approuvée et lecture seule qualifiée |

| Stationnaire → Transitoire | Benchmarks MOC et expertise disponibles |

| Liquide → Gaz | Propriétés, compresseurs et cas indépendants validés |

| Analytics → LDS | Données labellisées, métriques API 1175 et procédures opérateur |

| Site unique → Multi-sites | Isolation, HA, supervision et capacité support |



# 11. Risques long terme

| Risque | Réponse stratégique |

| Vouloir remplacer tous les logiciels spécialisés | Se positionner comme plateforme intégratrice et d’aide à la décision |

| Responsabilité liée aux résultats | Contrats, validation, limites et assurance |

| Données clients inaccessibles | Pilotes progressifs et données synthétiques ouvertes |

| Dépendance à deux personnes | Documentation, recrutement et partenariats |

| Normes évolutives | Moteur de règles et veille |

| Licences open source | Audit, adapters et alternatives |

| Complexité OT | Partenaire spécialisé et séparation réseau |

| Faux positifs de fuite | Approche hybride, procédures et mesure continue des performances |



# Sources et références

- D16 - Plan MVP.

- D20 - Pilote.

- D08/D14/D15 - Normes, open source et sécurité.

- Roadmap indicative à réviser trimestriellement selon ressources et partenaires.

Fin du document