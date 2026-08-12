from __future__ import annotations

import pytest

from hydro_leak import DetectionPerformance
from hydro_leak.validation_campaign import (
    LeakValidationCriteria,
    assess_validation_criteria,
)


def _performance() -> DetectionPerformance:
    return DetectionPerformance(
        true_positive=8,
        false_positive=1,
        false_negative=2,
        true_negative=9,
        precision=8 / 9,
        recall=0.8,
        specificity=0.9,
        false_positive_rate=0.1,
        accuracy=0.85,
        mean_detection_delay_s=12.0,
        maximum_detection_delay_s=25.0,
    )


def test_campaign_evaluates_only_explicit_preregistered_criteria() -> None:
    criteria = LeakValidationCriteria(
        source_ref="protocol://leak-campaign/v1",
        minimum_recall=0.75,
        maximum_false_positive_rate=0.15,
        minimum_sample_count=20,
    )

    assessment = assess_validation_criteria(_performance(), criteria)

    assert tuple(result.criterion for result in assessment.criterion_results) == (
        "minimum_recall",
        "minimum_sample_count",
        "maximum_false_positive_rate",
    )
    assert all(result.passed is True for result in assessment.criterion_results)
    assert assessment.all_evaluable_criteria_passed is True
    assert assessment.has_unevaluable_criteria is False
    assert assessment.criteria_source_ref == "protocol://leak-campaign/v1"


def test_campaign_reports_failure_without_changing_thresholds() -> None:
    criteria = LeakValidationCriteria(
        source_ref="protocol://leak-campaign/v2",
        minimum_precision=0.95,
        maximum_detection_delay_s=20.0,
    )

    assessment = assess_validation_criteria(_performance(), criteria)

    assert tuple(result.passed for result in assessment.criterion_results) == (False, False)
    assert assessment.all_evaluable_criteria_passed is False


def test_missing_metric_is_explicitly_unevaluable() -> None:
    performance = DetectionPerformance(
        true_positive=0,
        false_positive=0,
        false_negative=0,
        true_negative=10,
        precision=None,
        recall=None,
        specificity=1.0,
        false_positive_rate=0.0,
        accuracy=1.0,
        mean_detection_delay_s=None,
        maximum_detection_delay_s=None,
    )
    criteria = LeakValidationCriteria(
        source_ref="protocol://leak-campaign/v3",
        minimum_precision=0.8,
        maximum_mean_detection_delay_s=30.0,
    )

    assessment = assess_validation_criteria(performance, criteria)

    assert tuple(result.passed for result in assessment.criterion_results) == (None, None)
    assert assessment.all_evaluable_criteria_passed is None
    assert assessment.has_unevaluable_criteria is True
    assert all(result.reason == "metric_unavailable" for result in assessment.criterion_results)


def test_mixed_pass_and_unevaluable_does_not_hide_missing_evidence() -> None:
    performance = DetectionPerformance(
        true_positive=0,
        false_positive=0,
        false_negative=0,
        true_negative=10,
        precision=None,
        recall=None,
        specificity=1.0,
        false_positive_rate=0.0,
        accuracy=1.0,
        mean_detection_delay_s=None,
        maximum_detection_delay_s=None,
    )
    criteria = LeakValidationCriteria(
        source_ref="protocol://leak-campaign/v4",
        minimum_specificity=0.9,
        minimum_recall=0.8,
    )

    assessment = assess_validation_criteria(performance, criteria)

    assert assessment.all_evaluable_criteria_passed is True
    assert assessment.has_unevaluable_criteria is True


def test_campaign_criteria_require_explicit_source_and_at_least_one_threshold() -> None:
    with pytest.raises(ValueError, match="provenance"):
        LeakValidationCriteria(source_ref="", minimum_recall=0.8)

    with pytest.raises(ValueError, match="Au moins un critère"):
        LeakValidationCriteria(source_ref="protocol://empty")


def test_campaign_criteria_reject_invalid_ratios_delays_and_sample_counts() -> None:
    with pytest.raises(ValueError, match="\[0, 1\]"):
        LeakValidationCriteria(source_ref="protocol://bad-ratio", minimum_recall=1.1)

    with pytest.raises(ValueError, match="délai"):
        LeakValidationCriteria(
            source_ref="protocol://bad-delay",
            maximum_detection_delay_s=-1.0,
        )

    with pytest.raises(ValueError, match="strictement positif"):
        LeakValidationCriteria(source_ref="protocol://bad-count", minimum_sample_count=0)
