"""Gouvernance P6-B du futur solveur stationnaire Weymouth.

Le module décrit ce qui doit être approuvé avant qu'un algorithme numérique
puisse transformer ``x -> r(x)`` en décision de convergence. Il ne sélectionne
aucune méthode, n'instancie aucun seuil réel et n'exécute aucun solveur.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class StationarySolverPolicyState(StrEnum):
    """État documentaire d'une politique numérique."""

    DRAFT = "draft"
    APPROVED = "approved"


class StationaryWeymouthSolverStatus(StrEnum):
    """Vocabulaire réservé aux futurs résultats de solveur."""

    CONVERGED = "converged"
    NON_CONVERGED = "non_converged"
    OUT_OF_DOMAIN = "out_of_domain"
    INSUFFICIENT_DATA = "insufficient_data"
    NUMERICAL_FAILURE = "numerical_failure"


@dataclass(frozen=True, slots=True)
class StationarySolverQualificationContext:
    """Contexte exact dans lequel une politique de solveur peut être utilisée."""

    protocol_ref: str
    problem_family_ref: str
    numerical_representation_ref: str
    solver_method_ref: str
    scale_policy_ref: str
    initial_guess_policy_ref: str

    def __post_init__(self) -> None:
        values = (
            self.protocol_ref,
            self.problem_family_ref,
            self.numerical_representation_ref,
            self.solver_method_ref,
            self.scale_policy_ref,
            self.initial_guess_policy_ref,
        )
        if any(not value.strip() for value in values):
            raise ValueError("Le contexte de qualification solveur doit être entièrement référencé.")


@dataclass(frozen=True, slots=True)
class PreRegisteredStationaryConvergenceCriterion:
    """Critère de convergence pré-enregistré, sans valeur implicite."""

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
            raise ValueError("Le critère de convergence et toutes ses références sont obligatoires.")

        if (
            not math.isfinite(self.maximum_scaled_residual_inf_norm)
            or self.maximum_scaled_residual_inf_norm < 0.0
        ):
            raise ValueError(
                "La norme infinie maximale du résidu adimensionné doit être finie et positive ou nulle."
            )
        optional_limits = (
            self.maximum_mass_residual_kg_s,
            self.maximum_pipe_residual_pa2,
        )
        if any(
            value is not None and (not math.isfinite(value) or value < 0.0)
            for value in optional_limits
        ):
            raise ValueError("Les limites physiques optionnelles doivent être finies et positives ou nulles.")

        if self.state is StationarySolverPolicyState.APPROVED:
            if self.approval_ref is None or not self.approval_ref.strip():
                raise ValueError("Un critère APPROVED doit référencer son approbation.")
        elif self.approval_ref is not None:
            raise ValueError("Un critère DRAFT ne peut pas porter une approbation active.")


@dataclass(frozen=True, slots=True)
class ApprovedStationaryConvergenceCriterion:
    """Critère approuvé matérialisé pour un contexte numérique exact."""

    criterion_id: str
    criterion_version: str
    maximum_scaled_residual_inf_norm: float
    maximum_mass_residual_kg_s: float | None
    maximum_pipe_residual_pa2: float | None
    source_ref: str
    registration_ref: str
    approval_ref: str
    protocol_ref: str


def materialize_approved_stationary_convergence_criterion(
    *,
    context: StationarySolverQualificationContext,
    criterion: PreRegisteredStationaryConvergenceCriterion,
) -> ApprovedStationaryConvergenceCriterion:
    """Matérialise seulement un critère approuvé pour le contexte exact.

    Cette fonction ne décide pas qu'un résidu passe le critère. Elle protège
    uniquement la provenance et empêche l'utilisation d'un brouillon ou d'un
    critère rattaché à une autre méthode, représentation ou politique d'échelle.
    """

    if criterion.state is not StationarySolverPolicyState.APPROVED:
        raise PermissionError(
            f"Le critère {criterion.criterion_id} n'est pas APPROVED et ne peut pas être utilisé."
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
        raise ValueError("Le critère de convergence ne correspond pas au contexte solveur.")

    approval_ref = criterion.approval_ref
    if approval_ref is None:
        raise RuntimeError("Un critère APPROVED doit déjà avoir une approbation validée.")

    return ApprovedStationaryConvergenceCriterion(
        criterion_id=criterion.criterion_id,
        criterion_version=criterion.criterion_version,
        maximum_scaled_residual_inf_norm=criterion.maximum_scaled_residual_inf_norm,
        maximum_mass_residual_kg_s=criterion.maximum_mass_residual_kg_s,
        maximum_pipe_residual_pa2=criterion.maximum_pipe_residual_pa2,
        source_ref=criterion.source_ref,
        registration_ref=criterion.registration_ref,
        approval_ref=approval_ref,
        protocol_ref=criterion.protocol_ref,
    )


__all__ = [
    "ApprovedStationaryConvergenceCriterion",
    "PreRegisteredStationaryConvergenceCriterion",
    "StationarySolverPolicyState",
    "StationarySolverQualificationContext",
    "StationaryWeymouthSolverStatus",
    "materialize_approved_stationary_convergence_criterion",
]
