# Phase 6 — P6-B fondation réseau gaz stationnaire

Statut : implémenté comme brique de conservation et de topologie, **solveur gaz compressible complet non encore implémenté**.

## Références

- D07 §7 : conservation de masse aux noeuds et réseau orienté ;
- D07 §10 : réseau gaz réel séparé du moteur liquide ;
- D07 §13 : résidus numériques et bilan de masse traçables ;
- `docs/implementation/phase6_gas_execution.md` : sous-lot P6-B.

## Portée implémentée

Le module `hydro_gas.network_balance` fournit :

- des noeuds et conduites orientées avec provenance obligatoire ;
- validation d'unicité des identifiants et des références topologiques ;
- un débit massique signé par conduite ;
- des frontières externes explicites : injection positive, soutirage négatif ;
- gestion des écoulements inverses sans réécrire la topologie ;
- calcul du bilan massique par noeud ;
- résidu global et résidu nodal absolu maximal ;
- conservation des références de provenance des débits et frontières.

## Équation évaluée

Pour chaque noeud, la brique calcule uniquement :

`résidu = somme(m_entrant) - somme(m_sortant) + m_externe`

Elle ne transforme pas ce résidu en verdict industriel et ne définit aucune tolérance cachée.

## Limites volontaires

Cette implémentation **n'est pas** le solveur stationnaire gaz compressible final. Elle ne sélectionne ni Weymouth, ni Panhandle, ni une autre corrélation de conduite. Elle ne déduit pas non plus `Z`, la température, une perte de charge, une efficacité de compresseur ou une limite d'exploitation.

Le futur solveur P6-B devra être ajouté uniquement après sélection et documentation du modèle constitutif, de son domaine de validité, de ses sources et de ses jeux de validation indépendants. Il devra utiliser des pressions absolues, des propriétés gaz validées et conserver les diagnostics de convergence.

## Tests

`tests/test_gas_network_balance.py` couvre notamment :

- réseau équilibré injection → conduite → soutirage ;
- écoulement inverse ;
- refus d'un jeu incomplet de débits de conduites ;
- refus d'une conduite vers un noeud absent ;
- refus d'une frontière appliquée à un noeud absent.

## Statut scientifique

`IMPLEMENTED_FOUNDATION_NOT_FIELD_VALIDATED`

Cette brique est déterministe et testable mais ne constitue ni une validation thermofluide du solveur gaz, ni une qualification terrain, ni une certification ASME/API/ISO.
