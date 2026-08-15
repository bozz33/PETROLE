"""Solveur stationnaire borné pour conduites Weymouth + compresseurs actifs.

Le solveur consomme exclusivement le chemin physique canonique ``x -> r(x)``.
Les débits compresseurs sont bornés par les domaines des cartes et enveloppes
fournies. Une convergence PETROLE n'est déclarée que contre un critère
pré-enregistré et approuvé ; le ``success`` SciPy reste un diagnostic séparé.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import scipy
from scipy.optimize import least_squares

from hydro_gas.stationary_equipment_bounds import (
    StationaryActiveCompressorNumericalBounds,
    build_stationary_active_compressor_numerical_bounds,
)
from hydro_gas.stationary_equipment_evaluation import StationaryActiveCompressorEvaluation
from hydro_gas.stationary_equipment_numerical_evaluation import (
    StationaryActiveCompressorNumericalEvaluation,
    evaluate_stationary_active_compressor_numerical_vector,
)
from hydro_gas.stationary_equipment_numerics import (
    StationaryActiveCompressorNumericalVector,
    encode_stationary_active_compressor_unknown_state,
)
from hydro_gas.stationary_equipment_problem import (
    StationaryActiveCompressorProblem,
    StationaryActiveCompressorUnknownLayout,
    build_stationary_active_compressor_unknown_layout,
)
from hydro_gas.stationary_equipment_solver_governance import (
    ApprovedStationaryEquipmentConvergenceCriterion,
)
from hydro_gas.stationary_equipment_solver_inputs import (
    ApprovedStationaryEquipmentInitialGuessArtifact,
    ApprovedStationaryEquipmentScaleArtifact,
    stationary_active_compressor_layout_sha256,
)
from hydro_gas.stationary_solver import SCIPY_LEAST_SQUARES_TRF_METHOD_REF
from hydro_gas.stationary_solver_governance import (
    StationarySolverQualificationContext,
    StationaryWeymouthSolverStatus,
)
from hydro_gas.weymouth_si import WeymouthSiPipeParameters

ACTIVE_COMPRESSOR_PROBLEM_FAMILY_REF = "problem-family://gas/stationary/weymouth-active-compressors/v1"
ACTIVE_COMPRESSOR_P2_NUMERICAL_REPRESENTATION_REF = "numerics://gas/mixed/psqr-scaled/v1"

JacobianScheme = Literal["2-point", "3-point"]
TrustRegionSolver = Literal["exact", "lsmr"]


@dataclass(frozen=True, slots=True)
class ScipyActiveCompressorLeastSquaresTrfConfiguration:
    """Configuration numérique explicite du solveur mixte TRF."""

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
            raise ValueError("La configuration solveur mixte doit être entièrement référencée.")
        if self.solver_method_ref != SCIPY_LEAST_SQUARES_TRF_METHOD_REF:
            raise ValueError("Le solveur mixte doit utiliser exactement la méthode TRF implémentée.")
        if self.numerical_representation_ref != ACTIVE_COMPRESSOR_P2_NUMERICAL_REPRESENTATION_REF:
            raise ValueError("Le solveur mixte doit utiliser exactement la représentation p² mixte.")

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
class StationaryActiveCompressorConvergenceAssessment:
    """Évaluation des trois familles de résidus contre le critère approuvé."""

    criterion_id: str
    criterion_version: str
    scaled_residual_inf_norm: float
    maximum_mass_residual_kg_s: float
    maximum_pipe_residual_pa2: float
    maximum_compressor_residual_pa: float
    scaled_residual_passed: bool
    mass_residual_passed: bool | None
    pipe_residual_passed: bool | None
    compressor_residual_passed: bool | None
    all_approved_criteria_passed: bool
    approval_ref: str


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorSolveResult:
    """Résultat scientifique et numérique d'une exécution mixte gouvernée."""

    solve_ref: str
    status: StationaryWeymouthSolverStatus
    initial_vector: StationaryActiveCompressorNumericalVector
    final_vector: StationaryActiveCompressorNumericalVector
    final_evaluation: StationaryActiveCompressorNumericalEvaluation
    convergence: StationaryActiveCompressorConvergenceAssessment
    numerical_bounds: StationaryActiveCompressorNumericalBounds
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
    missing_operational_envelope_compressor_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorGovernedSolveResult:
    """Résultat avec preuves des entrées approuvées utilisées."""

    solve: StationaryActiveCompressorSolveResult
    scale_artifact_ref: str
    scale_policy_ref: str
    scale_approval_ref: str
    initial_guess_artifact_ref: str
    initial_guess_policy_ref: str
    initial_guess_approval_ref: str


def _criterion_context_tuple(
    criterion: ApprovedStationaryEquipmentConvergenceCriterion,
) -> tuple[str, ...]:
    return (
        criterion.protocol_ref,
        criterion.problem_family_ref,
        criterion.numerical_representation_ref,
        criterion.solver_method_ref,
        criterion.scale_policy_ref,
        criterion.initial_guess_policy_ref,
    )


