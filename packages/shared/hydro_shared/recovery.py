"""Preuve mesurée de restauration/reprise pour l'industrialisation PETROLE.

Le module compare des observations de drill à des objectifs fournis. Il ne
prétend pas qu'une sauvegarde existe parce qu'une configuration la décrit :
l'intégrité, la restauration et la mesure RPO/RTO doivent provenir d'un essai.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from hydro_shared.reliability import ReliabilityObjectives


@dataclass(frozen=True, slots=True)
class RecoveryDrillEvidence:
    """Résultats observés d'un exercice de reprise isolé."""

    started_at: datetime
    completed_at: datetime
    latest_recovered_data_at: datetime
    incident_reference_time: datetime
    database_integrity_verified: bool
    object_storage_integrity_verified: bool
    application_readiness_verified: bool
    drill_reference: str

    def __post_init__(self) -> None:
        timestamps = (
            self.started_at,
            self.completed_at,
            self.latest_recovered_data_at,
            self.incident_reference_time,
        )
        if any(timestamp.tzinfo is None for timestamp in timestamps):
            raise ValueError("Les horodatages d'un drill de reprise doivent être timezone-aware.")
        if self.completed_at <= self.started_at:
            raise ValueError("La fin du drill doit être postérieure à son début.")
        if self.latest_recovered_data_at > self.incident_reference_time:
            raise ValueError("La dernière donnée récupérée ne peut pas être postérieure à l'incident.")
        if not self.drill_reference.strip():
            raise ValueError("La référence de l'exercice de reprise est obligatoire.")

    @property
    def observed_rto_s(self) -> float:
        return (
            self.completed_at.astimezone(UTC) - self.started_at.astimezone(UTC)
        ).total_seconds()

    @property
    def observed_rpo_s(self) -> float:
        return (
            self.incident_reference_time.astimezone(UTC)
            - self.latest_recovered_data_at.astimezone(UTC)
        ).total_seconds()


@dataclass(frozen=True, slots=True)
class RecoveryDrillAssessment:
    """Verdict d'un exercice, séparé de la disponibilité générale du service."""

    passed: bool
    observed_rpo_s: float
    observed_rto_s: float
    violations: tuple[str, ...]


def assess_recovery_drill(
    objectives: ReliabilityObjectives,
    evidence: RecoveryDrillEvidence,
) -> RecoveryDrillAssessment:
    """Vérifie RPO/RTO et intégrités sans inventer de marge implicite."""

    rpo = evidence.observed_rpo_s
    rto = evidence.observed_rto_s
    if not math.isfinite(rpo) or not math.isfinite(rto):
        raise ValueError("Les mesures RPO/RTO calculées doivent être finies.")

    violations: list[str] = []
    if rpo > objectives.maximum_rpo_s:
        violations.append("rpo_above_objective")
    if rto > objectives.maximum_rto_s:
        violations.append("rto_above_objective")
    if not evidence.database_integrity_verified:
        violations.append("database_integrity_not_verified")
    if not evidence.object_storage_integrity_verified:
        violations.append("object_storage_integrity_not_verified")
    if not evidence.application_readiness_verified:
        violations.append("application_readiness_not_verified")

    return RecoveryDrillAssessment(
        passed=not violations,
        observed_rpo_s=rpo,
        observed_rto_s=rto,
        violations=tuple(violations),
    )


__all__ = [
    "RecoveryDrillAssessment",
    "RecoveryDrillEvidence",
    "assess_recovery_drill",
]
