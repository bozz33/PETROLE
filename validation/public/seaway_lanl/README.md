# PUBLIC-SEAWAY-LANL-01 — benchmark public d'un oléoduc complet

## Objet

Ce dossier fournit un **cas hydraulique complet de transport de pétrole brut** destiné à être rejoué dans PETROLE puis comparé à une implémentation scientifique indépendante.

Il est issu du cas `case_seaway.m` du projet open source **LANL PetroleumModels.jl**, associé à l'article :

- Elena Khlebnikova, Kaarthik Sundar, Anatoly Zlotnik, Russell Bent, Mary Ewers, Byron Tasseff,
  *Optimal Economic Operation of Liquid Petroleum Products Pipeline Systems*, AIChE Journal (2021),
  arXiv `2012.11755`, DOI `10.1002/aic.17124`.
- code et données : `lanl-ansi/PetroleumModels.jl`, `test/data/case_seaway.m`.

Le code LANL est distribué sous des conditions permissives de type BSD/MICOT ; le benchmark PETROLE est une transformation clairement identifiée, et ne prétend pas être la version LANL originale.

## Nature de la preuve

**Niveau : benchmark cross-solver, pas validation terrain.**

L'article indique que le cas est **synthétisé à partir d'un système réel et de données publiques**. Il est donc beaucoup plus représentatif qu'un cas académique à une seule conduite, mais il ne divulgue pas les données hydrauliques propriétaires du vrai Seaway.

Les faits publics sur le vrai système Seaway servent uniquement de contexte :

- système long-courrier réel Cushing → côte du Texas : environ 805 km / 500 miles ;
- diamètre public : 30 pouces ;
- capacité agrégée actuelle des deux lignes long-courrier : environ 950 000 bbl/j selon le brut ;
- stockage Seaway sur la côte du Golfe : environ 8,8 millions de barils.

Sources de contexte : site officiel Seaway et rapports publics Enbridge/Enterprise. **Ces valeurs réelles ne remplacent pas les données du modèle LANL ci-dessous.**

## Complétude du modèle LANL

Le cas fournit toutes les variables nécessaires pour reconstruire un oléoduc stationnaire complet au niveau hydraulique et opérationnel :

- 23 nœuds avec altitude et limites de charge ;
- 13 tronçons de conduite ;
- longueur totale des tronçons : **969,03 km** ;
- diamètre hydraulique uniforme : **0,75 m** ;
- 9 pompes / stations de relèvement dans la chaîne topologique ;
- 3 points d'injection ;
- 2 points de soutirage ;
- pétrole brut homogène : `rho = 827 kg/m3`, `nu = 4,9e-6 m2/s` ;
- limites de débit par conduite ;
- loi hydraulique de conduite Leibenzon ;
- loi H(Q, vitesse) des pompes ;
- rendement pompe, moteur et transmission ;
- limites de vitesse de rotation ;
- prix de l'électricité par pompe ;
- prix/offres et limites d'injection/soutirage ;
- solution numérique de référence publiée dans les tests du solveur LANL.

Fichiers :

- `junctions.csv` — nœuds, altitudes et charges admissibles du modèle ;
- `pipes.csv` — topologie, diamètres, longueurs, débits et paramètres Leibenzon ;
- `pumps.csv` — neuf pompes et leurs contraintes ;
- `producers.csv` — trois injections ;
- `consumers.csv` — deux soutirages ;
- `reference_solution.csv` — assertions arrondies du test public LANL ;
- `native_opf_output.json` — enregistrement compact de la sortie OPF LANL effectivement rejouée ;
- `reference_operating_point.csv` — conditions limites, vitesses et charges extraites de cette sortie native ;
- `petrole_pump_curve.csv` — échantillonnage de la loi analytique LANL vers la courbe H(Q) PETROLE.

## Topologie

La chaîne est :

`N1 --P1--> N2 --P2--> N3 --pipe3--> N4 --P4--> N5 --pipe5--> N6 --pipe6--> N7 --P7--> N8 --pipe8--> N9 --pipe9--> N10 --P10--> N11 --pipe11--> N12 --P12--> N13 --P13--> N14 --pipe14--> N15 --pipe15--> N16 --pipe16--> N17 --pipe17--> N18 --pipe18--> N19 --P19--> N20 --pipe20--> N21 --P21--> N22 --pipe22--> N23`

Injections : N1, N9, N18. Soutirages : N15, N23.

