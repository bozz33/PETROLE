from __future__ import annotations

import math

import pytest

import hydro_gas


def _problem() -> hydro_gas.StationaryWeymouthProblem:
    return hydro_gas.StationaryWeymouthProblem(
        problem_ref="problem://gas/numerics/simple-v1",
        network=hydro_gas.SteadyGasNetwork(
            nodes=(
                hydro_gas.SteadyGasNode("A", "model://node/A"),
                hydro_gas.SteadyGasNode("B", "model://node/B"),
            ),
            pipes=(hydro_gas.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),),
        ),
        pressure_slacks=(hydro_gas.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A"),),
        specified_boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("DEMAND-B", "B", -3.0, "boundary://demand/B"),
        ),
    )


def _state() -> hydro_gas.StationaryWeymouthUnknownState:
    return hydro_gas.StationaryWeymouthUnknownState(
        state_ref="state://gas/numerics/001",
        unknown_node_pressures=(hydro_gas.GasNodePressure("B", 4_900_000.0, "state://pressure/B"),),
        pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 3.0, "state://flow/P1"),),
        slack_external_flows=(
            hydro_gas.GasBoundaryMassFlow("SLACK-A", "A", 3.0, "state://slack/A"),
        ),
    )


def _scale() -> hydro_gas.StationaryWeymouthNumericalScale:
    return hydro_gas.StationaryWeymouthNumericalScale(
        pressure_squared_scale_pa2=25_000_000_000_000.0,
        mass_flow_scale_kg_s=10.0,
        mass_residual_scale_kg_s=10.0,
        pipe_residual_scale_pa2=1_000_000_000_000.0,
        source_ref="protocol://gas/numerics/scales/synthetic-test-only",
    )


def _parameters() -> tuple[hydro_gas.WeymouthSiPipeParameters, ...]:
    return (
        hydro_gas.WeymouthSiPipeParameters(
            pipe_id="P1",
            length_m=1_000.0,
            diameter_m=0.5,
            friction_factor=0.01,
            sound_speed_m_s=350.0,
            equation_ref="reference://weymouth/validated-formulation",
            parameter_source_ref="reference://parameters/numerics-simple",
        ),
    )


def test_unknown_state_encodes_to_deterministic_squared_pressure_coordinates() -> None:
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(_problem())

    vector = hydro_gas.encode_stationary_weymouth_unknown_state(layout, _state(), _scale())

    assert vector.values == pytest.approx((0.9604, 0.3, 0.3))
    assert vector.source_ref == "state://gas/numerics/001"
    assert len(vector.values) == layout.unknown_count


def test_numerical_vector_round_trip_preserves_physical_values_and_boundary_identity() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    state = _state()
    scale = _scale()
    vector = hydro_gas.encode_stationary_weymouth_unknown_state(layout, state, scale)

    decoded = hydro_gas.decode_stationary_weymouth_numerical_vector(
        layout,
        state,
        vector,
        scale,
        state_ref="state://gas/numerics/decoded-001",
    )

    assert decoded.state_ref == "state://gas/numerics/decoded-001"
    assert decoded.unknown_node_pressures[0].node_id == "B"
    assert decoded.unknown_node_pressures[0].pressure_pa == pytest.approx(4_900_000.0)
    assert decoded.pipe_flows[0].pipe_id == "P1"
    assert decoded.pipe_flows[0].mass_flow_kg_s == pytest.approx(3.0)
    assert decoded.slack_external_flows[0].boundary_id == "SLACK-A"
    assert decoded.slack_external_flows[0].node_id == "A"
    assert decoded.slack_external_flows[0].mass_flow_kg_s == pytest.approx(3.0)
    assert "#pressure-squared/B" in decoded.unknown_node_pressures[0].source_ref


def test_residual_encoding_uses_separate_explicit_mass_and_pipe_scales() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    evaluation = hydro_gas.evaluate_stationary_weymouth_unknown_state(
        problem,
        layout,
        _state(),
        _parameters(),
    )
    scale = _scale()

    vector = hydro_gas.encode_stationary_weymouth_residuals(
        layout,
        evaluation.residuals,
        scale,
        source_ref="evaluation://gas/numerics/residuals-001",
    )

    mass_residuals = tuple(
        item.residual_kg_s / scale.mass_residual_scale_kg_s
        for item in evaluation.residuals.mass_balance.node_balances
    )
    pipe_residuals = tuple(
        item.residual_pa2 / scale.pipe_residual_scale_pa2
        for item in evaluation.residuals.pipe_residuals
    )
    assert vector.values == pytest.approx(mass_residuals + pipe_residuals)
    assert len(vector.values) == layout.equation_count
    assert vector.source_ref == "evaluation://gas/numerics/residuals-001"


def test_decode_rejects_negative_squared_pressure_and_wrong_vector_size() -> None:
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(_problem())
    scale = _scale()

    negative_pressure = hydro_gas.StationaryWeymouthNumericalVector(
        values=(-0.1, 0.3, 0.3),
        source_ref="vector://gas/numerics/negative-pressure",
    )
    with pytest.raises(ValueError, match=r"pression au carré.*négative"):
        hydro_gas.decode_stationary_weymouth_numerical_vector(
            layout,
            _state(),
            negative_pressure,
            scale,
            state_ref="state://gas/numerics/rejected-negative",
        )

    wrong_size = hydro_gas.StationaryWeymouthNumericalVector(
        values=(0.9604, 0.3),
        source_ref="vector://gas/numerics/wrong-size",
    )
    with pytest.raises(ValueError, match="taille du vecteur"):
        hydro_gas.decode_stationary_weymouth_numerical_vector(
            layout,
            _state(),
            wrong_size,
            scale,
            state_ref="state://gas/numerics/rejected-size",
        )


def test_scales_are_explicit_sourced_finite_and_strictly_positive() -> None:
    with pytest.raises(ValueError, match="provenance"):
        hydro_gas.StationaryWeymouthNumericalScale(
            pressure_squared_scale_pa2=1.0,
            mass_flow_scale_kg_s=1.0,
            mass_residual_scale_kg_s=1.0,
            pipe_residual_scale_pa2=1.0,
            source_ref="",
        )

    with pytest.raises(ValueError, match="strictement positives"):
        hydro_gas.StationaryWeymouthNumericalScale(
            pressure_squared_scale_pa2=0.0,
            mass_flow_scale_kg_s=1.0,
            mass_residual_scale_kg_s=1.0,
            pipe_residual_scale_pa2=1.0,
            source_ref="protocol://scales/invalid-zero",
        )

    with pytest.raises(ValueError, match="strictement positives"):
        hydro_gas.StationaryWeymouthNumericalScale(
            pressure_squared_scale_pa2=1.0,
            mass_flow_scale_kg_s=math.inf,
            mass_residual_scale_kg_s=1.0,
            pipe_residual_scale_pa2=1.0,
            source_ref="protocol://scales/invalid-inf",
        )


def test_numerical_vector_requires_finite_values_and_provenance() -> None:
    with pytest.raises(ValueError, match="provenance"):
        hydro_gas.StationaryWeymouthNumericalVector(values=(1.0,), source_ref="")

    with pytest.raises(ValueError, match="valeurs finies"):
        hydro_gas.StationaryWeymouthNumericalVector(
            values=(math.nan,),
            source_ref="vector://gas/numerics/non-finite",
        )
