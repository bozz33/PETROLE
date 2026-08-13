from __future__ import annotations

import math

import pytest

from hydro_gas.weymouth_si import (
    WeymouthSiObservation,
    WeymouthSiPipeParameters,
    evaluate_weymouth_si_residual,
)

_EQUATION_REF = "GasModels.jl/docs/src/math-model.md@21422f18e7e328732ec8edd7995446d33f58e789"
_CASE_REF = "GasModels.jl/test/data/matgas/case-6-gf.m@21422f18e7e328732ec8edd7995446d33f58e789"
_REFERENCE_ARTIFACT = (
    "github-actions://bozz33/PETROLE/31657331294/9164893821/"
    "sha256:1ad529221dc0f4e05e30f0e73c1e01b8b4c80925f65d135a4c9b908a902e386e"
)


def _parameters(
    pipe_id: str = "P-1",
    *,
    length_m: float = 1_000.0,
    diameter_m: float = 0.5,
    friction_factor: float = 0.01,
    sound_speed_m_s: float = 350.0,
) -> WeymouthSiPipeParameters:
    return WeymouthSiPipeParameters(
        pipe_id=pipe_id,
        length_m=length_m,
        diameter_m=diameter_m,
        friction_factor=friction_factor,
        sound_speed_m_s=sound_speed_m_s,
        equation_ref=_EQUATION_REF,
        parameter_source_ref="engineering://gas/pipe/P-1/rev-1",
    )


def test_zero_flow_equal_pressures_has_exact_zero_residual() -> None:
    result = evaluate_weymouth_si_residual(
        _parameters(),
        WeymouthSiObservation(
            pipe_id="P-1",
            from_pressure_pa=4_000_000.0,
            to_pressure_pa=4_000_000.0,
            mass_flow_kg_s=0.0,
            source_ref="observation://gas/zero-flow",
        ),
    )

    assert result.pressure_squared_difference_pa2 == 0.0
    assert result.friction_term_pa2 == 0.0
    assert result.residual_pa2 == 0.0
    assert not hasattr(result, "passed")


def test_flow_sign_is_preserved_in_friction_term() -> None:
    parameters = _parameters()
    forward = evaluate_weymouth_si_residual(
        parameters,
        WeymouthSiObservation(
            pipe_id="P-1",
            from_pressure_pa=4_000_000.0,
            to_pressure_pa=4_000_000.0,
            mass_flow_kg_s=2.0,
            source_ref="observation://gas/forward",
        ),
    )
    reverse = evaluate_weymouth_si_residual(
        parameters,
        WeymouthSiObservation(
            pipe_id="P-1",
            from_pressure_pa=4_000_000.0,
            to_pressure_pa=4_000_000.0,
            mass_flow_kg_s=-2.0,
            source_ref="observation://gas/reverse",
        ),
    )

    assert forward.friction_term_pa2 == -reverse.friction_term_pa2
    assert forward.residual_pa2 == -reverse.residual_pa2


def test_resistance_coefficient_matches_documented_si_expression() -> None:
    parameters = _parameters(
        length_m=50_000.0,
        diameter_m=0.6,
        friction_factor=0.01,
        sound_speed_m_s=371.6643,
    )
    area_m2 = math.pi * 0.6 * 0.6 / 4.0
    expected = 0.01 * 50_000.0 * 371.6643 * 371.6643 / (0.6 * area_m2 * area_m2)

    assert parameters.area_m2 == area_m2
    assert parameters.resistance_coefficient_pa2_per_kg_s2 == expected


def test_case6_gasmodels_reference_is_recorded_as_raw_residuals_without_threshold() -> None:
    base_pressure_pa = 3_000_000.0
    base_flow_kg_s = 200.0
    sound_speed_m_s = 371.6643
    pressure_pu = {
        "1": 1.3333333333333333,
        "2": 1.2564960367699658,
        "3": 1.144205311555209,
        "4": 1.43389675344488,
        "5": 1.8328972602290563,
        "6": 1.5771456897361187,
    }
    flow_pu = {
        "1": 0.5275000000000001,
        "2": 0.1622573718391018,
        "3": 0.20524262816089825,
        "4": -0.04774262816089823,
    }
    pipe_data = {
        "1": ("5", "2", 0.6, 50_000.0, 0.01),
        "2": ("2", "3", 0.6, 80_000.0, 0.01),
        "3": ("6", "4", 0.6, 80_000.0, 0.01),
        "4": ("3", "4", 0.3, 80_000.0, 0.01),
    }
    expected_residuals_pa2 = {
        "1": 0.0,
        "2": 1.04248046875,
        "3": 1.06103515625,
        "4": -33.4970703125,
    }

    observed_residuals: dict[str, float] = {}
    for pipe_id, (from_id, to_id, diameter_m, length_m, friction_factor) in pipe_data.items():
        result = evaluate_weymouth_si_residual(
            WeymouthSiPipeParameters(
                pipe_id=pipe_id,
                length_m=length_m,
                diameter_m=diameter_m,
                friction_factor=friction_factor,
                sound_speed_m_s=sound_speed_m_s,
                equation_ref=_EQUATION_REF,
                parameter_source_ref=_CASE_REF,
            ),
            WeymouthSiObservation(
                pipe_id=pipe_id,
                from_pressure_pa=pressure_pu[from_id] * base_pressure_pa,
                to_pressure_pa=pressure_pu[to_id] * base_pressure_pa,
                mass_flow_kg_s=flow_pu[pipe_id] * base_flow_kg_s,
                source_ref=_REFERENCE_ARTIFACT,
            ),
        )
        observed_residuals[pipe_id] = result.residual_pa2
        assert result.equation_ref == _EQUATION_REF
        assert result.parameter_source_ref == _CASE_REF
        assert result.observation_source_ref == _REFERENCE_ARTIFACT
        assert not hasattr(result, "passed")

    assert observed_residuals == expected_residuals_pa2


def test_parameters_and_observation_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="strictement positif"):
        _parameters(length_m=0.0)
    with pytest.raises(ValueError, match="positif ou nul"):
        _parameters(friction_factor=-0.01)
    with pytest.raises(ValueError, match="pressions absolues"):
        WeymouthSiObservation(
            pipe_id="P-1",
            from_pressure_pa=-1.0,
            to_pressure_pa=1.0,
            mass_flow_kg_s=0.0,
            source_ref="observation://invalid",
        )
    with pytest.raises(ValueError, match="débit massique"):
        WeymouthSiObservation(
            pipe_id="P-1",
            from_pressure_pa=1.0,
            to_pressure_pa=1.0,
            mass_flow_kg_s=math.inf,
            source_ref="observation://invalid",
        )


def test_evaluator_rejects_pipe_mismatch() -> None:
    with pytest.raises(ValueError, match="même conduite"):
        evaluate_weymouth_si_residual(
            _parameters("P-1"),
            WeymouthSiObservation(
                pipe_id="P-2",
                from_pressure_pa=1.0,
                to_pressure_pa=1.0,
                mass_flow_kg_s=0.0,
                source_ref="observation://mismatch",
            ),
        )
