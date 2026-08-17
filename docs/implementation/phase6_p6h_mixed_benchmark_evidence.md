# Phase 6 P6-H — chaîne de preuve canonique du benchmark mixte

Statut : `IMPLEMENTED_EVIDENCE_CHAIN_NO_QUALIFICATION_CLAIM`.

## Objet

Cette brique fige dans un JSON canonique la chaîne de traçabilité d'un benchmark conduites + compresseurs.

Elle relie :

- le `solve_ref` PETROLE et son statut exact ;
- le SHA-256 du résultat PETROLE exporté ;
- le solveur externe et les SHA-256 de son entrée et de sa sortie ;
- le protocole, le modèle, la version du modèle, le cas et la formulation ;
- les observations comparées ;
- les critères pré-enregistrés puis `APPROVED` ;
- les références d'approbation et d'enregistrement ;
- une référence de revue optionnelle.

## Schéma v2 et liaison au contexte APPROVED

Le schéma courant est `phase6/stationary-equipment-benchmark-evidence/2`.

Le paquet `ApprovedGasBenchmarkCriteria` transporte le contexte complet qui a servi à sa matérialisation. L'export de preuve mixte :

- sérialise `model_id` et `model_version` en plus du protocole ;
- sérialise le `case_ref` et le `formulation_ref` du contexte APPROVED ;
- refuse un `case_ref` fourni à l'export qui diffère du cas APPROVED ;
- refuse une formulation fournie à l'export qui diffère de la formulation APPROVED.

Cette règle empêche qu'un paquet de critères pré-enregistré pour un cas/formulation soit réutilisé silencieusement pour une autre comparaison.

## Propriétés

- sérialisation JSON déterministe (`sort_keys`, séparateurs compacts, aucun `NaN/Infinity`) ;
- SHA-256 des octets exacts ;
- validation des hashes sur 64 caractères hexadécimaux ;
- couverture exacte des observations par les critères approuvés ;
- refus des critères désalignés ou incomplets ;
- conservation d'un statut source `NON_CONVERGED` sans le transformer en succès ;
- liaison explicite au contexte APPROVED complet.

## Non-objectifs

L'artefact :

- ne recalcule aucune grandeur ;
- ne calcule aucune erreur absolue/relative ;
- n'applique aucune tolérance ;
- ne décide aucun `PASS/FAIL` ;
- ne déclare jamais le solveur `benchmark_ready`, `benchmarked`, qualifié ou certifié.

Les champs `qualification_claim` et `certification_claim` restent explicitement `false` dans cette version.

## Utilisation prévue

La preuve canonique est produite après :

1. exécution PETROLE ;
2. export canonique du résultat PETROLE ;
3. exécution d'une référence externe identifiée et hashée ;
4. construction des observations P6-H ;
5. matérialisation des critères `APPROVED` dans le contexte exact du modèle/cas/formulation ;
6. revalidation de ce contexte lors de l'export de preuve.

L'évaluation quantitative reste assurée par le contrat P6-H existant. La revue scientifique et la décision de qualification restent des étapes séparées.
