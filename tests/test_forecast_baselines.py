from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hydro_api.services.forecast_baselines import (
    compare_linear_to_persistence,
    fit_persistence_forecast,
)
from hydro_api.services.forecasting import (
    ForecastDatasetSplit,
    ForecastObservation,
    fit_linear_forecast,
)


def _observation(hour: int, value: float) -> ForecastObservation:
    return ForecastObservation(
        timestamp=datetime(2026, 8, 1, tzinfo=UTC) + timedelta(hours=hour),
        value_si=value,
    )


def test_persistence_uses_only_latest_train_value() -> None:
    split = ForecastDatasetSplit(
        train=(_observation(0, 1.0), _observation(1, 2.0), _observation(2, 3.0)),
        validation=(_observation(3, 4.0), _observation(4, 5.0)),
        test=(_observation(5, 6.0),),
    )

    baseline = fit_persistence_forecast(split)

    assert baseline.reference_value_si == pytest.approx(3.0)
    assert baseline.validation_metrics.mae_si == pytest.approx(1.5)
    assert baseline.validation_metrics.rmse_si == pytest.approx((2.5) ** 0.5)
    assert baseline.test_metrics.mae_si == pytest.approx(3.0)


def test_linear_model_is_compared_factually_against_naive_baseline() -> None:
    split = ForecastDatasetSplit(
        train=(_observation(0, 0.0), _observation(1, 2.0), _observation(2, 4.0)),
        validation=(_observation(3, 6.0), _observation(4, 8.0)),
        test=(_observation(5, 10.0), _observation(6, 12.0)),
    )

    linear = fit_linear_forecast(split)
    baseline = fit_persistence_forecast(split)
    comparison = compare_linear_to_persistence(linear, baseline)

    assert linear.validation_metrics.rmse_si == pytest.approx(0.0)
    assert linear.test_metrics.rmse_si == pytest.approx(0.0)
    assert comparison.validation.mae_delta_si < 0.0
    assert comparison.validation.rmse_delta_si < 0.0
    assert comparison.test.mae_delta_si < 0.0
    assert comparison.test.rmse_delta_si < 0.0


def test_equal_constant_series_produces_zero_metric_delta() -> None:
    split = ForecastDatasetSplit(
        train=(_observation(0, 7.0), _observation(1, 7.0)),
        validation=(_observation(2, 7.0),),
        test=(_observation(3, 7.0),),
    )

    comparison = compare_linear_to_persistence(
        fit_linear_forecast(split),
        fit_persistence_forecast(split),
    )

    assert comparison.validation.mae_delta_si == pytest.approx(0.0)
    assert comparison.validation.rmse_delta_si == pytest.approx(0.0)
    assert comparison.test.mae_delta_si == pytest.approx(0.0)
    assert comparison.test.rmse_delta_si == pytest.approx(0.0)


def test_comparison_refuses_different_evaluation_populations() -> None:
    split = ForecastDatasetSplit(
        train=(_observation(0, 1.0), _observation(1, 2.0)),
        validation=(_observation(2, 3.0),),
        test=(_observation(3, 4.0),),
    )
    linear = fit_linear_forecast(split)
    baseline = fit_persistence_forecast(split)

    altered_metrics = type(baseline.validation_metrics)(
        sample_count=2,
        mae_si=baseline.validation_metrics.mae_si,
        rmse_si=baseline.validation_metrics.rmse_si,
        bias_si=baseline.validation_metrics.bias_si,
    )
    altered = type(baseline)(
        reference_value_si=baseline.reference_value_si,
        validation_metrics=altered_metrics,
        test_metrics=baseline.test_metrics,
    )

    with pytest.raises(ValueError, match="même nombre de points"):
        compare_linear_to_persistence(linear, altered)
