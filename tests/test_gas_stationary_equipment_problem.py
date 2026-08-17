from __future__ import annotations

import pytest

import hydro_gas
from hydro_gas.stationary_equipment_problem import (
    StationaryActiveCompressorProblem,
    StationaryCompressorSpeedControl,
    build_stationary_active_compressor_unknown_layout,
)
from hydro_gas.stationary_equipment_residual import StationaryCompressorMapBinding


def _map() -> hydro_gas.CompressorMap:
    return hydro_gas.CompressorMap(
        source_ref="vendor://compressor/C1/map",
        version="test-v1",
        speed_lines=(
            hydro_gas.CompressorSpeedLine(
                speed_rpm=10_000.0,
                points=(
                    hydro_gas.CompressorMapPoint(2.0, 1.20, 0.80),
                    hydro_gas.CompressorMapPoint(4.0, 1.30, 0.78),
                ),
            ),
        ),
    )


def _problem() -> StationaryActiveCompressorProblem:
    return StationaryActiveCompressorProblem(
        problem_ref="problem://gas/mixed/simple-v1",
        network=hydro_gas.SteadyGasNetwork(
            nodes=tuple(
                hydro_gas.SteadyGasNode(node_id, f"model://node/{node_id}")
                for node_id in ("A", "B", "C")
            ),
            pipes=(hydro_gas.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),),
        ),
        compressor_edges=(
            hydro_gas.SteadyGasCompressorEdge("C1", "B", "C", "model://compressor/C1"),
        ),
        pressure_slacks=(hydro_gas.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A"),),
        compressor_speed_controls=(
            StationaryCompressorSpeedControl("C1", 10_000.0, "control://compressor/C1/speed"),
        ),
        map_bindings=(
            StationaryCompressorMapBinding(
                compressor_id="C1",
                compressor_map=_map(),
                source_ref="binding://compressor/C1/map",
            ),
        ),
        specified_boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("DEMAND-C", "C", -3.0, "boundary://demand/C"),
        ),
    )


def test_mixed_problem_layout_is_square_with_all_active_compressor_equations() -> None:
    layout = build_stationary_active_compressor_unknown_layout(_problem())

    assert layout.connected_components == (("A", "B", "C"),)
    assert layout.fixed_pressure_node_ids == ("A",)
    assert layout.unknown_pressure_node_ids == ("B", "C")
    assert layout.pipe_flow_ids == ("P1",)
    assert layout.compressor_flow_ids == ("C1",)
    assert layout.slack_external_flow_node_ids == ("A",)
    assert layout.mass_equation_node_ids == ("A", "B", "C")
    assert layout.pipe_equation_ids == ("P1",)
    assert layout.compressor_equation_ids == ("C1",)
    assert layout.unknown_count == 5
    assert layout.equation_count == 5
    assert layout.structurally_square is True


def test_compressor_edge_connects_components_for_pressure_slack_validation() -> None:
    problem = _problem()
    invalid = StationaryActiveCompressorProblem(
        problem_ref=problem.problem_ref,
        network=problem.network,
        compressor_edges=problem.compressor_edges,
        pressure_slacks=(
            hydro_gas.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A"),
            hydro_gas.GasPressureSlack("C", 6_000_000.0, "boundary://pressure/C"),
        ),
        compressor_speed_controls=problem.compressor_speed_controls,
        map_bindings=problem.map_bindings,
        specified_boundary_flows=problem.specified_boundary_flows,
    )

    with pytest.raises(ValueError, match="exactement un slack"):
        build_stationary_active_compressor_unknown_layout(invalid)


def test_mixed_problem_requires_exact_speed_and_map_binding_coverage() -> None:
    problem = _problem()
    without_speed = StationaryActiveCompressorProblem(
        problem_ref=problem.problem_ref,
        network=problem.network,
        compressor_edges=problem.compressor_edges,
        pressure_slacks=problem.pressure_slacks,
        compressor_speed_controls=(),
        map_bindings=problem.map_bindings,
        specified_boundary_flows=problem.specified_boundary_flows,
    )
    with pytest.raises(ValueError, match="contrôles de vitesse doivent couvrir exactement"):
        build_stationary_active_compressor_unknown_layout(without_speed)

    without_binding = StationaryActiveCompressorProblem(
        problem_ref=problem.problem_ref,
        network=problem.network,
        compressor_edges=problem.compressor_edges,
        pressure_slacks=problem.pressure_slacks,
        compressor_speed_controls=problem.compressor_speed_controls,
        map_bindings=(),
        specified_boundary_flows=problem.specified_boundary_flows,
    )
    with pytest.raises(ValueError, match="bindings de cartes doivent couvrir exactement"):
        build_stationary_active_compressor_unknown_layout(without_binding)


def test_disconnected_mixed_components_each_require_one_pressure_slack() -> None:
    network = hydro_gas.SteadyGasNetwork(
        nodes=tuple(
            hydro_gas.SteadyGasNode(node_id, f"model://node/{node_id}")
            for node_id in ("A", "B", "C", "D")
        ),
        pipes=(
            hydro_gas.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),
            hydro_gas.SteadyGasPipe("P2", "C", "D", "model://pipe/P2"),
        ),
    )
    problem = StationaryActiveCompressorProblem(
        problem_ref="problem://gas/mixed/disconnected-v1",
        network=network,
        compressor_edges=(),
        pressure_slacks=(
            hydro_gas.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A"),
            hydro_gas.GasPressureSlack("C", 4_000_000.0, "boundary://pressure/C"),
        ),
        compressor_speed_controls=(),
        map_bindings=(),
    )

    layout = build_stationary_active_compressor_unknown_layout(problem)

    assert layout.connected_components == (("A", "B"), ("C", "D"))
    assert layout.unknown_count == 6
    assert layout.equation_count == 6
    assert layout.structurally_square is True
