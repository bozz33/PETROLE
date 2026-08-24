"""Tests analytiques du cadre d'évaluation LDS de Phase 7."""

from __future__ import annotations

import pytest

from hydro_leak import detection_performance


def test_detection_metrics_are_explicit_and_threshold_free() -> None:
    performance = detection_performance(
        truth=[True, True, False, False, False],
        predicted=[True, False, True, False, False],
        matched_detection_delays_s=[12.0],
    )

    assert performance.true_positive == 1
    assert performance.false_positive == 1
    assert performance.false_negative == 1
    assert performance.true_negative == 2
    assert performance.precision == pytest.approx(0.5)
    assert performance.recall == pytest.approx(0.5)
    assert performance.specificity == pytest.approx(2 / 3)
    assert performance.false_positive_rate == pytest.approx(1 / 3)
    assert performance.accuracy == pytest.approx(0.6)
    assert performance.mean_detection_delay_s == pytest.approx(12.0)
    assert performance.maximum_detection_delay_s == pytest.approx(12.0)


def test_detection_metrics_refuse_ambiguous_campaigns() -> None:
    with pytest.raises(ValueError, match="même taille"):
        detection_performance(truth=[True], predicted=[True, False])

    with pytest.raises(ValueError, match="au moins un"):
        detection_performance(truth=[], predicted=[])

    with pytest.raises(ValueError, match="délais"):
        detection_performance(
            truth=[True],
            predicted=[True],
            matched_detection_delays_s=[-1.0],
        )
