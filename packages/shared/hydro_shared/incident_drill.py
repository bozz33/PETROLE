"""Évaluation mesurée d'un exercice d'incident PETROLE.

La brique vérifie l'usage d'un runbook versionné et compare les temps observés
à des objectifs explicitement approuvés. Elle ne prétend pas qu'un service de
support est opérationnel sans exercice ni organisation réelle.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class IncidentResponseObjectives:
    """Objectifs contractuels/pré-pilote fournis pour l'exercice."""

    maximum_acknowledgement_s: float
    maximum_recovery_s: float

    def __post_init__(self) -> None:
        values = (self.maximum_acknowledgement_s, self.maximum_recovery_s)
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError("Les objectifs incident doivent être finis et strictement positifs.")
        if self.maximum_acknowledgement_s > self.maximum_recovery_s:
            raise ValueError(
                "L'objectif d'acquittement ne peut pas dépasser l'objectif de reprise."
            )


@dataclass(frozen=True, slots=True)
class IncidentDrillEvidence:
    """Chronologie et artefacts observés pendant un exercice."""

    drill_reference: str
    runbook_reference: str
    runbook_version: str
    runbook_sha256: str
    started_at: datetime
    acknowledged_at: datetime
    recovered_at: datetime
    communication_verified: bool
    escalation_verified: bool
    evidence_archive_ref: str

    def __post_init__(self) -> None:
        required = (
            self.drill_reference,
            self.runbook_reference,
            self.runbook_version,
            self.evidence_archive_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError("Références drill/runbook/preuve et version sont obligatoires.")
        if not _SHA256_PATTERN.fullmatch(self.runbook_sha256):
            raise ValueError("Le runbook doit être identifié par une empreinte SHA-256 complète.")
        timestamps = (self.started_at, self.acknowledged_at, self.recovered_at)
        if any(timestamp.tzinfo is None for timestamp in timestamps):
            raise ValueError("Les horodatages de l'exercice doivent être timezone-aware.")
        if not self.started_at < self.acknowledged_at <= self.recovered_at:
            raise ValueError("La chronologie incident doit respecter start < ack <= recovery.")

    @property
    def acknowledgement_s(self) -> float:
        return (
            self.acknowledged_at.astimezone(UTC) - self.started_at.astimezone(UTC)
        ).total_seconds()

    @property
    def recovery_s(self) -> float:
        return (self.recovered_at.astimezone(UTC) - self.started_at.astimezone(UTC)).total_seconds()


@dataclass(frozen=True, slots=True)
class IncidentDrillAssessment:
    """Verdict factuel d'un drill, distinct d'un SLA de production."""

    passed: bool
    acknowledgement_s: float
    recovery_s: float
    violations: tuple[str, ...]


def assess_incident_drill(
    objectives: IncidentResponseObjectives,
    evidence: IncidentDrillEvidence,
) -> IncidentDrillAssessment:
    """Compare le drill à ses objectifs sans marge ou tolérance implicite."""

    violations: list[str] = []
    if evidence.acknowledgement_s > objectives.maximum_acknowledgement_s:
        violations.append("acknowledgement_above_objective")
    if evidence.recovery_s > objectives.maximum_recovery_s:
        violations.append("recovery_above_objective")
    if not evidence.communication_verified:
        violations.append("communication_not_verified")
    if not evidence.escalation_verified:
        violations.append("escalation_not_verified")
    return IncidentDrillAssessment(
        passed=not violations,
        acknowledgement_s=evidence.acknowledgement_s,
        recovery_s=evidence.recovery_s,
        violations=tuple(violations),
    )


__all__ = [
    "IncidentDrillAssessment",
    "IncidentDrillEvidence",
    "IncidentResponseObjectives",
    "assess_incident_drill",
]
