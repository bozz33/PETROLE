"""Évaluation canonique P6-B d'un état inconnu stationnaire Weymouth.

Le futur solveur numérique doit passer par cette fonction : elle matérialise
l'état physique complet puis réutilise l'assemblage unique des résidus de masse
et de conduite. Elle ne choisit ni coordonnées numériques, ni échelles, ni
méthode de résolution, ni tolérance de convergence.
"""

from __future__ import annotations

from dataclasses import dataclass

from hydro_gas.stationary_candidate import (
    StationaryWeymouthUnknownState,
    materialize_stationary_weymouth_candidate,
)
from hydro_gas.stationary_problem import (
    StationaryWeymouthProblem,
    StationaryWeymouthUnknownLayout,
)
from hydro_gas.weymouth_network_residual import (
    WeymouthNetworkCandidateState,
    WeymouthNetworkResidualAssembly,
    assemble_weymouth_network_residuals,
)
from hydro_gas.weymouth_si import WeymouthSiPipeParameters


@dataclass(frozen=True, slots=True)
class StationaryWeymouthEvaluation:
    """État candidat matérialisé et résidus physiques issus du même chemin."""

    problem_ref: str
    state_ref: str
    candidate: WeymouthNetworkCandidateState
    residuals: WeymouthNetworkResidualAssembly


def evaluate_stationary_weymouth_unknown_state(
    problem: StationaryWeymouthProblem,
    layout: StationaryWeymouthUnknownLayout,
    unknown_state: StationaryWeymouthUnknownState,
    pipe_parameters: tuple[WeymouthSiPipeParameters, ...],
) -> StationaryWeymouthEvaluation:
    """Évalue un état inconnu sans ajouter de sémantique de solveur.

    Toute erreur de couverture, de layout ou de paramètres reste fail-closed
    dans les couches spécialisées appelées ici. Aucun résidu n'est normalisé ou
    agrégé entre unités différentes.
    """

    candidate = materialize_stationary_weymouth_candidate(
        problem,
        layout,
        unknown_state,
    )
    residuals = assemble_weymouth_network_residuals(
        problem.network,
        candidate,
        pipe_parameters,
    )
    return StationaryWeymouthEvaluation(
        problem_ref=problem.problem_ref,
        state_ref=unknown_state.state_ref,
        candidate=candidate,
        residuals=residuals,
    )


__all__ = [
    "StationaryWeymouthEvaluation",
    "evaluate_stationary_weymouth_unknown_state",
]
