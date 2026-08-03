Plateforme de transport et de stockage des hydrocarbures

D06

Catalogue des cas d’usage et scénarios

Cas d’usage métier, modes normaux, dégradés et de secours

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec validation métier et scientifique |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D06 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Convention

- Cas d’usage prioritaires

- Scénarios pipeline

- Scénarios dépôt

- Scénarios données

- Scénarios gaz futurs

- Fiches détaillées

- Matrice de couverture

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Convention

| Élément | Définition |

| Acteur principal | Rôle qui déclenche le cas d’usage. |

| Préconditions | Données et autorisations nécessaires. |

| Flux nominal | Étapes de réussite. |

| Alternatives | Erreurs, contraintes ou branches. |

| Postconditions | État final et données enregistrées. |

| Critère de réussite | Résultat mesurable pour la recette. |



# 2. Catalogue prioritaire

| ID | Cas d’usage | Acteur | Phase |

| UC-001 | Créer un projet et son référentiel | Ingénieur | MVP |

| UC-002 | Importer un profil et construire le réseau | Ingénieur | MVP |

| UC-003 | Créer une fiche produit et ses propriétés | Ingénieur | MVP |

| UC-004 | Importer une courbe de pompe | Ingénieur | MVP |

| UC-005 | Calculer le régime hydraulique de référence | Ingénieur | MVP |

| UC-006 | Configurer plusieurs pompes en série/parallèle | Ingénieur | MVP |

| UC-007 | Simuler une pompe indisponible et activer le secours | Exploitant | MVP |

| UC-008 | Comparer des modes de pompage | Exploitant | MVP |

| UC-009 | Créer un réservoir et importer son barémage | Ingénieur dépôt | MVP |

| UC-010 | Simuler un transfert bac-à-bac | Ingénieur dépôt | MVP |

| UC-011 | Établir un bilan matière | Exploitant dépôt | MVP |

| UC-012 | Générer une note de calcul | Ingénieur | MVP |

| UC-013 | Importer des historiques CSV/Excel | Analyste | MVP |

| UC-014 | Comparer mesures et simulation | Analyste | V1 |

| UC-015 | Simuler un coup de bélier | Ingénieur | V2 |

| UC-016 | Suivre un lot multiproduit | Dispatcher | V2 |

| UC-017 | Lire des tags OPC UA | Administrateur | V3 |

| UC-018 | Calculer un réseau gaz et ses compresseurs | Ingénieur gaz | V4 |

| UC-019 | Détecter une fuite | Exploitant/HSE | V5 |

| UC-020 | Former un opérateur sur incident | Formateur | V5 |



# 3. Scénarios de pipeline liquide

| ID | Scénario | Modifications | Résultats attendus |

| SC-L-01 | Fonctionnement normal | Toutes stations disponibles | Débit, pression, énergie et marges |

| SC-L-02 | Une pompe arrêtée | Pompe principale indisponible | Capacité restante et besoin de secours |

| SC-L-03 | Pompe de secours activée | Substitution ou ajout | Nouveau point et consommation |

| SC-L-04 | Station contournée | Bypass ouvert, pompes arrêtées | Débit maximal possible et pressions |

| SC-L-05 | Perte totale d’une station | Électricité/contrôle indisponible | Faisabilité et temps avant contrainte |

| SC-L-06 | Filtre colmaté | Coefficient de perte accru | Baisse débit et NPSH |

| SC-L-07 | Vanne partiellement fermée | Kv/Cv modifié | Surpression amont et perte |

| SC-L-08 | Soutirage intermédiaire | Débit extrait | Bilan de masse par section |

| SC-L-09 | Température basse | Viscosité élevée | Débit, puissance et non-faisabilité |

| SC-L-10 | Risque de cavitation | Niveau/pression aspiration bas | Marge NPSH et action corrective |

| SC-L-11 | Zone gravitaire | Profil descendant critique | Localisation et degré de remplissage selon modèle |

| SC-L-12 | Limite de pression | Débit/hauteur élevé | Tronçons en dépassement et réduction requise |



# 4. Scénarios de dépôt et stockage

| ID | Scénario | Contrôles |

| SC-T-01 | Transfert normal entre deux bacs | Volume disponible, chemin, pompe, durée, niveau final |

| SC-T-02 | Bac destinataire proche du niveau haut | Temps avant haut/haut-haut, arrêt sécurisé |

| SC-T-03 | Pompe de transfert indisponible | Pompe alternative, débit réduit, délai |

| SC-T-04 | Mauvais alignement de vannes | Chemin non valide et prévention du mauvais bac |

| SC-T-05 | Produit incompatible | Blocage ou plan de séparation/flush |

