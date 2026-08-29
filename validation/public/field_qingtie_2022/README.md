# FIELD-QINGTIE-2022 — candidat pipeline brut chauffé multi-stations

## Source primaire

Shanbi Peng, Zhe Zhang, Yongqiang Ji, Laimin Shi, *Optimization of Oil Pipeline Operations to Reduce Energy Consumption Using an Improved Squirrel Search Algorithm*, **Energies 15(20), 7453 (2022)**, DOI `10.3390/en15207453`.

Le cas est fondé sur l'exploitation réelle de la **Qingtie Fourth-Line**.

## Données publiques utiles

La famille d'articles sur ce système décrit notamment :

- longueur totale : **548,5 km** ;
- diamètre : **711 mm** ;
- brut à forte viscosité, transporté chauffé ;
- stations de pompage/chauffage ;
- pressions et températures d'entrée/sortie station par station ;
- nombre de pompes et vitesses ;
- valeurs réelles de débit massique publiées pour le régime de juillet 2018 ;
- coefficients de transfert thermique et températures du sol par section dans l'article.

`july_2018_station_observations.csv` conserve les valeurs numériques de la Table 7 de la source 2022 sans les présenter comme un réseau directement calculable par HydroLiquid.

## Pourquoi ce cas est important

Il est plus proche de l'usage cible PETROLE qu'un banc d'eau : longue distance, brut réel, pompes, chauffage et pressions de terrain. Il peut devenir une validation de niveau élevé lorsque le modèle thermique stationnaire axial sera dans le périmètre du produit et que les propriétés/géométries suffisantes seront disponibles.

## Pourquoi il ne ferme pas PUBLIC-VALIDATION-02 aujourd'hui

HydroLiquid MVP est un moteur stationnaire monophasique **isotherme** au sens où il ne résout pas l'évolution axiale de température. Or Qingtie est précisément un pipeline chauffé dont la viscosité varie avec la température et dont les conditions d'entrée/sortie de chaque station montrent des variations thermiques importantes.

De plus, les tableaux publics accessibles ne suffisent pas à reconstruire sans hypothèse gouvernante :

- chainage et altitude numérique de chaque station ;
- propriété complète `rho(T)` / `mu(T)` du brut exploité ;
- rugosité et diamètre hydraulique interne confirmé ;
- interprétation/synchronisation exacte des débits massiques différents publiés par station/section.

Par conséquent :

- `eligibility_status = BLOCKED_SCOPE_AND_INPUTS` ;
- `predictive_validation_verdict = NOT_EVALUATED` ;
- les données ne doivent pas être forcées dans un modèle isotherme puis présentées comme validation terrain du pipeline chauffé.

## Données à obtenir / phase cible

Ce cas doit être réouvert lors du lot « thermique pipeline » du cahier des charges. À ce moment, demander ou reconstruire de source contrôlée : chainages/altitudes, `rho(T)`, `mu(T)`, diamètre/roughness, pressions et températures synchronisées, débits par section, configuration exacte des pompes et incertitudes instrumentales.
