Plateforme de transport et de stockage des hydrocarbures

D20

Dossier pilote et protocole de validation industrielle

Sélection du site, collecte, calibration, essais, acceptation et retour d’expérience

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D20 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- But

- Critères de sélection

- Gouvernance

- Périmètre pilote

- Données requises

- Cybersécurité

- Préparation

- Campagne de tests

- Calibration

- Critères acceptation

- Gestion incidents

- Livrables

- Planning

- Go/No-Go

- Trame site

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. But du pilote

Le pilote transforme un MVP validé sur cas synthétiques en un outil évalué sur une installation réelle ou anonymisée. Il mesure l’exactitude, la robustesse, l’utilisabilité, la qualité des données et la valeur opérationnelle sans transférer la responsabilité de conduite à la plateforme.

| Statut du document La trame est complète, mais les champs site, équipements, données, autorités, tolérances et responsables doivent être remplis avec l’opérateur avant exécution. |



# 2. Critères de sélection d’un site pilote

| Critère | Minimum souhaité |

| Périmètre | Pipeline liquide ou dépôt avec limites claires |

| Disponibilité données | Plans, profils, fiches pompes, barémages et historiques |

| Instrumentation | Pressions/débits/niveaux suffisamment fiables |

| Référent métier | Ingénieur disponible pour revues et essais |

| Sécurité | Possibilité de travailler hors contrôle et en lecture seule |

| Cas d’exploitation | Modes normal et au moins un mode dégradé connu |

| Droits | Autorisation d’utiliser des données anonymisées et de comparer |

| Valeur | Problème concret : énergie, capacité, transferts ou qualité |

| Complexité | Assez représentatif mais pas le réseau le plus critique pour un premier pilote |



# 3. Gouvernance et responsabilités

| Rôle | Responsabilité |

| Sponsor opérateur | Autorise le pilote et arbitre |

| Chef de pilote | Plan, risques, accès, réunions et livrables |

| Ingénieur pipeline/dépôt | Données, hypothèses, validation des résultats |

| Équipe logiciel | Configuration, calcul, support et corrections |

| OT/cybersécurité | Architecture, accès et surveillance |

| HSE | Revue des scénarios et communication des limites |

| Métrologie/comptage | Capteurs, incertitudes et bilans |

| Utilisateur final | Essais UX et retour |

| Expert indépendant souhaité | Revue scientifique et conclusion |



# 4. Périmètre pilote recommandé

| Élément | Cible |

| Pipeline | 1 ligne principale, 2 à 5 stations ou un réseau de dépôt représentatif |

| Pompes | Au moins deux configurations et une pompe de secours |

| Réservoirs | 2 à 10 bacs avec barémages pour le pilote dépôt |

| Produits | 1 à 3 produits avec propriétés validées |

| Historique | 4 à 12 semaines, incluant plusieurs régimes |

| Scénarios | Normal, débit différent, équipement indisponible, transfert |

| Connexion | Fichiers d’abord ; historian/OPC UA read-only en option après revue |

| Utilisateurs | 3 à 10 utilisateurs pilotes |

| Durée | 8 à 16 semaines après préparation des données |



# 5. Données requises

| Domaine | Données | Validation |

| Conduites | Tracé, profil, longueur, diamètres, épaisseur, rugosité, matériau, MAOP | Plans/as-built et inspection |

| Stations | Schémas, altitude, collecteurs, limites | Revue ingénieur |

| Pompes | H(Q), η(Q), P(Q), NPSHr, vitesse, moteurs | Fiches fabricant/essais |

| Vannes/filtres | Type, diamètre, K/Cv/Kv, état | P&ID et terrain |

| Produits | ρ(T,p), ν(T), pv(T), température | Laboratoire/opérateur |

| Réservoirs | Barémage, niveaux, capacité, alarmes | Certificat/jaugeage |

| Mesures | Tags, unités, précision, qualité, calibration | Métrologie |

| Opérations | États pompes, vannes, transferts, événements | Journal opérateur |

| Normes | Référentiel et exigences du site | Contrat/autorité |

| Énergie | Puissance, compteur, tarif | Facture/mesure |



# 6. Cybersécurité et données

- Accord de confidentialité et classification des données.

- Anonymisation des noms/coordonnées si nécessaire.

- Aucun accès au SIS/ESD et aucune écriture.

- Architecture approuvée par OT/cybersécurité.

- Comptes temporaires, moindre privilège et journalisation.

- Stockage local ou cloud approuvé par l’opérateur.

- Plan de suppression/restitution en fin de pilote.

- Test de sauvegarde et restauration avant données réelles.

- Procédure d’incident et contacts.

# 7. Préparation des données et baseline

| Étape | Sortie |

| Inventaire | Liste des sources, propriétaires et dates |

| Extraction | Fichiers bruts immuables avec hash |

| Mapping | Tags/équipements/unités/qualités |

| Nettoyage | Règles et transformations versionnées |

| Reconstruction | Topologie et paramètres du site |

| Baseline | Premier modèle calculable et hypothèses |

| Revue | Validation par l’ingénieur du site |

| Gel | Version baseline approuvée pour campagne |



# 8. Campagne de tests

| Test | Description | Preuve |

| PIL-01 | Reproduction d’un régime stable | Pressions/débits mesurés vs simulés |

| PIL-02 | Deuxième débit ou configuration | Capacité de généralisation |

| PIL-03 | Pompe indisponible/ secours | Scénario réel ou historique |

