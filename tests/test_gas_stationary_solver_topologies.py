from __future__ import annotations

import math

import pytest

import hydro_gas

_SCALE_POLICY_REF = "scale-policy://synthetic-test-only/topologies/v1"
_INITIAL_GUESS_POLICY_REF = "initial-guess://synthetic-test-only/topologies/v1"
_PROTOCOL_REF = "protocol://gas/solver-topologies/synthetic-test-only/v1"
_PROBLEM_FAMILY_REF = "problem-family://gas/weymouth/pressure-slack/v1"


def _scale() -> hydro_gas.StationaryWeymouthNumericalScale:
    return hydro_gas.StationaryWeymouthNumericalScale(
        pressure_squared_scale_pa2=25_000_000_000_000.0,
        mass_flow_scale_kg_s=10.0,
        mass_residual_scale_kg_s=10.0,
        pipe_residual_scale_pa2=1_000_000_000_000.0,
        source_ref="scale-artifact://synthetic-test-only/topologies/v1",
    )


def _context() -> hydro_gas.StationarySolverQualificationContext:
    return hydro_gas.StationarySolverQualificationContext(
        protocol_ref=_PROTOCOL_REF,
        problem_family_ref=_PROBLEM_FAMILY_REF,
        numerical_representation_ref=hydro_gas.WEYMOUTH_P2_NUMERICAL_REPRESENTATION_REF,
        solver_method_ref=hydro_gas.SCIPY_LEAST_SQUARES_TRF_METHOD_REF,
        scale_policy_ref=_SCALE_POLICY_REF,
        initial_guess_policy_ref=_INITIAL_GUESS_POLICY_REF,
    )


def _configuration() -> hydro_gas.ScipyLeastSquaresTrfConfiguration:
    return hydro_gas.ScipyLeastSquaresTrfConfiguration(
        configuration_ref="solver-config://synthetic-test-only/topologies/trf/v1",
        source_ref="source://synthetic-test-only/topologies/trf-config",
        solver_method_ref=hydro_gas.SCIPY_LEAST_SQUARES_TRF_METHOD_REF,
        numerical_representation_ref=hydro_gas.WEYMOUTH_P2_NUMERICAL_REPRESENTATION_REF,
        scale_policy_ref=_SCALE_POLICY_REF,
        initial_guess_policy_ref=_INITIAL_GUESS_POLICY_REF,
        ftol=1e-12,
        xtol=1e-12,
        gtol=1e-12,
        x_scale=1.0,
        diff_step=1e-6,
        max_nfev=200,
        jacobian_scheme="2-point",
        trust_region_solver="exact",
    )


def _criterion() -> hydro_gas.ApprovedStationaryConvergenceCriterion:
    context = _context()
    preregistered = hydro_gas.PreRegisteredStationaryConvergenceCriterion(
        criterion_id="criterion://gas/solver-topologies/synthetic-test-only/v1",
        criterion_version="1",
        protocol_ref=context.protocol_ref,
        problem_family_ref=context.problem_family_ref,
        numerical_representation_ref=context.numerical_representation_ref,
        solver_method_ref=context.solver_method_ref,
        scale_policy_ref=context.scale_policy_ref,
        initial_guess_policy_ref=context.initial_guess_policy_ref,
        source_ref="source://synthetic-test-only/topologies/convergence",
        registration_ref="registration://synthetic-test-only/topologies/pre-run",
        maximum_scaled_residual_inf_norm=1e-8,
        state=hydro_gas.StationarySolverPolicyState.APPROVED,
        approval_ref="approval://synthetic-test-only/topologies/numerics-review",
        maximum_mass_residual_kg_s=1e-7,
        maximum_pipe_residual_pa2=1_000.0,
    )
    return hydro_gas.materialize_approved_stationary_convergence_criterion(
        context=context,
        criterion=preregistered,
    )


def _parameter(pipe_id: str) -> hydro_gas.WeymouthSiPipeParameters:
    return hydro_gas.WeymouthSiPipeParameters(
        pipe_id=pipe_id,
        length_m=1_000.0,
        diameter_m=0.5,
        friction_factor=0.01,
        sound_speed_m_s=350.0,
        equation_ref="reference://weymouth/validated-formulation",
        parameter_source_ref=f"reference://parameters/topology/{pipe_id}",
    )


def _initial_state(
    layout: hydro_gas.StationaryWeymouthUnknownLayout,
    *,
    pressure_pa: float,
    pipe_flow_guesses: dict[str, float],
    slack_flow_guesses: dict[str, float],
) -> hydro_gas.StationaryWeymouthUnknownState:
    return hydro_gas.StationaryWeymouthUnknownState(
        state_ref="state://gas/topologies/initial/synthetic-test-only",
        unknown_node_pressures=tuple(
            hydro_gas.GasNodePressure(
                node_id,
                pressure_pa,
                f"initial://pressure/{node_id}",
            )
            for node_id in layout.unknown_pressure_node_ids
        ),
        pipe_flows=tuple(
            hydro_gas.GasPipeMassFlow(
                pipe_id,
                pipe_flow_guesses[pipe_id],
                f"initial://pipe-flow/{pipe_id}",
            )
            for pipe_id in layout.pipe_flow_ids
        ),
        slack_external_flows=tuple(
            hydro_gas.GasBoundaryMassFlow(
                f"SLACK-{node_id}",
                node_id,
                slack_flow_guesses[node_id],
                f"initial://slack-flow/{node_id}",
            )
            for node_id in layout.slack_external_flow_node_ids
        ),
    )


