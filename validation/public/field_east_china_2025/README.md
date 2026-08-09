# FIELD-EAST-CHINA-2025 — données terrain d'un pipeline de produits pétroliers

## Source primaire

Likun Wang, Qi Wang, Hongchao Wang, Min Xiong, Shoutian Jiao, Xu Sun,
*A Leak Identification Method for Product Oil Pipelines Based on Flow Rate Balance: Principles and Applications*,
Processes 13(8), 2459 (2025), DOI `10.3390/pr13082459`.

Article en accès libre CC BY 4.0.

## Ce qui est réellement industriel

L'étude porte sur un **pipeline de produits pétroliers en exploitation en Chine de l'Est** :

- longueur totale de ligne principale : **615 km** ;
- capacité de conception : **3,0 Mt/an** ;
- pression de conception : **8 MPa** ;
- 8 stations : station initiale, 2 stations de raclage, 2 stations de pompage, 2 stations de dérivation et terminal ;
- 18 chambres de vannes de ligne ;
- transport batch : plusieurs diesels et essences.

Les auteurs ont réalisé six décharges d'huile contrôlées sur le terrain pour simuler des fuites.

## Tronçon publiquement reconstructible

La publication donne suffisamment de valeurs numériques pour reconstruire le tronçon entre `Pigging Station 2` et `Pumping Station 2` :

- mileage amont : 355,710 km ; altitude : 59,80 m ;
- chambre de vanne 3 : 367,552 km ; altitude : 80,20 m ;
- station aval : 395,788 km ; altitude : 72,50 m ;
- longueur totale : **40,078 km** ;
- diamètre intérieur : **273,1 mm** ;
- produit pendant les essais : diesel ;
- masse volumique : **847,4 kg/m3** ;
- viscosité cinématique : **4,72e-6 m2/s** ;
- débit principal mesuré : **270 m3/h**.

Au point de contrôle publié à 14:01, les auteurs obtiennent `Re = 76 918`, retiennent le régime hydrauliquement lisse (`beta=0.0246`, `m=0.25`) et reconstruisent, à partir des pressions de terrain, un débit de **268,70 m3/h**, soit **0,48 %** d'écart avec le débitmètre de 270 m3/h.

## Pourquoi ce cas complète Seaway-LANL

`PUBLIC-SEAWAY-LANL-01` apporte la **complétude système** : près de 1 000 km, 23 nœuds, 9 pompes, injections, soutirages et référence cross-solver.

`FIELD-EAST-CHINA-2025` apporte la **preuve terrain réelle** : géométrie, altitudes, fluide et débit mesuré d'un vrai pipeline de produits pétroliers.

Les deux preuves ne doivent pas être mélangées :

- Seaway-LANL = modèle complet mais synthétisé ;
- East-China = installation réelle mais seulement un tronçon est complètement chiffré dans l'article.

## Données de fuite

`leak_tests.csv` reprend les six essais contrôlés publiés : heures d'ouverture/fermeture et volume déchargé. Ils seront utiles ultérieurement pour le module de détection de fuite ; ils ne servent pas à qualifier le moteur stationnaire du MVP comme moteur transitoire.

`reference_observation.csv` enregistre séparément le point publié à 14:01 :

- débit mesuré : **270 m3/h** ;
- débit reconstruit par les auteurs depuis les pressions : **268,70 m3/h** ;
- erreur publiée : **0,48 %** ;
- Reynolds annoncé : **76 918** ;
- régime lisse annoncé : `beta=0.0246`, `m=0.25`.

## Limite actuelle pour un rejeu PETROLE strict

L'article publie les signaux de pression sous forme de figures, mais pas l'intégralité des séries numériques brutes dans les tableaux accessibles. Sans les valeurs numériques exactes `p1(t)` / `p2(t)`, on ne doit pas inventer une pression pour forcer PETROLE à retrouver 270 m3/h.

Le cas est utilisé immédiatement pour :

1. vérifier les propriétés, géométrie, Reynolds et perte de charge à débit imposé ;
2. documenter la comparaison de formulation Altshul ↔ Leibenzon ;
3. rechercher les données brutes/supplémentaires des auteurs avant de déclarer une validation pression→débit indépendante dans PETROLE.

## Runner et règles de verdict

