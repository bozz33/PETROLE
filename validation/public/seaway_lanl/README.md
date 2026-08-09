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
- `reference_solution.csv` — sorties de référence et allocation fixe reconstruite ;
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

Le test officiel `PetroleumModels.jl/test/opf.jl` attend notamment :

- objectif ≈ `-15.429` ;
- débit pipe 3 ≈ `0.3567 m3/s` ;
- débit pipe 9 ≈ `0.9644 m3/s` ;
- débit pipe 15 ≈ `0.1389 m3/s` ;
- débit pipe 22 ≈ `0.7178 m3/s`.

Comme la topologie est linéaire avec trois injections et deux soutirages, ces quatre débits permettent de reconstruire par bilan de masse une allocation fixe pour un rejeu hydraulique PETROLE :

- N1 injection : `0.3567 m3/s` ;
- N9 injection : `0.6077 m3/s` ;
- N15 soutirage : `0.8255 m3/s` ;
- N18 injection : `0.5789 m3/s` ;
- N23 soutirage : `0.7178 m3/s` ;
- total injecté = total soutiré = `1.5433 m3/s`.

Cette allocation est marquée **DERIVED** : elle est déduite des sorties de référence, pas directement copiée d'une table du papier. Les débits deviennent alors des **conditions limites d'entrée** du rejeu PETROLE : leur reproduction vérifie la topologie et le bilan matière, mais ne constitue pas une validation indépendante du solveur hydraulique.

Le fichier `reference_operating_point.csv` est également **DERIVED** : les charges et vitesses qu'il contient servent à diagnostiquer l'écart de formulation Leibenzon/Altshul. Elles ne doivent pas être présentées comme des sorties officielles de PetroleumModels.jl.

Le runner publie donc deux verdicts séparés :

- `execution_gate` — PASS uniquement si HydroLiquid converge, est réalisable et ne porte aucune violation ni avertissement non déclaré. Les seuls avertissements pré-déclarés pour ce cas sont l'absence de pression de vapeur dans la source publique et le fonctionnement hors BEP de certaines pompes au point LANL imposé ; ils restent exposés dans la preuve sous `PASS_WITH_EXPECTED_WARNINGS` ;
- `independent_validation_verdict` — `NOT_EVALUATED` tant qu'une sortie native, figée et reproductible de PetroleumModels.jl (pressions, vitesses et puissances) n'est pas archivée comme référence externe.

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