| SC-T-06 | Écart de bilan matière | Incertitudes, capteurs, fuite ou erreur de jaugeage |

| SC-T-07 | Réception et expédition simultanées | Bilan dynamique et conflit de ressources |

| SC-T-08 | Viscosité élevée | Besoin de chauffage et performance pompe |

| SC-T-09 | Débitmètre indisponible | Estimation par niveaux et incertitude accrue |

| SC-T-10 | Évent/soupape indisponible | Scénario bloqué et alerte HSE |



# 5. Scénarios de données

- Fichier avec unités mélangées ou colonnes ambiguës.

- Horodatages en fuseaux différents ou ordre non monotone.

- Valeurs manquantes, doublons et communication perdue.

- Capteur bloqué, dérive lente ou saut de calibration.

- Débit d’entrée différent du débit de sortie sans variation de stock cohérente.

- Modèle physique qui diverge des mesures après maintenance.

- Import partiel puis reprise idempotente.

# 6. Scénarios gaz futurs

| ID | Scénario | Capacités futures |

| SC-G-01 | Réseau gaz stationnaire | Pressions, débit, Z et line-pack |

| SC-G-02 | Un compresseur arrêté | Redistribution de charge et capacité |

| SC-G-03 | Station de compression bypassée | Pression de livraison et stock en ligne |

| SC-G-04 | Ouverture anti-surge | Point compresseur et recyclage |

| SC-G-05 | Température de refoulement élevée | Limite et refroidissement |

| SC-G-06 | Variation de demande | Prévision et gestion du line-pack |

| SC-G-07 | Décompression urgente | Transitoire et inventaire relâché |

| SC-G-08 | Présence de liquide/hydrates | Avertissement et modèle spécifique requis |



# 7. Fiche détaillée UC-005 - Calcul du régime de référence

| Élément | Définition |

| Acteur principal | Ingénieur pipeline. |

| Préconditions | Topologie valide, produit défini, conditions aux limites et stations configurées. |

| Déclencheur | L’utilisateur sélectionne « Calculer » sur un scénario brouillon. |

| Flux nominal | Validation des données; construction du système; résolution; contrôles physiques; stockage des résultats; affichage des graphiques. |

| Alternatives | Données manquantes; courbe pompe hors domaine; non-convergence; violation bloquante. |

| Postconditions | Résultat immuable lié au scénario, avec journal scientifique et avertissements. |

| Critère | Le cas de référence est reproduit dans la tolérance D10 et le rapport est générable. |



# 8. Fiche détaillée UC-007 - Pompe de secours

| Élément | Définition |

| Acteur principal | Exploitant ou ingénieur exploitation. |

| Préconditions | Baseline calculée et pompe de secours définie. |

| Flux nominal | Cloner le scénario; déclarer la pompe principale indisponible; sélectionner ou rechercher le secours; recalculer; comparer. |

| Contrôles | NPSH, puissance moteur, débit minimal, pression maximale et nombre de démarrages. |

| Sortie | Mode de secours faisable/non faisable, perte de capacité, coût et limites. |

| Critère | Le système explique le choix et les contraintes non satisfaites. |



# 9. Fiche détaillée UC-010 - Transfert bac-à-bac

| Élément | Définition |

| Acteur principal | Ingénieur dépôt. |

| Préconditions | Bacs, barémages, produit, réseau et pompes disponibles. |

| Flux nominal | Choisir source/destination/volume; trouver les chemins; calculer hydraulique; simuler niveaux; valider limites; générer ordre de mouvement. |

| Alternatives | Capacité insuffisante, cavitation, chemin bloqué, produit incompatible, temps excessif. |

| Sortie | Débit, durée, énergie, niveaux, positions de vannes et avertissements. |

| Critère | Conservation de masse et absence de dépassement de niveaux dans la tolérance. |



# 10. Matrice de couverture MVP

| Capacité | Cas couverts | Tests associés |

| Projet/version | UC-001 | D18 : intégration et RBAC |

| Réseau/profil | UC-002 | D10 : cas analytiques |

| Produit | UC-003 | D10 : propriétés et unités |

| Pompes | UC-004, UC-006, UC-007 | D10 : courbes et configurations |

| Hydraulique | UC-005 | D10 : pipeline multi-stations |

| Scénarios | UC-007, UC-008 | D18 : recette fonctionnelle |

| Stockage | UC-009, UC-010, UC-011 | D10 : transfert et bilan |

| Rapports | UC-012 | D19 : modèles de sortie |

| Données | UC-013 | D18 : import et qualité |



# Sources et références

- D03 - Processus métier.

- D04 - Exigences fonctionnelles.

- D10 - Cas de validation.

- D20 - Protocole du site pilote.

Fin du document