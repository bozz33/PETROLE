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

## Limite actuelle pour un rejeu PETROLE strict

L'article publie les signaux de pression sous forme de figures, mais pas l'intégralité des séries numériques brutes dans les tableaux accessibles. Sans les valeurs numériques exactes `p1(t)` / `p2(t)`, on ne doit pas inventer une pression pour forcer PETROLE à retrouver 270 m3/h.

Le cas sera donc utilisé immédiatement pour :

1. vérifier les propriétés, géométrie, Reynolds et perte de charge à débit imposé ;
2. documenter la comparaison avec le résultat terrain publié de 268,70 m3/h ;
3. rechercher les données brutes/supplémentaires des auteurs avant de déclarer une validation pression→débit indépendante dans PETROLE.
