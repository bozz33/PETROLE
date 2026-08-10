from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hydro_api.services.forecasting import (
    ForecastDatasetSplit,
    ForecastObservation,
    fit_linear_forecast,
)


def _point(hour: int, value: float) -> ForecastObservation:
    return ForecastObservation(
        timestamp=datetime(2026, 8, 10, 0, 0, tzinfo=UTC) + timedelta(hours=hour),
        value_si=value,
    )


def test_linear_forecast_keeps_validation_and_test_out_of_fit() -> None:
    split = ForecastDatasetSplit(
        train=(_point(0, 1.0), _point(1, 3.0), _point(2, 5.0)),
        validation=(_point(3, 7.0), _point(4, 9.0)),
        test=(_point(5, 11.0), _point(6, 13.0)),
    )
    result = fit_linear_forecast(split)
    assert result.intercept_si == pytest.approx(1.0)
    assert result.slope_si_per_second == pytest.approx(2.0 / 3600.0)
    assert result.validation_metrics.rmse_si == pytest.approx(0.0, abs=1e-12)
    assert result.test_metrics.rmse_si == pytest.approx(0.0, abs=1e-12)
    assert result.predict(_point(7, 0.0).timestamp) == pytest.approx(15.0)


def test_forecast_rejects_temporal_leakage_between_splits() -> None:
    with pytest.raises(ValueError, match="validation"):
        ForecastDatasetSplit(
            train=(_point(0, 1.0), _point(2, 5.0)),
            validation=(_point(1, 3.0),),
            test=(_point(3, 7.0),),
        )


def test_forecast_requires_independent_test_set() -> None:
    with pytest.raises(ValueError, match="validation et de test"):
        ForecastDatasetSplit(
            train=(_point(0, 1.0), _point(1, 3.0)),
            validation=(_point(2, 5.0),),
            test=(),
        )