def _solve(
    problem: hydro_gas.StationaryWeymouthProblem,
    *,
    parameters: tuple[hydro_gas.WeymouthSiPipeParameters, ...],
    pressure_guess_pa: float,
    pipe_flow_guesses: dict[str, float],
    slack_flow_guesses: dict[str, float],
    solve_suffix: str,
) -> hydro_gas.StationaryWeymouthSolveResult:
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    scale = _scale()
    initial_state = _initial_state(
        layout,
        pressure_pa=pressure_guess_pa,
        pipe_flow_guesses=pipe_flow_guesses,
        slack_flow_guesses=slack_flow_guesses,
    )
    initial_vector = hydro_gas.encode_stationary_weymouth_unknown_state(
        layout,
        initial_state,
        scale,
    )
    return hydro_gas.solve_stationary_weymouth_least_squares_trf(
        problem,
        layout,
        initial_state,
        initial_vector,
        scale,
        parameters,
        context=_context(),
        convergence_criterion=_criterion(),
        configuration=_configuration(),
        solve_ref=f"solve://gas/topologies/{solve_suffix}/synthetic-test-only",
    )


def _pressure_by_node(result: hydro_gas.StationaryWeymouthSolveResult) -> dict[str, float]:
    return {
        item.node_id: item.pressure_pa
        for item in result.final_evaluation.physical_evaluation.candidate.node_pressures
    }


def _flow_by_pipe(result: hydro_gas.StationaryWeymouthSolveResult) -> dict[str, float]:
    return {
        item.pipe_id: item.mass_flow_kg_s
        for item in result.final_evaluation.decoded_state.pipe_flows
    }


def test_series_network_recovers_mass_flows_and_cumulative_pressure_drop() -> None:
    problem = hydro_gas.StationaryWeymouthProblem(
        problem_ref="problem://gas/topologies/series/v1",
        network=hydro_gas.SteadyGasNetwork(
            nodes=tuple(
                hydro_gas.SteadyGasNode(node_id, f"model://node/{node_id}")
                for node_id in ("A", "B", "C")
            ),
            pipes=(
                hydro_gas.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),
                hydro_gas.SteadyGasPipe("P2", "B", "C", "model://pipe/P2"),
            ),
        ),
        pressure_slacks=(
            hydro_gas.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A"),
        ),
        specified_boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("DEMAND-C", "C", -3.0, "boundary://demand/C"),
        ),
    )
    parameters = (_parameter("P1"), _parameter("P2"))

    result = _solve(
        problem,
        parameters=parameters,
        pressure_guess_pa=4_800_000.0,
        pipe_flow_guesses={"P1": 2.0, "P2": 2.0},
        slack_flow_guesses={"A": 2.0},
        solve_suffix="series",
    )

    coefficient = parameters[0].resistance_coefficient_pa2_per_kg_s2
    expected_b = math.sqrt(5_000_000.0**2 - coefficient * 3.0 * 3.0)
    expected_c = math.sqrt(expected_b**2 - coefficient * 3.0 * 3.0)
    flows = _flow_by_pipe(result)
    pressures = _pressure_by_node(result)

    assert result.status is hydro_gas.StationaryWeymouthSolverStatus.CONVERGED
    assert flows == pytest.approx({"P1": 3.0, "P2": 3.0}, abs=1e-7)
    assert pressures["B"] == pytest.approx(expected_b, rel=1e-10)
    assert pressures["C"] == pytest.approx(expected_c, rel=1e-10)


