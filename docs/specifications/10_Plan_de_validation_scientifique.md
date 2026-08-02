Plateforme de transport et de stockage des hydrocarbures

D10

Plan de validation scientifique

Cas de référence, tolérances, benchmarks et protocole de preuve

| Version | 1.0 |

| Date | 2 août 2026 |

| Statut | Référence de conception - à valider par l’équipe |

| Équipe | 2 développeurs, avec assistants IA |

| Référentiel | ASME, API, ISO, IEC, ISA et exigences locales applicables |



Note : ce document structure la conception du logiciel. Il ne remplace ni les textes normatifs achetés auprès de leurs éditeurs, ni les validations d’un ingénieur habilité, ni les autorisations réglementaires d’un site réel.

# Contrôle du document

| Champ | Valeur |

| Code | D10 |

| Version | 1.0 |

| Date | 2 août 2026 |

| Auteur | Équipe projet - 2 développeurs assistés par IA |

| Validation attendue | Relecture technique, métier et réglementaire |

| Statut | Document de référence pour la conception |



# Table des matières

- Objectifs

- Niveaux de validation

- Tolérances

- Cas analytiques

- Pipeline multi-stations

- Pompes

- Zones gravitaires

- Réservoirs

- Optimisation

- Gaz et transitoires futurs

- Comparaison logiciels

- Gestion des écarts

- Dossier de preuve

La pagination peut évoluer après validation et mise en forme finale dans Microsoft Word ou LibreOffice.

# 1. Objectifs

- Prouver que chaque équation et algorithme produit un résultat correct dans son domaine.

- Détecter les régressions lors des évolutions de code et de dépendances.

- Comparer le moteur à des solutions analytiques, manuelles, académiques et industrielles.

- Définir clairement la tolérance et la source de vérité de chaque cas.

- Constituer un dossier auditable avant toute utilisation sur un site réel.

# 2. Niveaux de validation

| Niveau | Objet | Preuve |

| V1 - Fonction | Une formule ou corrélation isolée | Test unitaire avec valeur de référence |

| V2 - Composant | Conduite, pompe, vanne, bac | Cas analytique ou constructeur |

| V3 - Système | Pipeline/station/transfert | Bilan et comparaison indépendante |

| V4 - Logiciel | Workflow complet et rapports | Recette fonctionnelle reproductible |

| V5 - Site pilote | Mesures réelles | Calibration, validation croisée et incertitude |

| V6 - Exploitation | Suivi continu | Surveillance de dérive et revalidation |



# 3. Tolérances initiales proposées

| Grandeur | Tolérance MVP indicative | Condition |

| Débit cas analytique | ≤ 0,1 % | Données exactes et modèle identique |

| Pression/charge cas analytique | ≤ 0,2 % | Sans incertitude d’entrée |

| Facteur de frottement | ≤ 0,1 % | Comparaison à solveur Colebrook de haute précision |

| Courbe pompe approximée | Erreur RMS ≤ 1 % ou exigence constructeur | Dans la plage valide |

| Conservation de masse réseau | ≤ 10⁻⁶ relatif ou seuil absolu configuré | À chaque nœud |

| Transfert volume | ≤ 0,1 % numérique | Hors incertitude de jaugeage |

| Comparaison mesures réelles | Tolérance issue de l’incertitude instrumentale | Site pilote |

| Optimisation | Solution faisable et objectif vérifié | Optimalité selon gap déclaré |



| Important Ces seuils sont des cibles de développement et non des garanties métrologiques. Sur site, les tolérances doivent intégrer l’incertitude des capteurs, propriétés, barémages et conditions réelles. |



# 4. Cas analytiques minimaux

| ID | Cas | Référence attendue | Contrôles |

| VAL-LIQ-001 | Conduite horizontale laminaire | Hagen-Poiseuille / λ=64/Re | Q, Δp, Re |

| VAL-LIQ-002 | Conduite turbulente unique | Darcy-Weisbach + Colebrook | λ, h_f, p_out |

| VAL-LIQ-003 | Deux diamètres en série | Somme des pertes | Continuité du débit |

| VAL-LIQ-004 | Branche simple | Conservation et pertes égales selon montage | Débits branches |

| VAL-LIQ-005 | Différence d’altitude sans pompe | Bernoulli | Pressions extrêmes |

| VAL-LIQ-006 | Pertes singulières | ΣK | Contribution détaillée |

| VAL-PMP-001 | Pompe idéale + conduite | Intersection courbe réseau | Q et H |

| VAL-TNK-001 | Bac cylindrique | V=Ah | Niveau-volume |

| VAL-TNK-002 | Deux bacs sans pertes variables | Bilan dynamique simple | h(t), conservation |



# 5. Cas pipeline multi-stations fourni

Le programme Python et le support de cours transmis fournissent un cas de 460 km avec profil complexe, station de tête, deux stations intermédiaires, courbes de pompes et détection de zones gravitaires. Ce cas sera conservé comme benchmark académique, après correction des erreurs identifiées dans le prototype et séparation des règles russes du moteur international.

| Étape | Action de validation |

| 1 | Reconstituer exactement les entrées, unités et points de profil. |

| 2 | Corriger le double comptage de la charge de la station de tête et la conversion journalière. |

| 3 | Exécuter une version de référence figée et conserver les sorties. |

