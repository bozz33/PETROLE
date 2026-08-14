from __future__ import annotations

from dataclasses import replace

import pytest

import hydro_gas


def _problem() -> hydro_gas.StationaryWeymouthProblem:
    network = hydro_gas.SteadyGasNetwork(
        nodes=(
            hydro_gas.SteadyGasNode("A", "model://node/A"),
            hydro_gas.SteadyGasNode("B", "model://node/B"),
            hydro_gas.SteadyGasNode("C", "model://node/C"),
        ),
        pipes=(
            hydro_gas.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),
            hydro_gas.SteadyGasPipe("P2", "B", "C", "model://pipe/P2"),
        ),
    )
    return hydro_gas.StationaryWeymouthProblem(
        problem_ref="problem://gas/materialization/simple-v1",
        network=network,
        pressure_slacks=(hydro_gas.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A"),),
        specified_boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("DEMAND-C", "C", -4.0, "boundary://demand/C"),
        ),
    )


def _state() -> hydro_gas.StationaryWeymouthUnknownState:
    return hydro_gas.StationaryWeymouthUnknownState(
        state_ref="state://gas/materialization/001",
        unknown_node_pressures=(
            hydro_gas.GasNodePressure("C", 4_800_000.0, "state://pressure/C"),
            hydro_gas.GasNodePressure("B", 4_900_000.0, "state://pressure/B"),
        ),
        pipe_flows=(
            hydro_gas.GasPipeMassFlow("P2", 4.0, "state://flow/P2"),
            hydro_gas.GasPipeMassFlow("P1", 4.0, "state://flow/P1"),
        ),
        slack_external_flows=(
            hydro_gas.GasBoundaryMassFlow("SLACK-A", "A", 4.0, "state://slack/A"),
        ),
    )


def test_materialization_restores_fixed_pressures_and_network_order() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)

    candidate = hydro_gas.materialize_stationary_weymouth_candidate(
        problem,
        layout,
        _state(),
    )

    assert candidate.candidate_ref == "state://gas/materialization/001"
    assert tuple(item.node_id for item in candidate.node_pressures) == ("A", "B", "C")
    assert tuple(item.pressure_pa for item in candidate.node_pressures) == (
        5_000_000.0,
        4_900_000.0,
        4_800_000.0,
    )
    assert candidate.node_pressures[0].source_ref == "boundary://pressure/A"
    assert tuple(item.pipe_id for item in candidate.pipe_flows) == ("P1", "P2")
    assert tuple(item.boundary_id for item in candidate.boundary_flows) == (
        "DEMAND-C",
        "SLACK-A",
    )


def test_materialized_candidate_closes_mass_balance_for_consistent_unknown_state() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    candidate = hydro_gas.materialize_stationary_weymouth_candidate(problem, layout, _state())

    balance = hydro_gas.assess_stationary_mass_balance(
        problem.network,
        candidate.pipe_flows,
        candidate.boundary_flows,
    )

    assert tuple(item.residual_kg_s for item in balance.node_balances) == (0.0, 0.0, 0.0)
    assert balance.global_residual_kg_s == 0.0


def test_materialization_rejects_stale_layout() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    stale_layout = replace(layout, pipe_flow_ids=("P2", "P1"))

    with pytest.raises(ValueError, match="layout des inconnues"):
        hydro_gas.materialize_stationary_weymouth_candidate(problem, stale_layout, _state())


def test_materialization_requires_exact_unknown_pressure_coverage() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    state = _state()
    incomplete = hydro_gas.StationaryWeymouthUnknownState(
        state_ref=state.state_ref,
        unknown_node_pressures=(state.unknown_node_pressures[0],),
        pipe_flows=state.pipe_flows,
        slack_external_flows=state.slack_external_flows,
    )

    with pytest.raises(ValueError, match=r"pressions inconnues.*exactement"):
        hydro_gas.materialize_stationary_weymouth_candidate(problem, layout, incomplete)


def test_materialization_requires_exact_pipe_flow_coverage() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    state = _state()
    incomplete = hydro_gas.StationaryWeymouthUnknownState(
        state_ref=state.state_ref,
        unknown_node_pressures=state.unknown_node_pressures,
        pipe_flows=(state.pipe_flows[0],),
        slack_external_flows=state.slack_external_flows,
    )

    with pytest.raises(ValueError, match=r"débits de conduite.*exactement"):
        hydro_gas.materialize_stationary_weymouth_candidate(problem, layout, incomplete)


def test_materialization_requires_exact_slack_flow_coverage() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    state = _state()
    incomplete = hydro_gas.StationaryWeymouthUnknownState(
        state_ref=state.state_ref,
        unknown_node_pressures=state.unknown_node_pressures,
        pipe_flows=state.pipe_flows,
        slack_external_flows=(),
    )

    with pytest.raises(ValueError, match=r"débits externes slack.*exactement"):
        hydro_gas.materialize_stationary_weymouth_candidate(problem, layout, incomplete)


def test_materialization_rejects_boundary_identifier_collision() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    state = _state()
    colliding = hydro_gas.StationaryWeymouthUnknownState(
        state_ref=state.state_ref,
        unknown_node_pressures=state.unknown_node_pressures,
        pipe_flows=state.pipe_flows,
        slack_external_flows=(
            hydro_gas.GasBoundaryMassFlow("DEMAND-C", "A", 4.0, "state://slack/A"),
        ),
    )

    with pytest.raises(ValueError, match="réutiliser un identifiant"):
        hydro_gas.materialize_stationary_weymouth_candidate(problem, layout, colliding)


def test_unknown_state_rejects_duplicate_identifiers_and_missing_provenance() -> None:
    pressure = hydro_gas.GasNodePressure("B", 4_900_000.0, "state://pressure/B")
    flow = hydro_gas.GasPipeMassFlow("P1", 4.0, "state://flow/P1")
    slack = hydro_gas.GasBoundaryMassFlow("SLACK-A", "A", 4.0, "state://slack/A")

    with pytest.raises(ValueError, match="provenance"):
        hydro_gas.StationaryWeymouthUnknownState(
            state_ref="",
            unknown_node_pressures=(pressure,),
            pipe_flows=(flow,),
            slack_external_flows=(slack,),
        )

    with pytest.raises(ValueError, match="pression inconnue"):
        hydro_gas.StationaryWeymouthUnknownState(
            state_ref="state://duplicate-pressure",
            unknown_node_pressures=(pressure, pressure),
            pipe_flows=(flow,),
            slack_external_flows=(slack,),
        )

    with pytest.raises(ValueError, match="débit inconnu"):
        hydro_gas.StationaryWeymouthUnknownState(
            state_ref="state://duplicate-flow",
            unknown_node_pressures=(pressure,),
            pipe_flows=(flow, flow),
            slack_external_flows=(slack,),
        )

    with pytest.raises(ValueError, match="débits externes slack.*uniques"):
        hydro_gas.StationaryWeymouthUnknownState(
            state_ref="state://duplicate-slack-boundary",
            unknown_node_pressures=(pressure,),
            pipe_flows=(flow,),
            slack_external_flows=(slack, slack),
        )