def test_branched_network_recovers_flow_split_and_branch_pressures() -> None:
    problem = hydro_gas.StationaryWeymouthProblem(
        problem_ref="problem://gas/topologies/branched/v1",
        network=hydro_gas.SteadyGasNetwork(
            nodes=tuple(
                hydro_gas.SteadyGasNode(node_id, f"model://node/{node_id}")
                for node_id in ("A", "B", "C", "D")
            ),
            pipes=(
                hydro_gas.SteadyGasPipe("P_AB", "A", "B", "model://pipe/P_AB"),
                hydro_gas.SteadyGasPipe("P_BC", "B", "C", "model://pipe/P_BC"),
                hydro_gas.SteadyGasPipe("P_BD", "B", "D", "model://pipe/P_BD"),
            ),
        ),
        pressure_slacks=(
            hydro_gas.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A"),
        ),
        specified_boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("DEMAND-C", "C", -2.0, "boundary://demand/C"),
            hydro_gas.GasBoundaryMassFlow("DEMAND-D", "D", -1.0, "boundary://demand/D"),
        ),
    )
    parameters = (_parameter("P_AB"), _parameter("P_BC"), _parameter("P_BD"))

    result = _solve(
        problem,
        parameters=parameters,
        pressure_guess_pa=4_800_000.0,
        pipe_flow_guesses={"P_AB": 2.0, "P_BC": 1.0, "P_BD": 1.0},
        slack_flow_guesses={"A": 2.0},
        solve_suffix="branched",
    )

    coefficient = parameters[0].resistance_coefficient_pa2_per_kg_s2
    expected_b = math.sqrt(5_000_000.0**2 - coefficient * 3.0 * 3.0)
    expected_c = math.sqrt(expected_b**2 - coefficient * 2.0 * 2.0)
    expected_d = math.sqrt(expected_b**2 - coefficient * 1.0 * 1.0)
    flows = _flow_by_pipe(result)
    pressures = _pressure_by_node(result)

    assert result.status is hydro_gas.StationaryWeymouthSolverStatus.CONVERGED
    assert flows == pytest.approx(
        {"P_AB": 3.0, "P_BC": 2.0, "P_BD": 1.0},
        abs=1e-7,
    )
    assert pressures["B"] == pytest.approx(expected_b, rel=1e-10)
    assert pressures["C"] == pytest.approx(expected_c, rel=1e-10)
    assert pressures["D"] == pytest.approx(expected_d, rel=1e-10)


def test_reverse_flow_is_solved_with_negative_signed_pipe_flow() -> None:
    problem = hydro_gas.StationaryWeymouthProblem(
        problem_ref="problem://gas/topologies/reverse/v1",
        network=hydro_gas.SteadyGasNetwork(
            nodes=(
                hydro_gas.SteadyGasNode("A", "model://node/A"),
                hydro_gas.SteadyGasNode("B", "model://node/B"),
            ),
            pipes=(hydro_gas.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),),
        ),
        pressure_slacks=(
            hydro_gas.GasPressureSlack("B", 5_000_000.0, "boundary://pressure/B"),
        ),
        specified_boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("DEMAND-A", "A", -3.0, "boundary://demand/A"),
        ),
    )
    parameters = (_parameter("P1"),)

    result = _solve(
        problem,
        parameters=parameters,
        pressure_guess_pa=4_800_000.0,
        pipe_flow_guesses={"P1": -2.0},
        slack_flow_guesses={"B": 2.0},
        solve_suffix="reverse",
    )

    coefficient = parameters[0].resistance_coefficient_pa2_per_kg_s2
    expected_a = math.sqrt(5_000_000.0**2 - coefficient * 3.0 * 3.0)
    flows = _flow_by_pipe(result)
    pressures = _pressure_by_node(result)

    assert result.status is hydro_gas.StationaryWeymouthSolverStatus.CONVERGED
    assert flows["P1"] == pytest.approx(-3.0, abs=1e-7)
    assert pressures["A"] == pytest.approx(expected_a, rel=1e-10)
    assert pressures["A"] < pressures["B"]


def test_internal_injection_and_downstream_withdrawal_are_balanced_together() -> None:
    problem = hydro_gas.StationaryWeymouthProblem(
        problem_ref="problem://gas/topologies/injection-withdrawal/v1",
        network=hydro_gas.SteadyGasNetwork(
            nodes=tuple(
                hydro_gas.SteadyGasNode(node_id, f"model://node/{node_id}")
                for node_id in ("A", "B", "C")
            ),
            pipes=(
                hydro_gas.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),
                hydro_gas.SteadyGasPipe("P2", "B", "C", "model://pipe/P2"),
            ),
        ),
        pressure_slacks=(
            hydro_gas.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A"),
        ),
        specified_boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("INJECTION-B", "B", 1.0, "boundary://injection/B"),
            hydro_gas.GasBoundaryMassFlow("DEMAND-C", "C", -4.0, "boundary://demand/C"),
        ),
    )
    parameters = (_parameter("P1"), _parameter("P2"))

    result = _solve(
        problem,
        parameters=parameters,
        pressure_guess_pa=4_800_000.0,
        pipe_flow_guesses={"P1": 2.0, "P2": 3.0},
        slack_flow_guesses={"A": 2.0},
        solve_suffix="injection-withdrawal",
    )

    coefficient = parameters[0].resistance_coefficient_pa2_per_kg_s2
    expected_b = math.sqrt(5_000_000.0**2 - coefficient * 3.0 * 3.0)
    expected_c = math.sqrt(expected_b**2 - coefficient * 4.0 * 4.0)
    flows = _flow_by_pipe(result)
    pressures = _pressure_by_node(result)

    assert result.status is hydro_gas.StationaryWeymouthSolverStatus.CONVERGED
    assert flows == pytest.approx({"P1": 3.0, "P2": 4.0}, abs=1e-7)
    assert pressures["B"] == pytest.approx(expected_b, rel=1e-10)
    assert pressures["C"] == pytest.approx(expected_c, rel=1e-10)
    assert result.final_evaluation.physical_evaluation.residuals.mass_balance.max_abs_node_residual_kg_s <= 1e-7
