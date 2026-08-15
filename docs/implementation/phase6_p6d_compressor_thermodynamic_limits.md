# Phase 6 P6-D — limites thermodynamiques compresseur gouvernées

Statut : `IMPLEMENTED_APPROVAL_GATE_NO_VENDOR_LIMITS_BUNDLED`

## Objet

Cette couche permet de comparer les résultats thermodynamiques d'un compresseur
à des limites de puissance mécanique et/ou de température de refoulement
explicitement fournies par un dossier constructeur ou une règle projet
approuvée.

Elle ne contient **aucune valeur industrielle par défaut**.

## Contrat

Un jeu de limites est identifié par :

- `limit_set_id` ;
- `limit_set_version` ;
- `compressor_id` ;
- `source_ref` ;
- `registration_ref` ;
- éventuellement `maximum_shaft_power_input_w` ;
- éventuellement `maximum_actual_outlet_temperature_k`.

Au moins une limite explicite est obligatoire.

Un objet `DRAFT` ne peut pas porter une approbation active. Un objet
`APPROVED` doit porter `approval_ref`. Seuls les objets `APPROVED` peuvent être
matérialisés pour une évaluation.

## Comportement fail-closed

L'évaluation globale exige une couverture exacte : un jeu `APPROVED` par
compresseur thermodynamique actif, sans doublon.

Si le résultat source n'est pas `CONVERGED` :

- les valeurs observées restent conservées pour diagnostic ;
- aucune marge n'est présentée comme exploitable ;
- `shaft_power_within_limit = null` ;
- `outlet_temperature_within_limit = null` ;
- `all_approved_limits_passed = null`.

Ainsi, une valeur issue d'un résultat `NON_CONVERGED`, `OUT_OF_DOMAIN` ou d'un
autre statut non convergé ne peut jamais devenir un faux PASS par simple
comparaison numérique.

## Grandeurs actuellement couvertes

- puissance mécanique d'arbre entrante, en W ;
- température réelle de refoulement, en K.

Le moteur publie les marges algébriques `limite - valeur observée` lorsqu'elles
sont évaluables. Une puissance mécanique non positive est également conservée
comme diagnostic distinct ; elle n'est pas transformée en règle industrielle
implicite.

## Ce que cette couche ne fait pas

Elle ne choisit ni :

- puissance nominale moteur/turbine ;
- température maximale admissible ;
- marge de sécurité ;
- facteur de déclassement ;
- seuil anti-surge ;
- seuil de trip/SIS ;
- capacité station ;
- seuil d'acceptation réglementaire.

Ces valeurs doivent provenir de données constructeur, d'un référentiel projet
ou d'une exigence réglementaire identifiés et approuvés.

## Tests

Les valeurs numériques présentes dans les tests (`200 kW`, `350 K`, etc.) sont
**synthétiques** et servent uniquement à vérifier la mécanique du gate. Elles ne
constituent pas des limites PETROLE et ne doivent pas être réutilisées pour un
équipement réel.

## Qualification

Cette implémentation n'accorde aucune qualification ni certification :

- `qualification_claim = false` ;
- `certification_claim = false`.

La qualification P6-D reste conditionnée à des cartes/enveloppes réelles, des
limites constructeur sourcées, des cas thermodynamiques indépendants et une
revue ingénieur gaz/thermofluides.
