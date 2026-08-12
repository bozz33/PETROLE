from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hydro_api.services.forecast_horizons import (
    ForecastHorizonDefinition,
    ForecastHorizonEvaluationPoint,
    evaluate_forecast_horizon,
)

ORIGIN = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)


def _definition(**overrides) -> ForecastHorizonDefinition:
    payload = {
        "horizon_ref": "forecast-horizon://pressure/PT-101/30min",
        "target_ref": "tag://PT-101",
        "business_purpose_ref": "use-case://operations/30min-pressure-review",
        "decision_ref": "decision://pilot/analytics/horizon/v1",
        "source_ref": "protocol://phase3/forecast/pilot-v1",
        "sampling_interval_seconds": 300,
        "lead_steps": 6,
    }
    payload.update(overrides)
    return ForecastHorizonDefinition(**payload)


def _point(
    index: int,
    *,
    predicted: float,
    observed: float,
    lead: timedelta = timedelta(minutes=30),
) -> ForecastHorizonEvaluationPoint:
    issued = ORIGIN + timedelta(hours=index)
    return ForecastHorizonEvaluationPoint(
        point_ref=f"forecast-point://PT-101/{index}",
        issued_at=issued,
        target_timestamp=issued + lead,
        predicted_value_si=predicted,
        observed_value_si=observed,
        prediction_source_ref="run://forecast/ols/test-v1",
        observation_source_ref="dataset://historian/PT-101/test-v1",
    )


def test_horizon_evaluation_uses_only_exact_business_lead_time() -> None:
    evaluation = evaluate_forecast_horizon(
        _definition(),
        (
            _point(0, predicted=101.0, observed=100.0),
            _point(1, predicted=98.0, observed=100.0),
        ),
    )

    assert evaluation.horizon_ref == "forecast-horizon://pressure/PT-101/30min"
    assert evaluation.lead_time_seconds == 1800
    assert evaluation.sample_count == 2
    assert evaluation.metrics.mae_si == pytest.approx(1.5)
    assert evaluation.metrics.rmse_si == pytest.approx((2.5) ** 0.5)
    assert evaluation.metrics.bias_si == pytest.approx(-0.5)
    assert evaluation.prediction_source_refs == ("run://forecast/ols/test-v1",)
    assert evaluation.observation_source_refs == ("dataset://historian/PT-101/test-v1",)


def test_horizon_evaluation_rejects_mixed_lead_times() -> None:
    with pytest.raises(ValueError, match="ne respecte pas l'horizon"):
        evaluate_forecast_horizon(
            _definition(),
            (
                _point(0, predicted=100.0, observed=100.0),
                _point(1, predicted=100.0, observed=100.0, lead=timedelta(minutes=60)),
            ),
        )


def test_horizon_definition_requires_explicit_business_decision_and_positive_steps() -> None:
    with pytest.raises(ValueError, match="usage métier"):
        _definition(business_purpose_ref="")

    with pytest.raises(ValueError, match="intervalle"):
        _definition(sampling_interval_seconds=0)

    with pytest.raises(ValueError, match="nombre de pas"):
        _definition(lead_steps=0)


def test_horizon_point_requires_future_timezone_aware_target_and_finite_values() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        ForecastHorizonEvaluationPoint(
            point_ref="point://naive",
            issued_at=datetime(2026, 8, 1, 0, 0),
            target_timestamp=datetime(2026, 8, 1, 0, 30),
            predicted_value_si=1.0,
            observed_value_si=1.0,
            prediction_source_ref="run://1",
            observation_source_ref="dataset://1",
        )

    with pytest.raises(ValueError, match="strictement postérieure"):
        _point(0, predicted=1.0, observed=1.0, lead=timedelta(0))

    with pytest.raises(ValueError, match="finies"):
        _point(0, predicted=float("nan"), observed=1.0)


def test_horizon_evaluation_rejects_duplicate_references_and_issue_instants() -> None:
    first = _point(0, predicted=1.0, observed=1.0)
    duplicate_ref = ForecastHorizonEvaluationPoint(
        point_ref=first.point_ref,
        issued_at=ORIGIN + timedelta(hours=1),
        target_timestamp=ORIGIN + timedelta(hours=1, minutes=30),
        predicted_value_si=1.0,
        observed_value_si=1.0,
        prediction_source_ref="run://2",
        observation_source_ref="dataset://2",
    )
    with pytest.raises(ValueError, match="références"):
        evaluate_forecast_horizon(_definition(), (first, duplicate_ref))

    same_issue = ForecastHorizonEvaluationPoint(
        point_ref="forecast-point://PT-101/same-issue",
        issued_at=first.issued_at,
        target_timestamp=first.target_timestamp,
        predicted_value_si=2.0,
        observed_value_si=2.0,
        prediction_source_ref="run://2",
        observation_source_ref="dataset://2",
    )
    with pytest.raises(ValueError, match="même instant d'émission"):
        evaluate_forecast_horizon(_definition(), (first, same_issue))


def test_horizon_evaluation_requires_at_least_one_point() -> None:
    with pytest.raises(ValueError, match="au moins un point"):
        evaluate_forecast_horizon(_definition(), ())
