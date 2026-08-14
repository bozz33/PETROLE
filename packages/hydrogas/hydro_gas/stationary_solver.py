"""Solveur P6-B borné pour le réseau Weymouth stationnaire.

Cette couche orchestre SciPy sans dupliquer la physique PETROLE. La méthode,
les tolérances, le budget d'évaluations, le schéma de Jacobien, l'échelle du
trust-region et le solveur de sous-problème sont tous explicites et sourcés.

La propriété ``success`` de SciPy reste un diagnostic algorithmique. PETROLE ne
déclare ``CONVERGED`` que si le résidu final satisfait le critère de convergence
pré-enregistré et approuvé pour le contexte numérique exact.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import scipy
from scipy.optimize import least_squares

from hydro_gas.stationary_candidate import StationaryWeymouthUnknownState
from hydro_gas.stationary_numerical_evaluation import (
    StationaryWeymouthNumericalEvaluation,
    evaluate_stationary_weymouth_numerical_vector,
)
from hydro_gas.stationary_numerics import (
    StationaryWeymouthNumericalScale,
    StationaryWeymouthNumericalVector,
    encode_stationary_weymouth_unknown_state,
)
from hydro_gas.stationary_problem import (
    StationaryWeymouthProblem,
    StationaryWeymouthUnknownLayout,
)
from hydro_gas.stationary_solver_governance import (
    ApprovedStationaryConvergenceCriterion,
    StationarySolverQualificationContext,
    StationaryWeymouthSolverStatus,
)
from hydro_gas.stationary_solver_inputs import (
    ApprovedStationaryWeymouthInitialGuessArtifact,
    ApprovedStationaryWeymouthScaleArtifact,
    stationary_weymouth_layout_sha256,
)
from hydro_gas.weymouth_si import WeymouthSiPipeParameters

SCIPY_LEAST_SQUARES_TRF_METHOD_REF = "solver-method://scipy/least-squares/trf/v1"
WEYMOUTH_P2_NUMERICAL_REPRESENTATION_REF = "numerics://gas/weymouth/psqr-scaled/v1"

JacobianScheme = Literal["2-point", "3-point"]
TrustRegionSolver = Literal["exact", "lsmr"]


@dataclass(frozen=True, slots=True)
class ScipyLeastSquaresTrfConfiguration:
    """Configuration numérique complète du solveur TRF borné."""

    configuration_ref: str
    source_ref: str
    solver_method_ref: str
    numerical_representation_ref: str
    scale_policy_ref: str
    initial_guess_policy_ref: str
    ftol: float
    xtol: float
    gtol: float
    x_scale: float
    diff_step: float
    max_nfev: int
    jacobian_scheme: JacobianScheme
    trust_region_solver: TrustRegionSolver

    def __post_init__(self) -> None:
        references = (
            self.configuration_ref,
            self.source_ref,
            self.solver_method_ref,
            self.numerical_representation_ref,
            self.scale_policy_ref,
            self.initial_guess_policy_ref,
        )
        if any(not value.strip() for value in references):
            raise ValueError("La configuration solveur et toutes ses références sont obligatoires.")
        if self.solver_method_ref != SCIPY_LEAST_SQUARES_TRF_METHOD_REF:
            raise ValueError("La configuration doit viser exactement le solveur TRF implémenté.")
        if self.numerical_representation_ref != WEYMOUTH_P2_NUMERICAL_REPRESENTATION_REF:
            raise ValueError(
                "La configuration doit viser exactement la représentation p² implémentée."
            )

        machine_epsilon = float(np.finfo(float).eps)
        tolerances = (self.ftol, self.xtol, self.gtol)
        if any(not math.isfinite(value) or value <= machine_epsilon for value in tolerances):
            raise ValueError(
                "ftol, xtol et gtol doivent être finis et strictement supérieurs à l'epsilon machine."
            )
        if not math.isfinite(self.x_scale) or self.x_scale <= 0.0:
            raise ValueError("x_scale doit être fini et strictement positif.")
        if not math.isfinite(self.diff_step) or self.diff_step <= 0.0:
            raise ValueError("diff_step doit être fini et strictement positif.")
        if self.max_nfev <= 0:
            raise ValueError("max_nfev doit être strictement positif.")
        if self.jacobian_scheme not in {"2-point", "3-point"}:
            raise ValueError("Le schéma de Jacobien doit être '2-point' ou '3-point'.")
        if self.trust_region_solver not in {"exact", "lsmr"}:
            raise ValueError("Le solveur de sous-problème doit être 'exact' ou 'lsmr'.")


@dataclass(frozen=True, slots=True)
class StationaryWeymouthConvergenceAssessment:
    """Évaluation du résidu final contre le seul critère approuvé fourni."""

    criterion_id: str
    criterion_version: str
    scaled_residual_inf_norm: float
    maximum_mass_residual_kg_s: float
    maximum_pipe_residual_pa2: float
    scaled_residual_passed: bool
    mass_residual_passed: bool | None
    pipe_residual_passed: bool | None
    all_approved_criteria_passed: bool
    approval_ref: str


@dataclass(frozen=True, slots=True)
class StationaryWeymouthSolveResult:
    """Résultat traçable du solveur, distinct du diagnostic SciPy brut."""

    solve_ref: str
    status: StationaryWeymouthSolverStatus
    initial_vector: StationaryWeymouthNumericalVector
    final_vector: StationaryWeymouthNumericalVector
    final_evaluation: StationaryWeymouthNumericalEvaluation
    convergence: StationaryWeymouthConvergenceAssessment
    scipy_success: bool
    scipy_status: int
    scipy_message: str
    scipy_version: str
    nfev: int
    njev: int | None
    cost: float
    optimality: float
    active_mask: tuple[int, ...]
    configuration_ref: str
    configuration_source_ref: str


@dataclass(frozen=True, slots=True)
class StationaryWeymouthGovernedSolveResult:
    """Résultat du chemin gouverné avec preuves d'échelle et d'initialisation."""

    solve: StationaryWeymouthSolveResult
    scale_artifact_ref: str
    scale_policy_ref: str
    scale_approval_ref: str
    initial_guess_artifact_ref: str
    initial_guess_policy_ref: str
    initial_guess_approval_ref: str


def _context_tuple(context: StationarySolverQualificationContext) -> tuple[str, ...]:
    return (
        context.protocol_ref,
        context.problem_family_ref,
        context.numerical_representation_ref,
        context.solver_method_ref,
        context.scale_policy_ref,
        context.initial_guess_policy_ref,
    )


def _approved_criterion_context_tuple(
    criterion: ApprovedStationaryConvergenceCriterion,
) -> tuple[str, ...]:
    return (
        criterion.protocol_ref,
        criterion.problem_family_ref,
        criterion.numerical_representation_ref,
        criterion.solver_method_ref,
        criterion.scale_policy_ref,
        criterion.initial_guess_policy_ref,
    )


def _validate_execution_context(
    context: StationarySolverQualificationContext,
    criterion: ApprovedStationaryConvergenceCriterion,
    configuration: ScipyLeastSquaresTrfConfiguration,
) -> None:
    if _approved_criterion_context_tuple(criterion) != _context_tuple(context):
        raise ValueError(
            "Le critère approuvé ne correspond pas au contexte d'exécution du solveur."
        )
    if context.solver_method_ref != configuration.solver_method_ref:
        raise ValueError(
            "La méthode du contexte et celle de la configuration doivent être identiques."
        )
    if context.numerical_representation_ref != configuration.numerical_representation_ref:
        raise ValueError(
            "La représentation numérique du contexte et celle de la configuration doivent être identiques."
        )
    if context.scale_policy_ref != configuration.scale_policy_ref:
        raise ValueError(
            "La politique d'échelle du contexte et de la configuration doit être identique."
        )
    if context.initial_guess_policy_ref != configuration.initial_guess_policy_ref:
        raise ValueError(
            "La politique d'initialisation du contexte et de la configuration doit être identique."
        )


def assess_stationary_weymouth_convergence(
    evaluation: StationaryWeymouthNumericalEvaluation,
    criterion: ApprovedStationaryConvergenceCriterion,
) -> StationaryWeymouthConvergenceAssessment:
    """Évalue les résidus finaux sans ajouter de tolérance implicite."""

    scaled_values = evaluation.residual_vector.values
    scaled_inf_norm = max((abs(value) for value in scaled_values), default=0.0)
    mass_values = tuple(
        abs(item.residual_kg_s)
        for item in evaluation.physical_evaluation.residuals.mass_balance.node_balances
    )
    pipe_values = tuple(
        abs(item.residual_pa2) for item in evaluation.physical_evaluation.residuals.pipe_residuals
    )
    maximum_mass = max(mass_values, default=0.0)
    maximum_pipe = max(pipe_values, default=0.0)

    scaled_passed = scaled_inf_norm <= criterion.maximum_scaled_residual_inf_norm
    mass_passed = (
        None
        if criterion.maximum_mass_residual_kg_s is None
        else maximum_mass <= criterion.maximum_mass_residual_kg_s
    )
    pipe_passed = (
        None
        if criterion.maximum_pipe_residual_pa2 is None
        else maximum_pipe <= criterion.maximum_pipe_residual_pa2
    )
    required_results = [scaled_passed]
    if mass_passed is not None:
        required_results.append(mass_passed)
    if pipe_passed is not None:
        required_results.append(pipe_passed)

    return StationaryWeymouthConvergenceAssessment(
        criterion_id=criterion.criterion_id,
        criterion_version=criterion.criterion_version,
        scaled_residual_inf_norm=scaled_inf_norm,
        maximum_mass_residual_kg_s=maximum_mass,
        maximum_pipe_residual_pa2=maximum_pipe,
        scaled_residual_passed=scaled_passed,
        mass_residual_passed=mass_passed,
        pipe_residual_passed=pipe_passed,
        all_approved_criteria_passed=all(required_results),
        approval_ref=criterion.approval_ref,
    )


def solve_stationary_weymouth_least_squares_trf(
    problem: StationaryWeymouthProblem,
    layout: StationaryWeymouthUnknownLayout,
    template_state: StationaryWeymouthUnknownState,
    initial_vector: StationaryWeymouthNumericalVector,
    scale: StationaryWeymouthNumericalScale,
    pipe_parameters: tuple[WeymouthSiPipeParameters, ...],
    *,
    context: StationarySolverQualificationContext,
    convergence_criterion: ApprovedStationaryConvergenceCriterion,
    configuration: ScipyLeastSquaresTrfConfiguration,
    solve_ref: str,
) -> StationaryWeymouthSolveResult:
    """Résout le système borné sans confondre arrêt SciPy et convergence PETROLE."""

    normalized_ref = solve_ref.strip()
    if not normalized_ref:
        raise ValueError("La provenance de l'exécution solveur est obligatoire.")
    if not layout.structurally_square:
        raise ValueError("Le solveur P6-B exige un layout structurellement carré.")
    if len(initial_vector.values) != layout.unknown_count:
        raise ValueError(
            "Le vecteur initial doit couvrir exactement toutes les inconnues du layout."
        )

    _validate_execution_context(context, convergence_criterion, configuration)

    pressure_count = len(layout.unknown_pressure_node_ids)
    if any(value < 0.0 for value in initial_vector.values[:pressure_count]):
        raise ValueError("Les coordonnées initiales p² doivent être positives ou nulles.")

    evaluate_stationary_weymouth_numerical_vector(
        problem,
        layout,
        template_state,
        initial_vector,
        scale,
        pipe_parameters,
        evaluation_ref=f"{normalized_ref}#initial-evaluation",
    )

    lower_bounds = np.full(layout.unknown_count, -np.inf, dtype=float)
    lower_bounds[:pressure_count] = 0.0
    upper_bounds = np.full(layout.unknown_count, np.inf, dtype=float)
    x0 = np.asarray(initial_vector.values, dtype=float)

    evaluation_counter = 0

    def residual_function(values: np.ndarray) -> np.ndarray:
        nonlocal evaluation_counter
        evaluation_counter += 1
        vector = StationaryWeymouthNumericalVector(
            values=tuple(float(value) for value in values),
            source_ref=f"{normalized_ref}#iteration/{evaluation_counter}",
        )
        evaluation = evaluate_stationary_weymouth_numerical_vector(
            problem,
            layout,
            template_state,
            vector,
            scale,
            pipe_parameters,
            evaluation_ref=f"{normalized_ref}#iteration/{evaluation_counter}/evaluation",
        )
        return np.asarray(evaluation.residual_vector.values, dtype=float)

    optimizer_result = least_squares(
        residual_function,
        x0,
        jac=configuration.jacobian_scheme,
        bounds=(lower_bounds, upper_bounds),
        method="trf",
        ftol=configuration.ftol,
        xtol=configuration.xtol,
        gtol=configuration.gtol,
        x_scale=configuration.x_scale,
        loss="linear",
        f_scale=1.0,
        diff_step=configuration.diff_step,
        tr_solver=configuration.trust_region_solver,
        tr_options={},
        jac_sparsity=None,
        max_nfev=configuration.max_nfev,
        verbose=0,
    )

    final_vector = StationaryWeymouthNumericalVector(
        values=tuple(float(value) for value in optimizer_result.x),
        source_ref=f"{normalized_ref}#final-vector",
    )
    final_evaluation = evaluate_stationary_weymouth_numerical_vector(
        problem,
        layout,
        template_state,
        final_vector,
        scale,
        pipe_parameters,
        evaluation_ref=f"{normalized_ref}#final-evaluation",
    )
    convergence = assess_stationary_weymouth_convergence(
        final_evaluation,
        convergence_criterion,
    )

    if convergence.all_approved_criteria_passed:
        status = StationaryWeymouthSolverStatus.CONVERGED
    elif int(optimizer_result.status) < 0:
        status = StationaryWeymouthSolverStatus.NUMERICAL_FAILURE
    else:
        status = StationaryWeymouthSolverStatus.NON_CONVERGED

    raw_njev = optimizer_result.njev
    njev = None if raw_njev is None else int(raw_njev)
    return StationaryWeymouthSolveResult(
        solve_ref=normalized_ref,
        status=status,
        initial_vector=initial_vector,
        final_vector=final_vector,
        final_evaluation=final_evaluation,
        convergence=convergence,
        scipy_success=bool(optimizer_result.success),
        scipy_status=int(optimizer_result.status),
        scipy_message=str(optimizer_result.message),
        scipy_version=str(scipy.__version__),
        nfev=int(optimizer_result.nfev),
        njev=njev,
        cost=float(optimizer_result.cost),
        optimality=float(optimizer_result.optimality),
        active_mask=tuple(int(value) for value in optimizer_result.active_mask),
        configuration_ref=configuration.configuration_ref,
        configuration_source_ref=configuration.source_ref,
    )


def solve_stationary_weymouth_with_approved_inputs(
    problem: StationaryWeymouthProblem,
    layout: StationaryWeymouthUnknownLayout,
    pipe_parameters: tuple[WeymouthSiPipeParameters, ...],
    *,
    context: StationarySolverQualificationContext,
    convergence_criterion: ApprovedStationaryConvergenceCriterion,
    configuration: ScipyLeastSquaresTrfConfiguration,
    scale_artifact: ApprovedStationaryWeymouthScaleArtifact,
    initial_guess_artifact: ApprovedStationaryWeymouthInitialGuessArtifact,
    solve_ref: str,
) -> StationaryWeymouthGovernedSolveResult:
    """Exécute le solveur seulement avec échelle et initialisation approuvées."""

    if scale_artifact.policy_ref != context.scale_policy_ref:
        raise ValueError("L'artefact d'échelle ne correspond pas à la politique du contexte.")
    if initial_guess_artifact.policy_ref != context.initial_guess_policy_ref:
        raise ValueError(
            "L'artefact d'initialisation ne correspond pas à la politique du contexte."
        )
    if initial_guess_artifact.problem_ref != problem.problem_ref:
        raise ValueError("L'artefact d'initialisation ne correspond pas au problème exécuté.")
    if initial_guess_artifact.layout_sha256 != stationary_weymouth_layout_sha256(layout):
        raise ValueError("L'artefact d'initialisation ne correspond pas au layout exécuté.")

    scale = scale_artifact.to_numerical_scale()
    initial_state = initial_guess_artifact.unknown_state
    initial_vector = encode_stationary_weymouth_unknown_state(layout, initial_state, scale)
    solve = solve_stationary_weymouth_least_squares_trf(
        problem,
        layout,
        initial_state,
        initial_vector,
        scale,
        pipe_parameters,
        context=context,
        convergence_criterion=convergence_criterion,
        configuration=configuration,
        solve_ref=solve_ref,
    )
    return StationaryWeymouthGovernedSolveResult(
        solve=solve,
        scale_artifact_ref=scale_artifact.artifact_ref,
        scale_policy_ref=scale_artifact.policy_ref,
        scale_approval_ref=scale_artifact.approval_ref,
        initial_guess_artifact_ref=initial_guess_artifact.artifact_ref,
        initial_guess_policy_ref=initial_guess_artifact.policy_ref,
        initial_guess_approval_ref=initial_guess_artifact.approval_ref,
    )


__all__ = [
    "SCIPY_LEAST_SQUARES_TRF_METHOD_REF",
    "WEYMOUTH_P2_NUMERICAL_REPRESENTATION_REF",
    "ScipyLeastSquaresTrfConfiguration",
    "StationaryWeymouthConvergenceAssessment",
    "StationaryWeymouthGovernedSolveResult",
    "StationaryWeymouthSolveResult",
    "assess_stationary_weymouth_convergence",
    "solve_stationary_weymouth_least_squares_trf",
    "solve_stationary_weymouth_with_approved_inputs",
]
