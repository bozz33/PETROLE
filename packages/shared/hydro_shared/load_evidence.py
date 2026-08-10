"""Évaluation factuelle d'une campagne de charge PETROLE.

Les objectifs de latence, erreur, débit et concurrence sont fournis par le
protocole de qualification. Le module n'exécute pas le générateur de charge et
n'invente aucune cible de performance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LoadTestObjectives:
    """Objectifs approuvés avant la campagne de charge."""

    maximum_p95_latency_s: float
    maximum_error_fraction: float
    minimum_throughput_requests_s: float
    minimum_concurrency: int
    policy_ref: str

    def __post_init__(self) -> None:
        positive = (self.maximum_p95_latency_s, self.minimum_throughput_requests_s)
        if any(not math.isfinite(value) or value <= 0 for value in positive):
            raise ValueError("Latence P95 et débit minimal doivent être finis et positifs.")
        if (
            not math.isfinite(self.maximum_error_fraction)
            or self.maximum_error_fraction < 0
            or self.maximum_error_fraction > 1
        ):
            raise ValueError("La fraction d'erreur maximale doit appartenir à [0, 1].")
        if self.minimum_concurrency <= 0:
            raise ValueError("La concurrence minimale doit être strictement positive.")
        if not self.policy_ref.strip():
            raise ValueError("La référence de politique de charge est obligatoire.")


@dataclass(frozen=True, slots=True)
class LoadTestEvidence:
    """Mesures observées d'une campagne externe de charge."""

    evidence_ref: str
    duration_s: float
    total_requests: int
    failed_requests: int
    p95_latency_s: float
    observed_concurrency: int

    def __post_init__(self) -> None:
        if not self.evidence_ref.strip():
            raise ValueError("La référence de preuve de charge est obligatoire.")
        if not math.isfinite(self.duration_s) or self.duration_s <= 0:
            raise ValueError("La durée de campagne doit être finie et strictement positive.")
        if self.total_requests <= 0:
            raise ValueError("La campagne doit contenir au moins une requête.")
        if self.failed_requests < 0 or self.failed_requests > self.total_requests:
            raise ValueError("Le nombre de requêtes en échec est incohérent.")
        if not math.isfinite(self.p95_latency_s) or self.p95_latency_s < 0:
            raise ValueError("La latence P95 observée doit être finie et positive ou nulle.")
        if self.observed_concurrency <= 0:
            raise ValueError("La concurrence observée doit être strictement positive.")

    @property
    def throughput_requests_s(self) -> float:
        return self.total_requests / self.duration_s

    @property
    def error_fraction(self) -> float:
        return self.failed_requests / self.total_requests


@dataclass(frozen=True, slots=True)
class LoadTestAssessment:
    passed: bool
    throughput_requests_s: float
    error_fraction: float
    p95_latency_s: float
    observed_concurrency: int
    violations: tuple[str, ...]
    evidence_ref: str
    policy_ref: str


def assess_load_test(
    objectives: LoadTestObjectives,
    evidence: LoadTestEvidence,
) -> LoadTestAssessment:
    """Compare les mesures aux objectifs sans tolérance implicite."""

    violations: list[str] = []
    if evidence.p95_latency_s > objectives.maximum_p95_latency_s:
        violations.append("p95_latency_above_objective")
    if evidence.error_fraction > objectives.maximum_error_fraction:
        violations.append("error_fraction_above_objective")
    if evidence.throughput_requests_s < objectives.minimum_throughput_requests_s:
        violations.append("throughput_below_objective")
    if evidence.observed_concurrency < objectives.minimum_concurrency:
        violations.append("concurrency_below_objective")
    return LoadTestAssessment(
        passed=not violations,
        throughput_requests_s=evidence.throughput_requests_s,
        error_fraction=evidence.error_fraction,
        p95_latency_s=evidence.p95_latency_s,
        observed_concurrency=evidence.observed_concurrency,
        violations=tuple(violations),
        evidence_ref=evidence.evidence_ref,
        policy_ref=objectives.policy_ref,
    )


__all__ = [
    "LoadTestAssessment",
    "LoadTestEvidence",
    "LoadTestObjectives",
    "assess_load_test",
]
