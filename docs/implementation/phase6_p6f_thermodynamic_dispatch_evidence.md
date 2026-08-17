# Phase 6 — P6-F/P6-G — preuve thermodynamique pour la sélection énergétique

Statut : `IMPLEMENTED_FAIL_CLOSED_NO_VENDOR_LIMIT_BUNDLED`

## Objet

Ce lot relie le post-traitement thermodynamique des compresseurs à la sélection énergétique discrète P6-F **sans dupliquer les limites constructeur dans l'optimiseur**.

La chaîne est volontairement séparée :

1. le solveur stationnaire produit un état réseau/compresseurs ;
2. le post-traitement thermodynamique calcule les températures, enthalpies et puissances ;
3. des limites puissance/température explicitement pré-enregistrées puis `APPROVED` sont évaluées ;
4. P6-G exporte le résultat, les limites et leurs références dans un JSON canonique SHA-256 ;
5. l'adaptateur P6-F vérifie l'intégrité et la cohérence de cet export ;
6. P6-F reçoit uniquement un `GasDispatchConstraintEvidence` booléen et une référence SHA-256.

Aucune valeur limite n'est créée ou recopiée par P6-F.

## Implémentation

Modules principaux :

- `stationary_compressor_thermodynamic_limits.py` : gouvernance DRAFT/APPROVED et évaluation des limites ;
- `stationary_thermodynamic_result_export.py` : export P6-G canonique ;
- `thermodynamic_dispatch_evidence.py` : vérification de la preuve P6-G puis conversion en contrainte P6-F ;
- `energy_optimization.py` : classement énergétique des candidats déjà évalués.

Contrat public :

- `THERMODYNAMIC_LIMIT_DISPATCH_CONSTRAINT_ID = "stationary-compressor-thermodynamic-approved-limits"` ;
- `THERMODYNAMIC_LIMIT_EVIDENCE_REF_PREFIX = "sha256://petrole/gas/stationary-compressor-thermodynamics/"` ;
- `build_thermodynamic_limit_dispatch_constraint_evidence(...)`.

## Vérifications avant création de la preuve P6-F

L'adaptateur refuse la preuve si l'un des éléments suivants est incohérent :

- type média différent de `application/json` ;
- SHA-256 différent du contenu reçu ;
- export JSON UTF-8 invalide ;
- version d'export thermodynamique inattendue ;
- version de modèle thermodynamique inattendue ;
- `calculation_ref` différent du `solve_ref` évalué ;
- statut solveur différent ;
- état `all_limits_evaluable` différent ;
- verdict `all_approved_limits_passed` différent ;
- couverture compresseurs différente ou identifiants dupliqués ;
- dérive de `limit_set_id`, `limit_set_version`, `source_ref`, `registration_ref` ou `approval_ref` ;
- prétention de qualification ou de certification dans la preuve.

La référence finale utilisée par P6-F pointe vers le SHA-256 exact de l'export vérifié.

## Politique fail-closed

La contrainte P6-F est vraie uniquement lorsque :

```text
all_limits_evaluable == true
AND
all_approved_limits_passed == true
```

En particulier :

- limite dépassée -> `passed=false` ;
- solveur source non convergé -> limites inévaluables -> `passed=false` ;
- donnée manquante ou preuve incohérente -> exception, aucune preuve P6-F produite ;
- aucun fallback ne transforme un état inconnu en faisabilité.

Ainsi, un candidat moins énergivore mais thermodynamiquement inévaluable est rejeté de l'énumération faisable.

## Portée scientifique

Ce mécanisme **ne qualifie pas** le modèle thermodynamique ni les limites constructeur.

Il ne fournit :

- aucune limite de puissance par défaut ;
- aucune température maximale par défaut ;
- aucune marge industrielle implicite ;
- aucun rendement moteur/turbine implicite ;
- aucune logique anti-surge/SIS ;
- aucune commande compresseur ou vanne.

Les valeurs numériques utilisées dans les tests unitaires sont synthétiques et servent uniquement à vérifier le mécanisme logiciel. Elles ne constituent pas des limites PETROLE ni des recommandations d'exploitation.

## Tests couverts

`tests/test_gas_thermodynamic_dispatch_evidence.py` vérifie notamment :

- preuve valide -> contrainte P6-F satisfaite ;
- limites dépassées -> contrainte échouée ;
- limites inévaluables -> contrainte échouée ;
- candidat moins énergivore mais inévaluable rejeté au profit d'un candidat évaluable ;
- contenu altéré rejeté par SHA-256 ;
- mauvais `calculation_ref` rejeté ;
- dérive du verdict ou de l'approbation rejetée ;
- mauvaise version d'export/modèle rejetée.

## Gates restant avant qualification industrielle

La présence de ce pont ne change pas les gates scientifiques de Phase 6 :

- limites réelles issues de données constructeur ou projet sourcées et approuvées ;
- compositions de gaz naturel représentatives et méthode de mélange retenue ;
- validation indépendante de la thermodynamique compresseur ;
- plusieurs benchmarks réseau/compresseurs indépendants ;
- revue ingénieur gaz/thermofluides ;
- documentation des incertitudes et domaines de validité ;
- pilote D20 avant toute prétention industrielle.
