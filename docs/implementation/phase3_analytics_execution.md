# Phase 3 — Data analytics

Statut : fondations d’implémentation post-MVP, non certifiantes.

Base logicielle de travail : `6d18ef39d16c2dd9ae34128ccf6d87f4788e19bc` (V1-B1), avant intégration finale dans `main`.

## 1. Références projet

- D04 : FR-DAT-004 / FR-DAT-005 et exigences de traçabilité.
- D09 / D12 : séries brutes, normalisées, qualité et versions de traitement.
- D17 : Phase 3 — historique, qualité, comparaison, prévisions et maintenance.
- D19 : interface données/qualité et comparaison mesure-modèle.
- D20 : séparation calibration/validation et données pilotes.

## 2. Périmètre produit

La Phase 3 étend les fondations V1 sans remplacer l’historian industriel ni introduire de commande procédé.

Sous-lots :

1. P3-A — agrégations temporelles déterministes et tendances ;
2. P3-B — complétude, latence, stagnation et dérives ;
3. P3-C — comparaison multi-régimes et suivi des KPI ;
4. P3-D — prévisions analytiques explicables avec horizon et incertitude ;
5. P3-E — indicateurs de maintenance conditionnelle, sans diagnostic automatique de sûreté ;
6. P3-F — tableaux de bord et exports versionnés.

## 3. Règles scientifiques

- aucune prédiction n’est produite sans jeu d’apprentissage et de validation identifiés ;
- séparation stricte apprentissage/calibration/validation/test ;
- aucune valeur `bad` n’entre silencieusement dans un modèle ;
- toute interpolation, agrégation ou imputation est versionnée et traçable ;
- les modèles statistiques publient variables, fenêtre, métriques, version et empreinte des données ;
- absence de seuil industriel arbitraire codé en dur ;
- les résultats sont des aides à l’analyse, pas des alarmes de sécurité.

## 4. Fondations déjà codées

### P3-A — agrégations et tendances

- fenêtre temporelle explicite ;
- filtre qualité ;
- pas de réécriture des échantillons ;
- buckets déterministes UTC ;
- `count`, `min`, `max`, `mean`, `stddev` ;
- taux de complétude lorsque l’intervalle attendu est fourni ;
- pente de tendance uniquement si le nombre de points est suffisant ;
- lignage vers le tag, la version de traitement et la plage source.

### P3-D — baseline de prévision contrôlée

- split chronologique strict `train / validation / test` ;
- ajustement OLS uniquement sur `train` ;
- aucune réutilisation de validation/test pour réajuster le modèle ;
- MAE, RMSE et biais calculés séparément sur les trois jeux ;
- rejet d’un split qui crée une fuite temporelle ;
- modèle linéaire utilisé comme baseline explicable, pas comme prédicteur industriel validé.

### P3-E — maintenance conditionnelle non-sûreté

- baseline statistique versionnée avec unité SI et provenance ;
- écart normalisé par rapport à la baseline ;
- seuils `watch` et `investigate` fournis explicitement par le contexte métier ;
- aucun seuil industriel par défaut ;
- aucune commande, alarme procédé ou ordre automatique de maintenance.

## 5. Porte avant publication P3-D/P3-E

Les capacités prédictives/conditionnelles ne deviennent publiables sur un pilote qu’après :

- données terrain suffisantes ;
- horizon métier convenu ;
- baseline naïve documentée ;
- protocole train/validation/test figé ;
- métriques choisies avant observation du test ;
- seuils conditionnels justifiés et approuvés ;
- revue ingénieur des variables et limites d’usage.

## 6. Hors portée

- SCADA/OPC UA : Phase 5 ;
- multiproduit/transitoires : Phase 4 ;
- gaz : Phase 6 ;
- détection de fuite/jumeau : Phase 7 ;
- HA multi-sites/certification : Phase 8.
