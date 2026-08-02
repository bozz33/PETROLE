Plateforme de transport et de stockage des hydrocarbures

D08

Référentiel normatif international

Cadre ASME, API, ISO, IEC, ISA et exigences locales

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D08 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Principes

- Hiérarchie

- Pipelines liquides

- Gazoducs

- Pompes et compresseurs

- Réservoirs et terminaux

- Fuites et intégrité

- Sécurité fonctionnelle

- SCADA et cybersécurité

- Mesure et qualité

- Côte d’Ivoire et CEDEAO

- Moteur de règles

- Gestion des éditions

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Principes

| Décision normative La plateforme est fondée sur des standards internationaux reconnus et sur les exigences réglementaires du pays. Les documents russes sont uniquement des références académiques et comparatives. |



Les normes citées ne sont pas toutes applicables simultanément. Le référentiel d’un projet dépend du produit, du type d’installation, du pays, du contrat, de l’opérateur et de la phase du cycle de vie. L’équipe doit acquérir légalement les textes complets nécessaires et vérifier l’édition active avant toute implémentation ou validation contractuelle.

# 2. Hiérarchie des exigences

| Rang | Source | Règle |

| 1 | Lois, décrets, permis et décisions de l’autorité locale | Obligatoire et prioritaire |

| 2 | Exigences contractuelles et cahier des charges de l’opérateur | Obligatoire pour le projet |

| 3 | Codes et normes internationales adoptés | Base technique sélectionnée |

| 4 | Procédures internes approuvées | Complément organisationnel |

| 5 | Méthodes scientifiques validées | Calcul lorsque la norme ne prescrit pas tout |

| 6 | Sources académiques et cas comparatifs | Recherche, formation et vérification |



# 3. Pipelines de liquides

| Référence | Édition/état au 02/08/2026 | Rôle dans la plateforme |

| ASME B31.4 | 2025 | Conception, matériaux, construction, essais, exploitation et maintenance des pipelines liquides et installations associées. |

| ISO 13623 | 2017 + Amd 1:2024 | Systèmes de transport par pipeline ; complément pour CO₂/hydrogène dans l’amendement. |

| API RP 1160 | Édition applicable à confirmer | Gestion de l’intégrité des pipelines de liquides dangereux. |

| ISO 19345-1 | 2019 | Gestion de l’intégrité des pipelines terrestres sur le cycle de vie. |

| API Spec 5L | Édition applicable à confirmer | Spécification des tubes de canalisation. |

| ASME B31G | Édition applicable à confirmer | Évaluation de la résistance restante des conduites corrodées. |



# 4. Gazoducs et systèmes de gaz

| Référence | Édition/état | Usage |

| ASME B31.8 | 2025 | Gazoducs, stations de compression, mesure et régulation, distribution. |

| ASME B31.8S | 2025 | Gestion de l’intégrité des gazoducs. |

| ISO 13623 | 2017 + Amd 1:2024 | Base internationale pipeline selon périmètre. |

| API 617 | 9e éd. | Compresseurs axiaux et centrifuges et expander-compressors. |

| API 618 | 5e éd. au catalogue 2025 | Compresseurs alternatifs. |

| API 614 | 6e éd. | Systèmes de lubrification, étanchéité et auxiliaires. |

| API 670 | 5e éd. | Systèmes de protection des machines. |



# 5. Pompes, essais et équipements rotatifs

| Référence | État | Fonction |

| API 610 | 12e édition | Pompes centrifuges pour pétrole, pétrochimie et gaz. |

| ISO 13709 | Équivalent/adoption liée à API 610 selon édition | Pompes centrifuges ; vérifier la relation exacte de l’édition retenue. |

| ISO 9906 | Édition applicable à confirmer | Essais d’acceptation hydraulique des pompes rotodynamiques. |

| API 682 | 4e édition au catalogue 2025 | Systèmes d’étanchéité d’arbres. |

| API RP 686 | Édition applicable à confirmer | Installation et conception d’installation des machines. |



# 6. Réservoirs, dépôts et terminaux

| Référence | État | Usage |

| API 650 | 14e édition publiée en 2025 | Réservoirs soudés de stockage d’huile. |

| API 653 | Édition applicable à confirmer | Inspection, réparation, modification et reconstruction des réservoirs. |

| API 2350 | 5e édition | Protection contre le débordement des réservoirs pétroliers. |

| API 2000 | 8e édition selon le catalogue de référence | Ventilation normale et d’urgence des réservoirs. |

| API 2610 | Édition applicable à confirmer | Conception, exploitation, maintenance et inspection de terminaux et tank farms. |

| API MPMS | Chapitres applicables | Mesure, jaugeage, correction des volumes, échantillonnage et custody transfer. |

| NFPA 30 | Édition applicable localement | Liquides inflammables et combustibles ; adoption à confirmer. |



# 7. Détection de fuite, surveillance et intégrité

| Référence | Rôle logiciel |

| API RP 1130 | Surveillance informatique des pipelines de liquides (computational pipeline monitoring). |

| API RP 1175 | Gestion du programme de détection de fuite, performances, formation et amélioration. |

| API TR 1149 | Impact des incertitudes de mesure sur la détection des fuites. |

| API RP 1160 / ASME B31.8S | Lien entre détection, risque et gestion de l’intégrité. |