def _context_tuple(context: StationarySolverQualificationContext) -> tuple[str, ...]:
    return (
        context.protocol_ref,
        context.problem_family_ref,
        context.numerical_representation_ref,
        context.solver_method_ref,
        context.scale_policy_ref,
        context.initial_guess_policy_ref,
    )


def _validate_execution_context(
    context: StationarySolverQualificationContext,
    criterion: ApprovedStationaryEquipmentConvergenceCriterion,
    configuration: ScipyActiveCompressorLeastSquaresTrfConfiguration,
) -> None:
    if context.problem_family_ref != ACTIVE_COMPRESSOR_PROBLEM_FAMILY_REF:
        raise ValueError("Le contexte ne vise pas la famille de problème mixte implémentée.")
    if context.numerical_representation_ref != ACTIVE_COMPRESSOR_P2_NUMERICAL_REPRESENTATION_REF:
        raise ValueError("Le contexte ne vise pas la représentation numérique mixte implémentée.")
    if context.solver_method_ref != SCIPY_LEAST_SQUARES_TRF_METHOD_REF:
        raise ValueError("Le contexte ne vise pas la méthode solveur mixte implémentée.")
    if _criterion_context_tuple(criterion) != _context_tuple(context):
        raise ValueError("Le critère approuvé ne correspond pas au contexte du solveur mixte.")
    if configuration.solver_method_ref != context.solver_method_ref:
        raise ValueError("La méthode de la configuration diffère du contexte mixte.")
    if configuration.numerical_representation_ref != context.numerical_representation_ref:
        raise ValueError("La représentation de la configuration diffère du contexte mixte.")
    if configuration.scale_policy_ref != context.scale_policy_ref:
        raise ValueError("La politique d'échelle de la configuration diffère du contexte mixte.")
    if configuration.initial_guess_policy_ref != context.initial_guess_policy_ref:
        raise ValueError("La politique d'initialisation de la configuration diffère du contexte mixte.")


def assess_stationary_active_compressor_convergence(
    evaluation: StationaryActiveCompressorNumericalEvaluation,
    criterion: ApprovedStationaryEquipmentConvergenceCriterion,
) -> StationaryActiveCompressorConvergenceAssessment:
    """Évalue les résidus finaux sans ajouter de tolérance implicite."""

    scaled_inf_norm = max((abs(value) for value in evaluation.residual_vector.values), default=0.0)
    physical: StationaryActiveCompressorEvaluation = evaluation.physical_evaluation
    mass_values = tuple(
        abs(item.residual_kg_s)
        for item in physical.equipment_residuals.mass_balance.node_balances
    )
    pipe_values = tuple(abs(item.residual_pa2) for item in physical.pipe_residuals)
    compressor_values = tuple(
        abs(item.pressure_ratio_residual_pa)
        for item in physical.equipment_residuals.compressor_constraints
    )
    maximum_mass = max(mass_values, default=0.0)
    maximum_pipe = max(pipe_values, default=0.0)
    maximum_compressor = max(compressor_values, default=0.0)

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
    compressor_passed = (
        None
        if criterion.maximum_compressor_residual_pa is None
        else maximum_compressor <= criterion.maximum_compressor_residual_pa
    )
    required = [scaled_passed]
    for result in (mass_passed, pipe_passed, compressor_passed):
        if result is not None:
            required.append(result)

    return StationaryActiveCompressorConvergenceAssessment(
        criterion_id=criterion.criterion_id,
        criterion_version=criterion.criterion_version,
        scaled_residual_inf_norm=scaled_inf_norm,
        maximum_mass_residual_kg_s=maximum_mass,
        maximum_pipe_residual_pa2=maximum_pipe,
        maximum_compressor_residual_pa=maximum_compressor,
        scaled_residual_passed=scaled_passed,
        mass_residual_passed=mass_passed,
        pipe_residual_passed=pipe_passed,
        compressor_residual_passed=compressor_passed,
        all_approved_criteria_passed=all(required),
        approval_ref=criterion.approval_ref,
    )


