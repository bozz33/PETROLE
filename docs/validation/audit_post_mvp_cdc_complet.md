# Audit post-MVP — cahier des charges complet

- Statut : **constat de référence, sans effet de certification**
- Date : 9 août 2026
- Produit figé examiné : `main` à `dde0481380cd792f20e15eb640bc3acc9d198bd0`
- Travaux de validation séparés : PR draft #17, `feat/public-validation-seaway`
- Documents directeurs : D04, D05, D06, D07, D10, D11, D13, D15, D17 et D20.

Ce document distingue strictement le logiciel présent, la preuve déjà exécutée,
et les capacités qui restent des phases ultérieures. Une capacité marquée
« implémentée » ne vaut ni certification réglementaire ni validation sur une
installation industrielle.

## Méthode et limites de l'audit

L'audit repose sur les contrats FastAPI et Pydantic, les modèles relationnels,
les services, les moteurs `hydroliquid`, `hydro_tanks` et
`hydro_optimization`, l'interface React et les tests versionnés. Les preuves
VPS restent des artefacts d'environnement : elles ne sont pas déduites d'une
lecture du code.

Les statuts sont les suivants :

| Statut | Signification |
|---|---|
| **Implémenté** | Fonction disponible dans le périmètre effectivement couvert par le MVP. |
| **Partiel** | Fondations présentes, mais un critère littéral ou un usage produit reste à fermer. |
| **Planifié** | Fonction explicitement reportée par le CDC ; aucun moteur produit ne prétend la couvrir. |

## Verdict de périmètre

PETROLE est un **outil d'étude de pipelines liquides stationnaires linéaires et
de transferts de bacs**. Le terme « réseau » dans l'interface désigne un graphe
persisté et validé ; le moteur HydroLiquid de production n'accepte toutefois
qu'une chaîne orientée continue. Les injections et soutirages intermédiaires
sont pris en charge. Un réseau liquide maillé ou ramifié n'est pas une capacité
produit actuelle.

Cela correspond au périmètre MVP annoncé par D04 et D17 : il ne faut pas
présenter l'application comme un simulateur universel de réseau, un simulateur
transitoire, un système SCADA ou un jumeau numérique.

| Domaine du CDC | État constaté | Évidence principale | Suite officielle |
|---|---|---|---|
| Organisation, sites, projets, versions, audit | **Implémenté** | `models/core.py`, `services/core.py`, API `/organizations`, `/sites`, `/projects` | Pilote : MFA/OIDC et isolation base renforcée |
| Réseau linéaire, profils, actifs et catalogues | **Implémenté** | `models/network.py`, `services/network.py`, React Flow, topologie JSON | Améliorer l'éditeur et la comparaison de versions |
| Hydraulique liquide stationnaire | **Implémenté** | `hydroliquid/long_distance.py`, diagnostics, 41 cas scientifiques | Calibration et validation indépendante |
| Branches/mailles liquides généralistes | **Partiel** | Le graphe les persiste, mais le validateur impose une chaîne ; pandapipes est un adaptateur de comparaison, non le moteur produit | À concevoir avant de l'annoncer comme fonction produit |
| Pompes, stations, NPSH, vitesse, énergie | **Implémenté** | `hydro_domain/pumps.py`, `stations.py`, `operations.py` | Données constructeur et calibration pilote |
| Bacs, barémages, transfert et bilan matière | **Implémenté** | `hydro_tanks`, `operations.py`, rapports RPT-05/RPT-06 | Planification de mouvements et chemins alternatifs |
| Scénarios, comparaison et optimisation bornée | **Implémenté** | `ScenarioPayloadInput`, `OptimizationCreate`, énumération/Pyomo | Optimisation lourde asynchrone et multi-périodes |
| Imports CSV/XLSX/JSON et lignage | **Implémenté** | `data_import.py`, données brutes/normalisées/corrigées | Qualité temporelle, statistiques et résidus |
| Rapports et exports de calcul | **Partiel** | PDF versionné et exports CSV/XLSX/JSON ; pas d'export DOCX ni PNG autonome exposé | Fermer l'interprétation de D04 FR-RPT-001/002 avant promesse contractuelle |
| Calibration mesure-modèle et analytics historiques | **Partiel** | Les mesures s'importent avec horodatage/qualité ; aucune UI de séries, de résidus, RMSE ou calibration | **Phase 2 — pilote/V1** |
| Multiproduit, interfaces et mélange | **Planifié** | `batch_reference` est seulement une métadonnée ; aucun suivi de lot | **Phase 4 / V2** |
| Thermique axiale et produits visqueux chauffés | **Planifié** | Propriétés évaluées à une température imposée globale ; aucun bilan thermique axial | Phase 4 ou lot scientifique spécialisé après données |
| Transitoires et coups de bélier | **Planifié** | Aucun MOC/DAE ; le moteur le déclare explicitement hors domaine | **Phase 4 / V2** avec benchmarks MOC |
| Historian, OPC UA et SCADA | **Planifié** | Aucun connecteur, aucune écriture industrielle ; imports de fichiers seulement | **Phase 5 / V2.5**, lecture seule en DMZ |
| Gaz, compression et line-pack | **Planifié** | Le type de projet peut être déclaré mais l'UI indique « hors calcul MVP » ; aucun moteur gaz | **Phase 6 / V3** |
| Détection de fuite / RTTM | **Planifié** | Aucun service de détection ni données labellisées | **Phase 7 / V4** après pilote et métriques API 1175 |
| Jumeau numérique / temps quasi réel | **Planifié** | Pas d'estimation d'état, orchestration temps réel ou synchronisation site | Après SCADA, données fiables et moteurs validés |
| Multi-sites haute disponibilité / produit industriel | **Planifié** | Déploiement conteneurisé et sauvegarde existent ; pas de HA ni exploitation multi-site | **Phase 8** |