Dans PETROLE, cette topologie source devient **15 nœuds**, **14 tronçons** et
**9 équipements de pompage** : les 13 conduites physiques totalisent toujours
969,03 km, auxquels s'ajoute uniquement le connecteur synthétique source →
station. Les 23 jonctions LANL restent donc une cardinalité de la source, pas
une cardinalité faussement attribuée au modèle PETROLE adapté.

## Référence numérique externe disponible

Le test officiel `PetroleumModels.jl/test/opf.jl` attend notamment, avec une
tolérance volontairement large :

- objectif ≈ `-15.429` ;
- débit pipe 3 ≈ `0.3567 m3/s` ;
- débit pipe 9 ≈ `0.9644 m3/s` ;
- débit pipe 15 ≈ `0.1389 m3/s` ;
- débit pipe 22 ≈ `0.7178 m3/s`.

La campagne PETROLE exécute aussi le solveur LANL lui-même, à la révision
`df35cd4999a1289710640a46882de7f665d4b32f`, avec Julia `1.5.4`, Ipopt `0.6.5`
et le cas exact `test/data/case_seaway.m`. La sortie est `LOCALLY_SOLVED`, avec
un objectif `-15.428061594560887`. Le record compact, versionné dans
`native_opf_output.json`, contient les 23 charges, les 13 débits de conduite,
les neuf vitesses de pompe ainsi que les trois injections et deux soutirages.

Les charges `h` de cette sortie sont normalisées explicitement par
`base_head=100 m` : le nœud contraint N1 donne `1.9 × 100 = 190 m`, exactement
la contrainte du fichier LANL. Ce point est contrôlé par les tests ; aucune
conversion implicite ne subsiste.

La référence native donne notamment :

- N1 injection : `0.356724281076506 m3/s` ;
- N9 injection : `0.6077287813384165 m3/s` ;
- N15 soutirage : `0.8254530724072793 m3/s` ;
- N18 injection : `0.5787995029407432 m3/s` ;
- N23 soutirage : `0.7177994929483865 m3/s` ;
- total injecté = total soutiré = `1.543252565355666 m3/s` à la précision flottante.

Le runner réinjecte délibérément ces conditions limites **et** les vitesses OPF
LANL dans PETROLE. Il compare alors les charges et les pertes à point de
fonctionnement identique. Les débits ne sont donc pas présentés comme une
prédiction de PETROLE : ils sont un contrôle de topologie et de bilan matière.

Le rapport publie trois statuts sans les confondre :

- `execution_gate` — réussite du calcul HydroLiquid uniquement si convergence,
  faisabilité, zéro violation et aucun avertissement non pré-déclaré ;
- `cross_solver_comparison_verdict = COMPARISON_COMPLETE` — comparaison
  reproductible contre les charges/vitesses issues du solveur LANL ;
- `predictive_validation_verdict = NOT_EVALUATED` — aucune capacité prédictive
  indépendante n'est revendiquée, puisque le point OPF sert d'entrée au rejeu
  et que le modèle LANL est synthétisé, non une série SCADA mesurée.

## Exécution PETROLE tracée

Le 9 août 2026, le runner a été exécuté contre l'instance PETROLE servant le
SHA `dde0481380cd792f20e15eb640bc3acc9d198bd0`. Le projet actif de preuve est
`BENCH-SEAWAY-LANL-R6` ; les cinq tentatives antérieures, conservées dans
l'audit applicatif, ont été archivées pour ne pas encombrer le panel.

Le contrat persistant de l'API a été contrôlé avant le calcul : **15 nœuds**,
**14 arêtes**, **9 équipements**, dont 13 conduites physiques pour
**969 030 m** et un seul connecteur d'adaptation de 1,001 m. Chaque arête
renvoie et respecte `from_node_code`, `to_node_code`, `length_m`,
`inner_diameter_m`, `roughness_m`, `mawp_pa`, `status` et `profile` ; chaque
pompe est rattachée à son nœud par `node_code`, avec le rôle `main` et le
catalogue attendu.

HydroLiquid a retourné `SIM_CONVERGED_WARN`, réalisable, avec **zéro violation**.
Les cinq warnings sont pré-déclarés et non masqués : pression de vapeur absente
dans la source publique (contrôles vapeur/NPSH non conclusifs) et quatre pompes
hors BEP au point OPF LANL. La porte d'exécution est donc
`PASS_WITH_EXPECTED_WARNINGS`, pas un PASS sans réserve.

