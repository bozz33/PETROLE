from __future__ import annotations

import pytest

from hydro_gas.compressor_map import CompressorMap, CompressorMapPoint, CompressorSpeedLine
from hydro_gas.network_balance import (
    GasBoundaryMassFlow,
    GasPipeMassFlow,
    SteadyGasNetwork,
    SteadyGasNode,
    SteadyGasPipe,
)
from hydro_gas.stationary_equipment_balance import GasCompressorMassFlow, SteadyGasCompressorEdge
from hydro_gas.stationary_equipment_candidate import StationaryActiveCompressorUnknownState
from hydro_gas.stationary_equipment_numerical_evaluation import (
    evaluate_stationary_active_compressor_numerical_vector,
)
from hydro_gas.stationary_equipment_numerics import (
    StationaryActiveCompressorNumericalScale,
    StationaryActiveCompressorNumericalVector,
    decode_stationary_active_compressor_numerical_vector,
    encode_stationary_active_compressor_unknown_state,
)
from hydro_gas.stationary_equipment_problem import (
    StationaryActiveCompressorProblem,
    StationaryCompressorSpeedControl,
    build_stationary_active_compressor_unknown_layout,
)
from hydro_gas.stationary_equipment_residual import StationaryCompressorMapBinding
from hydro_gas.stationary_problem import GasPressureSlack
from hydro_gas.weymouth_network_residual import GasNodePressure
from hydro_gas.weymouth_si import WeymouthSiPipeParameters


def _problem() -> StationaryActiveCompressorProblem:
    compressor_map = CompressorMap(
        source_ref="supplier://synthetic-numerical-test",
        version="test-v1",
        speed_lines=(
            CompressorSpeedLine(
                speed_rpm=1000.0,
                points=(
                    CompressorMapPoint(1.0, 1.5, 0.8),
                    CompressorMapPoint(2.0, 1.5, 0.8),
                ),
            ),
        ),
    )
    return StationaryActiveCompressorProblem(
        problem_ref="problem://mixed/numerical-test",
        network=SteadyGasNetwork(
            nodes=tuple(
                SteadyGasNode(node_id, f"model://node/{node_id}")
                for node_id in ("A", "B", "C")
            ),
            pipes=(SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),),
        ),
        compressor_edges=(SteadyGasCompressorEdge("C1", "B", "C", "model://compressor/C1"),),
        pressure_slacks=(GasPressureSlack("A", 2_000_000.0, "boundary://pressure/A"),),
        compressor_speed_controls=(
            StationaryCompressorSpeedControl("C1", 1000.0, "control://speed/C1"),
        ),
        map_bindings=(
            StationaryCompressorMapBinding("C1", compressor_map, "binding://map/C1"),
        ),
        specified_boundary_flows=(
            GasBoundaryMassFlow("DEMAND-C", "C", -1.0, "boundary://demand/C"),
        ),
    )


def _state() -> StationaryActiveCompressorUnknownState:
    return StationaryActiveCompressorUnknownState(
        state_ref="state://mixed/numerical-test",
        unknown_node_pressures=(
            GasNodePressure("B", 2_000_000.0, "state://pressure/B"),
            GasNodePressure("C", 3_000_000.0, "state://pressure/C"),
        ),
        pipe_flows=(GasPipeMassFlow("P1", 1.0, "state://pipe/P1"),),
        compressor_flows=(GasCompressorMassFlow("C1", 1.0, "state://compressor/C1"),),
        slack_external_flows=(GasBoundaryMassFlow("SLACK-A", "A", 1.0, "state://slack/A"),),
    )


def _scale() -> StationaryActiveCompressorNumericalScale:
    return StationaryActiveCompressorNumericalScale(
        pressure_squared_scale_pa2=1_000_000_000_000.0,
        mass_flow_scale_kg_s=1.0,
        mass_residual_scale_kg_s=1.0,
        pipe_residual_scale_pa2=1_000_000_000_000.0,
        compressor_residual_scale_pa=1_000_000.0,
        source_ref="scale://synthetic/mixed-test",
    )


def _pipe_parameters() -> tuple[WeymouthSiPipeParameters, ...]:
    return (
        WeymouthSiPipeParameters(
            pipe_id="P1",
            length_m=1000.0,
            diameter_m=0.5,
            friction_factor=0.0,
            sound_speed_m_s=350.0,
            equation_ref="equation://weymouth/test",
            parameter_source_ref="parameters://pipe/P1/test",
        ),
    )


def test_mixed_numerical_round_trip_preserves_physical_values() -> None:
    problem = _problem()
    layout = build_stationary_active_compressor_unknown_layout(problem)
    state = _state()
    scale = _scale()

    vector = encode_stationary_active_compressor_unknown_state(layout, state, scale)
    assert vector.values == (4.0, 9.0, 1.0, 1.0, 1.0)

    decoded = decode_stationary_active_compressor_numerical_vector(
        layout,
        state,
        vector,
        scale,
        state_ref="state://mixed/decoded",
    )
    assert tuple(item.pressure_pa for item in decoded.unknown_node_pressures) == (
        2_000_000.0,
        3_000_000.0,
    )
    assert decoded.pipe_flows[0].mass_flow_kg_s == 1.0
    assert decoded.compressor_flows[0].mass_flow_kg_s == 1.0
    assert decoded.slack_external_flows[0].mass_flow_kg_s == 1.0


def test_mixed_numerical_evaluation_returns_square_zero_residual_vector() -> None:
    problem = _problem()
    layout = build_stationary_active_compressor_unknown_layout(problem)
    state = _state()
    scale = _scale()
    vector = encode_stationary_active_compressor_unknown_state(layout, state, scale)

    evaluation = evaluate_stationary_active_compressor_numerical_vector(
        problem,
        layout,
        state,
        vector,
        scale,
        _pipe_parameters(),
        evaluation_ref="evaluation://mixed/numerical-test",
    )

    assert len(evaluation.residual_vector.values) == layout.equation_count
    assert layout.equation_count == layout.unknown_count == 5
    assert evaluation.residual_vector.values == (0.0, 0.0, 0.0, 0.0, 0.0)


def test_mixed_decoder_refuses_nonpositive_active_compressor_flow_coordinate() -> None:
    problem = _problem()
    layout = build_stationary_active_compressor_unknown_layout(problem)
    vector = StationaryActiveCompressorNumericalVector(
        values=(4.0, 9.0, 1.0, 0.0, 1.0),
        source_ref="vector://mixed/invalid-compressor-flow",
    )

    with pytest.raises(ValueError, match=r"compresseur actif.*strictement positif"):
        decode_stationary_active_compressor_numerical_vector(
            layout,
            _state(),
            vector,
            _scale(),
            state_ref="state://mixed/invalid",
        )
