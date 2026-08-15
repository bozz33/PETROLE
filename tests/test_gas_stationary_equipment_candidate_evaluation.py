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
from hydro_gas.stationary_equipment_candidate import (
    StationaryActiveCompressorUnknownState,
    materialize_stationary_active_compressor_candidate,
)
from hydro_gas.stationary_equipment_evaluation import (
    evaluate_stationary_active_compressor_unknown_state,
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


def _compressor_map() -> CompressorMap:
    return CompressorMap(
        source_ref="supplier://synthetic-test-map",
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


def _problem() -> StationaryActiveCompressorProblem:
    network = SteadyGasNetwork(
        nodes=tuple(
            SteadyGasNode(node_id, f"model://node/{node_id}") for node_id in ("A", "B", "C")
        ),
        pipes=(SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),),
    )
    return StationaryActiveCompressorProblem(
        problem_ref="problem://mixed/test",
        network=network,
        compressor_edges=(SteadyGasCompressorEdge("C1", "B", "C", "model://compressor/C1"),),
        pressure_slacks=(GasPressureSlack("A", 2_000_000.0, "boundary://pressure/A"),),
        compressor_speed_controls=(
            StationaryCompressorSpeedControl("C1", 1000.0, "control://speed/C1"),
        ),
        map_bindings=(
            StationaryCompressorMapBinding(
                compressor_id="C1",
                compressor_map=_compressor_map(),
                source_ref="binding://map/C1",
            ),
        ),
        specified_boundary_flows=(
            GasBoundaryMassFlow("DEMAND-C", "C", -1.0, "boundary://demand/C"),
        ),
    )


def _unknown_state(*, compressor_flow_kg_s: float = 1.0) -> StationaryActiveCompressorUnknownState:
    return StationaryActiveCompressorUnknownState(
        state_ref="state://mixed/test",
        unknown_node_pressures=(
            GasNodePressure("B", 2_000_000.0, "state://pressure/B"),
            GasNodePressure("C", 3_000_000.0, "state://pressure/C"),
        ),
        pipe_flows=(GasPipeMassFlow("P1", 1.0, "state://pipe/P1"),),
        compressor_flows=(
            GasCompressorMassFlow("C1", compressor_flow_kg_s, "state://compressor/C1"),
        ),
        slack_external_flows=(GasBoundaryMassFlow("SLACK-A", "A", 1.0, "state://slack/A"),),
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


def test_materializer_combines_fixed_speed_with_unknown_compressor_flow() -> None:
    problem = _problem()
    layout = build_stationary_active_compressor_unknown_layout(problem)

    candidate = materialize_stationary_active_compressor_candidate(
        problem,
        layout,
        _unknown_state(),
    )

    assert tuple(item.node_id for item in candidate.node_pressures) == ("A", "B", "C")
    assert tuple(item.pressure_pa for item in candidate.node_pressures) == (
        2_000_000.0,
        2_000_000.0,
        3_000_000.0,
    )
    assert candidate.compressor_inputs[0].compressor_id == "C1"
    assert candidate.compressor_inputs[0].mass_flow_kg_s == 1.0
    assert candidate.compressor_inputs[0].speed_rpm == 1000.0
    assert tuple(item.boundary_id for item in candidate.boundary_flows) == (
        "DEMAND-C",
        "SLACK-A",
    )


def test_materializer_rejects_missing_compressor_unknown() -> None:
    problem = _problem()
    layout = build_stationary_active_compressor_unknown_layout(problem)
    state = _unknown_state()
    incomplete = StationaryActiveCompressorUnknownState(
        state_ref=state.state_ref,
        unknown_node_pressures=state.unknown_node_pressures,
        pipe_flows=state.pipe_flows,
        compressor_flows=(),
        slack_external_flows=state.slack_external_flows,
    )

    with pytest.raises(ValueError, match=r"débits compresseurs.*exactement"):
        materialize_stationary_active_compressor_candidate(problem, layout, incomplete)


def test_mixed_evaluation_keeps_all_three_physical_residual_families() -> None:
    problem = _problem()
    layout = build_stationary_active_compressor_unknown_layout(problem)

    evaluation = evaluate_stationary_active_compressor_unknown_state(
        problem,
        layout,
        _unknown_state(),
        _pipe_parameters(),
        evaluation_ref="evaluation://mixed/test",
    )

    mass_balance = evaluation.equipment_residuals.mass_balance
    assert tuple(item.residual_kg_s for item in mass_balance.node_balances) == (
        0.0,
        0.0,
        0.0,
    )
    assert mass_balance.global_residual_kg_s == 0.0
    assert evaluation.pipe_residuals[0].residual_pa2 == 0.0
    compressor = evaluation.equipment_residuals.compressor_constraints[0]
    assert compressor.expected_outlet_pressure_pa == 3_000_000.0
    assert compressor.pressure_ratio_residual_pa == 0.0


def test_mixed_evaluation_refuses_compressor_map_extrapolation() -> None:
    problem = _problem()
    layout = build_stationary_active_compressor_unknown_layout(problem)

    with pytest.raises(ValueError, match="hors du domaine"):
        evaluate_stationary_active_compressor_unknown_state(
            problem,
            layout,
            _unknown_state(compressor_flow_kg_s=3.0),
            _pipe_parameters(),
            evaluation_ref="evaluation://mixed/out-of-map",
        )