| 4 | Comparer le nouveau moteur sur débit, pressions, charge et localisation des zones. |

| 5 | Expliquer tout écart par une différence de modèle, corrélation ou correction. |

| 6 | Créer des variantes : nombre de pompes, stations, rugosité et conditions de limite. |



# 6. Validation des pompes

| ID | Cas | Critère |

| VAL-PMP-002 | Ajustement H=a-bQ² sur points fournis | Coefficients et erreur reproduits |

| VAL-PMP-003 | Deux pompes identiques en série | Charge doublée au même débit |

| VAL-PMP-004 | Deux pompes identiques en parallèle | Débit doublé à charge donnée, selon domaine |

| VAL-PMP-005 | Pompes différentes en parallèle | Partage de débit stable et enveloppes respectées |

| VAL-PMP-006 | Variation de vitesse | Loi d’affinité et limites |

| VAL-PMP-007 | NPSH | Marge correcte sur cas manuel |

| VAL-PMP-008 | Puissance/rendement | Comparaison fiche constructeur |



# 7. Validation des zones gravitaires

- Cas sans zone gravitaire : aucune fausse détection.

- Cas avec sommet de profil et pression atteignant la pression de vapeur.

- Sensibilité au maillage et à l’interpolation du profil.

- Localisation x* comparée au calcul géométrique du support fourni.

- Vérification du degré de remplissage si le modèle est activé.

- Cas où le modèle n’est pas applicable : avertissement et absence de conclusion industrielle.

# 8. Validation réservoirs et transferts

| ID | Cas | Attendus |

| VAL-TNK-003 | Interpolation d’un barémage non linéaire | Monotonie et inversion h(V) |

| VAL-TNK-004 | Transfert avec niveaux variables | Conservation de volume et durée |

| VAL-TNK-005 | Pompe + lignes aspiration/refoulement | Point de fonctionnement manuel |

| VAL-TNK-006 | Arrêt au niveau haut | Événement au pas de temps interpolé |

| VAL-TNK-007 | Capacité insuffisante | Scénario déclaré non faisable avant démarrage |

| VAL-TNK-008 | Bilan matière avec incertitudes | Écart et intervalle calculés |

| VAL-TNK-009 | Deux chemins de transfert | Choix cohérent avec pertes/contraintes |



# 9. Validation de l’optimisation

| Cas | Méthode de preuve |

| Petit ensemble de 2 à 6 pompes | Énumérer exhaustivement et comparer le choix de l’optimiseur. |

| Contraintes incompatibles | Vérifier diagnostic d’infaisabilité. |

| Tarif énergétique variable | Comparer solution à une règle heuristique. |

| Objectifs pondérés | Test de sensibilité aux poids. |

| Solveur arrêté avant optimum | Afficher gap, statut et meilleure solution faisable. |

| Données identiques | Répéter et obtenir le même résultat. |



# 10. Gaz et transitoires - plan futur

| Domaine | Benchmarks requis |

| Gaz stationnaire | Réseau simple analytique, exemples GasModels/pandapipes, comparaison à logiciel industriel si accessible. |

| Compresseur | Point de carte, lois de similitude, limites anti-surge. |

| Line-pack | Bilan d’inventaire sur conduite uniforme et variation de pression. |

| Coup de bélier | Joukowsky, fermeture instantanée, réservoir amont/aval, valve. |

| MOC | Convergence maillage/pas de temps et comparaison publication. |

| Séparation de colonne | Benchmark spécialisé avant activation industrielle. |



# 11. Comparaison avec logiciels et projets tiers

| Outil | Usage de validation | Limite |

| fluids/SciPy | Fonctions de base et racines | Pas un solveur de pipeline complet |

| pandapipes | Réseaux simples gaz/liquide | Domaine différent de l’oléoduc multiproduit |

| OpenModelica/Modelica.Fluid | Dynamiques et composants | Modèles à aligner exactement |

| DWSIM | Thermodynamique/équipements de terminal | Licence et périmètre procédé |

| GasModels.jl | Optimisation de réseaux gaziers | Service futur, formulations spécifiques |

| Logiciel industriel partenaire | Référence site | Données et licence nécessaires |



# 12. Gestion des écarts

| Classe | Décision |

| A - Conforme | Sous tolérance ; test automatisé accepté. |

| B - Écart expliqué | Différence de méthode/corrélation documentée et approuvée. |

| C - Défaut logiciel | Ticket bloquant selon impact ; correction et test de non-régression. |

| D - Référence douteuse | Suspendre le cas, chercher une source indépendante. |

| E - Domaine non couvert | Afficher la limite et empêcher une conclusion approuvée. |



# 13. Dossier de preuve

- Description du cas, source et droits d’utilisation.

- Jeu d’entrée immuable et checksum.

- Résultats attendus avec unités et tolérances.

- Version du code, dépendances, solveur et environnement.

- Résultat réel, erreur, statut et journal.

- Revue et approbation par un ingénieur métier.

- Historique des changements du cas et des tolérances.

- Rapport consolidé par version du produit.

# Sources et références

- Documents académiques et programme Python transmis par l’utilisateur.

- Cas analytiques dérivés des équations de D07.

- Standards et guides de D08, sans reproduction de leur contenu protégé.

- Projets open source et logiciels comparatifs décrits dans D14.

Fin du document