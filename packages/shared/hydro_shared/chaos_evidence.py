"""Preuve factuelle d'un exercice de chaos ciblé PETROLE.

Le module n'injecte aucune panne. Le scénario, les objectifs et les observations
proviennent d'un protocole externe préalablement approuvé. L'évaluation reste
limitée à la résilience logicielle de l'environnement référencé.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChaosExperimentObjectives:
    """Objectifs pré-enregistrés d'un scénario de perturbation ciblé."""

    policy_ref: str
    scenario_ref: str
    target_ref: str
    maximum_recovery_time_s: float
    maximum_error_fraction: float

    def __post_init__(self) -> None:
        references = (self.policy_ref, self.scenario_ref, self.target_ref)
        if any(not value.strip() for value in references):
            raise ValueError("Politique, scénario et cible de chaos sont obligatoires.")
        if not math.isfinite(self.maximum_recovery_time_s) or self.maximum_recovery_time_s < 0:
            raise ValueError("Le temps maximal de reprise doit être fini et positif ou nul.")
        if (
            not math.isfinite(self.maximum_error_fraction)
            or self.maximum_error_fraction < 0
            or self.maximum_error_fraction > 1
        ):
            raise ValueError("La fraction d'erreur maximale doit appartenir à [0, 1].")


@dataclass(frozen=True, slots=True)
class ChaosExperimentEvidence:
    """Observations issues d'un outil ou d'un exercice externe de chaos."""

    evidence_ref: str
    recovery_time_s: float
    total_requests: int
    failed_requests: int
    service_recovered: bool
    data_integrity_preserved: bool
    scope_isolation_preserved: bool

    def __post_init__(self) -> None:
        if not self.evidence_ref.strip():
            raise ValueError("La référence de preuve de chaos est obligatoire.")
        if not math.isfinite(self.recovery_time_s) or self.recovery_time_s < 0:
            raise ValueError("Le temps de reprise observé doit être fini et positif ou nul.")
        if self.total_requests < 1:
            raise ValueError("L'exercice doit observer au moins une requête.")
        if self.failed_requests < 0 or self.failed_requests > self.total_requests:
            raise ValueError("Le nombre de requêtes en échec est incohérent.")

    @property
    def error_fraction(self) -> float:
        return self.failed_requests / self.total_requests


@dataclass(frozen=True, slots=True)
class ChaosExperimentAssessment:
    """Verdict logiciel limité aux objectifs et observations référencés."""

    passed: bool
    violations: tuple[str, ...]
    recovery_time_s: float
    error_fraction: float
    service_recovered: bool
    data_integrity_preserved: bool
    scope_isolation_preserved: bool
    policy_ref: str
    scenario_ref: str
    target_ref: str
    evidence_ref: str


def assess_chaos_experiment(
    objectives: ChaosExperimentObjectives,
    evidence: ChaosExperimentEvidence,
) -> ChaosExperimentAssessment:
    """Compare l'exercice aux objectifs sans tolérance ni scénario implicite.

    L'intégrité des données et l'isolation des périmètres sont des invariants
    produit Phase 8 : elles restent obligatoires quel que soit le scénario ou
    le protocole d'exercice.
    """

    violations: list[str] = []
    if not evidence.service_recovered:
        violations.append("service_not_recovered")
    if evidence.recovery_time_s > objectives.maximum_recovery_time_s:
        violations.append("recovery_time_above_objective")
    if evidence.error_fraction > objectives.maximum_error_fraction:
        violations.append("error_fraction_above_objective")
    if not evidence.data_integrity_preserved:
        violations.append("data_integrity_not_preserved")
    if not evidence.scope_isolation_preserved:
        violations.append("scope_isolation_not_preserved")

    return ChaosExperimentAssessment(
        passed=not violations,
        violations=tuple(violations),
        recovery_time_s=evidence.recovery_time_s,
        error_fraction=evidence.error_fraction,
        service_recovered=evidence.service_recovered,
        data_integrity_preserved=evidence.data_integrity_preserved,
        scope_isolation_preserved=evidence.scope_isolation_preserved,
        policy_ref=objectives.policy_ref,
        scenario_ref=objectives.scenario_ref,
        target_ref=objectives.target_ref,
        evidence_ref=evidence.evidence_ref,
    )


__all__ = [
    "ChaosExperimentAssessment",
    "ChaosExperimentEvidence",
    "ChaosExperimentObjectives",
    "assess_chaos_experiment",
]
