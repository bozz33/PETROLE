from __future__ import annotations

import pytest

from hydro_shared.reliability import (
    ReliabilityEvidence,
    ReliabilityObjectives,
    assess_reliability,
)


def test_reliability_assessment_uses_only_explicit_objectives() -> None:
    assessment = assess_reliability(
        ReliabilityObjectives(
            minimum_availability_ratio=0.995,
            maximum_p95_latency_s=2.0,
            maximum_rpo_s=60.0,
            maximum_rto_s=300.0,
        ),
        ReliabilityEvidence(
            availability_ratio=0.999,
            p95_latency_s=1.2,
            observed_rpo_s=30.0,
            observed_rto_s=180.0,
        ),
    )
    assert assessment.passed is True
    assert assessment.violations == ()


def test_reliability_assessment_reports_each_failed_objective() -> None:
    assessment = assess_reliability(
        ReliabilityObjectives(
            minimum_availability_ratio=0.999,
            maximum_p95_latency_s=1.0,
            maximum_rpo_s=10.0,
            maximum_rto_s=60.0,
        ),
        ReliabilityEvidence(
            availability_ratio=0.99,
            p95_latency_s=1.5,
            observed_rpo_s=30.0,
            observed_rto_s=120.0,
        ),
    )
    assert assessment.passed is False
    assert assessment.violations == (
        "availability_below_objective",
        "p95_latency_above_objective",
        "rpo_above_objective",
        "rto_above_objective",
    )


def test_invalid_reliability_targets_are_rejected() -> None:
    with pytest.raises(ValueError, match="disponibilité minimale"):
        ReliabilityObjectives(
            minimum_availability_ratio=1.1,
            maximum_p95_latency_s=1.0,
            maximum_rpo_s=10.0,
            maximum_rto_s=60.0,
        )