| IEC/ISO applicables aux capteurs | À sélectionner selon la technologie externe : fibre, acoustique, gaz, etc. |



# 8. Sécurité fonctionnelle, alarmes et procédés

| Référence | Usage |

| IEC 61511 | Cycle de vie des systèmes instrumentés de sécurité dans les industries de procédé. |

| IEC 61508 | Base générique de sécurité fonctionnelle des systèmes électriques/électroniques/programmables. |

| ISA-18.2 / IEC 62682 | Gestion du cycle de vie des alarmes de procédés. |

| IEC 60079 | Atmosphères explosives : sélection selon zones et équipements. |

| ISO 31000 | Cadre général de management du risque. |

| IEC 31010 | Techniques d’appréciation du risque. |



| Séparation de sécurité Le MVP reste un outil d’analyse et ne remplace pas un SIS, un ESD ou un automate de contrôle. Aucune commande d’équipement n’est autorisée sans une phase séparée de conception, d’évaluation et de certification. |



# 9. SCADA, communication et cybersécurité

| Référence | Application |

| IEC 62541 - OPC UA | Interopérabilité, modèles d’information, sécurité et abonnements. |

| IEC 60870-5-104 | Téléconduite pour sites distribués, si utilisée par l’opérateur. |

| IEC 62443 | Cybersécurité IACS : zones, conduits, composants, processus et niveaux de sécurité. |

| MQTT 5 / Sparkplug | Messagerie IIoT ; spécification et gouvernance à définir. |

| Modbus TCP/RTU | Protocole terrain, généralement via passerelle et segmentation. |

| NTP/PTP selon architecture | Synchronisation temporelle, indispensable aux historiques et fuites. |



# 10. Qualité, logiciels et données

| Référence/guide | Usage |

| ISO 9001 | Processus qualité de l’organisation, si adopté. |

| ISO/IEC 25010 | Modèle de qualité logicielle. |

| ISO/IEC 27001 | Management de la sécurité de l’information. |

| ISO 80000 | Grandeurs et unités. |

| Guide GUM / JCGM 100 | Expression de l’incertitude de mesure. |

| VIM / JCGM 200 | Vocabulaire international de métrologie. |

| OWASP ASVS/API Security | Référentiel pratique de sécurité applicative, non normatif. |



# 11. Côte d’Ivoire et sous-région

Pour un déploiement en Côte d’Ivoire, le projet doit établir une matrice de conformité locale avant le site pilote. Les sources identifiées incluent le Code pétrolier et ses textes d’application, le Code de l’environnement n° 2023-900 du 23 novembre 2023, les dispositions relatives aux évaluations environnementales et sociales, les installations classées, la métrologie, la sécurité incendie et les exigences de l’autorité chargée des hydrocarbures.

| Niveau | Action requise |

| Côte d’Ivoire | Consulter la Direction générale des hydrocarbures, l’autorité environnementale, CODINORM, la métrologie et la protection civile. |

| Opérateur | Recueillir standards d’entreprise, limites, procédures, architecture OT et règles de reporting. |

| CEDEAO/UEMOA | Prendre en compte spécifications harmonisées des carburants et exigences régionales pertinentes. |

| Projet | Établir la liste des permis, études, autorités, normes contractuelles et responsabilités. |



| Point à confirmer La recherche publique ne remplace pas une consultation officielle. La plateforme doit pouvoir ajouter des règles locales sans les coder en dur dans le moteur physique. |



# 12. Moteur de règles normatives

| Objet | Structure minimale |

| RuleSet | Code, titre, pays, organisme, édition, statut, date d’effet |

| Rule | Identifiant, texte interne synthétique, sévérité, domaine, formule ou contrôle |

| Paramètre | Valeur, unité, source, conditions d’application |

| Résultat de contrôle | Conforme/non conforme/non applicable, marge, justification |

| Trace | Version du rule set et paramètres utilisés |

| Approbation | Auteur technique, relecteur, date et preuve |



# 13. Gestion des éditions et propriété intellectuelle

- Ne pas reproduire intégralement dans la plateforme les textes protégés par droit d’auteur.

- Acheter les standards nécessaires et documenter les droits d’accès de l’équipe.

- Implémenter les contrôles sous forme de règles internes synthétiques et traçables.

- Conserver plusieurs éditions mais n’en activer qu’une par projet et par domaine.

- Prévoir un workflow de revue lors de la publication d’une nouvelle édition ou d’un erratum.

- Marquer toute règle « non validée » comme indisponible pour les rapports approuvés.

- Vérifier l’édition en vigueur au lancement de chaque projet réel.

# Sources et références

| Règle d’utilisation Les titres et éditions sont un inventaire de cadrage. Le texte officiel acquis auprès de l’organisme émetteur reste la source contractuelle. |



- ASME : pages officielles B31.4-2025, B31.8-2025 et B31.8S-2025 consultées en août 2026.

- ISO : ISO 13623:2017 et Amendement 1:2024, catalogue officiel.

- API : catalogue officiel des publications 2025 et pages des standards concernés.

- IEC et ISA : catalogues officiels des normes de sécurité, communication et alarmes.

- Portails officiels de Côte d’Ivoire : hydrocarbures et environnement ; textes régionaux CEDEAO à confirmer par le projet.

Fin du document