| PIL-04 | Sensibilité rugosité/propriétés | Courbes et paramètres identifiables |

| PIL-05 | Transfert bac-à-bac | Durée, niveaux et bilan |

| PIL-06 | Import de données imparfaites | Rapport de qualité et reprise |

| PIL-07 | Rapport utilisateur | Revue et approbation |

| PIL-08 | Performance et charge | Temps et stabilité |

| PIL-09 | Sécurité/RBAC/audit | Tests négatifs et logs |

| PIL-10 | Restauration | Récupération du pilote |

| PIL-11 | UX | Temps de tâche et retours |

| PIL-12 | Mode hors connexion | Fonctionnement local si exigé |



# 9. Calibration et validation croisée

- Séparer les périodes de calibration et de validation.

- N’ajuster que les paramètres physiquement justifiables : rugosité, biais capteur documenté, coefficient local.

- Imposer des bornes et conserver les valeurs avant/après.

- Éviter de compenser une fuite, une vanne mal positionnée ou un capteur défectueux par une rugosité irréaliste.

- Évaluer biais, RMSE, erreur max, bilan de masse et résidus temporels.

- Tester au moins un régime non utilisé pour la calibration.

- Faire approuver les paramètres calibrés et leur période de validité.

| Métrique | Formulation/usage |

| Biais | Moyenne(simulé - mesuré) |

| MAE | Erreur absolue moyenne |

| RMSE | Sensibilité aux grandes erreurs |

| Erreur max | Vérification des limites |

| Bilan matière | Entrées - sorties - stock |

| Couverture incertitude | Mesure dans l’intervalle prévu |

| Stabilité paramètres | Variation entre périodes |

| Faux avertissements | Nombre et cause |



# 10. Critères d’acceptation du pilote

| Domaine | Critère proposé |

| Science | Tolérances convenues atteintes sur les régimes de validation ou écarts expliqués |

| Masse | Bilan conforme aux incertitudes du site |

| Robustesse | Aucune corruption et diagnostics exploitables |

| Performance | Temps compatible avec le workflow |

| UX | Utilisateurs réalisent les tâches prioritaires avec formation raisonnable |

| Traçabilité | Toutes les entrées, changements et résultats sont auditables |

| Sécurité | Aucun flux non autorisé, tests et sauvegarde réussis |

| Valeur | Au moins un bénéfice mesurable ou décision améliorée |

| Limites | Cas non couverts clairement documentés |

| Go-live | Plan de correction et de support accepté |



# 11. Gestion des incidents et changements

| Événement | Action |

| Résultat incohérent | Suspendre l’usage, conserver preuves, analyser |

| Donnée erronée | Corriger dans une nouvelle version, ne pas écraser |

| Vulnérabilité | Contenir, notifier, corriger et revalider |

| Changement site | Créer nouvelle version/baseline |

| Norme modifiée | Revue de rule set et impact |

| Capteur indisponible | Marquer qualité et appliquer stratégie approuvée |

| Non-convergence | Diagnostic, cas simplifié et ticket |

| Demande de nouvelle fonction | Évaluer hors périmètre et roadmap |



# 12. Livrables du pilote

- Charte et périmètre signés.

- Architecture de sécurité approuvée.

- Dictionnaire des données et rapport de qualité.

- Modèle baseline et paramètres calibrés.

- Dossier des tests PIL-01 à PIL-12.

- Rapport d’écarts et limitations.

- Rapport de valeur métier et retours utilisateurs.

- Plan de corrections et backlog.

- Décision Go/No-Go et conditions de production.

- Plan de support, sauvegarde et réversibilité.

# 13. Planning indicatif du pilote

| Semaine | Activités |

| 1-2 | Cadrage, sécurité, accès et inventaire |

| 3-4 | Extraction, mapping, nettoyage et modèle |

| 5-6 | Baseline, revue et corrections |

| 7-9 | Calibration et tests de régimes |

| 10-11 | Transferts/scénarios/UX et sécurité |

| 12 | Rapport intermédiaire et corrections |

| 13-14 | Validation croisée et recette |

| 15 | Formation et test d’autonomie |

| 16 | Rapport final et décision |



# 14. Décision Go/No-Go

| Décision | Condition |

| GO | Critères atteints, risques acceptés et plan support approuvé |

| GO conditionnel | Écarts limités, actions datées et périmètre restreint |

| REWORK | Valeur confirmée mais défauts techniques à corriger avant usage |

| NO-GO | Exactitude, sécurité, données ou valeur insuffisantes |

| RESEARCH | Modèle scientifique non mature ; retour R&D |



# 15. Trame à compléter pour le site

| Champ | Valeur à renseigner |

| Opérateur / site | À confirmer |

| Sponsor / chef pilote | À confirmer |

| Type d’installation | Pipeline liquide / dépôt / combiné |

| Produits | À confirmer |

| Périmètre physique | À confirmer |

| Normes et règles locales | À confirmer officiellement |

| Données disponibles | À inventorier |

| Architecture OT | À documenter |

| Tolérances acceptées | À approuver |

| Période pilote | À planifier |

| Utilisateurs | À nommer |

| Critères de valeur | À quantifier |

| Restrictions de données | À contractualiser |



# Sources et références

- D10 - Validation scientifique.

- D15 - Sécurité et SCADA.

- D16/D17 - Plan MVP et roadmap.

- D20 doit être adapté avec l’opérateur, les autorités et les experts du site.

Fin du dossier pilote - trame à compléter