from __future__ import annotations

import pytest

import hydro_gas


def _problem() -> hydro_gas.StationaryWeymouthProblem:
    return hydro_gas.StationaryWeymouthProblem(
        problem_ref="problem://gas/evaluation/simple-v1",
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


def _unknown_state() -> hydro_gas.StationaryWeymouthUnknownState:
    return hydro_gas.StationaryWeymouthUnknownState(
        state_ref="state://gas/evaluation/001",
        unknown_node_pressures=(hydro_gas.GasNodePressure("B", 4_900_000.0, "state://pressure/B"),),
        pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 3.0, "state://flow/P1"),),
        slack_external_flows=(
            hydro_gas.GasBoundaryMassFlow("SLACK-A", "A", 3.0, "state://slack/A"),
        ),
    )


def _parameters(pipe_id: str = "P1") -> hydro_gas.WeymouthSiPipeParameters:
    return hydro_gas.WeymouthSiPipeParameters(
        pipe_id=pipe_id,
        length_m=1_000.0,
        diameter_m=0.5,
        friction_factor=0.01,
        sound_speed_m_s=350.0,
        equation_ref="reference://weymouth/validated-formulation",
        parameter_source_ref="reference://parameters/evaluation-simple",
    )


def test_evaluation_uses_materialized_candidate_and_canonical_residual_path() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    state = _unknown_state()
    parameters = (_parameters(),)

    evaluation = hydro_gas.evaluate_stationary_weymouth_unknown_state(
        problem,
        layout,
        state,
        parameters,
    )
    direct_candidate = hydro_gas.materialize_stationary_weymouth_candidate(
        problem,
        layout,
        state,
    )
    direct_residuals = hydro_gas.assemble_weymouth_network_residuals(
        problem.network,
        direct_candidate,
        parameters,
    )

    assert evaluation.problem_ref == problem.problem_ref
    assert evaluation.state_ref == state.state_ref
    assert evaluation.candidate == direct_candidate
    assert evaluation.residuals == direct_residuals
    assert tuple(
        item.residual_kg_s for item in evaluation.residuals.mass_balance.node_balances
    ) == (0.0, 0.0)
    assert not hasattr(evaluation, "converged")


def test_evaluation_preserves_raw_residual_units_without_solver_status() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)

    evaluation = hydro_gas.evaluate_stationary_weymouth_unknown_state(
        problem,
        layout,
        _unknown_state(),
        (_parameters(),),
    )

    assert evaluation.residuals.mass_balance.node_balances[0].residual_kg_s == 0.0
    assert isinstance(evaluation.residuals.pipe_residuals[0].residual_pa2, float)
    assert not hasattr(evaluation.residuals, "passed")


def test_evaluation_fails_closed_on_stale_layout_or_parameter_coverage() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    stale_layout = hydro_gas.StationaryWeymouthUnknownLayout(
        connected_components=layout.connected_components,
        fixed_pressure_node_ids=layout.fixed_pressure_node_ids,
        unknown_pressure_node_ids=layout.unknown_pressure_node_ids,
        pipe_flow_ids=("OTHER",),
        slack_external_flow_node_ids=layout.slack_external_flow_node_ids,
        mass_equation_node_ids=layout.mass_equation_node_ids,
        pipe_equation_ids=layout.pipe_equation_ids,
    )

    with pytest.raises(ValueError, match="layout des inconnues"):
        hydro_gas.evaluate_stationary_weymouth_unknown_state(
            problem,
            stale_layout,
            _unknown_state(),
            (_parameters(),),
        )

    with pytest.raises(ValueError, match=r"paramètres Weymouth.*exactement"):
        hydro_gas.evaluate_stationary_weymouth_unknown_state(
            problem,
            layout,
            _unknown_state(),
            (_parameters("OTHER"),),
        )
