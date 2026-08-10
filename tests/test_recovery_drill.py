from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hydro_shared.recovery import RecoveryDrillEvidence, assess_recovery_drill
from hydro_shared.reliability import ReliabilityObjectives


def _objectives() -> ReliabilityObjectives:
    return ReliabilityObjectives(
        minimum_availability_ratio=0.995,
        maximum_p95_latency_s=2.0,
        maximum_rpo_s=60.0,
        maximum_rto_s=300.0,
    )


def test_recovery_drill_passes_only_with_measured_integrity_and_objectives() -> None:
    incident = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    evidence = RecoveryDrillEvidence(
        started_at=incident + timedelta(minutes=1),
        completed_at=incident + timedelta(minutes=4),
        latest_recovered_data_at=incident - timedelta(seconds=30),
        incident_reference_time=incident,
        database_integrity_verified=True,
        object_storage_integrity_verified=True,
        application_readiness_verified=True,
        drill_reference="DRILL-2026-08-10-A",
    )
    result = assess_recovery_drill(_objectives(), evidence)

    assert result.passed is True
    assert result.observed_rpo_s == pytest.approx(30.0)
    assert result.observed_rto_s == pytest.approx(180.0)
    assert result.violations == ()


def test_recovery_drill_reports_rpo_rto_and_integrity_failures() -> None:
    incident = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    evidence = RecoveryDrillEvidence(
        started_at=incident + timedelta(minutes=1),
        completed_at=incident + timedelta(minutes=10),
        latest_recovered_data_at=incident - timedelta(minutes=3),
        incident_reference_time=incident,
        database_integrity_verified=False,
        object_storage_integrity_verified=True,
        application_readiness_verified=False,
        drill_reference="DRILL-2026-08-10-B",
    )
    result = assess_recovery_drill(_objectives(), evidence)

    assert result.passed is False
    assert result.violations == (
        "rpo_above_objective",
        "rto_above_objective",
        "database_integrity_not_verified",
        "application_readiness_not_verified",
    )


def test_recovery_drill_rejects_impossible_timeline() -> None:
    incident = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="postérieure à l'incident"):
        RecoveryDrillEvidence(
            started_at=incident,
            completed_at=incident + timedelta(minutes=1),
            latest_recovered_data_at=incident + timedelta(seconds=1),
            incident_reference_time=incident,
            database_integrity_verified=True,
            object_storage_integrity_verified=True,
            application_readiness_verified=True,
            drill_reference="DRILL-INVALID",
        )
