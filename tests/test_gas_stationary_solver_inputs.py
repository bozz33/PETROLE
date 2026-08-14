from __future__ import annotations

import pytest

import hydro_gas

_SCALE_POLICY_REF = "scale-policy://synthetic-test-only/approved-inputs/v1"
_INITIAL_GUESS_POLICY_REF = "initial-guess://synthetic-test-only/approved-inputs/v1"
_PROTOCOL_REF = "protocol://gas/approved-inputs/synthetic-test-only/v1"
_PROBLEM_FAMILY_REF = "problem-family://gas/weymouth/pressure-slack/v1"


def _problem() -> hydro_gas.StationaryWeymouthProblem:
    return hydro_gas.StationaryWeymouthProblem(
        problem_ref="problem://gas/approved-inputs/simple/v1",
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
        configuration_ref="solver-config://synthetic-test-only/approved-inputs/trf/v1",
        source_ref="source://synthetic-test-only/approved-inputs/trf-config",
        solver_method_ref=hydro_gas.SCIPY_LEAST_SQUARES_TRF_METHOD_REF,
        numerical_representation_ref=hydro_gas.WEYMOUTH_P2_NUMERICAL_REPRESENTATION_REF,
        scale_policy_ref=_SCALE_POLICY_REF,
        initial_guess_policy_ref=_INITIAL_GUESS_POLICY_REF,
        ftol=1e-12,
        xtol=1e-12,
        gtol=1e-12,
        x_scale=1.0,
        diff_step=1e-6,
        max_nfev=100,
        jacobian_scheme="2-point",
        trust_region_solver="exact",
    )


def _criterion() -> hydro_gas.ApprovedStationaryConvergenceCriterion:
    context = _context()
    criterion = hydro_gas.PreRegisteredStationaryConvergenceCriterion(
        criterion_id="criterion://gas/approved-inputs/synthetic-test-only/v1",
        criterion_version="1",
        protocol_ref=context.protocol_ref,
        problem_family_ref=context.problem_family_ref,
        numerical_representation_ref=context.numerical_representation_ref,
        solver_method_ref=context.solver_method_ref,
        scale_policy_ref=context.scale_policy_ref,
        initial_guess_policy_ref=context.initial_guess_policy_ref,
        source_ref="source://synthetic-test-only/approved-inputs/convergence",
        registration_ref="registration://synthetic-test-only/approved-inputs/pre-run",
        maximum_scaled_residual_inf_norm=1e-8,
        state=hydro_gas.StationarySolverPolicyState.APPROVED,
        approval_ref="approval://synthetic-test-only/approved-inputs/convergence",
        maximum_mass_residual_kg_s=1e-7,
        maximum_pipe_residual_pa2=1_000.0,
    )
    return hydro_gas.materialize_approved_stationary_convergence_criterion(
        context=context,
        criterion=criterion,
    )


def _scale_artifact(
    *,
    state: hydro_gas.StationarySolverPolicyState = hydro_gas.StationarySolverPolicyState.APPROVED,
    approval_ref: str | None = "approval://synthetic-test-only/scale",
    policy_ref: str = _SCALE_POLICY_REF,
) -> hydro_gas.PreRegisteredStationaryWeymouthScaleArtifact:
    return hydro_gas.PreRegisteredStationaryWeymouthScaleArtifact(
        artifact_ref="scale-artifact://synthetic-test-only/approved-inputs/v1",
        policy_ref=policy_ref,
        policy_version="1",
        source_ref="source://synthetic-test-only/approved-inputs/scales",
        registration_ref="registration://synthetic-test-only/approved-inputs/scales/pre-run",
        pressure_squared_scale_pa2=25_000_000_000_000.0,
        mass_flow_scale_kg_s=10.0,
        mass_residual_scale_kg_s=10.0,
        pipe_residual_scale_pa2=1_000_000_000_000.0,
        state=state,
        approval_ref=approval_ref,
    )


def _unknown_state() -> hydro_gas.StationaryWeymouthUnknownState:
    return hydro_gas.StationaryWeymouthUnknownState(
        state_ref="state://gas/approved-inputs/initial/synthetic-test-only",
        unknown_node_pressures=(
            hydro_gas.GasNodePressure("B", 4_800_000.0, "initial://pressure/B"),
        ),
        pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 2.0, "initial://pipe-flow/P1"),),
        slack_external_flows=(
            hydro_gas.GasBoundaryMassFlow("SLACK-A", "A", 2.0, "initial://slack-flow/A"),
        ),
    )


def _initial_guess_artifact(
    problem: hydro_gas.StationaryWeymouthProblem,
    layout: hydro_gas.StationaryWeymouthUnknownLayout,
    *,
    state: hydro_gas.StationarySolverPolicyState = hydro_gas.StationarySolverPolicyState.APPROVED,
    approval_ref: str | None = "approval://synthetic-test-only/initial-guess",
    policy_ref: str = _INITIAL_GUESS_POLICY_REF,
    layout_sha256: str | None = None,
) -> hydro_gas.PreRegisteredStationaryWeymouthInitialGuessArtifact:
    return hydro_gas.PreRegisteredStationaryWeymouthInitialGuessArtifact(
        artifact_ref="initial-guess-artifact://synthetic-test-only/approved-inputs/v1",
        policy_ref=policy_ref,
        policy_version="1",
        problem_ref=problem.problem_ref,
        layout_sha256=layout_sha256 or hydro_gas.stationary_weymouth_layout_sha256(layout),
        source_ref="source://synthetic-test-only/approved-inputs/initial-guess",
        registration_ref="registration://synthetic-test-only/approved-inputs/initial-guess/pre-run",
        unknown_state=_unknown_state(),
        state=state,
        approval_ref=approval_ref,
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
            parameter_source_ref="reference://parameters/approved-inputs",
        ),
    )


