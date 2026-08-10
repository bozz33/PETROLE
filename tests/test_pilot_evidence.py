from __future__ import annotations

import pytest

from hydro_api.pilot_evidence import (
    PilotCampaignEvidence,
    PilotEvidenceStatus,
    PilotTestCode,
    PilotTestEvidence,
    assess_pilot_campaign,
)


def _evidence(code: PilotTestCode, status: PilotEvidenceStatus) -> PilotTestEvidence:
    evidence_ref = None
    if status in {PilotEvidenceStatus.PASS, PilotEvidenceStatus.FAIL}:
        evidence_ref = f"evidence://pilot/{code.value.lower()}"
    return PilotTestEvidence(code=code, status=status, evidence_ref=evidence_ref)


def _campaign(tests: tuple[PilotTestEvidence, ...]) -> PilotCampaignEvidence:
    return PilotCampaignEvidence(
        site_reference="site://pilot-A",
        baseline_reference="model://baseline/v4",
        protocol_reference="protocol://D20/site-A/v1",
        tests=tests,
    )


def test_complete_terminal_campaign_is_ready_for_human_decision_even_with_failures() -> None:
    tests = tuple(
        _evidence(
            code,
            PilotEvidenceStatus.FAIL if code is PilotTestCode.PIL_08 else PilotEvidenceStatus.PASS,
        )
        for code in PilotTestCode
    )
    assessment = assess_pilot_campaign(_campaign(tests))

    assert assessment.ready_for_decision_review is True
    assert assessment.missing_tests == ()
    assert assessment.blocked_tests == ()
    assert assessment.not_run_tests == ()
    assert assessment.failed_tests == (PilotTestCode.PIL_08,)
    assert len(assessment.passed_tests) == 11


def test_missing_or_blocked_tests_prevent_decision_review() -> None:
    tests = (
        _evidence(PilotTestCode.PIL_01, PilotEvidenceStatus.PASS),
        _evidence(PilotTestCode.PIL_02, PilotEvidenceStatus.BLOCKED),
    )
    assessment = assess_pilot_campaign(_campaign(tests))

    assert assessment.ready_for_decision_review is False
    assert assessment.blocked_tests == (PilotTestCode.PIL_02,)
    assert PilotTestCode.PIL_03 in assessment.missing_tests
    assert len(assessment.missing_tests) == 10


def test_pass_or_fail_requires_archived_evidence_reference() -> None:
    with pytest.raises(ValueError, match="preuve archivée"):
        PilotTestEvidence(
            code=PilotTestCode.PIL_01,
            status=PilotEvidenceStatus.PASS,
        )


def test_campaign_rejects_duplicate_pil_codes() -> None:
    duplicate = _evidence(PilotTestCode.PIL_01, PilotEvidenceStatus.PASS)
    with pytest.raises(ValueError, match="qu'une fois"):
        _campaign((duplicate, duplicate))
