# Phase 7 — P7-F Contrat de localisation et incertitude

Références : D10, D15, D17 et D20.

## Implémentation

`hydro_leak.localization.LeakLocationEstimate` représente un résultat de localisation sans imposer d'algorithme :

- conduite et longueur de référence ;
- chaînage estimé ;
- borne basse et borne haute de l'intervalle d'incertitude ;
- méthode explicitement référencée ;
- version de modèle ;
- référence de preuve/campagne.

Le contrat vérifie que l'intervalle reste dans la conduite et que l'estimation appartient à cet intervalle. Il publie la largeur et les marges de l'intervalle.

## Règles

- aucune « confiance » arbitraire n'est générée ;
- un résultat sans méthode/version/preuve est refusé ;
- la localisation ne devient pas valide parce qu'elle respecte le schéma ;
- l'algorithme futur devra produire l'intervalle à partir d'une méthode sourcée et validée.

## Gate

Une performance de localisation nécessite des événements dont la position réelle est connue et tenue hors de l'algorithme d'estimation, des métriques pré-définies et une campagne indépendante. Le présent lot prépare uniquement le contrat de sortie et sa traçabilité.