def test_layout_fingerprint_is_deterministic_and_order_sensitive() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)

    first = hydro_gas.stationary_weymouth_layout_sha256(layout)
    second = hydro_gas.stationary_weymouth_layout_sha256(layout)
    altered = hydro_gas.StationaryWeymouthUnknownLayout(
        connected_components=layout.connected_components,
        fixed_pressure_node_ids=layout.fixed_pressure_node_ids,
        unknown_pressure_node_ids=layout.unknown_pressure_node_ids,
        pipe_flow_ids=layout.pipe_flow_ids,
        slack_external_flow_node_ids=layout.slack_external_flow_node_ids,
        mass_equation_node_ids=tuple(reversed(layout.mass_equation_node_ids)),
        pipe_equation_ids=layout.pipe_equation_ids,
    )

    assert first == second
    assert first.startswith("sha256:")
    assert first != hydro_gas.stationary_weymouth_layout_sha256(altered)


def test_draft_scale_and_initial_guess_artifacts_are_refused() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    draft_scale = _scale_artifact(
        state=hydro_gas.StationarySolverPolicyState.DRAFT,
        approval_ref=None,
    )
    draft_initial = _initial_guess_artifact(
        problem,
        layout,
        state=hydro_gas.StationarySolverPolicyState.DRAFT,
        approval_ref=None,
    )

    with pytest.raises(PermissionError, match=r"échelle.*APPROVED"):
        hydro_gas.materialize_approved_stationary_weymouth_scale(draft_scale)
    with pytest.raises(PermissionError, match=r"initialisation.*APPROVED"):
        hydro_gas.materialize_approved_stationary_weymouth_initial_guess(
            problem=problem,
            layout=layout,
            artifact=draft_initial,
        )


def test_initial_guess_artifact_is_bound_to_exact_layout() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    wrong_hash = "sha256:" + "0" * 64
    artifact = _initial_guess_artifact(problem, layout, layout_sha256=wrong_hash)

    with pytest.raises(ValueError, match="autre layout"):
        hydro_gas.materialize_approved_stationary_weymouth_initial_guess(
            problem=problem,
            layout=layout,
            artifact=artifact,
        )


def test_approved_scale_preserves_exact_explicit_values() -> None:
    approved = hydro_gas.materialize_approved_stationary_weymouth_scale(_scale_artifact())
    scale = approved.to_numerical_scale()

    assert approved.policy_ref == _SCALE_POLICY_REF
    assert scale.pressure_squared_scale_pa2 == 25_000_000_000_000.0
    assert scale.mass_flow_scale_kg_s == 10.0
    assert scale.mass_residual_scale_kg_s == 10.0
    assert scale.pipe_residual_scale_pa2 == 1_000_000_000_000.0
    assert scale.source_ref.endswith("#approved-scale")


def test_governed_solver_records_approved_scale_and_initial_guess_proofs() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    approved_scale = hydro_gas.materialize_approved_stationary_weymouth_scale(_scale_artifact())
    approved_initial = hydro_gas.materialize_approved_stationary_weymouth_initial_guess(
        problem=problem,
        layout=layout,
        artifact=_initial_guess_artifact(problem, layout),
    )

    result = hydro_gas.solve_stationary_weymouth_with_approved_inputs(
        problem,
        layout,
        _parameters(),
        context=_context(),
        convergence_criterion=_criterion(),
        configuration=_configuration(),
        scale_artifact=approved_scale,
        initial_guess_artifact=approved_initial,
        solve_ref="solve://gas/approved-inputs/synthetic-test-only/001",
    )

    assert result.solve.status is hydro_gas.StationaryWeymouthSolverStatus.CONVERGED
    assert result.scale_artifact_ref == approved_scale.artifact_ref
    assert result.scale_policy_ref == _SCALE_POLICY_REF
    assert result.scale_approval_ref == "approval://synthetic-test-only/scale"
    assert result.initial_guess_artifact_ref == approved_initial.artifact_ref
    assert result.initial_guess_policy_ref == _INITIAL_GUESS_POLICY_REF
    assert result.initial_guess_approval_ref == "approval://synthetic-test-only/initial-guess"


def test_governed_solver_rejects_policy_mismatch_even_for_approved_artifact() -> None:
    problem = _problem()
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    approved_scale = hydro_gas.materialize_approved_stationary_weymouth_scale(
        _scale_artifact(policy_ref="scale-policy://other/v1")
    )
    approved_initial = hydro_gas.materialize_approved_stationary_weymouth_initial_guess(
        problem=problem,
        layout=layout,
        artifact=_initial_guess_artifact(problem, layout),
    )

    with pytest.raises(ValueError, match="artefact d'échelle"):
        hydro_gas.solve_stationary_weymouth_with_approved_inputs(
            problem,
            layout,
            _parameters(),
            context=_context(),
            convergence_criterion=_criterion(),
            configuration=_configuration(),
            scale_artifact=approved_scale,
            initial_guess_artifact=approved_initial,
            solve_ref="solve://gas/approved-inputs/rejected-policy",
        )
