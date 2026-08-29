# FIELD-BN1-2022 — candidat prédictif brut chauffé

## Source primaire

Lixin Wei, Yu Zhang, Lili Ji, Lin Ye, Xuanchen Zhu, Jin Fu, *Pressure Drop Prediction of Crude Oil Pipeline Based on PSO-BP Neural Network*, **Energies 15(16), 5880 (2022)**, DOI `10.3390/en15165880`, CC BY 4.0.

## Installation publiée

Le cas utilise les données réelles de fonctionnement d'une conduite de brut du dépôt B au dépôt N1 dans le nord-est de la Chine. Après reconstruction en 2017 :

- longueur : **28,3049 km** ;
- spécification : **φ529×7 mm** ;
- pression de conception : **6,4 MPa** ;
- brut chauffé, à viscosité fortement dépendante de la température ;
- **2791** enregistrements sélectionnés par les auteurs ;
- l'article publie un échantillon numérique avec débit massique, température de départ, pression de départ, densité et perte de pression.

`published_sample.csv` transcrit l'échantillon numérique public. `outlet_pressure_mpa` est `DERIVED` par `P_start - ΔP`; il n'est pas une colonne originale du tableau.

## Potentiel pour PETROLE

Si les grandeurs critiques manquantes sont obtenues, ce jeu est presque idéal pour une validation prédictive :

1. convertir `mass_flow_t_h / density_kg_m3` en débit volumique mesuré ;
2. fournir à PETROLE la géométrie, le fluide, `P_start` et `P_out` ;
3. **ne pas fournir le débit mesuré** ;
4. comparer `Q_PETROLE` au débit dérivé du débitmètre massique.

## Blocages actuels

Le papier indique que la viscosité dépend de la température, mais ne publie pas la relation numérique viscosité-température ni une table de propriétés permettant un rejeu physique indépendant. Il explique également que l'altitude intervient dans le calcul de perte de charge, sans publier dans les données tabulaires la différence d'altitude numérique B → N1.

La spécification `φ529×7 mm` permet vraisemblablement de dériver un diamètre intérieur de 515 mm si elle suit la notation diamètre extérieur × épaisseur, mais cette interprétation doit rester `DERIVED_FROM_PIPE_SPEC` et ne remplace pas une confirmation de la source.

Par conséquent :

- `predictive_validation_verdict = NOT_EVALUATED` ;
- `eligibility_status = BLOCKED_CRITICAL_INPUTS` ;
- aucune viscosité ou différence d'altitude ne doit être choisie après coup pour rapprocher PETROLE des débits publiés.

## Données à obtenir

- altitude ou différence d'altitude B/N1 ;
- relation ou table `nu(T)` / `mu(T)` du brut réel ;
- confirmation du diamètre intérieur ;
- idéalement les 2791 lignes annoncées et les incertitudes des capteurs.
