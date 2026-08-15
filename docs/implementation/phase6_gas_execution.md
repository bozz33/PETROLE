# Phase 6 — Gazoducs et compression

Statut : moteurs stationnaires exécutables et gouvernés, **non benchmarkés pour usage industriel et non certifiants**.

Base de travail : `main = 6c0ed6aa1632eef0cb207f5ec3bcce9c382a140e`. La branche Phase 6 reste indépendante et la PR demeure draft.

## 1. Références projet

- D07 : modèles thermofluides et limites ;
- D08 : ASME B31.8, ISO 13623 et références compresseurs sélectionnées par projet ;
- D10 : validation scientifique ;
- D17 : Phase 6 — gaz et compression ;
- D20 : pilote gaz futur.

## 2. Sous-lots

1. P6-A — propriétés gaz/composition et enveloppes de validité ;
2. P6-B — conduite gaz stationnaire compressible ;
3. P6-C — line-pack et inventaire ;
4. P6-D — compresseurs via cartes fournisseur versionnées ;
5. P6-E — stations, régulation, soutirages/injections ;
6. P6-F — optimisation énergétique sous contraintes ;
7. P6-G — résultats et rapports gaz ;
8. P6-H — benchmarks indépendants et pilote.

## 3. P6-A — propriétés gaz

Implémenté comme fondation :

- état minimal `p/T/M/Z` en unités absolues ;
- densité calculée uniquement avec `Z` explicitement fourni ;
- composition molaire explicite et source obligatoire ;
- masse molaire de mélange `Σ yᵢ Mᵢ` ;
- adaptateur CoolProp avec enveloppe d'évaluation contrôlée.

Reste à qualifier pour les cas industriels : compositions représentatives, méthodes de propriétés retenues par projet, domaines P/T/composition et validation indépendante.

## 4. P6-B — conduite Weymouth stationnaire

### Implémenté

- topologie gaz séparée du moteur liquide ;
- bilan massique nodal avec injections/soutirages et flux inverses ;
- registre de modèles constitutifs, domaine/hypothèses/source/version ;
- binding unique conduite → modèle/version → paramètres SHA-256 ;
- équation Weymouth SI évaluée sous la forme `p_to² - p_from² + K f|f|` ;
- `K = λ L a² / (D A²)` calculé uniquement depuis les paramètres fournis ;
- artefacts canoniques/hashés des paramètres Weymouth ;
- problème `pressure-slack` structurellement carré ;
- état candidat et assemblage séparé des résidus masse `kg/s` / conduite `Pa²` ;
- représentation numérique `p²` avec échelles explicites ;
- round-trip état physique ↔ vecteur numérique ;
- fonction pure `x -> r(x)` ;
- artefacts d'échelle et d'initialisation pré-enregistrables puis `APPROVED` ;
- critère de convergence pré-enregistrable puis `APPROVED` ;
- solveur borné SciPy `least_squares(..., method="trf")` ;
- `SciPy success` conservé séparément de `PETROLE CONVERGED` ;
- aucun seuil industriel implicite.

### Qualification

Le moteur P6-B est **implémenté** mais n'est pas déclaré `benchmarked` pour usage industriel. Un résultat numérique convergé démontre seulement que le système fourni satisfait les critères explicitement approuvés pour cette exécution.

## 5. P6-C — line-pack

Implémenté comme fondation : line-pack segmenté `ΣρAΔx` à partir de propriétés fournies.

Reste : couplage à des scénarios réseau représentatifs, validation indépendante et, plus tard, vraie dynamique/transitoire gaz.

## 6. P6-D/P6-E — réseau avec compresseurs actifs

### Carte et enveloppe

- cartes compresseur avec source/version obligatoires ;
- interpolation débit/vitesse uniquement dans le domaine fourni ;
- extrapolation systématiquement refusée ;
- domaine de débit de carte exposé à vitesse imposée ;
- entre deux lignes de vitesse, le domaine utilisable est l'intersection des domaines des deux lignes ;
- enveloppes de débit fournisseur versionnées ;
- interpolation des limites d'enveloppe sans marge cachée.

### Problème mixte

Le premier problème couplé supporté est : conduites Weymouth + compresseurs **actifs à vitesse imposée**.

Le layout compte :

- `(N-K)` pressions inconnues ;
- `E` débits de conduites ;
- `C` débits compresseurs ;
- `K` débits externes slack.

Les équations sont :

- `N` bilans massiques ;
- `E` relations Weymouth ;
- `C` contraintes de rapport de pression issues des cartes.

Le système est donc structurellement carré : `N + E + C` inconnues et `N + E + C` équations.

### Chemin scientifique canonique

`x -> état physique -> bilan massique équipements + Weymouth + cartes compresseurs -> r(x)`.

Les trois familles de résidus restent distinctes :

- masse en `kg/s` ;
- Weymouth en `Pa²` ;
- compresseur en `Pa`.

### Bornes

- `p² >= 0` ;
- débits compresseurs bornés par `domaine carte ∩ enveloppe fournisseur` lorsque l'enveloppe est disponible ;
- intervalle vide/dégénéré refusé ;
- aucune borne métier de conduite ou slack inventée.

### Gouvernance et solveur

Implémenté :