Les quatre débits comparés sont reproduits avec un écart relatif maximal de
`0,00000719 %`. La charge terminale PETROLE est supérieure de `39,110990 m` à
la sortie LANL. Ce n'est pas un écart inexpliqué : Altshul prédit, sur les
13 conduites, `39,114021 m` de pertes cumulées en moins que Leibenzon ; le
résidu non expliqué est `-0,003032 m` (environ `0,008 %` de cet écart).
Le rapport JSON de preuve est conservé sur le VPS dans
`var/validation-vps/benchmark-seaway-lanl-native.json`.

Cette exécution démontre donc la cohérence de PETROLE sur le réseau complet
adapté et la traçabilité de sa différence de formulation. Elle ne constitue ni
une validation prédictive indépendante, ni une certification industrielle.

## Adaptation scientifique vers PETROLE

### Frottement

Le cas LANL emploie, en régime turbulent lisse, la forme Leibenzon avec `m=0.25` et `beta=0.0246`.
PETROLE possède la corrélation d'Altshul :

`lambda = 0.11 * (epsilon/D + 68/Re)^0.25`.

Avec `epsilon/D = 0`, cette corrélation a la même dépendance en `Re^-0.25` que le régime lisse du benchmark. Elle sera utilisée comme **base de comparaison déclarée**. La différence résiduelle de formulation ne sera pas calibrée après coup : elle sera mesurée et publiée.

### Pompe

La loi LANL au régime nominal est :

`H = 276.8 - 92 * Q^2`

avec `Q` en m3/s, vitesse nominale `50 r/s = 3000 rpm`, plage `40–60 r/s` et rendement nominal maximal `0.87`.

`petrole_pump_curve.csv` échantillonne cette loi entre 0,8 et 1,2 m3/s. Les puissances sont dérivées de `rho*g*Q*H/(eta_pump*eta_motor*eta_transmission)` et sont donc marquées **DERIVED**.

### MAWP

Le fichier LANL donne des limites de **charge hydraulique de fonctionnement**, pas une MAWP constructeur de conduite. PETROLE exige actuellement `mawp_pa` à la création d'un tronçon.

Le script d'adaptation utilisera une valeur **non bloquante et explicitement marquée ASSUMPTION**. Cette valeur ne devra jamais être présentée comme la MAWP du vrai Seaway et sera exclue des conclusions de validation.

La borne source `740 m` correspond, avec `rho=827 kg/m3` et `g=9.8 m/s2`, à environ `5.997 MPa` de pression de charge ; elle sera conservée séparément comme contrainte du benchmark.

### Connecteur source → première station

PETROLE porte les pompes sur un nœud `station`, tandis que LANL représente les pompes par des arêtes de longueur nulle. L'adaptateur insère donc un connecteur source → station de **1,001 m**. Cette longueur est négligeable face aux 969,03 km physiques, mais dépasse la tolérance de recherche de station de 1 m du moteur : avec un connecteur de 1 mm, les pompes de tête étaient appliquées deux fois. La longueur synthétique reste explicitement exclue de la longueur physique du benchmark.

## Ce que ce cas permettra de vérifier dans PETROLE

1. reconstruction d'un réseau pétrolier de près de 1 000 km ;
2. injections et soutirages intermédiaires ;
3. neuf relèvements par pompe ;
4. profil altimétrique station par station ;
5. bilan de masse ;
6. pertes de charge par tronçon ;
7. pressions/charges nodales ;
8. courbes de pompe et vitesses variables ;
9. contraintes de débit et de charge ;
10. énergie de pompage ;
11. comparaison des débits de référence LANL ;
12. comparaison ultérieure des régimes optimisés lorsqu'un mapping objectif-à-objectif strict est défini.

## Limites — à ne pas masquer

Le jeu **ne contient pas** les données industrielles confidentielles suivantes du vrai Seaway :

- courbes constructeur réellement installées ;
- NPSHr constructeur ;
- épaisseurs et nuances exactes de chaque tronçon ;
- MAOP/MAWP réelle par segment ;
- positions exactes et configurations internes des stations ;
- historique SCADA réel ;
- pression/débit terrain simultanés ;
- état réel des vannes, DRA, pigging et vieillissement.

Par conséquent, un bon accord PETROLE ↔ LANL démontrera une **cohérence de solveur sur un oléoduc complet**, pas encore une validation prédictive industrielle.

## Étape de validation terrain complémentaire

Le dossier public `FIELD-EAST-CHINA-2025` sera ajouté séparément : il provient d'un **vrai pipeline de produits pétroliers de 615 km** (8 stations, 18 chambres de vannes, pression de conception 8 MPa) et publie un tronçon de terrain de 40,078 km avec diamètre, altitudes, densité, viscosité, débit mesuré et essais de fuite. Il fournira la preuve terrain que le cas LANL ne peut pas fournir.
