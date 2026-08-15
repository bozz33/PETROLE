"""Évaluation numérique pure ``x -> r(x)`` du problème gaz mixte.

La fonction décode le vecteur selon le layout, reconstruit l'état physique,
appelle l'évaluation canonique puis encode les trois familles de résidus avec
des échelles explicites. Aucun solveur ni critère de convergence n'est présent.
"""

from __future__ import annotations

from dataclasses import dataclass

from hydro_gas.stationary_equipment_candidate import StationaryActiveCompressorUnknownState
from hydro_gas.stationary_equipment_evaluation import (
    StationaryActiveCompressorEvaluation,
    evaluate_stationary_active_compressor_unknown_state,
)
from hydro_gas.stationary_equipment_numerics import (
    StationaryActiveCompressorNumericalScale,
    StationaryActiveCompressorNumericalVector,
    decode_stationary_active_compressor_numerical_vector,
    encode_stationary_active_compressor_residuals,
)
from hydro_gas.stationary_equipment_problem import (
    StationaryActiveCompressorProblem,
    StationaryActiveCompressorUnknownLayout,
)
from hydro_gas.weymouth_si import WeymouthSiPipeParameters


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorNumericalEvaluation:
    """État physique et résidu numérique produits pour un même vecteur."""

    evaluation_ref: str
    unknown_state: StationaryActiveCompressorUnknownState
    physical_evaluation: StationaryActiveCompressorEvaluation
    residual_vector: StationaryActiveCompressorNumericalVector

    def __post_init__(self) -> None:
        if not self.evaluation_ref.strip():
            raise ValueError("La provenance de l'évaluation numérique mixte est obligatoire.")


def evaluate_stationary_active_compressor_numerical_vector(
    problem: StationaryActiveCompressorProblem,
    layout: StationaryActiveCompressorUnknownLayout,
    template_state: StationaryActiveCompressorUnknownState,
    vector: StationaryActiveCompressorNumericalVector,
    scale: StationaryActiveCompressorNumericalScale,
    pipe_parameters: tuple[WeymouthSiPipeParameters, ...],
    *,
    evaluation_ref: str,
) -> StationaryActiveCompressorNumericalEvaluation:
    """Applique le chemin canonique ``x -> état -> physique -> r(x)``."""

    normalized_ref = evaluation_ref.strip()
    if not normalized_ref:
        raise ValueError("La provenance de l'évaluation numérique mixte est obligatoire.")

    state = decode_stationary_active_compressor_numerical_vector(
        layout,
        template_state,
        vector,
        scale,
        state_ref=f"{normalized_ref}#decoded-state",
    )
    physical = evaluate_stationary_active_compressor_unknown_state(
        problem,
        layout,
        state,
        pipe_parameters,
        evaluation_ref=f"{normalized_ref}#physical",
    )
    residual_vector = encode_stationary_active_compressor_residuals(
        layout,
        physical,
        scale,
        source_ref=f"{normalized_ref}#residual-vector",
    )
    return StationaryActiveCompressorNumericalEvaluation(
        evaluation_ref=normalized_ref,
        unknown_state=state,
        physical_evaluation=physical,
        residual_vector=residual_vector,
    )


__all__ = [
    "StationaryActiveCompressorNumericalEvaluation",
    "evaluate_stationary_active_compressor_numerical_vector",
]
