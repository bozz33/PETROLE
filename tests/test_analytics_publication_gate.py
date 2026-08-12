from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hydro_api.services.analytics_publication_gate import (
    AnalyticsPublicationEvidence,
    AnalyticsPublicationRequirement,
    assess_analytics_publication_gate,
)

_OBSERVED_AT = datetime(2026, 8, 11, 6, 0, tzinfo=UTC)


def _evidence(
    requirement: AnalyticsPublicationRequirement,
    *,
    satisfied: bool = True,
) -> AnalyticsPublicationEvidence:
    return AnalyticsPublicationEvidence(
        requirement=requirement,
        satisfied=satisfied,
        evidence_ref=f"evidence://phase3/{requirement.value}/run-1",
        protocol_or_decision_ref=f"protocol://phase3/{requirement.value}/v1",
        observed_at=_OBSERVED_AT,
        note=None,
    )


def _all_requirements() -> tuple[AnalyticsPublicationRequirement, ...]:
    return (
        AnalyticsPublicationRequirement.FIELD_DATA_SUFFICIENT,
        AnalyticsPublicationRequirement.BUSINESS_HORIZON_AGREED,
        AnalyticsPublicationRequirement.NAIVE_BASELINE_DOCUMENTED,
        AnalyticsPublicationRequirement.SPLIT_PROTOCOL_FROZEN,
        AnalyticsPublicationRequirement.METRICS_PREDECLARED,
        AnalyticsPublicationRequirement.CONDITIONAL_THRESHOLDS_APPROVED,
        AnalyticsPublicationRequirement.ENGINEER_REVIEW_COMPLETED,
    )


def test_complete_positive_evidence_opens_documentary_pilot_gate() -> None:
    assessment = assess_analytics_publication_gate(
        tuple(_evidence(requirement) for requirement in _all_requirements())
    )

    assert assessment.publishable_for_pilot is True
    assert assessment.blocking_requirements == ()
    assert all(item.satisfied for item in assessment.requirements)


def test_missing_requirement_blocks_publication_without_being_inferred() -> None:
    evidence = tuple(
        _evidence(requirement)
        for requirement in _all_requirements()
        if requirement is not AnalyticsPublicationRequirement.ENGINEER_REVIEW_COMPLETED
    )

    assessment = assess_analytics_publication_gate(evidence)

    assert assessment.publishable_for_pilot is False
    assert assessment.blocking_requirements == (
        AnalyticsPublicationRequirement.ENGINEER_REVIEW_COMPLETED,
    )
    engineer_review = assessment.requirements[-1]
    assert engineer_review.satisfied is False
    assert engineer_review.evidence_ref is None


def test_explicit_negative_evidence_remains_visible_and_blocking() -> None:
    evidence = tuple(
        _evidence(
            requirement,
            satisfied=requirement is not AnalyticsPublicationRequirement.METRICS_PREDECLARED,
        )
        for requirement in _all_requirements()
    )

    assessment = assess_analytics_publication_gate(evidence)

    assert assessment.publishable_for_pilot is False
    assert assessment.blocking_requirements == (
        AnalyticsPublicationRequirement.METRICS_PREDECLARED,
    )
    metrics = assessment.requirements[4]
    assert metrics.satisfied is False
    assert metrics.evidence_ref == "evidence://phase3/metrics_chosen_before_test_observation/run-1"


def test_duplicate_requirement_evidence_is_rejected() -> None:
    item = _evidence(AnalyticsPublicationRequirement.FIELD_DATA_SUFFICIENT)
    with pytest.raises(ValueError, match="Une seule preuve"):
        assess_analytics_publication_gate((item, item))


def test_publication_evidence_requires_timezone_and_references() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        AnalyticsPublicationEvidence(
            requirement=AnalyticsPublicationRequirement.FIELD_DATA_SUFFICIENT,
            satisfied=True,
            evidence_ref="evidence://field-data",
            protocol_or_decision_ref="protocol://field-data/v1",
            observed_at=datetime(2026, 8, 11, 6, 0),
        )
