from __future__ import annotations

from hydro_shared.load_evidence import LoadTestAssessment
from hydro_shared.migration_evidence import MigrationCompatibilityAssessment, RollbackStrategy
from hydro_shared.qualification_gate import (
    DeploymentQualificationEvidence,
    assess_deployment_qualification,
)
from hydro_shared.recovery import RecoveryDrillAssessment


def _evidence(
    *,
    recovery_passed: bool = True,
    migration_passed: bool = True,
    load_passed: bool = True,
    security_scan_passed: bool = True,
    readiness_verified: bool = True,
) -> DeploymentQualificationEvidence:
    return DeploymentQualificationEvidence(
        release_ref="release://PETROLE/1.1.0",
        revision="0123456789abcdef",
        environment_ref="env://pilot-abidjan/staging",
        qualification_archive_ref="evidence://qualification/2026-08-11",
        security_scan_ref="evidence://security/2026-08-11",
        readiness_probe_ref="evidence://readiness/2026-08-11",
        recovery=RecoveryDrillAssessment(
            passed=recovery_passed,
            observed_rpo_s=10.0,
            observed_rto_s=30.0,
            violations=() if recovery_passed else ("rto_above_objective",),
        ),
        migration=MigrationCompatibilityAssessment(
            passed=migration_passed,
            violations=() if migration_passed else ("rollback_not_executed",),
            rollback_strategy=RollbackStrategy.DATABASE_RESTORE,
        ),
        load=LoadTestAssessment(
            passed=load_passed,
            throughput_requests_s=20.0,
            error_fraction=0.0,
            p95_latency_s=0.8,
            observed_concurrency=10,
            violations=() if load_passed else ("p95_latency_above_objective",),
            evidence_ref="evidence://load/2026-08-11",
            policy_ref="policy://load/pilot-v1",
        ),
        security_scan_passed=security_scan_passed,
        readiness_verified=readiness_verified,
    )


def test_qualification_gate_passes_only_with_all_required_positive_evidence() -> None:
    assessment = assess_deployment_qualification(_evidence())

    assert assessment.passed is True
    assert assessment.violations == ()
    assert assessment.revision == "0123456789abcdef"


def test_qualification_gate_reports_every_failed_required_gate() -> None:
    assessment = assess_deployment_qualification(
        _evidence(
            recovery_passed=False,
            migration_passed=False,
            load_passed=False,
            security_scan_passed=False,
            readiness_verified=False,
        )
    )

    assert assessment.passed is False
    assert assessment.violations == (
        "recovery_drill_failed",
        "migration_compatibility_failed",
        "load_test_failed",
        "security_scan_failed",
        "readiness_not_verified",
    )


def test_qualification_evidence_requires_traceable_references() -> None:
    base = _evidence()
    try:
        DeploymentQualificationEvidence(
            release_ref=base.release_ref,
            revision=base.revision,
            environment_ref="",
            qualification_archive_ref=base.qualification_archive_ref,
            security_scan_ref=base.security_scan_ref,
            readiness_probe_ref=base.readiness_probe_ref,
            recovery=base.recovery,
            migration=base.migration,
            load=base.load,
            security_scan_passed=True,
            readiness_verified=True,
        )
    except ValueError as exc:
        assert "références" in str(exc)
    else:
        raise AssertionError("Une preuve sans environnement traçable doit être rejetée.")
