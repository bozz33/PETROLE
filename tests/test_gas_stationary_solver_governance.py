from __future__ import annotations

import math

import pytest

import hydro_gas

_CONTEXT = hydro_gas.StationarySolverQualificationContext(
    protocol_ref="protocol://gas/solver/qualification/v1",
    problem_family_ref="problem-family://gas/weymouth/pressure-slack/v1",
    numerical_representation_ref="numerics://gas/weymouth/psqr-scaled/v1",
    solver_method_ref="solver-method://synthetic-test-only/v1",
    scale_policy_ref="scale-policy://synthetic-test-only/v1",
    initial_guess_policy_ref="initial-guess://synthetic-test-only/v1",
)


def _criterion(
    *,
    state: hydro_gas.StationarySolverPolicyState = hydro_gas.StationarySolverPolicyState.APPROVED,
    approval_ref: str | None = "approval://numerics/review-001",
    solver_method_ref: str = _CONTEXT.solver_method_ref,
    maximum_scaled_residual_inf_norm: float = 1e-6,
    maximum_mass_residual_kg_s: float | None = 1e-5,
    maximum_pipe_residual_pa2: float | None = 1.0,
) -> hydro_gas.PreRegisteredStationaryConvergenceCriterion:
    return hydro_gas.PreRegisteredStationaryConvergenceCriterion(
        criterion_id="criterion://gas/solver/convergence/synthetic-v1",
        criterion_version="1",
        protocol_ref=_CONTEXT.protocol_ref,
        problem_family_ref=_CONTEXT.problem_family_ref,
        numerical_representation_ref=_CONTEXT.numerical_representation_ref,
        solver_method_ref=solver_method_ref,
        scale_policy_ref=_CONTEXT.scale_policy_ref,
        initial_guess_policy_ref=_CONTEXT.initial_guess_policy_ref,
        source_ref="source://synthetic-test-only/convergence",
        registration_ref="registration://synthetic-test-only/pre-run",
        maximum_scaled_residual_inf_norm=maximum_scaled_residual_inf_norm,
        state=state,
        approval_ref=approval_ref,
        maximum_mass_residual_kg_s=maximum_mass_residual_kg_s,
        maximum_pipe_residual_pa2=maximum_pipe_residual_pa2,
    )


def test_approved_convergence_criterion_materializes_for_exact_context() -> None:
    criterion = _criterion()

    approved = hydro_gas.materialize_approved_stationary_convergence_criterion(
        context=_CONTEXT,
        criterion=criterion,
    )

    assert approved.criterion_id == criterion.criterion_id
    assert approved.maximum_scaled_residual_inf_norm == 1e-6
    assert approved.maximum_mass_residual_kg_s == 1e-5
    assert approved.maximum_pipe_residual_pa2 == 1.0
    assert approved.approval_ref == "approval://numerics/review-001"
    assert approved.registration_ref == "registration://synthetic-test-only/pre-run"


def test_draft_convergence_criterion_cannot_be_materialized() -> None:
    draft = _criterion(
        state=hydro_gas.StationarySolverPolicyState.DRAFT,
        approval_ref=None,
    )

    with pytest.raises(PermissionError, match="n'est pas APPROVED"):
        hydro_gas.materialize_approved_stationary_convergence_criterion(
            context=_CONTEXT,
            criterion=draft,
        )


def test_approved_state_requires_approval_and_draft_rejects_active_approval() -> None:
    with pytest.raises(ValueError, match=r"APPROVED.*approbation"):
        _criterion(approval_ref=None)

    with pytest.raises(ValueError, match=r"DRAFT.*approbation"):
        _criterion(state=hydro_gas.StationarySolverPolicyState.DRAFT)


def test_context_mismatch_is_rejected() -> None:
    criterion = _criterion(solver_method_ref="solver-method://other/v1")

    with pytest.raises(ValueError, match="contexte solveur"):
        hydro_gas.materialize_approved_stationary_convergence_criterion(
            context=_CONTEXT,
            criterion=criterion,
        )


def test_convergence_limits_must_be_explicit_finite_and_nonnegative() -> None:
    with pytest.raises(ValueError, match="norme infinie"):
        _criterion(maximum_scaled_residual_inf_norm=-1.0)

    with pytest.raises(ValueError, match="norme infinie"):
        _criterion(maximum_scaled_residual_inf_norm=math.inf)

    with pytest.raises(ValueError, match="limites physiques optionnelles"):
        _criterion(maximum_mass_residual_kg_s=-1.0)

    with pytest.raises(ValueError, match="limites physiques optionnelles"):
        _criterion(maximum_pipe_residual_pa2=math.nan)


def test_solver_status_vocabulary_does_not_imply_any_result_exists() -> None:
    assert set(hydro_gas.StationaryWeymouthSolverStatus) == {
        hydro_gas.StationaryWeymouthSolverStatus.CONVERGED,
        hydro_gas.StationaryWeymouthSolverStatus.NON_CONVERGED,
        hydro_gas.StationaryWeymouthSolverStatus.OUT_OF_DOMAIN,
        hydro_gas.StationaryWeymouthSolverStatus.INSUFFICIENT_DATA,
        hydro_gas.StationaryWeymouthSolverStatus.NUMERICAL_FAILURE,
    }
