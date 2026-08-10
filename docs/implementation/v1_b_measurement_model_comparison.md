# V1-B — comparaison mesure ↔ modèle

Statut : contrat d’implémentation Pilote/V1, sans effet de certification.

Base documentaire : D04 FR-DAT-005, D09, D12, D17, D20.

Base logicielle : `feat/pilot-v1-timeseries-explorer` à `7aacd47b7cd6e74b7c2afb6228ed738268557d07`.

## 1. But

Comparer explicitement des mesures terrain qualifiées à une sortie de simulation stationnaire PETROLE et calculer des résidus reproductibles, sans transformer cette comparaison en calibration implicite.

Le lot doit produire au minimum : résidus signés, biais, MAE, RMSE, nombre de points comparés et bilan des exclusions. Il reste analytique, hors contrôle-commande et hors certification industrielle.

## 2. Principes non négociables

- La mesure et la simulation restent deux sources distinctes et traçables.
- Aucun tag n’est associé silencieusement à une sortie calculée à partir de son nom.
- La correspondance `tag → objet calculé → métrique` est explicite, versionnée et validée.
- Les comparaisons s’effectuent en unités SI.
- Les mesures `bad` sont exclues par défaut mais restent comptées et consultables.
- Aucune interpolation, correction, substitution ou lissage n’est appliqué sans option explicite et trace de traitement.
- Une comparaison ne modifie ni le dataset, ni `SampleRaw`, ni `SampleNormalized`, ni le calcul source.
- Une calibration future ne pourra pas réutiliser comme validation indépendante les mêmes données/régimes qui ont servi à l’ajustement.

## 3. Périmètre V1-B1

Première tranche : comparaison d’un régime stationnaire sur une fenêtre temporelle explicite.

Entrées :

- un `MeasurementTag` ;
- une `processing_version` de série normalisée ;
- une fenêtre `[start_timestamp, end_timestamp]` ;
- une politique qualité ;
- un `CalculationRun` terminé ;
- une cible calculée explicite ;
- une métrique compatible avec la dimension du tag.

Cibles initiales autorisées :

- `node.pressure_pa` ;
- `edge.flow_m3_s` ;
- `edge.pressure_min_pa` / `edge.pressure_max_pa` uniquement si la sémantique du tag le justifie explicitement ;
- `pump.suction_pressure_pa` ;
- `pump.discharge_pressure_pa` ;
- `pump.flow_m3_s`.

Toute autre métrique reste hors contrat tant que son extraction et sa dimension ne sont pas définies.

## 4. Contrat de correspondance

Créer une correspondance versionnée contenant au minimum :

- `organization_id` ;
- `project_id` ;
- `tag_id` ;
- `target_type` (`node`, `edge`, `pump`) ;
- `target_id` ;
- `metric` ;
- `dimension` ;
- `si_unit` ;
- `status` (`draft`, `approved`, `archived`) ;
- `source_ref` / commentaire métier ;
- auteur et horodatage d’approbation.

La cible doit appartenir au même projet/site logique que le tag. Une correspondance approuvée devient immuable ; toute évolution crée une nouvelle version.

## 5. Sémantique de comparaison stationnaire

Le moteur MVP/Pilote est stationnaire. Une simulation produit donc une valeur de référence constante pour un régime calculé donné.

Pour chaque échantillon admissible de la fenêtre :

`residual_i = measured_si_i - simulated_si`

Les KPI sont calculés sur les mêmes points :

- `bias = mean(residual_i)` ;
- `MAE = mean(abs(residual_i))` ;
- `RMSE = sqrt(mean(residual_i²))` ;
- `min_residual` ;
- `max_residual` ;
- `n_compared` ;
- `n_excluded_quality` ;
- `n_excluded_outlier` uniquement si une politique explicite demande l’exclusion ; par défaut les aberrants restent inclus et seulement signalés.

