from __future__ import annotations

import math

import pytest

import hydro_gas


_SCALE_POLICY_REF = "scale-policy://synthetic-test-only/weymouth/v1"
_INITIAL_GUESS_POLICY_REF = "initial-guess://synthetic-test-only/weymouth/v1"
_PROTOCOL_REF = "protocol://gas/solver/synthetic-test-only/v1"
_PROBLEM_FAMILY_REF = "problem-family://gas/weymouth/pressure-slack/v1"


def _problem(*, slack_pressure_pa: float = 5_000_000.0, demand_kg_s: float = 3.0) -> hydro_gas.StationaryWeymouthProblem:
    return hydro_gas.StationaryWeymouthProblem(
        problem_ref="problem://gas/solver/simple-v1",
        network=hydro_gas.SteadyGasNetwork(
            nodes=(
                hydro_gas.SteadyGasNode("A", "model://node/A"),
                hydro_gas.SteadyGasNode("B", "model://node/B"),
            ),
            pipes=(hydro_gas.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),),
        ),
        pressure_slacks=(
            hydro_gas.GasPressureSlack("A", slack_pressure_pa, "boundary://pressure/A"),
        ),
        specified_boundary_flows=(
            hydro_gas.GasBoundaryMassFlow(
                "DEMAND-B",
                "B",
                -demand_kg_s,
                "boundary://demand/B",
            ),
        ),
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
            parameter_source_ref="reference://parameters/solver-test",
        ),
    )


