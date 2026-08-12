from __future__ import annotations

import pytest

from hydro_api.services.condition_monitoring import (
    ConditionBaseline,
    ConditionStatus,
    ConditionThresholds,
    assess_condition,
)


def _baseline() -> ConditionBaseline:
    return ConditionBaseline(
        reference="baseline://pump-P01/v3",
        mean_si=100.0,
        standard_deviation_si=5.0,
        unit="K",
    )


def _thresholds() -> ConditionThresholds:
    return ConditionThresholds(watch_absolute_z=2.0, investigate_absolute_z=3.0)


def test_condition_monitoring_classifies_against_explicit_thresholds() -> None:
    normal = assess_condition(value_si=104.0, baseline=_baseline(), thresholds=_thresholds())
    watch = assess_condition(value_si=111.0, baseline=_baseline(), thresholds=_thresholds())
    investigate = assess_condition(
        value_si=116.0,
        baseline=_baseline(),
        thresholds=_thresholds(),
    )

    assert normal.status is ConditionStatus.NORMAL
    assert watch.status is ConditionStatus.WATCH
    assert investigate.status is ConditionStatus.INVESTIGATE
    assert investigate.z_score == pytest.approx(3.2)
    assert investigate.baseline_reference == "baseline://pump-P01/v3"


def test_condition_monitoring_is_symmetric_for_negative_deviation() -> None:
    assessment = assess_condition(value_si=84.0, baseline=_baseline(), thresholds=_thresholds())
    assert assessment.status is ConditionStatus.INVESTIGATE
    assert assessment.z_score == pytest.approx(-3.2)


def test_condition_thresholds_must_be_ordered() -> None:
    with pytest.raises(ValueError, match="strictement inférieur"):
        ConditionThresholds(watch_absolute_z=3.0, investigate_absolute_z=2.0)
