# PUBLIC-VALIDATION-02 — matrice des candidats prédictifs publics

## Objectif

Cette campagne cherche des jeux indépendants dans lesquels PETROLE peut recevoir les mesures disponibles **avant** la mesure de vérité (par exemple pressions amont/aval, géométrie, propriétés du fluide) puis prédire une grandeur tenue à l'écart du solveur, prioritairement le débit.

Le critère strict pour une validation prédictive de débit est :

- longueur hydraulique et diamètre intérieur ;
- altitude amont/aval ou différence d'altitude ;
- fluide, masse volumique et viscosité au régime étudié ;
- pression amont et pression aval synchronisées ;
- débit mesuré, conservé comme vérité de contrôle et **non transmis au solveur** ;
- provenance de chaque valeur (`MEASURED`, `PUBLISHED`, `DERIVED`, `CALIBRATED`, `ASSUMPTION`).

Une hypothèse portant sur une grandeur qui gouverne la prédiction interdit de classer le cas comme validation prédictive stricte. Une valeur nécessaire uniquement pour satisfaire un contrat API mais exclue mathématiquement du verdict peut être `ASSUMPTION`, à condition d'être publiée comme telle.

## Résultat de la recherche publique

Au 9 août 2026, la recherche a identifié plusieurs cas industriels de grande valeur, mais **aucun ensemble public supplémentaire ne fournit encore toutes les grandeurs critiques nécessaires pour fermer trois validations prédictives terrain HydroLiquid sans hypothèse gouvernante**. Ce constat est une limite de disponibilité des données publiques, pas un échec du moteur.

| ID | Installation / source | Fluide | Atouts publics | Blocage strict actuel | Statut |
| --- | --- | --- | --- | --- | --- |
| `FIELD-BN1-2022` | B oil depot → N1 oil depot, Northeast China, Wei et al., Energies 2022, DOI `10.3390/en15165880` | brut chauffé | 28,3049 km, `φ529×7 mm`, pression départ, perte de pression, température, densité, débit massique, 2791 enregistrements annoncés et un échantillon publié | loi viscosité-température et différence d'altitude numériques non publiées ; les 2791 lignes ne sont pas publiées | `BLOCKED_CRITICAL_INPUTS` |
| `FIELD-GUANGDONG-NO1-2021` | Guangdong refined-oil pipeline No.1, Wang et al., Energies 2021, DOI `10.3390/en14185871` | diesel / essence | SCADA réel, sans DRA sur No.1 ; L=38,71 km, D=0,392 m, Δz=1,08 m ; propriétés diesel/essence publiées ; article confirme P entrée/sortie + Q + densité dans les données | séries SCADA numériques non publiques ; disponibilité uniquement sur demande à cause des restrictions du financeur | `BLOCKED_RAW_SCADA` |
| `FIELD-QINGTIE-2022` | Qingtie Fourth-Line, Peng et al., Energies 2022, DOI `10.3390/en15207453` | brut chauffé | pipeline réel 548,5 km, D=711 mm, pressions/températures station par station, débits massiques réels de juillet 2018, pompes et vitesses | modèle actuel HydroLiquid n'intègre pas l'évolution thermique axiale ; kilométrage/altitudes détaillés et propriétés rhéologiques nécessaires au rejeu strict ne sont pas tous publiés dans les tableaux exploitables | `BLOCKED_SCOPE_AND_INPUTS` |
| `LAB-WELLBORE-WATER-2020` | University of Oklahoma, Kiran et al., JPSE 2020, DOI `10.1016/j.petrol.2020.107822` | eau | calibration monophasique : D=83 mm, L=5,5 m, 4 débits et pertes de pression mesurées tabulées | pertes publiées = composante frictionnelle d'une conduite verticale ; rugosité et état thermophysique exact de l'eau non entièrement publiés | `SUPPORTING_ONLY` |
| `LAB-WATERLOO-2019` | Waterloo pipeline rig, Pal, Fluids 2019, DOI `10.3390/fluids4020103` | émulsions Newtoniennes | 5 tubes lisses horizontaux, géométries exactes, 25 °C, densité/viscosité tabulées, ΔP et Q mesurés | séries numériques ΔP(Q) affichées principalement en figures, pas en table machine-readable retrouvée | `BLOCKED_NUMERIC_SERIES` |
| `LAB-FITTINGS-2026` | Mulani & Patil, Zenodo DOI `10.5281/zenodo.20917487` | eau | D=25 mm, Re=8k–48k, débitmètre électromagnétique, transducteurs ΔP, 5 accessoires, K expérimentaux | le dépôt public expose le PDF mais pas encore un tableau brut machine-readable dans les métadonnées ; utile surtout pour les pertes singulières | `BLOCKED_RAW_NUMBERS` |
| `FIELD-DRIP-2024` | Mendeley Data DOI `10.17632/w9594tjkwp.2` | eau | 911 mesures IoT, Pressure1, Pressure2, débit, CSV brut/filtré | géométrie hydraulique (L, D, Δz) non documentée dans la description publique | `BLOCKED_GEOMETRY` |