def _scale() -> hydro_gas.StationaryWeymouthNumericalScale:
    return hydro_gas.StationaryWeymouthNumericalScale(
        pressure_squared_scale_pa2=25_000_000_000_000.0,
        mass_flow_scale_kg_s=10.0,
        mass_residual_scale_kg_s=10.0,
        pipe_residual_scale_pa2=1_000_000_000_000.0,
        source_ref="scale-artifact://synthetic-test-only/weymouth/v1",
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


def _configuration(
    *,
    scale_policy_ref: str = _SCALE_POLICY_REF,
    max_nfev: int = 100,
) -> hydro_gas.ScipyLeastSquaresTrfConfiguration:
    return hydro_gas.ScipyLeastSquaresTrfConfiguration(
        configuration_ref="solver-config://synthetic-test-only/trf/v1",
        source_ref="source://synthetic-test-only/scipy-trf-config",
        solver_method_ref=hydro_gas.SCIPY_LEAST_SQUARES_TRF_METHOD_REF,
        numerical_representation_ref=hydro_gas.WEYMOUTH_P2_NUMERICAL_REPRESENTATION_REF,
        scale_policy_ref=scale_policy_ref,
        initial_guess_policy_ref=_INITIAL_GUESS_POLICY_REF,
        ftol=1e-12,
        xtol=1e-12,
        gtol=1e-12,
        x_scale=1.0,
        diff_step=1e-6,
        max_nfev=max_nfev,
        jacobian_scheme="2-point",
        trust_region_solver="exact",
    )


def _approved_criterion(
    *,
    scaled_limit: float = 1e-8,
    mass_limit: float | None = 1e-7,
    pipe_limit: float | None = 1_000.0,
) -> hydro_gas.ApprovedStationaryConvergenceCriterion:
    context = _context()
    preregistered = hydro_gas.PreRegisteredStationaryConvergenceCriterion(
        criterion_id="criterion://gas/solver/synthetic-test-only/v1",
        criterion_version="1",
        protocol_ref=context.protocol_ref,
        problem_family_ref=context.problem_family_ref,
        numerical_representation_ref=context.numerical_representation_ref,
        solver_method_ref=context.solver_method_ref,
        scale_policy_ref=context.scale_policy_ref,
        initial_guess_policy_ref=context.initial_guess_policy_ref,
        source_ref="source://synthetic-test-only/convergence",
        registration_ref="registration://synthetic-test-only/pre-run",
        maximum_scaled_residual_inf_norm=scaled_limit,
        state=hydro_gas.StationarySolverPolicyState.APPROVED,
        approval_ref="approval://synthetic-test-only/numerics-review",
        maximum_mass_residual_kg_s=mass_limit,
        maximum_pipe_residual_pa2=pipe_limit,
    )
    return hydro_gas.materialize_approved_stationary_convergence_criterion(
        context=context,
        criterion=preregistered,
    )


def _initial_state(
    *,
    pressure_pa: float = 4_800_000.0,
    pipe_flow_kg_s: float = 2.0,
    slack_flow_kg_s: float = 2.0,
) -> hydro_gas.StationaryWeymouthUnknownState:
    return hydro_gas.StationaryWeymouthUnknownState(
        state_ref="state://gas/solver/initial/synthetic-test-only",
        unknown_node_pressures=(
            hydro_gas.GasNodePressure("B", pressure_pa, "initial://pressure/B"),
        ),
        pipe_flows=(
            hydro_gas.GasPipeMassFlow("P1", pipe_flow_kg_s, "initial://pipe-flow/P1"),
        ),
        slack_external_flows=(
            hydro_gas.GasBoundaryMassFlow(
                "SLACK-A",
                "A",
                slack_flow_kg_s,
                "initial://slack-flow/A",
            ),
        ),
    )


def _solve(
    problem: hydro_gas.StationaryWeymouthProblem,
    *,
    criterion: hydro_gas.ApprovedStationaryConvergenceCriterion | None = None,
    configuration: hydro_gas.ScipyLeastSquaresTrfConfiguration | None = None,
    initial_state: hydro_gas.StationaryWeymouthUnknownState | None = None,
) -> hydro_gas.StationaryWeymouthSolveResult:
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    scale = _scale()
    state = initial_state or _initial_state()
    initial_vector = hydro_gas.encode_stationary_weymouth_unknown_state(layout, state, scale)
    return hydro_gas.solve_stationary_weymouth_least_squares_trf(
        problem,
        layout,
        state,
        initial_vector,
        scale,
        _parameters(),
        context=_context(),
        convergence_criterion=criterion or _approved_criterion(),
        configuration=configuration or _configuration(),
        solve_ref="solve://gas/weymouth/synthetic-test-only/001",
    )


def test_bounded_solver_converges_only_after_approved_residual_gate() -> None:
    problem = _problem()

    result = _solve(problem)

    parameters = _parameters()[0]
    expected_flow = 3.0
    expected_pressure = math.sqrt(
        5_000_000.0**2
        - parameters.resistance_coefficient_pa2_per_kg_s2 * expected_flow * abs(expected_flow)
    )
    final_state = result.final_evaluation.decoded_state

    assert result.status is hydro_gas.StationaryWeymouthSolverStatus.CONVERGED
    assert result.convergence.all_approved_criteria_passed is True
    assert final_state.pipe_flows[0].mass_flow_kg_s == pytest.approx(expected_flow, abs=1e-7)
    assert final_state.slack_external_flows[0].mass_flow_kg_s == pytest.approx(
        expected_flow,
        abs=1e-7,
    )
    assert final_state.unknown_node_pressures[0].pressure_pa == pytest.approx(
        expected_pressure,
        rel=1e-10,
    )
    assert result.final_vector.values[0] >= 0.0
    assert result.scipy_version
    assert result.nfev > 0


def test_scipy_success_does_not_override_stricter_petrole_residual_gate() -> None:
    strict_criterion = _approved_criterion(
        scaled_limit=1e-16,
        mass_limit=0.0,
        pipe_limit=1e-4,
    )

    result = _solve(_problem(), criterion=strict_criterion)

    assert result.scipy_success is True
    assert result.convergence.all_approved_criteria_passed is False
    assert result.status is hydro_gas.StationaryWeymouthSolverStatus.NON_CONVERGED


def test_solver_rejects_configuration_not_bound_to_approved_context() -> None:
    incompatible = _configuration(scale_policy_ref="scale-policy://other/v1")

    with pytest.raises(ValueError, match="politique d'échelle"):
        _solve(_problem(), configuration=incompatible)


def test_solver_rejects_negative_initial_pressure_squared_coordinate() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    scale = _scale()
    state = _initial_state()
    invalid_vector = hydro_gas.StationaryWeymouthNumericalVector(
        values=(-0.1, 0.2, 0.2),
        source_ref="vector://gas/solver/negative-p2/synthetic-test-only",
    )

    with pytest.raises(ValueError, match=r"coordonnées initiales p²"):
        hydro_gas.solve_stationary_weymouth_least_squares_trf(
            problem,
            layout,
            state,
            invalid_vector,
            scale,
            _parameters(),
            context=_context(),
            convergence_criterion=_approved_criterion(),
            configuration=_configuration(),
            solve_ref="solve://gas/weymouth/rejected-negative-p2",
        )


def test_bound_prevents_negative_p2_when_requested_flow_has_no_physical_pressure_solution() -> None:
    problem = _problem(slack_pressure_pa=1_000_000.0, demand_kg_s=200.0)
    initial_state = _initial_state(
        pressure_pa=100_000.0,
        pipe_flow_kg_s=200.0,
        slack_flow_kg_s=200.0,
    )

    result = _solve(problem, initial_state=initial_state)

    assert result.final_vector.values[0] >= 0.0
    assert result.status is hydro_gas.StationaryWeymouthSolverStatus.NON_CONVERGED
    assert result.convergence.all_approved_criteria_passed is False


def test_solver_configuration_has_no_hidden_tolerance_or_evaluation_budget() -> None:
    epsilon = float(__import__("numpy").finfo(float).eps)

    with pytest.raises(ValueError, match="epsilon machine"):
        hydro_gas.ScipyLeastSquaresTrfConfiguration(
            configuration_ref="config://invalid/tolerance",
            source_ref="source://invalid/tolerance",
            solver_method_ref=hydro_gas.SCIPY_LEAST_SQUARES_TRF_METHOD_REF,
            numerical_representation_ref=hydro_gas.WEYMOUTH_P2_NUMERICAL_REPRESENTATION_REF,
            scale_policy_ref=_SCALE_POLICY_REF,
            initial_guess_policy_ref=_INITIAL_GUESS_POLICY_REF,
            ftol=epsilon,
            xtol=1e-12,
            gtol=1e-12,
            x_scale=1.0,
            diff_step=1e-6,
            max_nfev=100,
            jacobian_scheme="2-point",
            trust_region_solver="exact",
        )

    with pytest.raises(ValueError, match="max_nfev"):
        _configuration(max_nfev=0)
