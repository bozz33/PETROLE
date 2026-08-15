"""Évaluation physique canonique d'un réseau stationnaire gaz avec compresseurs.

Cette couche matérialise les inconnues puis évalue, sans solveur ni tolérance,
les trois familles de résidus nécessaires au problème couplé : conservation de
masse, lois Weymouth des conduites et contraintes de cartes compresseurs.
"""

from __future__ import annotations

from dataclasses import dataclass

from hydro_gas.stationary_equipment_candidate import (
    StationaryActiveCompressorCandidateState,
    StationaryActiveCompressorUnknownState,
    materialize_stationary_active_compressor_candidate,
)
from hydro_gas.stationary_equipment_problem import (
    StationaryActiveCompressorProblem,
    StationaryActiveCompressorUnknownLayout,
)
from hydro_gas.stationary_equipment_residual import (
    StationaryEquipmentResidualAssembly,
    assemble_stationary_equipment_residuals,
)
from hydro_gas.weymouth_network_residual import (
    WeymouthNetworkCandidateState,
    evaluate_weymouth_pipe_residuals,
)
from hydro_gas.weymouth_si import WeymouthSiPipeParameters, WeymouthSiResidual


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorEvaluation:
    """Résultat physique brut du problème mixte, sans décision de convergence."""

    evaluation_ref: str
    candidate: StationaryActiveCompressorCandidateState
    equipment_residuals: StationaryEquipmentResidualAssembly
    pipe_residuals: tuple[WeymouthSiResidual, ...]

    def __post_init__(self) -> None:
        if not self.evaluation_ref.strip():
            raise ValueError("La provenance de l'évaluation mixte est obligatoire.")


def evaluate_stationary_active_compressor_unknown_state(
    problem: StationaryActiveCompressorProblem,
    layout: StationaryActiveCompressorUnknownLayout,
    unknown_state: StationaryActiveCompressorUnknownState,
    pipe_parameters: tuple[WeymouthSiPipeParameters, ...],
    *,
    evaluation_ref: str,
) -> StationaryActiveCompressorEvaluation:
    """Évalue l'état inconnu mixte par le chemin physique canonique."""

    normalized_ref = evaluation_ref.strip()
    if not normalized_ref:
        raise ValueError("La provenance de l'évaluation mixte est obligatoire.")

    candidate = materialize_stationary_active_compressor_candidate(
        problem,
        layout,
        unknown_state,
    )
    equipment_residuals = assemble_stationary_equipment_residuals(
        problem.network,
        candidate.pipe_flows,
        problem.compressor_edges,
        candidate.compressor_inputs,
        candidate.node_pressures,
        problem.map_bindings,
        candidate.boundary_flows,
    )
    weymouth_candidate = WeymouthNetworkCandidateState(
        candidate_ref=candidate.candidate_ref,
        node_pressures=candidate.node_pressures,
        pipe_flows=candidate.pipe_flows,
        boundary_flows=candidate.boundary_flows,
    )
    pipe_residuals = evaluate_weymouth_pipe_residuals(
        problem.network,
        weymouth_candidate,
        pipe_parameters,
    )

    return StationaryActiveCompressorEvaluation(
        evaluation_ref=normalized_ref,
        candidate=candidate,
        equipment_residuals=equipment_residuals,
        pipe_residuals=pipe_residuals,
    )


__all__ = [
    "StationaryActiveCompressorEvaluation",
    "evaluate_stationary_active_compressor_unknown_state",
]
