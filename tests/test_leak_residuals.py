from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hydro_leak import MeasurementModelResidualInput, compute_measurement_model_residual


def test_residual_combines_uncertainties_without_detection_threshold() -> None:
    result = compute_measurement_model_residual(
        MeasurementModelResidualInput(
            timestamp=datetime(2026, 8, 11, 10, 0, tzinfo=UTC),
            measured_value_si=102.0,
            modeled_value_si=100.0,
            measurement_standard_uncertainty_si=0.6,
            model_standard_uncertainty_si=0.8,
            si_unit="Pa",
            measurement_ref="sample://PT-101/42",
            model_ref="twin://snapshot/42",
        )
    )

    assert result.residual_si == pytest.approx(2.0)
    assert result.absolute_residual_si == pytest.approx(2.0)
    assert result.combined_standard_uncertainty_si == pytest.approx(1.0)
    assert result.normalized_residual == pytest.approx(2.0)
    assert not hasattr(result, "leak_detected")


def test_zero_combined_uncertainty_does_not_invent_normalized_score() -> None:
    result = compute_measurement_model_residual(
        MeasurementModelResidualInput(
            timestamp=datetime(2026, 8, 11, 10, 0, tzinfo=UTC),
            measured_value_si=12.0,
            modeled_value_si=11.0,
            measurement_standard_uncertainty_si=0.0,
            model_standard_uncertainty_si=0.0,
            si_unit="m3/s",
            measurement_ref="sample://FT-101/42",
            model_ref="twin://snapshot/42",
        )
    )

    assert result.normalized_residual is None


def test_residual_rejects_negative_uncertainty() -> None:
    with pytest.raises(ValueError, match="incertitudes-types"):
        MeasurementModelResidualInput(
            timestamp=datetime(2026, 8, 11, 10, 0, tzinfo=UTC),
            measured_value_si=1.0,
            modeled_value_si=1.0,
            measurement_standard_uncertainty_si=-0.1,
            model_standard_uncertainty_si=0.1,
            si_unit="Pa",
            measurement_ref="sample://PT-101/42",
            model_ref="twin://snapshot/42",
        )
