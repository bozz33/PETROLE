from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hydro_shared.incident_drill import (
    IncidentDrillEvidence,
    IncidentResponseObjectives,
    assess_incident_drill,
)


def _evidence(*, ack_s: int, recovery_s: int) -> IncidentDrillEvidence:
    start = datetime(2026, 8, 10, 22, 0, tzinfo=UTC)
    return IncidentDrillEvidence(
        drill_reference="DRILL-INC-2026-08-10",
        runbook_reference="runbook://incident/api-unavailable",
        runbook_version="3.1",
        runbook_sha256="a" * 64,
        started_at=start,
        acknowledged_at=start + timedelta(seconds=ack_s),
        recovered_at=start + timedelta(seconds=recovery_s),
        communication_verified=True,
        escalation_verified=True,
        evidence_archive_ref="evidence://incident-drill/2026-08-10",
    )


def test_incident_drill_passes_only_against_explicit_objectives() -> None:
    result = assess_incident_drill(
        IncidentResponseObjectives(
            maximum_acknowledgement_s=120.0,
            maximum_recovery_s=600.0,
        ),
        _evidence(ack_s=60, recovery_s=300),
    )

    assert result.passed is True
    assert result.acknowledgement_s == pytest.approx(60.0)
    assert result.recovery_s == pytest.approx(300.0)
    assert result.violations == ()


def test_incident_drill_exposes_each_failed_gate() -> None:
    evidence = _evidence(ack_s=180, recovery_s=900)
    evidence = IncidentDrillEvidence(
        drill_reference=evidence.drill_reference,
        runbook_reference=evidence.runbook_reference,
        runbook_version=evidence.runbook_version,
        runbook_sha256=evidence.runbook_sha256,
        started_at=evidence.started_at,
        acknowledged_at=evidence.acknowledged_at,
        recovered_at=evidence.recovered_at,
        communication_verified=False,
        escalation_verified=False,
        evidence_archive_ref=evidence.evidence_archive_ref,
    )
    result = assess_incident_drill(
        IncidentResponseObjectives(
            maximum_acknowledgement_s=120.0,
            maximum_recovery_s=600.0,
        ),
        evidence,
    )

    assert result.passed is False
    assert result.violations == (
        "acknowledgement_above_objective",
        "recovery_above_objective",
        "communication_not_verified",
        "escalation_not_verified",
    )


def test_incident_drill_rejects_invalid_timeline() -> None:
    start = datetime(2026, 8, 10, 22, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="chronologie"):
        IncidentDrillEvidence(
            drill_reference="DRILL-INVALID",
            runbook_reference="runbook://incident/api-unavailable",
            runbook_version="3.1",
            runbook_sha256="a" * 64,
            started_at=start,
            acknowledged_at=start + timedelta(minutes=5),
            recovered_at=start + timedelta(minutes=4),
            communication_verified=True,
            escalation_verified=True,
            evidence_archive_ref="evidence://incident-drill/invalid",
        )
