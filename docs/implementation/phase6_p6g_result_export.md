# Phase 6 — P6-G export versionné des résultats gaz

Statut : implémenté comme couche de restitution déterministe, **sans recalcul scientifique et sans qualification terrain**.

## Références

- D07 : propriétés gaz, line-pack, compresseurs, bilans et diagnostics traçables ;
- D17 : Phase 6 — gazoducs et compression ;
- D19 : résultats, hypothèses, diagnostics, fichiers et retour vers les données sources ;
- `docs/implementation/phase6_gas_execution.md` : sous-lot P6-G.

## Portée implémentée

Le module `hydro_gas.result_export` produit un JSON canonique à partir de résultats déjà calculés. L'enveloppe impose :

- une référence de calcul ;
- une version de modèle ;
- la provenance de la composition gaz ;
- la référence de la méthode de propriétés ;
- les résultats pré-calculés ;
- les diagnostics pré-calculés ;
- des hypothèses et références sources optionnelles ;
- un horodatage uniquement s'il est timezone-aware ;
- une version d'export ;
- une empreinte SHA-256 du contenu exact.

Le JSON est sérialisé avec clés triées, nombres non finis refusés et séparateurs stables. Deux payloads équivalents avec un ordre de clés différent produisent donc le même contenu et la même empreinte.

## Règle de non-recalcul

L'export **ne recalcule aucune grandeur scientifique**. Il ne déduit pas `Z`, densité, line-pack, débit, pression, rendement, marge compresseur ou résidu. Les valeurs présentes dans `results` et `diagnostics` sont sérialisées telles qu'elles ont été produites par les moteurs amont.

Cette séparation évite qu'un export ou un futur rapport PDF modifie silencieusement les résultats qualifiés.

## Limites volontaires

- aucun verdict de conformité ;
- aucun seuil d'exploitation ajouté ;
- aucune certification ASME/API/ISO ;
- aucun rapport gaz final tant que P6-B/P6-F et les benchmarks P6-H ne sont pas qualifiés ;
- aucun texte normatif protégé embarqué.

## Tests

`tests/test_gas_result_export.py` vérifie :

- déterminisme et adressage par contenu ;
- conservation des résultats pré-calculés ;
- provenance scientifique obligatoire ;
- refus des références vides ;
- refus des horodatages naïfs ;
- refus de `NaN` et autres nombres JSON non finis ;
- version d'export obligatoire.

## Statut scientifique

`IMPLEMENTED_RESTITUTION_FOUNDATION_NOT_FIELD_VALIDATED`

Cette brique améliore la traçabilité P6-G mais ne ferme pas les gates scientifiques de la Phase 6.
