from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hydro_api.industrial.ot_qualification import (
    OtGateStatus,
    OtQualificationStage,
    OtStageEvidence,
    assess_ot_qualification,
    required_stages_through,
)

_OBSERVED_AT = datetime(2026, 8, 11, 5, 30, tzinfo=UTC)


def _evidence(stage: OtQualificationStage, *, passed: bool = True) -> OtStageEvidence:
    return OtStageEvidence(
        stage=stage,
        evidence_ref=f"evidence://ot/{stage.value}/run-1",
        protocol_ref=f"protocol://ot/{stage.value}/v1",
        environment_ref="environment://ot-lab/site-A",
        observed_at=_OBSERVED_AT,
        passed=passed,
        findings=() if passed else ("finding://security/review-required",),
    )


def test_required_stages_follow_d15_order() -> None:
    assert required_stages_through(OtQualificationStage.OT_3) == (
        OtQualificationStage.OT_0,
        OtQualificationStage.OT_1,
        OtQualificationStage.OT_2,
        OtQualificationStage.OT_3,
    )


def test_ot_gate_requires_every_stage_through_target() -> None:
    assessment = assess_ot_qualification(
        (
            _evidence(OtQualificationStage.OT_0),
            _evidence(OtQualificationStage.OT_1),
            _evidence(OtQualificationStage.OT_3),
        ),
        target_stage=OtQualificationStage.OT_3,
    )

    assert assessment.passed is False
    assert assessment.blocking_stages == (OtQualificationStage.OT_2,)
    assert tuple(item.status for item in assessment.stages) == (
        OtGateStatus.PASSED,
        OtGateStatus.PASSED,
        OtGateStatus.MISSING,
        OtGateStatus.PASSED,
    )


def test_failed_observed_stage_blocks_qualification_without_hiding_evidence() -> None:
    evidence = tuple(
        _evidence(stage, passed=stage is not OtQualificationStage.OT_2)
        for stage in required_stages_through(OtQualificationStage.OT_4)
    )
    assessment = assess_ot_qualification(
        evidence,
        target_stage=OtQualificationStage.OT_4,
    )

    assert assessment.passed is False
    assert assessment.blocking_stages == (OtQualificationStage.OT_2,)
    failed = assessment.stages[2]
    assert failed.status is OtGateStatus.FAILED
    assert failed.evidence_ref == "evidence://ot/OT-2/run-1"
    assert failed.findings == ("finding://security/review-required",)


def test_complete_ot0_to_ot5_evidence_passes_documentary_gate() -> None:
    evidence = tuple(
        _evidence(stage) for stage in required_stages_through(OtQualificationStage.OT_5)
    )

    assessment = assess_ot_qualification(evidence)

    assert assessment.passed is True
    assert assessment.blocking_stages == ()
    assert assessment.target_stage is OtQualificationStage.OT_5
    assert all(item.status is OtGateStatus.PASSED for item in assessment.stages)


def test_duplicate_stage_evidence_is_rejected() -> None:
    duplicate = _evidence(OtQualificationStage.OT_1)
    with pytest.raises(ValueError, match="Une seule preuve OT"):
        assess_ot_qualification((duplicate, duplicate))


def test_ot_evidence_requires_timezone_and_references() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        OtStageEvidence(
            stage=OtQualificationStage.OT_0,
            evidence_ref="evidence://ot/OT-0",
            protocol_ref="protocol://ot/OT-0",
            environment_ref="environment://workshop",
            observed_at=datetime(2026, 8, 11, 5, 30),
            passed=True,
        )