- artefact d'échelle mixte `DRAFT/APPROVED` ;
- artefact d'initialisation lié au `problem_ref` et au SHA-256 du layout exact ;
- critère de convergence mixte `DRAFT/APPROVED` ;
- contrôle optionnel séparé des maxima masse/Weymouth/compresseur ;
- solveur borné SciPy TRF consommant uniquement les entrées approuvées ;
- initialisation hors domaine refusée avant l'optimiseur ;
- absence d'enveloppe opérationnelle explicitement reportée par `missing_operational_envelope_compressor_ids`.

Le solveur mixte est **implémenté mais non benchmarké/qualifié**.

## 7. Ce que le solveur compresseur ne fait pas encore

Il ne calcule pas encore :

- puissance absorbée validée ;
- température de refoulement validée ;
- limites moteur/turbine ;
- recycle ;
- anti-surge opérationnel ;
- choke/stonewall dynamique ;
- commande de vitesse ;
- commande de vanne ou bypass ;
- dispatch automatique d'une station multi-unités.

Ces fonctions exigent des modèles thermodynamiques et données constructeur réellement sourcés.

## 8. P6-F — optimisation énergétique

Implémenté : sélection déterministe parmi des plans **déjà évalués**, avec preuves explicites de contraintes. Un candidat sans preuve est rejeté et l'infaisabilité est explicite.

Non implémenté/qualifié : NLP/MILP/MINLP réseau couplé, choix automatique de vitesse/ON-OFF ou commande d'exploitation.

Aucune optimisation continue ne doit être activée avant qualification suffisante des modèles physiques et contraintes.

## 9. P6-G — résultats et traçabilité

Implémenté :

- export JSON canonique de résultats déjà calculés ;
- SHA-256 des octets exportés ;
- versions de modèle, composition/propriétés, hypothèses et diagnostics ;
- aucun recalcul scientifique dans la couche d'export ;
- adaptateur dédié du solveur mixte conservant état final, résidus, bornes, diagnostics SciPy et preuves d'approbation ;
- les bornes numériques non finies sont exportées comme `null` avec sémantique explicite `unbounded`, afin de respecter le JSON canonique sans `NaN/Infinity`.

Reste : rapports PDF/Excel et vues métier gaz complètes.

## 10. P6-H — validation externe

### Référence réelle disponible

Runner GasModels réellement exécuté :

- GasModels `0.13.4` ; commit `21422f18e7e328732ec8edd7995446d33f58e789` ;
- `WPGasModel` / `solve_gf` / Ipopt ;
- cas `case-6-gf.m` ;
- run figé `31657331294` ;
- artifact id `9164893821` ;
- ZIP digest `sha256:66f04db97d1ab1b8cd8ddffad9e1b14e74b5bf6d5b1f870bb0be01bddccd1831` ;
- input SHA-256 `9ebe79b0ac61892af4db71b5d78190a46cc1269a3942d0b18217dec1d28bf5ac` ;
- JSON référence SHA-256 `1ad529221dc0f4e05e30f0e73c1e01b8b4c80925f65d135a4c9b908a902e386e` ;
- Manifest Julia SHA-256 `831a5243dbd9b30278946313063ed46918d5d4f7652e09ea1d229b1adde1b16b` ;
- terminaison `LOCALLY_SOLVED` ; objectif `0.0`.

Cette exécution valide la recette de référence externe, **pas les solveurs PETROLE**.

### Protocole PETROLE

- observations et critères de benchmark versionnés ;
- `DRAFT` interdit pour une comparaison acceptée ;
- `APPROVED` exige une preuve d'approbation ;
- modèle/version/formulation/cas/grandeur/unité doivent correspondre exactement ;
- aucune tolérance GasModels n'est déduite automatiquement ;
- hash du résultat externe = preuve d'une exécution, pas garantie de reproductibilité bit à bit.

## 11. Règles scientifiques obligatoires

- gaz et liquide restent deux domaines séparés ;
- aucune corrélation, propriété, efficacité, marge ou limite machine inventée ;
- cartes brutes et sources conservées/versionnées ;
- extrapolation hors domaine refusée ;
- bilan massique, loi de conduite et modèle compresseur restent des couches distinctes ;
- tout solveur publie méthode, représentation, scaling, initialisation et convergence ;
- `success` d'un optimiseur n'est jamais équivalent à validation scientifique ;
- `benchmark_ready`/`benchmarked` sont des statuts internes, jamais une certification ;
- la couche export ne recalcule jamais la physique ;
- aucune comparaison cross-solver n'est utilisée comme validation si les critères ont été choisis après observation des résultats.

## 12. Gates avant qualification/publication industrielle

Il reste obligatoirement :

1. plusieurs cas indépendants de validation ;
2. critères numériques pré-enregistrés avant comparaison ;
3. compositions et propriétés gaz représentatives ;
4. cartes/enveloppes constructeur réelles ou références publiques adéquates ;
5. validation des modèles de puissance/température compresseur ;
6. revue ingénieur gaz/thermofluides ;
7. documentation des incertitudes et limites ;
8. pilote D20 avec données réelles/anonymisées ;
9. seulement ensuite qualification des modèles/solveurs pour le périmètre validé.

## 13. Normes et propriété intellectuelle

Les normes internationales sélectionnées restent les références principales. Les pages officielles servent à confirmer édition/statut ; les clauses protégées ne sont implémentées qu'à partir de copies légalement acquises et revues. Aucun texte normatif protégé n'est recopié dans le dépôt.

## 14. Hors portée opérationnelle actuelle

- commande compresseur/vanne ;
- SIS ;
- anti-surge opérationnel ;
- certification ASME/API/ISO ;
- détection de fuite opérationnelle : Phase 7.
