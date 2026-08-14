"""Matérialisation P6-B d'un état inconnu stationnaire en état candidat complet.

Cette couche relie le contrat structurel ``pressure-slack`` à l'assemblage des
résidus réseau. Elle ne transforme pas les inconnues en vecteur numérique,
n'applique aucune mise à l'échelle et n'appelle aucun solveur.
"""

from __future__ import annotations

from dataclasses import dataclass

from hydro_gas.network_balance import GasBoundaryMassFlow, GasPipeMassFlow
from hydro_gas.stationary_problem import (
    StationaryWeymouthProblem,
    StationaryWeymouthUnknownLayout,
    build_stationary_weymouth_unknown_layout,
)
from hydro_gas.weymouth_network_residual import (
    GasNodePressure,
    WeymouthNetworkCandidateState,
)


@dataclass(frozen=True, slots=True)
class StationaryWeymouthUnknownState:
    """Valeurs physiques des seules inconnues du contrat pressure-slack."""

    state_ref: str
    unknown_node_pressures: tuple[GasNodePressure, ...]
    pipe_flows: tuple[GasPipeMassFlow, ...]
    slack_external_flows: tuple[GasBoundaryMassFlow, ...]

    def __post_init__(self) -> None:
        if not self.state_ref.strip():
            raise ValueError("La provenance de l'état inconnu est obligatoire.")

        pressure_ids = tuple(item.node_id for item in self.unknown_node_pressures)
        if len(pressure_ids) != len(set(pressure_ids)):
            raise ValueError("Une seule pression inconnue peut être fournie par nœud.")

        pipe_ids = tuple(item.pipe_id for item in self.pipe_flows)
        if len(pipe_ids) != len(set(pipe_ids)):
            raise ValueError("Un seul débit inconnu peut être fourni par conduite.")

        slack_boundary_ids = tuple(item.boundary_id for item in self.slack_external_flows)
        if len(slack_boundary_ids) != len(set(slack_boundary_ids)):
            raise ValueError("Les identifiants des débits externes slack doivent être uniques.")

        slack_node_ids = tuple(item.node_id for item in self.slack_external_flows)
        if len(slack_node_ids) != len(set(slack_node_ids)):
            raise ValueError("Un seul débit externe slack peut être fourni par nœud.")


def materialize_stationary_weymouth_candidate(
    problem: StationaryWeymouthProblem,
    layout: StationaryWeymouthUnknownLayout,
    unknown_state: StationaryWeymouthUnknownState,
) -> WeymouthNetworkCandidateState:
    """Construit l'état candidat complet dans l'ordre du réseau.

    Le layout est recalculé depuis le problème afin de refuser un layout périmé
    ou provenant d'un autre réseau. Les identifiants des inconnues doivent
    couvrir exactement le layout. Aucune valeur manquante n'est déduite.
    """

    expected_layout = build_stationary_weymouth_unknown_layout(problem)
    if layout != expected_layout:
        raise ValueError("Le layout des inconnues ne correspond pas au problème stationnaire.")

    pressure_by_node = {item.node_id: item for item in unknown_state.unknown_node_pressures}
    if set(pressure_by_node) != set(layout.unknown_pressure_node_ids):
        raise ValueError("Les pressions inconnues doivent couvrir exactement le layout stationnaire.")

    flow_by_pipe = {item.pipe_id: item for item in unknown_state.pipe_flows}
    if set(flow_by_pipe) != set(layout.pipe_flow_ids):
        raise ValueError("Les débits de conduite doivent couvrir exactement le layout stationnaire.")

    slack_flow_by_node = {item.node_id: item for item in unknown_state.slack_external_flows}
    if set(slack_flow_by_node) != set(layout.slack_external_flow_node_ids):
        raise ValueError("Les débits externes slack doivent couvrir exactement les nœuds slack.")

    specified_boundary_ids = {
        item.boundary_id for item in problem.specified_boundary_flows
    }
    slack_boundary_ids = {
        item.boundary_id for item in unknown_state.slack_external_flows
    }
    if specified_boundary_ids & slack_boundary_ids:
        raise ValueError(
            "Un débit externe slack ne peut pas réutiliser un identifiant de frontière imposée."
        )

    fixed_pressure_by_node = {
        slack.node_id: GasNodePressure(
            node_id=slack.node_id,
            pressure_pa=slack.pressure_pa,
            source_ref=slack.source_ref,
        )
        for slack in problem.pressure_slacks
    }

    node_pressures = tuple(
        fixed_pressure_by_node[node.node_id]
        if node.node_id in fixed_pressure_by_node
        else pressure_by_node[node.node_id]
        for node in problem.network.nodes
    )
    pipe_flows = tuple(flow_by_pipe[pipe.pipe_id] for pipe in problem.network.pipes)
    ordered_slack_flows = tuple(
        slack_flow_by_node[node_id] for node_id in layout.slack_external_flow_node_ids
    )

    return WeymouthNetworkCandidateState(
        candidate_ref=unknown_state.state_ref,
        node_pressures=node_pressures,
        pipe_flows=pipe_flows,
        boundary_flows=problem.specified_boundary_flows + ordered_slack_flows,
    )


__all__ = [
    "StationaryWeymouthUnknownState",
    "materialize_stationary_weymouth_candidate",
]
