"""Gouvernance des critères de convergence du futur solveur gaz mixte.

Le problème conduites + compresseurs possède trois familles de résidus
physiques. Cette couche impose qu'un critère de convergence couvrant ce contexte
soit pré-enregistré et approuvé avant toute décision ``CONVERGED``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.stationary_solver_governance import (
    StationarySolverPolicyState,
    StationarySolverQualificationContext,
)


@dataclass(frozen=True, slots=True)
class PreRegisteredStationaryEquipmentConvergenceCriterion:
    """Critère mixte pré-enregistré, sans limite implicite."""

    criterion_id: str
    criterion_version: str
    protocol_ref: str
    problem_family_ref: str
    numerical_representation_ref: str
    solver_method_ref: str
    scale_policy_ref: str
    initial_guess_policy_ref: str
    source_ref: str
    registration_ref: str
    maximum_scaled_residual_inf_norm: float
    state: StationarySolverPolicyState = StationarySolverPolicyState.DRAFT
    approval_ref: str | None = None
    maximum_mass_residual_kg_s: float | None = None
    maximum_pipe_residual_pa2: float | None = None
    maximum_compressor_residual_pa: float | None = None

    def __post_init__(self) -> None:
        required = (
            self.criterion_id,
            self.criterion_version,
            self.protocol_ref,
            self.problem_family_ref,
            self.numerical_representation_ref,
            self.solver_method_ref,
            self.scale_policy_ref,
            self.initial_guess_policy_ref,
            self.source_ref,
            self.registration_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError("Le critère mixte et toutes ses références sont obligatoires.")
        if (
            not math.isfinite(self.maximum_scaled_residual_inf_norm)
            or self.maximum_scaled_residual_inf_norm < 0.0
        ):
            raise ValueError(
                "La norme infinie maximale du résidu mixte doit être finie et positive ou nulle."
            )
        optional_limits = (
            self.maximum_mass_residual_kg_s,
            self.maximum_pipe_residual_pa2,
            self.maximum_compressor_residual_pa,
        )
        if any(
            value is not None and (not math.isfinite(value) or value < 0.0)
            for value in optional_limits
        ):
            raise ValueError(
                "Les limites physiques mixtes doivent être finies et positives ou nulles."
            )
        if self.state is StationarySolverPolicyState.APPROVED:
            if self.approval_ref is None or not self.approval_ref.strip():
                raise ValueError("Un critère mixte APPROVED doit référencer son approbation.")
        elif self.approval_ref is not None:
            raise ValueError("Un critère mixte DRAFT ne peut pas porter une approbation active.")


@dataclass(frozen=True, slots=True)
class ApprovedStationaryEquipmentConvergenceCriterion:
    """Critère mixte approuvé pour un contexte numérique exact."""

    criterion_id: str
    criterion_version: str
    maximum_scaled_residual_inf_norm: float
    maximum_mass_residual_kg_s: float | None
    maximum_pipe_residual_pa2: float | None
    maximum_compressor_residual_pa: float | None
    source_ref: str
    registration_ref: str
    approval_ref: str
    protocol_ref: str
    problem_family_ref: str
    numerical_representation_ref: str
    solver_method_ref: str
    scale_policy_ref: str
    initial_guess_policy_ref: str


def materialize_approved_stationary_equipment_convergence_criterion(
    *,
    context: StationarySolverQualificationContext,
    criterion: PreRegisteredStationaryEquipmentConvergenceCriterion,
) -> ApprovedStationaryEquipmentConvergenceCriterion:
    """Libère uniquement un critère APPROVED correspondant au contexte exact."""

    if criterion.state is not StationarySolverPolicyState.APPROVED:
        raise PermissionError(
            f"Le critère mixte {criterion.criterion_id} n'est pas APPROVED."
        )
    expected_context = (
        context.protocol_ref,
        context.problem_family_ref,
        context.numerical_representation_ref,
        context.solver_method_ref,
        context.scale_policy_ref,
        context.initial_guess_policy_ref,
    )
    actual_context = (
        criterion.protocol_ref,
        criterion.problem_family_ref,
        criterion.numerical_representation_ref,
        criterion.solver_method_ref,
        criterion.scale_policy_ref,
        criterion.initial_guess_policy_ref,
    )
    if actual_context != expected_context:
        raise ValueError("Le critère mixte ne correspond pas au contexte solveur.")

    approval_ref = criterion.approval_ref
    if approval_ref is None:
        raise RuntimeError("Un critère mixte APPROVED doit porter une approbation.")
    return ApprovedStationaryEquipmentConvergenceCriterion(
        criterion_id=criterion.criterion_id,
        criterion_version=criterion.criterion_version,
        maximum_scaled_residual_inf_norm=criterion.maximum_scaled_residual_inf_norm,
        maximum_mass_residual_kg_s=criterion.maximum_mass_residual_kg_s,
        maximum_pipe_residual_pa2=criterion.maximum_pipe_residual_pa2,
        maximum_compressor_residual_pa=criterion.maximum_compressor_residual_pa,
        source_ref=criterion.source_ref,
        registration_ref=criterion.registration_ref,
        approval_ref=approval_ref,
        protocol_ref=criterion.protocol_ref,
        problem_family_ref=criterion.problem_family_ref,
        numerical_representation_ref=criterion.numerical_representation_ref,
        solver_method_ref=criterion.solver_method_ref,
        scale_policy_ref=criterion.scale_policy_ref,
        initial_guess_policy_ref=criterion.initial_guess_policy_ref,
    )


__all__ = [
    "ApprovedStationaryEquipmentConvergenceCriterion",
    "PreRegisteredStationaryEquipmentConvergenceCriterion",
    "materialize_approved_stationary_equipment_convergence_criterion",
]
