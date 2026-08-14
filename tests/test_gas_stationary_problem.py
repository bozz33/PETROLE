from __future__ import annotations

import pytest

from hydro_gas import network_balance, stationary_problem


def _connected_network() -> network_balance.SteadyGasNetwork:
    return network_balance.SteadyGasNetwork(
        nodes=(
            network_balance.SteadyGasNode("A", "model://node/A"),
            network_balance.SteadyGasNode("B", "model://node/B"),
            network_balance.SteadyGasNode("C", "model://node/C"),
        ),
        pipes=(
            network_balance.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),
            network_balance.SteadyGasPipe("P2", "B", "C", "model://pipe/P2"),
        ),
    )


def test_single_component_layout_keeps_all_mass_equations_and_is_square() -> None:
    problem = stationary_problem.StationaryWeymouthProblem(
        problem_ref="problem://gas/pressure-slack/simple-v1",
        network=_connected_network(),
        pressure_slacks=(
            stationary_problem.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A"),
        ),
        specified_boundary_flows=(
            network_balance.GasBoundaryMassFlow("DEMAND-C", "C", -4.0, "boundary://demand/C"),
        ),
    )

    layout = stationary_problem.build_stationary_weymouth_unknown_layout(problem)

    assert layout.connected_components == (("A", "B", "C"),)
    assert layout.fixed_pressure_node_ids == ("A",)
    assert layout.unknown_pressure_node_ids == ("B", "C")
    assert layout.pipe_flow_ids == ("P1", "P2")
    assert layout.slack_external_flow_node_ids == ("A",)
    assert layout.mass_equation_node_ids == ("A", "B", "C")
    assert layout.pipe_equation_ids == ("P1", "P2")
    assert layout.unknown_count == 5
    assert layout.equation_count == 5
    assert layout.structurally_square is True


def test_disconnected_network_requires_one_slack_per_component() -> None:
    network = network_balance.SteadyGasNetwork(
        nodes=(
            network_balance.SteadyGasNode("A", "model://node/A"),
            network_balance.SteadyGasNode("B", "model://node/B"),
            network_balance.SteadyGasNode("C", "model://node/C"),
            network_balance.SteadyGasNode("D", "model://node/D"),
        ),
        pipes=(
            network_balance.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),
            network_balance.SteadyGasPipe("P2", "C", "D", "model://pipe/P2"),
        ),
    )
    problem = stationary_problem.StationaryWeymouthProblem(
        problem_ref="problem://gas/disconnected/v1",
        network=network,
        pressure_slacks=(
            stationary_problem.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A"),
            stationary_problem.GasPressureSlack("C", 4_000_000.0, "boundary://pressure/C"),
        ),
    )

    layout = stationary_problem.build_stationary_weymouth_unknown_layout(problem)

    assert layout.connected_components == (("A", "B"), ("C", "D"))
    assert layout.fixed_pressure_node_ids == ("A", "C")
    assert layout.unknown_pressure_node_ids == ("B", "D")
    assert layout.slack_external_flow_node_ids == ("A", "C")
    assert layout.unknown_count == layout.equation_count == 6


def test_missing_or_multiple_component_slacks_are_rejected() -> None:
    network = _connected_network()
    missing = stationary_problem.StationaryWeymouthProblem(
        problem_ref="problem://gas/missing-slack",
        network=network,
        pressure_slacks=(),
    )
    with pytest.raises(ValueError, match="exactement une pression slack"):
        stationary_problem.build_stationary_weymouth_unknown_layout(missing)

    multiple = stationary_problem.StationaryWeymouthProblem(
        problem_ref="problem://gas/multiple-slacks",
        network=network,
        pressure_slacks=(
            stationary_problem.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A"),
            stationary_problem.GasPressureSlack("C", 4_900_000.0, "boundary://pressure/C"),
        ),
    )
    with pytest.raises(ValueError, match="exactement une pression slack"):
        stationary_problem.build_stationary_weymouth_unknown_layout(multiple)


def test_problem_rejects_duplicate_or_unknown_slack_nodes() -> None:
    network = _connected_network()
    slack = stationary_problem.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A")

    with pytest.raises(ValueError, match="qu'une seule pression slack"):
        stationary_problem.StationaryWeymouthProblem(
            problem_ref="problem://gas/duplicate-slack",
            network=network,
            pressure_slacks=(slack, slack),
        )

    with pytest.raises(ValueError, match="nœud absent"):
        stationary_problem.StationaryWeymouthProblem(
            problem_ref="problem://gas/unknown-slack",
            network=network,
            pressure_slacks=(
                stationary_problem.GasPressureSlack(
                    "UNKNOWN", 5_000_000.0, "boundary://pressure/UNKNOWN"
                ),
            ),
        )


def test_problem_rejects_duplicate_or_unknown_flow_boundaries() -> None:
    network = _connected_network()
    slack = stationary_problem.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A")
    boundary = network_balance.GasBoundaryMassFlow("D1", "C", -1.0, "boundary://demand/C")

    with pytest.raises(ValueError, match=r"frontières de débit.*uniques"):
        stationary_problem.StationaryWeymouthProblem(
            problem_ref="problem://gas/duplicate-boundary",
            network=network,
            pressure_slacks=(slack,),
            specified_boundary_flows=(boundary, boundary),
        )

    with pytest.raises(ValueError, match="nœud absent"):
        stationary_problem.StationaryWeymouthProblem(
            problem_ref="problem://gas/unknown-boundary-node",
            network=network,
            pressure_slacks=(slack,),
            specified_boundary_flows=(
                network_balance.GasBoundaryMassFlow(
                    "D2", "UNKNOWN", -1.0, "boundary://demand/UNKNOWN"
                ),
            ),
        )


def test_pressure_slack_requires_valid_pressure_and_provenance() -> None:
    with pytest.raises(ValueError, match="provenance"):
        stationary_problem.GasPressureSlack("A", 1.0, "")

    with pytest.raises(ValueError, match="pression slack"):
        stationary_problem.GasPressureSlack("A", -1.0, "boundary://pressure/A")
