"""Indicateurs descriptifs de maintenance conditionnelle Phase 3.

Le module compare une mesure agrégée à une baseline fournie et à des seuils
approuvés par le contexte métier. Il ne déclenche ni commande, ni arrêt, ni
ordre de maintenance et n'invente aucune tolérance industrielle.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class ConditionStatus(StrEnum):
    """Classification analytique sans portée de sûreté."""

    NORMAL = "normal"
    WATCH = "watch"
    INVESTIGATE = "investigate"


@dataclass(frozen=True, slots=True)
class ConditionBaseline:
    """Baseline statistique versionnée d'un indicateur SI."""

    reference: str
    mean_si: float
    standard_deviation_si: float
    unit: str

    def __post_init__(self) -> None:
        if not self.reference.strip():
            raise ValueError("La référence de baseline est obligatoire.")
        if not math.isfinite(self.mean_si):
            raise ValueError("La moyenne de baseline doit être finie.")
        if not math.isfinite(self.standard_deviation_si) or self.standard_deviation_si <= 0:
            raise ValueError("L'écart-type de baseline doit être fini et strictement positif.")
        if not self.unit.strip():
            raise ValueError("L'unité SI de la baseline est obligatoire.")


@dataclass(frozen=True, slots=True)
class ConditionThresholds:
    """Seuils métier explicites en nombre d'écarts-types."""

    watch_absolute_z: float
    investigate_absolute_z: float

    def __post_init__(self) -> None:
        values = (self.watch_absolute_z, self.investigate_absolute_z)
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError("Les seuils conditionnels doivent être finis et strictement positifs.")
        if self.watch_absolute_z >= self.investigate_absolute_z:
            raise ValueError("Le seuil watch doit être strictement inférieur au seuil investigate.")


@dataclass(frozen=True, slots=True)
class ConditionAssessment:
    """Écart normalisé et statut descriptif d'un indicateur."""

    value_si: float
    z_score: float
    status: ConditionStatus
    baseline_reference: str
    unit: str


def assess_condition(
    *,
    value_si: float,
    baseline: ConditionBaseline,
    thresholds: ConditionThresholds,
) -> ConditionAssessment:
    """Classe un indicateur sans action automatique et sans seuil caché."""

    if not math.isfinite(value_si):
        raise ValueError("La valeur conditionnelle doit être finie.")
    z_score = (value_si - baseline.mean_si) / baseline.standard_deviation_si
    absolute_z = abs(z_score)
    if absolute_z >= thresholds.investigate_absolute_z:
        status = ConditionStatus.INVESTIGATE
    elif absolute_z >= thresholds.watch_absolute_z:
        status = ConditionStatus.WATCH
    else:
        status = ConditionStatus.NORMAL
    return ConditionAssessment(
        value_si=value_si,
        z_score=z_score,
        status=status,
        baseline_reference=baseline.reference,
        unit=baseline.unit,
    )


__all__ = [
    "ConditionAssessment",
    "ConditionBaseline",
    "ConditionStatus",
    "ConditionThresholds",
    "assess_condition",
]