`deployment/scripts/vps/benchmark_east_china_2025.py` exécute **EC-01** via
les seules APIs publiques de PETROLE. Il construit trois nœuds (Pigging Station
2 → Valve Chamber 3 → Pumping Station 2), les deux arêtes de 11,842 km et
28,236 km, puis impose le débit terrain de 270 m3/h.

L'API requiert une pression absolue d'entrée et une MAWP ; la campagne emploie
respectivement **5 MPa** et **8 MPa** comme *adapter assumptions*. Elles ne
sont ni des mesures de terrain, ni des valeurs certifiées du tronçon, et sont
exclues des verdicts physiques et terrain. La rugosité n'est pas publiée ;
`epsilon=0` est donc uniquement le mapping explicite vers le régime lisse de
l'article.

Les verdicts ne sont pas interchangeables :

- `execution_gate` vérifie convergence, faisabilité, violations et warnings ;
- `physics_reproduction_verdict` vérifie le moteur à partir du débit imposé et
  des propriétés/géométries publiées ; ses trois contrôles (débit, Reynolds,
  perte Altshul) doivent rester sous **0,001 %** ;
- `published_reynolds_reconciliation_verdict` teste la cohérence interne des
  nombres publiés, avec un seuil diagnostique pré-déclaré de 0,5 % ;
- `field_data_comparison_verdict` reste `NOT_EVALUATED` puisque le débitmètre
  est l'entrée du calcul ;
- `predictive_validation_verdict` reste `NOT_EVALUATED` tant que les séries
  numériques de pressions terrain ne sont pas publiques.

## Exécution VPS EC-01

Le 9 août 2026, le runner a été exécuté contre l'instance PETROLE servant le
SHA `dde0481380cd792f20e15eb640bc3acc9d198bd0`. La preuve active dans le panel
est `BENCH-EAST-CHINA-2025-R3`; les tentatives R1 (parseur initial) et R2
(précédente porte de reproduction) sont archivées dans l'audit applicatif.

Le contrat API persistant a été validé : **3 nœuds**, **2 arêtes**, **0
équipement**. Chaque arête expose et respecte `from_node_code`, `to_node_code`,
`length_m`, `inner_diameter_m`, `roughness_m`, `mawp_pa`, `status` et `profile`.

HydroLiquid retourne `SIM_CONVERGED_WARN`, faisable, avec **zéro violation**.
L'unique warning est attendu : la pression de vapeur du diesel n'est pas publiée
et les contrôles vapeur/NPSH restent donc non conclusifs.

Les résultats EC-01 sont :

| Grandeur | Résultat |
| --- | ---: |
| Débit imposé / moteur | 270,000 m3/h / 270,000 m3/h |
| Reynolds PETROLE | 74 081,1445 |
| Perte Altshul analytique | 234,845707 m |
| Perte Altshul moteur | 234,845707 m |
| Écart moteur ↔ formule Altshul | `7,3e-14 %` |
| Perte Leibenzon sur mêmes entrées | 239,748531 m |
| Écart Altshul ↔ Leibenzon | `−2,044986 %` |

### Incohérence source non masquée

Avec exactement les valeurs de la Table 2 (`D=273,1 mm`, `nu=4,72e-6 m2/s`) et
le débit mesuré annoncé (`270 m3/h`), la formule donne `Re=74 081,1445`, alors
que l'article indique `Re=76 918`. L'écart est **−3,688 %**, supérieur au seuil
diagnostique de 0,5 %. PETROLE ne modifie ni diamètre, ni viscosité, ni débit
pour forcer la concordance : le verdict est donc `NOT_RECONCILED` et non PASS.

La preuve JSON est conservée sur le VPS dans
`var/validation-vps/benchmark-east-china-2025.json`. EC-01 prouve la
reproduction physique à entrées imposées et rend visible cette incohérence ; il
ne prouve pas encore une prédiction de débit par pression ni une certification
industrielle.

## Conditions pour EC-03

Il faut récupérer les valeurs numériques synchronisées des pressions aux deux
extrémités du tronçon, leur référence (absolue ou relative), l'horodatage, les
incertitudes instrumentales et, idéalement, température/rugosité. Alors
seulement PETROLE pourra recevoir les pressions sans débit imposé et comparer sa
prédiction à 270 m3/h.
