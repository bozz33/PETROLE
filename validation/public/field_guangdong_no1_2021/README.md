# FIELD-GUANGDONG-NO1-2021 — candidat SCADA raffiné sans DRA

## Source primaire

Shengshi Wang et al., *The Data-Driven Modeling of Pressure Loss in Multi-Batch Refined Oil Pipelines with Drag Reducer Using Long Short-Term Memory (LSTM) Network*, **Energies 14(18), 5871 (2021)**, DOI `10.3390/en14185871`.

## Pourquoi Pipeline No.1 est prioritaire

Les auteurs étudient sept conduites réelles du réseau de produits raffinés du Guangdong à partir de données SCADA de production. Ils déclarent que les données brutes comprennent les pressions d'entrée et de sortie des stations, le débit de la conduite et la densité de l'huile.

Le **Pipeline No.1 ne contient pas de drag reducer** : il est donc le meilleur des sept pour une comparaison avec le moteur stationnaire monophasique actuel.

Les métadonnées publiques sont :

- longueur : **38,71 km** ;
- diamètre intérieur : **0,392 m** ;
- différence d'altitude : **1,08 m** ;
- essence : `rho=760 kg/m3`, `nu=5.8e-7 m2/s` ;
- diesel : `rho=840 kg/m3`, `nu=4.0e-6 m2/s`.

Voir `published_metadata.csv`.

## Validation prédictive prévue

Pour chaque timestamp mono-produit ou batch suffisamment identifié :

1. fournir `P_in`, `P_out`, géométrie, altitude et propriétés au solveur ;
2. masquer `Q_measured` ;
3. laisser HydroLiquid résoudre `Q` ;
4. comparer la prédiction au SCADA ;
5. publier MAE, RMSE, biais, MAPE et erreur max, sans calibrer après lecture des résultats.

## Blocage public

La publication indique explicitement que les données sont disponibles sur demande auprès de l'auteur correspondant et qu'elles ne sont **pas publiquement disponibles en raison d'une restriction du financeur**. Les tableaux donnent la géométrie et les propriétés mais pas les séries temporelles numériques `P_in/P_out/Q` nécessaires à une exécution indépendante.

Par conséquent :

- `eligibility_status = BLOCKED_RAW_SCADA` ;
- `predictive_validation_verdict = NOT_EVALUATED` ;
- aucun point ne sera extrait approximativement des figures pour obtenir artificiellement un PASS de niveau terrain.

## Données à obtenir

Pour le Pipeline No.1 : timestamp, produit ou composition de batch, `P_in`, `P_out`, `Q`, densité, température si disponible, unités/référence de pression et métadonnées d'instrumentation. Le débit sera conservé hors des entrées PETROLE au moment de la validation.
