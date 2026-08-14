from __future__ import annotations

import pytest

import hydro_gas


def _problem() -> hydro_gas.StationaryWeymouthProblem:
    return hydro_gas.StationaryWeymouthProblem(
        problem_ref="problem://gas/numerical-evaluation/simple-v1",
        network=hydro_gas.SteadyGasNetwork(
            nodes=(
                hydro_gas.SteadyGasNode("A", "model://node/A"),
                hydro_gas.SteadyGasNode("B", "model://node/B"),
            ),
            pipes=(hydro_gas.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),),
        ),
        pressure_slacks=(
            hydro_gas.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A"),
        ),
        specified_boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("DEMAND-B", "B", -3.0, "boundary://demand/B"),
        ),
    )


def _state() -> hydro_gas.StationaryWeymouthUnknownState:
    return hydro_gas.StationaryWeymouthUnknownState(
        state_ref="state://gas/numerical-evaluation/template",
        unknown_node_pressures=(
            hydro_gas.GasNodePressure("B", 4_900_000.0, "template://pressure/B"),
        ),
        pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 3.0, "template://flow/P1"),),
        slack_external_flows=(
            hydro_gas.GasBoundaryMassFlow("SLACK-A", "A", 3.0, "template://slack/A"),
        ),
    )


def _scale() -> hydro_gas.StationaryWeymouthNumericalScale:
    return hydro_gas.StationaryWeymouthNumericalScale(
        pressure_squared_scale_pa2=25_000_000_000_000.0,
        mass_flow_scale_kg_s=10.0,
        mass_residual_scale_kg_s=10.0,
        pipe_residual_scale_pa2=1_000_000_000_000.0,
        source_ref="protocol://gas/numerical-evaluation/scales/synthetic-test-only",
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
            parameter_source_ref="reference://parameters/numerical-evaluation",
        ),
    )


def test_numerical_evaluation_matches_manual_adapter_chain() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    template = _state()
    scale = _scale()
    input_vector = hydro_gas.encode_stationary_weymouth_unknown_state(layout, template, scale)

    result = hydro_gas.evaluate_stationary_weymouth_numerical_vector(
        problem,
        layout,
        template,
        input_vector,
        scale,
        _parameters(),
        evaluation_ref="evaluation://gas/numerical/001",
    )
    manual_state = hydro_gas.decode_stationary_weymouth_numerical_vector(
        layout,
        template,
        input_vector,
        scale,
        state_ref="evaluation://gas/numerical/001#decoded-state",
    )
    manual_physical = hydro_gas.evaluate_stationary_weymouth_unknown_state(
        problem,
        layout,
        manual_state,
        _parameters(),
    )
    manual_residual = hydro_gas.encode_stationary_weymouth_residuals(
        layout,
        manual_physical.residuals,
        scale,
        source_ref="evaluation://gas/numerical/001#residual-vector",
    )

    assert result.input_vector == input_vector
    assert result.decoded_state == manual_state
    assert result.physical_evaluation == manual_physical
    assert result.residual_vector == manual_residual
    assert result.scale_source_ref == scale.source_ref
    assert not hasattr(result, "converged")


def test_numerical_evaluation_preserves_square_vector_dimensions() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    input_vector = hydro_gas.encode_stationary_weymouth_unknown_state(
        layout,
        _state(),
        _scale(),
    )

    result = hydro_gas.evaluate_stationary_weymouth_numerical_vector(
        problem,
        layout,
        _state(),
        input_vector,
        _scale(),
        _parameters(),
        evaluation_ref="evaluation://gas/numerical/dimensions",
    )

    assert len(result.input_vector.values) == layout.unknown_count
    assert len(result.residual_vector.values) == layout.equation_count
    assert layout.structurally_square is True


def test_numerical_evaluation_requires_provenance_and_valid_input_domain() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    valid_vector = hydro_gas.encode_stationary_weymouth_unknown_state(layout, _state(), _scale())

    with pytest.raises(ValueError, match="provenance"):
        hydro_gas.evaluate_stationary_weymouth_numerical_vector(
            problem,
            layout,
            _state(),
            valid_vector,
            _scale(),
            _parameters(),
            evaluation_ref="",
        )

    invalid_vector = hydro_gas.StationaryWeymouthNumericalVector(
        values=(-0.1, 0.3, 0.3),
        source_ref="vector://gas/numerical/negative-pressure",
    )
    with pytest.raises(ValueError, match="pression au carré.*négative"):
        hydro_gas.evaluate_stationary_weymouth_numerical_vector(
            problem,
            layout,
            _state(),
            invalid_vector,
            _scale(),
            _parameters(),
            evaluation_ref="evaluation://gas/numerical/rejected",
        )
