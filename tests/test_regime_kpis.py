from __future__ import annotations

import math

import pytest

from hydro_api.services.regime_kpis import RegimeKpiObservation, summarize_regime_kpis


def test_multi_regime_summary_reconstructs_weighted_metrics_exactly() -> None:
    summary = summarize_regime_kpis(
        (
            RegimeKpiObservation(
                regime_id="low-flow",
                comparison_ref="comparison://1",
                si_unit="Pa",
                sample_count=10,
                bias_si=100.0,
                mae_si=200.0,
                rmse_si=250.0,
            ),
            RegimeKpiObservation(
                regime_id="high-flow",
                comparison_ref="comparison://2",
                si_unit="Pa",
                sample_count=30,
                bias_si=-50.0,
                mae_si=300.0,
                rmse_si=400.0,
            ),
        )
    )

    assert summary.regime_count == 2
    assert summary.total_sample_count == 40
    assert summary.weighted_bias_si == pytest.approx(-12.5)
    assert summary.weighted_mae_si == pytest.approx(275.0)
    expected_rmse = math.sqrt((10 * 250.0**2 + 30 * 400.0**2) / 40)
    assert summary.pooled_rmse_si == pytest.approx(expected_rmse)
    assert summary.minimum_regime_rmse_si == pytest.approx(250.0)
    assert summary.maximum_regime_rmse_si == pytest.approx(400.0)


def test_multi_regime_summary_refuses_mixed_units() -> None:
    with pytest.raises(ValueError, match="même unité SI"):
        summarize_regime_kpis(
            (
                RegimeKpiObservation("r1", "comparison://1", "Pa", 2, 0.0, 1.0, 1.0),
                RegimeKpiObservation("r2", "comparison://2", "m^3/s", 2, 0.0, 1.0, 1.0),
            )
        )


def test_multi_regime_summary_refuses_duplicate_regime_identifier() -> None:
    observation = RegimeKpiObservation("r1", "comparison://1", "Pa", 2, 0.0, 1.0, 1.0)
    with pytest.raises(ValueError, match="qu'une fois"):
        summarize_regime_kpis((observation, observation))
