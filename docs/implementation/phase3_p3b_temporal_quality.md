# Phase 3 — P3-B Diagnostics temporels D15

Référence principale : D15 §9, complétée par D09/D12/D17.

## Implémentation

`hydro_api.services.temporal_quality` calcule sans modifier les points :

- latence `ingest_timestamp - source_timestamp` ;
- nombre de latences négatives ;
- moyenne et maximum de latence ;
- violations d'un objectif de latence lorsqu'il est fourni ;
- violations d'ordre dans la séquence source reçue ;
- compte et fraction par qualité PETROLE ;
- nombre de sauts consécutifs dépassant une amplitude explicitement fournie ;
- durée maximale de stagnation selon une tolérance de variation consécutive et une durée minimale explicitement fournies.

## Règles

- les timestamps doivent être timezone-aware ;
- aucune série n'est réordonnée ou corrigée en place ;
- une latence négative reste visible comme anomalie temporelle ;
- saut, stagnation et latence n'ont aucune valeur seuil par défaut ;
- désactiver un diagnostic se fait explicitement avec `None` ;
- qualité `bad` n'est pas supprimée de ce diagnostic : la distribution complète reste observable.

## Limites

La complétude est déjà calculée dans l'analyse temporelle Phase 3 lorsque l'intervalle attendu est fourni. Le biais dépend de V1-B/du capteur redondant. L'échéance de calibration exige des métadonnées métrologiques propres au tag/capteur et reste un sous-lot séparé.