Un bilan dimensionnel doit être calculé lorsque la grandeur le permet, par exemple écart moyen relatif, mais aucune tolérance d’acceptation industrielle arbitraire ne doit être codée en dur.

## 6. Qualité et exclusions

Par défaut :

- `good`, `uncertain`, `substituted`, `estimated` restent sélectionnables ;
- `bad` est exclu des KPI ;
- les doublons restent visibles et la politique de sélection doit être explicite ;
- les trous ne sont jamais interpolés automatiquement ;
- les aberrants détectés par V1-A3 sont annotés, pas supprimés silencieusement.

La réponse doit restituer les compteurs par motif d’exclusion.

## 7. Persistance proposée

Ajouter des objets immuables de comparaison, séparés des calculs et de la calibration :

- `measurement_model_mappings` : correspondances tag/cible/métrique ;
- `measurement_comparisons` : exécution d’une comparaison ;
- `measurement_residuals` : points comparés et résidus, ou stockage équivalent borné/partitionnable si le volume l’impose.

Une comparaison doit mémoriser :

- IDs des sources ;
- hash des entrées ;
- version de traitement de la série ;
- `calculation_id` et `input_hash` du calcul ;
- fenêtre temporelle ;
- politique qualité ;
- KPI ;
- statut et diagnostics ;
- version du code/moteur qui a produit la comparaison.

## 8. API cible

Contrat minimal :

- `POST /measurement-model-mappings` ;
- `GET /measurement-model-mappings` ;
- `POST /measurement-comparisons` ;
- `GET /measurement-comparisons/{id}` ;
- `GET /measurement-comparisons/{id}/residuals`.

L’API doit refuser :

- dimensions incompatibles ;
- cible absente ou hors projet ;
- calcul non terminé ;
- fenêtre vide ;
- série/version de traitement inexistante ;
- association implicite par nom de tag ;
- métrique non supportée.

## 9. UI ingénieur

Ajouter une vue de comparaison depuis Données/Résultats :

- choix du tag et de la version de traitement ;
- choix d’une correspondance approuvée ;
- choix du calcul source ;
- période ;
- filtres qualité ;
- graphe mesures + référence simulée ;
- graphe ou panneau des résidus ;
- cartes KPI biais/MAE/RMSE/n ;
- table paginée/scrollable avec timestamp, mesure SI, simulation SI, résidu, qualité et lignage.

La vue doit afficher clairement `Comparaison`, et jamais `Calibration`, tant que V1-C n’est pas engagé.

## 10. Critères d’acceptation V1-B1

- cas pression : valeurs en bar importées puis comparées en Pa sans perte de provenance ;
- cas débit : unité source variable normalisée avant comparaison ;
- résidus signés vérifiés sur jeu déterministe ;
- biais, MAE et RMSE vérifiés analytiquement ;
- `bad` exclu des KPI mais visible dans le bilan ;
- incompatibilité dimensionnelle refusée ;
- calcul source et série source restent immuables ;
- idempotence ou hash d’entrée empêche les doublons logiques ;
- tests PostgreSQL, Ruff, mypy, Vitest/Playwright si UI incluse ;
- migrations upgrade/downgrade et `alembic check` verts ;
- CI GitHub complète verte avant fermeture.

## 11. Hors portée V1-B

- ajustement de rugosité, viscosité ou paramètres pompe ;
- optimisation de paramètres ;
- tolérance de conformité industrielle codée en dur ;
- SCADA temps réel ;
- transitoires ;
- fuite ;
- certification.

## 12. Porte avant V1-C

La calibration ne démarre qu’après validation de V1-B sur au moins deux régimes distincts et après définition explicite :

- du dataset/régime de calibration ;
- du dataset/régime tenu hors ajustement pour validation ;
- des paramètres ajustables et de leurs bornes physiques ;
- de la fonction objectif ;
- des métriques d’acceptation convenues avant lecture du résultat de validation.
