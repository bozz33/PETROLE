# Phase 6 P6-G — tables typées du solveur mixte

Statut : `IMPLEMENTED_PRESENTATION_ROWS_NO_RECOMPUTATION`.

## Objet

`build_stationary_active_compressor_result_tables(...)` transforme un résultat gouverné déjà calculé en tables typées destinées aux couches API, UI, PDF et Excel.

La couche ne résout rien et ne recalcule aucune grandeur.

## Tables produites

### Nœuds

- identifiant ;
- pression absolue `Pa` ;
- résidu massique `kg/s` ;
- provenance de la pression.

### Conduites

- identifiant ;
- débit massique signé `kg/s` ;
- résidu Weymouth `Pa²` ;
- différence de pression au carré ;
- terme de friction ;
- équation et provenance des paramètres.

### Compresseurs

- identifiant ;
- débit `kg/s` ;
- vitesse `rpm` ;
- rapport de pression ;
- rendement isentropique interpolé depuis la carte ;
- pression de refoulement attendue par la carte ;
- résidu de rapport de pression ;
- carte/version ;
- état et limites d'enveloppe lorsqu'elles existent.

### Frontières

- identifiant ;
- nœud ;
- débit massique signé ;
- provenance.

## Cohérence

La construction refuse les résultats dont les familles ne couvrent pas les mêmes entités :

- pression ↔ résidu massique ;
- débit conduite ↔ résidu Weymouth ;
- état compresseur ↔ contrainte de carte.

Les enveloppes opérationnelles manquantes sont conservées dans `warnings` et ne sont jamais masquées.

## Limite

Ces tables sont une représentation de résultats. Elles ne constituent ni un rapport d'ingénierie signé, ni une preuve de validation scientifique, ni une autorisation d'exploitation.
