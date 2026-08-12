# Phase 7 — P7-I protocole de campagne de validation

Statut : contrat de critères pré-enregistrés et évaluation déterministe implémentés, **sans données labellisées réelles et sans qualification industrielle**.

## Références

- D17 : Phase 7, campagne de validation sur données labellisées ou essais contrôlés ;
- D20 : critères définis avant la campagne et décision humaine Go/No-Go ;
- `phase7_leak_digital_twin_execution.md` : faux positifs, faux négatifs, délais et performances à mesurer.

## Principe

`hydro_leak.validation_campaign` sépare les critères d'acceptation des métriques observées. Les critères doivent être fournis explicitement par un protocole identifié par `source_ref`. Aucun seuil industriel PETROLE n'est défini par défaut.

Les critères configurables sont :

- précision minimale ;
- rappel/sensibilité minimale ;
- spécificité minimale ;
- taux maximal de faux positifs ;
- délai moyen maximal de détection ;
- délai maximal de détection ;
- nombre minimal d'échantillons.

Au moins un critère doit être pré-enregistré. Les ratios sont contraints à `[0, 1]`, les délais doivent être finis et positifs ou nuls et le nombre minimal d'échantillons doit être strictement positif.

## Évaluation

`assess_validation_criteria(...)` reçoit un `DetectionPerformance` déjà calculé et produit un résultat par critère. Une métrique absente reste `unevaluable` (`passed=None`) au lieu d'être transformée en succès ou en échec arbitraire.

Le résultat expose séparément :

- si tous les critères réellement évaluables passent ;
- si au moins un critère reste non évaluable faute de preuve.

Cette séparation empêche qu'une campagne incomplète soit présentée comme validée simplement parce que les métriques disponibles sont favorables.

## Limites volontaires

Cette brique ne :

- sélectionne aucun seuil ;
- ne génère aucune alerte de fuite ;
- ne détecte ni ne localise une fuite ;
- ne transforme pas le résultat en certification API ;
- ne remplace pas la revue humaine indépendante ;
- ne crée pas de données de fuite labellisées.

## Tests

`tests/test_leak_validation_campaign.py` couvre :

- évaluation uniquement des critères explicitement configurés ;
- critères réussis et échoués ;
- métriques indisponibles conservées comme non évaluables ;
- coexistence d'un critère réussi et d'une preuve manquante ;
- provenance et présence d'au moins un critère ;
- validation des ratios, délais et tailles d'échantillon.

## Statut de qualification

`IMPLEMENTED_PREREGISTERED_CRITERIA_NOT_INDUSTRIALLY_VALIDATED`

La gate P7-I reste ouverte tant qu'il n'existe pas de données labellisées ou d'essais contrôlés, de critères approuvés par l'opérateur, d'un protocole figé et d'une revue indépendante des résultats.
