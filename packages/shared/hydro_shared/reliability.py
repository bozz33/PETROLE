"""Évaluation explicite des objectifs de fiabilité d'un déploiement.

Les objectifs sont fournis par le contrat de service ou le protocole de pilote.
Ce module n'invente aucune disponibilité, latence, RPO ou RTO par défaut et ne
constitue pas une certification de l'infrastructure.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReliabilityObjectives:
    """Objectifs approuvés pour un site ou une classe de service."""

    minimum_availability_ratio: float
    maximum_p95_latency_s: float
    maximum_rpo_s: float
    maximum_rto_s: float

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.minimum_availability_ratio)
            or self.minimum_availability_ratio <= 0
            or self.minimum_availability_ratio > 1
        ):
            raise ValueError("La disponibilité minimale doit appartenir à ]0, 1].")
        limits = (
            self.maximum_p95_latency_s,
            self.maximum_rpo_s,
            self.maximum_rto_s,
        )
        if any(not math.isfinite(value) or value < 0 for value in limits):
            raise ValueError("Les limites de latence, RPO et RTO doivent être finies et positives.")


@dataclass(frozen=True, slots=True)
class ReliabilityEvidence:
    """Mesures observées pendant une campagne de fiabilité."""

    availability_ratio: float
    p95_latency_s: float
    observed_rpo_s: float
    observed_rto_s: float

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.availability_ratio)
            or self.availability_ratio < 0
            or self.availability_ratio > 1
        ):
            raise ValueError("La disponibilité observée doit appartenir à [0, 1].")
        values = (self.p95_latency_s, self.observed_rpo_s, self.observed_rto_s)
        if any(not math.isfinite(value) or value < 0 for value in values):
            raise ValueError("Les mesures de latence, RPO et RTO doivent être finies et positives.")


@dataclass(frozen=True, slots=True)
class ReliabilityAssessment:
    """Comparaison reproductible entre mesures et objectifs fournis."""

    passed: bool
    violations: tuple[str, ...]


def assess_reliability(
    objectives: ReliabilityObjectives,
    evidence: ReliabilityEvidence,
) -> ReliabilityAssessment:
    """Évalue uniquement les quatre objectifs explicitement fournis."""

    violations: list[str] = []
    if evidence.availability_ratio < objectives.minimum_availability_ratio:
        violations.append("availability_below_objective")
    if evidence.p95_latency_s > objectives.maximum_p95_latency_s:
        violations.append("p95_latency_above_objective")
    if evidence.observed_rpo_s > objectives.maximum_rpo_s:
        violations.append("rpo_above_objective")
    if evidence.observed_rto_s > objectives.maximum_rto_s:
        violations.append("rto_above_objective")
    return ReliabilityAssessment(passed=not violations, violations=tuple(violations))


__all__ = [
    "ReliabilityAssessment",
    "ReliabilityEvidence",
    "ReliabilityObjectives",
    "assess_reliability",
]
