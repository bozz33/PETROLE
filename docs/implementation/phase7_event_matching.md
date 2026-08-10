# Phase 7 — Matching événements labellisés ↔ alertes

Références : D10, D15, D17 et D20.

## Implémentation

`hydro_leak.event_matching` associe des événements de vérité terrain à des alertes analytiques avec une règle de campagne explicitement fournie :

- événement : identifiant, début, provenance ;
- alerte : identifiant, horodatage, provenance ;
- politique : délai maximal de détection et référence de protocole ;
- association un-à-un avec la première alerte non utilisée dans `[début, début + délai_max]` ;
- délai de détection calculé uniquement après association ;
- événements et alertes non associés conservés séparément.

## Règles

- aucune alerte antérieure au début de l'événement n'est associée ;
- les identifiants doivent être uniques ;
- deux fenêtres d'événements qui se chevauchent sont refusées : le protocole doit lever l'ambiguïté avant l'analyse ;
- le délai maximal est un paramètre de campagne, jamais une constante produit ;
- le résultat du matching n'est pas un verdict de performance.

## Intégration avec les métriques

Les `detection_delay_s` des événements appariés peuvent ensuite alimenter `detection_performance`, qui calcule les métriques mais ne réalise volontairement aucun matching implicite.

## Gate

Les événements doivent provenir de données labellisées ou d'essais contrôlés dont la provenance et les règles de campagne ont été figées avant évaluation. Une campagne synthétique valide le code, pas la performance industrielle du détecteur.