def solve_stationary_active_compressor_with_approved_inputs(
    problem: StationaryActiveCompressorProblem,
    layout: StationaryActiveCompressorUnknownLayout,
    pipe_parameters: tuple[WeymouthSiPipeParameters, ...],
    *,
    context: StationarySolverQualificationContext,
    convergence_criterion: ApprovedStationaryEquipmentConvergenceCriterion,
    configuration: ScipyActiveCompressorLeastSquaresTrfConfiguration,
    scale_artifact: ApprovedStationaryEquipmentScaleArtifact,
    initial_guess_artifact: ApprovedStationaryEquipmentInitialGuessArtifact,
    solve_ref: str,
) -> StationaryActiveCompressorGovernedSolveResult:
    """Résout le problème mixte uniquement avec les entrées APPROVED fournies."""

    normalized_ref = solve_ref.strip()
    if not normalized_ref:
        raise ValueError("La provenance de l'exécution solveur mixte est obligatoire.")
    expected_layout = build_stationary_active_compressor_unknown_layout(problem)
    if layout != expected_layout or not layout.structurally_square:
        raise ValueError("Le solveur mixte exige le layout carré exact du problème.")
    _validate_execution_context(context, convergence_criterion, configuration)

    if scale_artifact.policy_ref != context.scale_policy_ref:
        raise ValueError("L'artefact d'échelle mixte ne correspond pas au contexte.")
    if initial_guess_artifact.policy_ref != context.initial_guess_policy_ref:
        raise ValueError("L'artefact d'initialisation mixte ne correspond pas au contexte.")
    if initial_guess_artifact.problem_ref != problem.problem_ref:
        raise ValueError("L'artefact d'initialisation mixte vise un autre problème.")
    if initial_guess_artifact.layout_sha256 != stationary_active_compressor_layout_sha256(layout):
        raise ValueError("L'artefact d'initialisation mixte vise un autre layout.")

    scale = scale_artifact.to_numerical_scale()
    initial_state = initial_guess_artifact.unknown_state
    initial_vector = encode_stationary_active_compressor_unknown_state(
        layout,
        initial_state,
        scale,
    )
    bounds = build_stationary_active_compressor_numerical_bounds(
        problem,
        layout,
        scale,
        source_ref=f"{normalized_ref}#domain-bounds",
    )
    if any(
        value < lower or value > upper
        for value, lower, upper in zip(
            initial_vector.values,
            bounds.lower_values,
            bounds.upper_values,
            strict=True,
        )
    ):
        raise ValueError("L'initialisation approuvée est hors des bornes du problème mixte.")

    evaluate_stationary_active_compressor_numerical_vector(
        problem,
        layout,
        initial_state,
        initial_vector,
        scale,
        pipe_parameters,
        evaluation_ref=f"{normalized_ref}#initial-evaluation",
    )

    evaluation_counter = 0

    def residual_function(values: np.ndarray) -> np.ndarray:
        nonlocal evaluation_counter
        evaluation_counter += 1
        vector = StationaryActiveCompressorNumericalVector(
            values=tuple(float(value) for value in values),
            source_ref=f"{normalized_ref}#iteration/{evaluation_counter}",
        )
        evaluation = evaluate_stationary_active_compressor_numerical_vector(
            problem,
            layout,
            initial_state,
            vector,
            scale,
            pipe_parameters,
            evaluation_ref=f"{normalized_ref}#iteration/{evaluation_counter}/evaluation",
        )
        return np.asarray(evaluation.residual_vector.values, dtype=float)

    optimizer_result = least_squares(
        residual_function,
        np.asarray(initial_vector.values, dtype=float),
        jac=configuration.jacobian_scheme,
        bounds=(
            np.asarray(bounds.lower_values, dtype=float),
            np.asarray(bounds.upper_values, dtype=float),
        ),
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

    final_vector = StationaryActiveCompressorNumericalVector(
        values=tuple(float(value) for value in optimizer_result.x),
        source_ref=f"{normalized_ref}#final-vector",
    )
    final_evaluation = evaluate_stationary_active_compressor_numerical_vector(
        problem,
        layout,
        initial_state,
        final_vector,
        scale,
        pipe_parameters,
        evaluation_ref=f"{normalized_ref}#final-evaluation",
    )
    convergence = assess_stationary_active_compressor_convergence(
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
    missing_envelopes = tuple(
        binding.compressor_id for binding in problem.map_bindings if binding.envelope is None
    )
    solve = StationaryActiveCompressorSolveResult(
        solve_ref=normalized_ref,
        status=status,
        initial_vector=initial_vector,
        final_vector=final_vector,
        final_evaluation=final_evaluation,
        convergence=convergence,
        numerical_bounds=bounds,
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
        missing_operational_envelope_compressor_ids=missing_envelopes,
    )
    return StationaryActiveCompressorGovernedSolveResult(
        solve=solve,
        scale_artifact_ref=scale_artifact.artifact_ref,
        scale_policy_ref=scale_artifact.policy_ref,
        scale_approval_ref=scale_artifact.approval_ref,
        initial_guess_artifact_ref=initial_guess_artifact.artifact_ref,
        initial_guess_policy_ref=initial_guess_artifact.policy_ref,
        initial_guess_approval_ref=initial_guess_artifact.approval_ref,
    )


__all__ = [
    "ACTIVE_COMPRESSOR_P2_NUMERICAL_REPRESENTATION_REF",
    "ACTIVE_COMPRESSOR_PROBLEM_FAMILY_REF",
    "ScipyActiveCompressorLeastSquaresTrfConfiguration",
    "StationaryActiveCompressorConvergenceAssessment",
    "StationaryActiveCompressorGovernedSolveResult",
    "StationaryActiveCompressorSolveResult",
    "assess_stationary_active_compressor_convergence",
    "solve_stationary_active_compressor_with_approved_inputs",
]