## Couverture D04 — 76 exigences fonctionnelles

Les fonctions MVP ne doivent pas être confondues avec celles dont D04 demande
explicitement le report. Le tableau suivant donne le décompte et les écarts qui
méritent un travail identifié.

| Bloc D04 | Implémenté | Partiel | Planifié | Constat / écart restant |
|---|---:|---:|---:|---|
| FR-GEN-001..005 — principes généraux | 5 | 0 | 0 | SI, version/méthode/scénario tracés, erreurs structurées, règles séparées du solveur. |
| FR-PRJ-001..006 — projets et versions | 5 | 1 | 0 | **FR-PRJ-005** : clone/filiation présents ; diff lisible de deux versions absent. |
| FR-MOD-001..008 — réseau et équipements | 7 | 1 | 0 | **FR-MOD-007** : carte MapLibre présente, mais pas de sélection synchronisée carte ↔ schéma. |
| FR-FLD-001..005 — produits et propriétés | 4 | 1 | 0 | **FR-FLD-003** : méthode/incertitude présentes dans les points ; date de laboratoire et workflow complet restent à modéliser. |
| FR-LIQ-001..009 — hydraulique liquide | 9 | 0 | 0 | Couverture du pipeline continu ; cette ligne ne signifie pas un solveur maillé généraliste. |
| FR-PMP-001..008 — pompes et stations | 8 | 0 | 0 | Courbes, fit/interpolation, configurations, NPSH, puissance et recherche bornée. |
| FR-TNK-001..008 — bacs et transferts | 6 | 1 | 1 | **FR-TNK-007** : chemin explicite validé, pas de recherche/choix automatique parmi des chemins alternatifs ; **FR-TNK-008** : planning multi-mouvements est LATER. |
| FR-SCN-001..008 — scénarios et optimisation | 6 | 0 | 2 | Les transitoires et le gaz sont volontairement LATER. |
| FR-DAT-001..007 — données et analyses | 3 | 2 | 2 | **FR-DAT-004/005** : pas encore de dashboard séries/aberrants ni comparaison mesure-modèle avec RMSE/biais ; SCADA et fuite sont LATER. |
| FR-RPT-001..006 — rapports et collaboration | 3 | 3 | 0 | PDF, CSV/XLSX/JSON et RPT-01 à RPT-06 sont présents. À décider/fermer : DOCX si « Word/PDF » signifie les deux formats, image de graphique téléchargeable, logo/langue par organisation. |
| FR-ADM-001..006 — administration et sécurité | 6 | 0 | 0 | RBAC/audit/sauvegarde-restauration/règles/déploiements séparés ; aucune commande industrielle. |
| **Total** | **62** | **9** | **5** | Les 5 planifiées sont explicitement hors MVP ; les 9 partielles doivent être arbitrées selon leur priorité contractuelle. |

### Points MVP à fermer ou à accepter explicitement

