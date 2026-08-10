from __future__ import annotations

import math

import pytest

from hydro_optimization.calibration import (
    CalibrationDataset,
    CalibrationObservation,
    CalibrationParameter,
    calibrate_parameters,
)


def _linear_model(parameters, observation: CalibrationObservation) -> float:
    x_value = observation.inputs[0]
    return parameters["slope"] * x_value + parameters["intercept"]


def test_calibration_never_uses_held_out_validation_points() -> None:
    dataset = CalibrationDataset(
        calibration=(
            CalibrationObservation("c-0", 1.0, "steady-low", (0.0,)),
            CalibrationObservation("c-1", 3.0, "steady-low", (1.0,)),
            CalibrationObservation("c-2", 5.0, "steady-low", (2.0,)),
        ),
        validation=(
            CalibrationObservation("v-0", 7.0, "steady-high", (3.0,)),
            CalibrationObservation("v-1", 9.0, "steady-high", (4.0,)),
        ),
    )
    result = calibrate_parameters(
        parameters=(
            CalibrationParameter("slope", 1.0, 0.1, 4.0, "1"),
            CalibrationParameter("intercept", 0.0, -5.0, 5.0, "Pa"),
        ),
        dataset=dataset,
        evaluator=_linear_model,
    )

    values = {parameter.name: parameter.value for parameter in result.parameters}
    assert values["slope"] == pytest.approx(2.0, rel=1e-8, abs=1e-8)
    assert values["intercept"] == pytest.approx(1.0, rel=1e-8, abs=1e-8)
    assert result.calibration_metrics.rmse_si == pytest.approx(0.0, abs=1e-8)
    assert result.validation_metrics.rmse_si == pytest.approx(0.0, abs=1e-8)
    assert result.validation_regimes == ("steady-high",)
    assert result.converged is True
    assert result.function_evaluations > 0


def test_validation_regime_must_be_distinct_by_default() -> None:
    with pytest.raises(ValueError, match="régime de validation"):
        CalibrationDataset(
            calibration=(CalibrationObservation("c", 1.0, "steady", (0.0,)),),
            validation=(CalibrationObservation("v", 2.0, "steady", (1.0,)),),
        )


def test_dataset_rejects_observation_reuse_between_splits() -> None:
    with pytest.raises(ValueError, match="doivent être disjoints"):
        CalibrationDataset(
            calibration=(CalibrationObservation("same", 1.0, "low", (0.0,)),),
            validation=(CalibrationObservation("same", 2.0, "high", (1.0,)),),
        )


def test_calibration_rejects_underdetermined_observation_count() -> None:
    dataset = CalibrationDataset(
        calibration=(CalibrationObservation("c", 1.0, "low", (0.0,)),),
        validation=(CalibrationObservation("v", 2.0, "high", (1.0,)),),
    )
    with pytest.raises(ValueError, match="moins d'observations"):
        calibrate_parameters(
            parameters=(
                CalibrationParameter("slope", 1.0, 0.0, 2.0),
                CalibrationParameter("intercept", 0.0, -1.0, 1.0),
            ),
            dataset=dataset,
            evaluator=_linear_model,
        )


def test_non_finite_model_prediction_is_rejected() -> None:
    dataset = CalibrationDataset(
        calibration=(CalibrationObservation("c", 1.0, "low", (0.0,)),),
        validation=(CalibrationObservation("v", 2.0, "high", (1.0,)),),
    )

    def invalid_model(parameters, observation) -> float:
        del parameters, observation
        return math.nan

    with pytest.raises(ValueError, match="valeur non finie"):
        calibrate_parameters(
            parameters=(CalibrationParameter("slope", 1.0, 0.0, 2.0),),
            dataset=dataset,
            evaluator=invalid_model,
        )
