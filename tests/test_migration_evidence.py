from __future__ import annotations

from hydro_shared.migration_evidence import (
    MigrationCompatibilityEvidence,
    RollbackStrategy,
    assess_migration_compatibility,
)


def _evidence(**overrides: bool) -> MigrationCompatibilityEvidence:
    values = {
        "upgrade_applied": True,
        "new_release_readiness_verified": True,
        "data_integrity_after_upgrade_verified": True,
        "rollback_executed": True,
        "previous_release_readiness_verified": True,
        "data_integrity_after_rollback_verified": True,
    }
    values.update(overrides)
    return MigrationCompatibilityEvidence(
        from_release="v1.1.0",
        to_release="v1.2.0",
        from_revision="rev-a",
        to_revision="rev-b",
        environment_ref="staging://migration-drill/2026-08-10",
        evidence_archive_ref="evidence://migration-drill/2026-08-10",
        rollback_strategy=RollbackStrategy.DATABASE_RESTORE,
        **values,
    )


def test_migration_drill_passes_only_with_upgrade_and_rollback_evidence() -> None:
    result = assess_migration_compatibility(_evidence())
    assert result.passed is True
    assert result.violations == ()
    assert result.rollback_strategy is RollbackStrategy.DATABASE_RESTORE


def test_migration_drill_reports_missing_readiness_integrity_and_rollback() -> None:
    result = assess_migration_compatibility(
        _evidence(
            new_release_readiness_verified=False,
            data_integrity_after_upgrade_verified=False,
            rollback_executed=False,
            previous_release_readiness_verified=False,
        )
    )
    assert result.passed is False
    assert result.violations == (
        "new_release_readiness_not_verified",
        "upgrade_data_integrity_not_verified",
        "rollback_not_executed",
        "previous_release_readiness_not_verified",
    )
