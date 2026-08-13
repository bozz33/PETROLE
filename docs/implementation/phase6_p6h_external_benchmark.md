# Phase 6 — P6-H benchmark gaz externe

Statut : contrat de comparaison reproductible implémenté et **runner de référence GasModels ajouté**, sans valider encore le solveur gaz PETROLE.

## Références

- D10 : validation scientifique et comparaison indépendante ;
- D14 : GasModels.jl comme benchmark/service futur, avec contrat indépendant ;
- D17 : P6-H benchmarks indépendants et pilote gaz ;
- `phase6_gas_execution.md`.

## Objectif

`hydro_gas.external_benchmark` fournit une couche de comparaison indépendante du format interne du solveur externe. Cette séparation évite de lier le noyau PETROLE à une sérialisation GasModels, pandapipes ou autre qui pourrait évoluer.

La preuve du solveur externe conserve obligatoirement :

- nom du solveur ;
- version exacte observée ;
- référence de formulation ;
- référence du format de données ;
- SHA-256 du cas d'entrée ;
- SHA-256 du résultat externe ;
- provenance de l'exécution.

## Observations

Chaque observation de benchmark associe :

- un identifiant unique ;
- une grandeur ;
- une localisation ;
- une unité commune explicite ;
- la valeur PETROLE ;
- la valeur de référence ;
- les provenances des deux valeurs.

La couche calcule uniquement :

- erreur signée `PETROLE - référence` ;
- erreur absolue ;
- erreur relative lorsque la valeur de référence est non nulle.

Elle ne convertit pas silencieusement les unités et ne recalcule aucune grandeur scientifique.

## Critères

Les tolérances sont facultatives mais, lorsqu'elles existent, elles doivent être pré-enregistrées avec leur provenance. Aucun seuil par défaut n'est défini.

Un critère peut fournir :

- erreur absolue maximale ;
- erreur relative maximale ;
- ou les deux.

Une observation sans critère reste explicitement non évaluée. Elle n'est jamais transformée en `PASS`. Une erreur relative demandée avec une référence égale à zéro devient une violation explicite plutôt qu'une division masquée.

## GasModels : référence exécutable

D14 retient GasModels.jl comme outil de benchmark/service futur et non comme cœur universel. Le contrat PETROLE conserve donc la version du solveur et la référence de son format au lieu d'adopter son dictionnaire JSON comme modèle persistant du produit.

Un premier runner reproductible est maintenant présent :

- workflow : `.github/workflows/gasmodels-reference.yml` ;
- environnement : `tools/gasmodels_reference/Project.toml` ;
- exécution : `tools/gasmodels_reference/run_case6_wp.jl`.

### Référence verrouillée

Le runner utilise :

- dépôt upstream : `lanl-ansi/GasModels.jl` ;
- commit : `21422f18e7e328732ec8edd7995446d33f58e789` ;
- version déclarée GasModels : `0.13.4` ;
- cas upstream : `test/data/matgas/case-6-gf.m` ;
- problème : `solve_gf` ;
- formulation : `WPGasModel` ;
- solveur NLP : Ipopt ;
- Julia : série 1.10, version patch exacte enregistrée dans l'artefact ;
- action `julia-actions/setup-julia` épinglée sur le commit correspondant à v3.0.0.

L'environnement résolu produit un `Manifest.toml` archivé avec son SHA-256. La version exacte d'Ipopt et la version Julia réellement exécutée sont également inscrites dans l'artefact.

### Données archivées

Le runner conserve sans conversion implicite :

- pressions de jonctions `p` en valeur de sortie GasModels ;
- débits de conduites `f` ;
- débits des compresseurs `f` ;
- ratios des compresseurs extraits du champ `r` réellement utilisé par les tests GasModels 0.13.4, puis exposés sous le nom explicite `ratio` dans l'artefact PETROLE ;
- débits des deliveries, receipts et transfers lorsqu'ils sont présents ;
- statut de terminaison ;
- objectif ;
- temps solveur lorsque fourni ;
- métadonnées de base du cas ;
- commit GasModels ;
- hashes du cas, du projet Julia, du Manifest et du résultat JSON.

Les pressions et débits de solution sont étiquetés `_pu`. Le ratio compresseur est conservé comme grandeur sans dimension sous le champ `ratio`, sans suffixe `_pu`. Le runner ne fabrique aucune conversion SI ; toute conversion future devra être explicite, testée et attachée à la version GasModels concernée.

Le commit épinglé présente une divergence documentaire à connaître : la page de format de résultat montre un champ compresseur `ratio`, alors que `test/common.jl` vérifie le champ `r`. Le runner suit le comportement effectivement vérifié par les tests de la version 0.13.4 et enregistre cette référence dans l'artefact, afin que cette convention ne soit pas implicite.

### Contrôle upstream distinct du benchmark PETROLE

GasModels teste officiellement ce cas en exigeant un statut de résolution admissible et un objectif proche de zéro avec une tolérance absolue de `1e-6`. Le runner reproduit ce contrôle **uniquement comme contrôle d'intégrité de la référence upstream** et l'étiquette séparément dans l'artefact.

Cette tolérance n'est pas une tolérance PETROLE et ne doit jamais être réutilisée comme critère d'acceptation d'une pression, d'un débit ou d'un modèle constitutif.

### Déclenchement

Le workflow est :

- exécuté sur une pull request lorsque le runner ou son environnement changent ;
- disponible en déclenchement manuel après présence du workflow sur la branche par défaut ;
- isolé du workflow qualité principal pour ne pas transformer une référence externe en dépendance de disponibilité du produit.

L'artefact GitHub Actions est nommé `gasmodels-case-6-gf-wp-reference` et est conservé temporairement pour revue. Un résultat destiné à un dossier scientifique durable devra ensuite être copié dans le stockage de preuves du projet selon la gouvernance D10/D18.

## Ce que le runner ne fait pas

Le runner ne :

- convertit pas un modèle PETROLE vers GasModels ;
- compare pas encore PETROLE à GasModels ;
- définit pas de tolérance PETROLE ;
- valide pas Weymouth pour tous les réseaux gaz ;
- valide pas une installation réelle ;
- certifie pas un résultat ;
- commande aucun équipement.

Il fabrique seulement une **référence externe versionnée et hashée** à partir d'un cas upstream officiel.

## Gate scientifique suivant

Cette brique ne rend pas P6-B valide. Un benchmark P6-H publiable exige encore :

1. exécution réussie et archivage du runner de référence ;
2. revue des grandeurs réellement produites et de leur convention d'unités ;
3. formulation de conduite PETROLE sélectionnée et documentée ;
4. paramètres PETROLE du cas construits depuis les données de référence sans hypothèse cachée ;
5. critères PETROLE approuvés **avant** la comparaison ;
6. calcul PETROLE indépendant ;
7. comparaison observation par observation via `hydro_gas.external_benchmark` ;
8. revue thermofluides ;
9. répétition sur plusieurs cas couvrant le domaine revendiqué.

## Statut de qualification

`IMPLEMENTED_REFERENCE_RUNNER_NOT_PETROLE_VALIDATED`
