"""Fonction résiduelle numérique pure P6-B pour le futur solveur Weymouth.

Cette couche compose exclusivement les adapters déjà séparés : vecteur
adimensionné -> état physique -> évaluation canonique -> résidu adimensionné.
Elle ne contient aucun algorithme de résolution, critère d'arrêt ou décision de
convergence.
"""

from __future__ import annotations

from dataclasses import dataclass

from hydro_gas.stationary_candidate import StationaryWeymouthUnknownState
from hydro_gas.stationary_evaluation import (
    StationaryWeymouthEvaluation,
    evaluate_stationary_weymouth_unknown_state,
)
from hydro_gas.stationary_numerics import (
    StationaryWeymouthNumericalScale,
    StationaryWeymouthNumericalVector,
    decode_stationary_weymouth_numerical_vector,
    encode_stationary_weymouth_residuals,
)
from hydro_gas.stationary_problem import (
    StationaryWeymouthProblem,
    StationaryWeymouthUnknownLayout,
)
from hydro_gas.weymouth_si import WeymouthSiPipeParameters


@dataclass(frozen=True, slots=True)
class StationaryWeymouthNumericalEvaluation:
    """Trace complète d'une évaluation numérique, sans statut de convergence."""

    evaluation_ref: str
    input_vector: StationaryWeymouthNumericalVector
    decoded_state: StationaryWeymouthUnknownState
    physical_evaluation: StationaryWeymouthEvaluation
    residual_vector: StationaryWeymouthNumericalVector
    scale_source_ref: str


def evaluate_stationary_weymouth_numerical_vector(
    problem: StationaryWeymouthProblem,
    layout: StationaryWeymouthUnknownLayout,
    template_state: StationaryWeymouthUnknownState,
    input_vector: StationaryWeymouthNumericalVector,
    scale: StationaryWeymouthNumericalScale,
    pipe_parameters: tuple[WeymouthSiPipeParameters, ...],
    *,
    evaluation_ref: str,
) -> StationaryWeymouthNumericalEvaluation:
    """Calcule ``r(x)`` sans convergence implicite.

    Le résultat conserve simultanément le vecteur d'entrée, l'état physique
    décodé, les résidus physiques et le vecteur de résidus adimensionné. Une
    méthode numérique future pourra appeler cette fonction sans dupliquer la
    physique PETROLE.
    """

    normalized_ref = evaluation_ref.strip()
    if not normalized_ref:
        raise ValueError("La provenance de l'évaluation numérique est obligatoire.")

    decoded_state = decode_stationary_weymouth_numerical_vector(
        layout,
        template_state,
        input_vector,
        scale,
        state_ref=f"{normalized_ref}#decoded-state",
    )
    physical_evaluation = evaluate_stationary_weymouth_unknown_state(
        problem,
        layout,
        decoded_state,
        pipe_parameters,
    )
    residual_vector = encode_stationary_weymouth_residuals(
        layout,
        physical_evaluation.residuals,
        scale,
        source_ref=f"{normalized_ref}#residual-vector",
    )
    return StationaryWeymouthNumericalEvaluation(
        evaluation_ref=normalized_ref,
        input_vector=input_vector,
        decoded_state=decoded_state,
        physical_evaluation=physical_evaluation,
        residual_vector=residual_vector,
        scale_source_ref=scale.source_ref,
    )


__all__ = [
    "StationaryWeymouthNumericalEvaluation",
    "evaluate_stationary_weymouth_numerical_vector",
]
