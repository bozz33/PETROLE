"""Métriques de performance d'un détecteur sur données labellisées.

Aucun seuil de performance n'est défini ici. Les critères d'acceptation sont
convenus avec l'opérateur avant la campagne, conformément au plan D20. Ce
module évalue un résultat déjà labellisé ; il ne détecte ni ne localise une
fuite et ne commande aucun équipement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DetectionPerformance:
    """Résumé d'une campagne binaire fuite/non-fuite."""

    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    precision: float | None
    recall: float | None
    specificity: float | None
    false_positive_rate: float | None
    accuracy: float | None
    mean_detection_delay_s: float | None
    maximum_detection_delay_s: float | None


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def detection_performance(
    *,
    truth: list[bool],
    predicted: list[bool],
    matched_detection_delays_s: list[float] | None = None,
) -> DetectionPerformance:
    """Évalue des décisions binaires sans inventer de seuil ou d'objectif.

    Les délais sont fournis uniquement pour les événements correctement
    détectés et doivent avoir été associés aux événements par le protocole de
    campagne. Cette fonction ne réalise pas de matching temporel implicite.
    """

    if len(truth) != len(predicted):
        raise ValueError("Les séries vérité terrain et prédiction doivent avoir la même taille.")
    if not truth:
        raise ValueError("Une campagne de performance doit contenir au moins un échantillon.")

    true_positive = sum(
        expected and observed for expected, observed in zip(truth, predicted, strict=True)
    )
    false_positive = sum(
        (not expected) and observed for expected, observed in zip(truth, predicted, strict=True)
    )
    false_negative = sum(
        expected and (not observed) for expected, observed in zip(truth, predicted, strict=True)
    )
    true_negative = sum(
        (not expected) and (not observed)
        for expected, observed in zip(truth, predicted, strict=True)
    )

    delays = matched_detection_delays_s or []
    if any(not math.isfinite(delay) or delay < 0 for delay in delays):
        raise ValueError("Les délais de détection doivent être finis et positifs ou nuls.")
    if len(delays) > true_positive:
        raise ValueError("Le nombre de délais associés ne peut pas dépasser les vrais positifs.")

    total = len(truth)
    mean_delay = math.fsum(delays) / len(delays) if delays else None
    maximum_delay = max(delays) if delays else None
    return DetectionPerformance(
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
        true_negative=true_negative,
        precision=_ratio(true_positive, true_positive + false_positive),
        recall=_ratio(true_positive, true_positive + false_negative),
        specificity=_ratio(true_negative, true_negative + false_positive),
        false_positive_rate=_ratio(false_positive, false_positive + true_negative),
        accuracy=(true_positive + true_negative) / total,
        mean_detection_delay_s=mean_delay,
        maximum_detection_delay_s=maximum_delay,
    )


__all__ = ["DetectionPerformance", "detection_performance"]