Les jeux multiphasiques (huile-eau, air-eau, écoulements de blowout diphasiques) restent hors du domaine du moteur stationnaire monophasique actuel et ne sont pas reclassés artificiellement comme candidats HydroLiquid.

## Trois dépendances industrielles prioritaires

### 1. FIELD-GUANGDONG-NO1-2021

C'est le meilleur candidat à court terme. Le pipeline No.1 n'emploie pas de drag reducer et l'article fournit exactement la géométrie et les propriétés nécessaires. Les auteurs indiquent que les données SCADA contiennent pression d'entrée, pression de sortie, débit et densité. Le seul verrou est l'accès aux séries numériques.

**Données à demander :** timestamp, produit/batch, pression amont, pression aval, débit, densité, température si disponible, qualité/unité des capteurs. Les débits seront masqués au solveur lors de la validation.

### 2. FIELD-BN1-2022

Le tableau public fournit déjà plusieurs dizaines de régimes réels et permet de dériver `P_out = P_start - ΔP` et `Q_vol = m_dot / rho`. Le diamètre intérieur peut être dérivé de la spécification `φ529×7 mm` comme 0,515 m si cette notation est confirmée comme diamètre extérieur × épaisseur.

**Données à demander :** altitude B/N1 (ou Δz), relation viscosité-température réellement employée / analyses labo, et si possible le jeu de 2791 enregistrements annoncé. Sans ces valeurs, PETROLE ne doit pas utiliser une viscosité inventée pour obtenir un verdict terrain.

### 3. FIELD-QINGTIE-2022

Les tableaux publics donnent des pressions, températures et débits réels à plusieurs stations. Ce cas devient particulièrement important pour la phase du cahier des charges qui ajoutera la thermique axiale.

**Données à demander :** chainage et altitude des neuf stations, propriétés du brut en fonction de T, rugosité/diamètre intérieur exact, cohérence des débits par section et séries temporelles synchronisées. Tant que HydroLiquid reste isotherme, ce cas ne ferme pas une validation prédictive du pipeline chauffé complet.

## Cas déjà exécutés — classification immuable

- `BENCH-TUXTLA-2020` : reproduction expérimentale d'un banc réel ;
- `PUBLIC-SEAWAY-LANL-01` : comparaison cross-solver sur un réseau complet, pas prédiction terrain ;
- `FIELD-EAST-CHINA-2025 / EC-01` : reproduction physique à débit terrain imposé ; `predictive_validation_verdict = NOT_EVALUATED` tant que les pressions numériques brutes ne sont pas disponibles.

Ils ne sont pas promus artificiellement en validation prédictive.

## État de fermeture

`PUBLIC-VALIDATION-02 = OPEN / BLOCKED_PUBLIC_DATA`

La fermeture stricte requiert toujours **trois** jeux indépendants pour lesquels la vérité mesurée est cachée au solveur. La recherche publique n'autorise pas encore cette conclusion sans inventer des données critiques.

Cette campagne peut néanmoins continuer en parallèle du prochain lot fonctionnel du cahier des charges : les dépendances externes sont désormais identifiées, versionnées et auditables. Lorsqu'un jeu débloqué arrive, il doit passer par un runner API dédié avec les verdicts séparés `execution_gate`, `physics_reproduction_verdict`, `field_data_comparison_verdict`, `predictive_validation_verdict`, `source_consistency_verdict` et `certification=false`.
