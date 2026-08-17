# P6-B — artefacts gouvernés d'échelle et d'initialisation

Statut : fondation logicielle, non qualifiée industriellement.

## Objectif

Le solveur P6-B exige des références de politique d'échelle et d'initialisation. Cette brique ferme le lien entre ces références et les valeurs réellement utilisées au runtime.

Aucune échelle et aucune valeur initiale ne sont générées automatiquement ici.

## Artefact d'échelle

`PreRegisteredStationaryWeymouthScaleArtifact` enregistre explicitement :

- `artifact_ref` ;
- `policy_ref` ;
- `policy_version` ;
- `source_ref` ;
- `registration_ref` ;
- échelle de pression au carré `Pa²` ;
- échelle de débit `kg/s` ;
- échelle de résidu massique `kg/s` ;
- échelle de résidu de conduite `Pa²` ;
- état `DRAFT` ou `APPROVED` ;
- `approval_ref` uniquement pour un artefact approuvé.

Les quatre valeurs doivent être finies et strictement positives via le même contrat `StationaryWeymouthNumericalScale` utilisé par le solveur.

Un artefact `DRAFT` ne peut pas être matérialisé pour l'exécution.

## Artefact d'initialisation

`PreRegisteredStationaryWeymouthInitialGuessArtifact` enregistre :

- identité et version de la politique ;
- problème exact ;
- empreinte SHA-256 du layout exact ;
- source ;
- pré-enregistrement ;
- état physique initial explicite ;
- état d'approbation et preuve d'approbation.

L'état initial reste exprimé dans les unités physiques PETROLE. Il est converti vers `p²` et les coordonnées adimensionnées uniquement au moment de préparer le solveur avec l'artefact d'échelle approuvé.

## Empreinte du layout

`stationary_weymouth_layout_sha256(...)` couvre de manière canonique :

- composantes connexes ;
- nœuds de pression fixée ;
- nœuds de pression inconnue ;
- ordre des débits de conduite ;
- nœuds de débit slack ;
- ordre des équations de masse ;
- ordre des équations de conduite.

Une initialisation approuvée pour un ordre d'inconnues ne peut donc pas être réutilisée silencieusement sur un autre layout.

## Chemin d'exécution gouverné

`solve_stationary_weymouth_with_approved_inputs(...)` exige :

1. contexte de qualification ;
2. critère de convergence approuvé ;
3. configuration TRF explicite ;
4. artefact d'échelle approuvé ;
5. artefact d'initialisation approuvé ;
6. paramètres de conduite sourcés.

Avant exécution, le chemin vérifie :

- `scale_artifact.policy_ref == context.scale_policy_ref` ;
- `initial_guess_artifact.policy_ref == context.initial_guess_policy_ref` ;
- correspondance du `problem_ref` ;
- correspondance de l'empreinte du layout ;
- correspondance méthode/représentation/politiques déjà vérifiée par le solveur bas niveau.

Le résultat `StationaryWeymouthGovernedSolveResult` conserve les références et approbations des deux artefacts en plus du résultat numérique complet.

## Non-objectifs

Cette brique ne décide pas :

- comment choisir une bonne échelle pour un site réel ;
- comment générer automatiquement un état initial ;
- quels seuils de convergence sont industriels ;
- si Weymouth est la formulation correcte pour un réseau réel.

Ces choix doivent être définis, sourcés, pré-enregistrés et qualifiés séparément.

## Tests

Les tests utilisent uniquement des valeurs et références `synthetic-test-only` et vérifient :

- stabilité de l'empreinte de layout ;
- sensibilité de l'empreinte à l'ordre des équations ;
- refus des artefacts `DRAFT` ;
- refus d'un layout différent ;
- conservation exacte des valeurs d'échelle approuvées ;
- résolution via le chemin gouverné ;
- présence des preuves d'approbation dans le résultat ;
- refus d'une politique d'échelle approuvée mais incompatible avec le contexte.
