"""Porte de qualification factuelle d'un déploiement PETROLE.

Cette brique agrège des résultats de qualification déjà calculés. Elle ne lance
aucun test, ne transforme pas un succès logiciel en certification industrielle
et ne possède aucun mécanisme permettant d'ignorer silencieusement une preuve.
"""

from __future__ import annotations

from dataclasses import dataclass

from hydro_shared.chaos_evidence import ChaosExperimentAssessment
from hydro_shared.load_evidence import LoadTestAssessment
from hydro_shared.migration_evidence import MigrationCompatibilityAssessment
from hydro_shared.recovery import RecoveryDrillAssessment


@dataclass(frozen=True, slots=True)
class DeploymentQualificationEvidence:
    """Références et verdicts observés pour une baseline/environnement précis."""

    release_ref: str
    revision: str
    environment_ref: str
    qualification_archive_ref: str
    security_scan_ref: str
    readiness_probe_ref: str
    recovery: RecoveryDrillAssessment
    migration: MigrationCompatibilityAssessment
    load: LoadTestAssessment
    chaos: ChaosExperimentAssessment
    security_scan_passed: bool
    readiness_verified: bool

    def __post_init__(self) -> None:
        required = (
            self.release_ref,
            self.revision,
            self.environment_ref,
            self.qualification_archive_ref,
            self.security_scan_ref,
            self.readiness_probe_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError("Toutes les références de preuve de qualification sont obligatoires.")


@dataclass(frozen=True, slots=True)
class DeploymentQualificationAssessment:
    """Verdict logiciel limité à la baseline et l'environnement référencés."""

    passed: bool
    release_ref: str
    revision: str
    environment_ref: str
    violations: tuple[str, ...]
    qualification_archive_ref: str


def assess_deployment_qualification(
    evidence: DeploymentQualificationEvidence,
) -> DeploymentQualificationAssessment:
    """Refuse la qualification dès qu'une preuve obligatoire n'est pas positive."""

    violations: list[str] = []
    if not evidence.recovery.passed:
        violations.append("recovery_drill_failed")
    if not evidence.migration.passed:
        violations.append("migration_compatibility_failed")
    if not evidence.load.passed:
        violations.append("load_test_failed")
    if not evidence.chaos.passed:
        violations.append("chaos_experiment_failed")
    if not evidence.security_scan_passed:
        violations.append("security_scan_failed")
    if not evidence.readiness_verified:
        violations.append("readiness_not_verified")

    return DeploymentQualificationAssessment(
        passed=not violations,
        release_ref=evidence.release_ref,
        revision=evidence.revision,
        environment_ref=evidence.environment_ref,
        violations=tuple(violations),
        qualification_archive_ref=evidence.qualification_archive_ref,
    )


__all__ = [
    "DeploymentQualificationAssessment",
    "DeploymentQualificationEvidence",
    "assess_deployment_qualification",
]
