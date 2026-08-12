# Phase 6 — P6-H benchmark gaz externe

Statut : contrat de comparaison reproductible implémenté, **sans valider encore le solveur gaz PETROLE ni exécuter un solveur externe**.

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

## GasModels

D14 retient GasModels.jl comme outil de benchmark/service futur et non comme cœur universel. Le contrat PETROLE conserve donc la version du solveur et la référence de son format au lieu d'adopter son dictionnaire JSON comme modèle persistant du produit.

L'adapter d'exécution GasModels reste un sous-lot ultérieur : il devra convertir un cas PETROLE approuvé vers le format de la version GasModels verrouillée, exécuter la formulation sélectionnée, archiver les fichiers exacts et ramener uniquement les grandeurs nécessaires au contrat de benchmark.

## Gate scientifique

Cette brique ne rend pas P6-B valide. Un benchmark P6-H publiable exige encore :

- formulation de conduite gaz sélectionnée et documentée ;
- jeux de référence indépendants ;
- critères approuvés avant comparaison ;
- solveur externe et versions verrouillés ;
- revue thermofluides ;
- résultats reproductibles archivés.

## Statut de qualification

`IMPLEMENTED_BENCHMARK_CONTRACT_NOT_EXTERNALLY_VALIDATED`
