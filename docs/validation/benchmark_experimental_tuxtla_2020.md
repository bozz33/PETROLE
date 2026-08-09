# Benchmark expérimental — conduite de Tuxtla 2020

## Résultat

Le 9 août 2026, le moteur `long_distance_liquid` de PETROLE a rejoué les six
points permanents du banc physique serpentin de l'Institut technologique
national du Mexique, à Tuxtla Gutiérrez. Les six calculs ont convergé et
l'écart maximal sur la perte de charge est de **0,513 %**.

Le projet conservé dans l'instance est `BENCH-TUXTLA-2020`, modèle
`Modèle publié — conduite équivalente`. La preuve machine complète est
archivée sur le VPS dans
`/opt/petrole/var/validation-vps/benchmark-tuxtla-2020.json`.

| Point | Perte de charge publiée (m) | PETROLE (m) | Écart relatif |
| --- | ---: | ---: | ---: |
| B01 | 2,146500 | 2,135486 | -0,513 % |
| B02 | 2,950100 | 2,946357 | -0,127 % |
| B03 | 3,851700 | 3,852715 | +0,026 % |
| B04 | 4,850900 | 4,847377 | -0,073 % |
| B05 | 5,950100 | 5,939165 | -0,184 % |
| B06 | 7,129900 | 7,116087 | -0,194 % |

Critère du rejeu : écart de perte de charge inférieur ou égal à 1 %. Résultat :
**6/6 conformes**.

## Référence et données

La source primaire est l'article en accès libre de Santos-Ruiz, López-Estrada,
Puig et Valencia-Palomo, « Simultaneous Optimal Estimation of Roughness and
Minor Loss Coefficients in a Pipeline », *Mathematics and Computational
Applications*, 25(3), 56, 2020, DOI
[10.3390/mca25030056](https://doi.org/10.3390/mca25030056).

L'article décrit un prototype réel : un réservoir de 2 500 L, une pompe
centrifuge de 5 hp pilotée par variateur, 84,58 m de conduite et 18 coudes à
90°. Il publie les six couples de hauteurs aux extrémités, débits et viscosités
cinématiques utilisés ci-dessus, ainsi que la longueur équivalente calibrée de
112,2238 m et la rugosité relative `ε/D = 3,4652e-4`.

Le modèle PETROLE utilise une conduite horizontale équivalente de 112,2238 m,
un diamètre intérieur de 0,0486001 m (déduit des valeurs publiées `Q`, `ν` et
`Re`), `ε/D = 3,4652e-4`, de l'eau à 1 000 kg/m³ et la corrélation
Colebrook–White. Les coudes sont représentés par la longueur équivalente
publiée ; ils ne sont donc pas décomposés individuellement dans ce benchmark.
La viscosité retenue est la moyenne des six mesures (`8,36e-7 m²/s`), ce qui
explique les faibles écarts résiduels.

## Portée et limite de la conclusion

Ce résultat apporte une preuve supplémentaire que le noyau hydraulique
stationnaire monophasique reproduit correctement un banc physique publié, dans
ce domaine de débit turbulent et pour les données entrées.

Il ne constitue pas une certification de PETROLE ni une autorisation
d'exploitation d'un oléoduc. Les paramètres de rugosité et longueur équivalente
ont été calibrés dans l'article à partir de ces mêmes mesures : c'est donc une
reproduction de régression expérimentale, pas une prédiction indépendante. Il
ne couvre ni produits pétroliers réels, ni transitoires/coups de bélier, ni
écoulement multiphasique, ni courbes constructeur, ni qualification normative
ou validation par un ingénieur responsable.
