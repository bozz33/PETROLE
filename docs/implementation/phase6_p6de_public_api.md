# Phase 6 P6-D/P6-E — façade publique du moteur mixte

Statut : `IMPLEMENTED_STABLE_FACADE_NOT_INDUSTRIALLY_QUALIFIED`.

## Objet

`hydro_gas.stationary_equipment_api` fournit un point d'import stable pour les couches backend, UI et intégration qui consomment le moteur stationnaire conduites + compresseurs actifs.

La façade regroupe uniquement les contrats déjà séparés et testés :

- définition du problème/layout ;
- état candidat et évaluation physique ;
- représentation numérique et bornes ;
- gouvernance échelle/initialisation/convergence ;
- solveur borné ;
- export canonique ;
- adaptateur P6-H ;
- artefact de chaîne de preuve benchmark.

## Pourquoi une façade dédiée

Le paquet racine ne doit pas devenir un registre indifférencié des détails scientifiques internes. La façade permet aux couches applicatives d'importer une API cohérente sans dépendre de la structure physique des modules P6-D/P6-E/P6-H.

## Sémantique

L'existence de cette façade ne change aucun statut scientifique :

- solveur mixte implémenté ;
- critères/artefacts d'exécution toujours gouvernés ;
- benchmark mixte non encore qualifié sur des cas indépendants ;
- aucune certification ;
- aucune commande procédé.

Les modules internes restent accessibles aux tests scientifiques, tandis que les nouvelles intégrations applicatives doivent préférer la façade lorsque le contrat qu'elles utilisent y est exposé.