1. **Rapports.** Le produit génère actuellement des PDF, pas des DOCX, et ne
   fournit pas un bouton/API d'export PNG distinct des graphiques. Si le slash
   « Word/PDF » de FR-RPT-001 signifie « l'un des deux », le PDF ferme ce point ;
   s'il signifie les deux, il faut rouvrir un petit lot de reporting sur `main`.
2. **Carte.** La vue carte affiche un tracé lorsque les coordonnées existent,
   mais son état de sélection ne se synchronise pas avec React Flow. C'est une
   exigence SHOULD, non une porte MVP.
3. **Topologie.** Le modèle de données est un graphe, mais la validation et le
   moteur principal refusent une branche. Cette limite doit rester visible dans
   l'UI, les propositions commerciales et les rapports.
4. **Mesures.** L'import a le bon lignage (`raw`, `normalized`, `corrected`) et
   impose `timestamp`, `unit`, `quality`, `source`. Il n'est pas encore un
   produit d'analytics ni de calibration.

## État scientifique et validation externe

| Preuve | Conclusion correcte | Ce qu'elle ne prouve pas |
|---|---|---|
| Cas scientifiques versionnés | Vérification des équations, diagnostics et non-régressions dans leurs tolérances | Exactitude d'un pipeline industriel réel |
| Tuxtla 2020 | Reproduction d'un banc physique publiée | Prédiction indépendante, car des paramètres ont été calibrés sur la même étude |
| Seaway/LANL | Comparaison inter-solveur complète sur un oléoduc long et un point OPF natif | Validation terrain ou certification ; le point de référence est réinjecté |
| East China EC-01 | Reproduction physique à débit terrain imposé et incohérence de Reynolds signalée | Prédiction du débit, faute de pressions terrain brutes publiques |
| PUBLIC-VALIDATION-02 | Candidats, blocages et demandes de données rendus auditables | Trois validations prédictives strictes : compteur volontairement à zéro |

La campagne de données publiques est donc correctement **ouverte et bloquée par
les données**, non par un résultat caché du moteur. Les règles du registre
interdisent qu'un cas `BLOCKED_*` soit promu en PASS prédictif.

## Ordre de réalisation recommandé

La roadmap D17 fixe l'ordre : pilote/V1 avant multiproduits, transitoires et
SCADA. Le prochain lot ne doit donc pas être un moteur thermique ou un
connecteur OPC UA isolé.

| Priorité | Lot | Sortie mesurable | Porte de passage |
|---:|---|---|---|
| P0 | Décision de release MVP | Fiche ingénieur externe, identité de signature, rapport de qualification rattaché au SHA final | Tag signé `v1.0.0-mvp`, sans prétention de certification industrielle |
| P1 | **Pilote/V1 : calibration et mesures** | Dataset immuable, séparation calibration/validation, résidus, biais, MAE/RMSE, incertitudes et RPT-07/RPT-08 | Un régime non utilisé pour ajuster le modèle est prédit dans la tolérance convenue |
| P1 | Durcissement pilote | MFA/OIDC, RLS ou contrôle d'accès équivalent démontré, politique de rétention, alerting et revue UX | Architecture et procédures acceptées par l'opérateur |
| P1 | Fermer les choix MVP partiels | Décision documentée sur DOCX/PNG, carte, chemins alternatifs et diff de version | Aucun écart MUST ambigu dans l'offre ou la recette contractuelle |
| P2 | Multiproduit + thermique si le pilote le justifie | Modèle de lots/interfaces et bilan thermique validé sur benchmarks | Sources, domaine et validation séparés avant activation |
| P3 | Transitoires | MOC, vannes/pompes/protections et benchmarks Joukowsky/publications | Expertise dédiée et validation de maillage/pas de temps |
| P4 | SCADA lecture seule | Passerelle isolée, OPC UA/historian, qualité temporelle, aucun write | Revue OT, DMZ et essai laboratoire réussis |
| P5 | Gaz, fuite, jumeau numérique | Moteurs spécialisés et données labellisées | Gates D17/D20 franchies séparément |

## Décision d'architecture conservée

La séparation actuelle est saine : les ressources et l'identité restent dans le
monolithe ; les futurs moteurs doivent entrer derrière le contrat
`HydraulicEngine` ou derrière un service typé versionné. Aucun nouveau moteur
ne doit contourner les versions de modèle, les droits, l'audit, le stockage ou
les résultats immuables.

Avant un pilote industriel, D20 reste obligatoire : site autorisé, données
anonymisées si nécessaire, revue ingénieur, architecture OT lecture seule,
calibration séparée de la validation et décision Go/No-Go formelle.
