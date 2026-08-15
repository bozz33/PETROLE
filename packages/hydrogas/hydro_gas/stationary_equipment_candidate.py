"""Matérialisation physique d'un problème stationnaire gaz avec compresseurs actifs.

Cette couche transforme uniquement les inconnues physiques du layout mixte en
un état candidat complet. Elle ne crée aucun vecteur numérique, n'applique
aucune échelle et n'appelle aucun solveur.
"""

from __future__ import annotations

from dataclasses import dataclass

from hydro_gas.network_balance import GasBoundaryMassFlow, GasPipeMassFlow
from hydro_gas.stationary_equipment_balance import GasCompressorMassFlow
from hydro_gas.stationary_equipment_problem import (
    StationaryActiveCompressorProblem,
    StationaryActiveCompressorUnknownLayout,
    build_stationary_active_compressor_unknown_layout,
)
from hydro_gas.stationary_equipment_residual import StationaryCompressorOperatingInput
from hydro_gas.weymouth_network_residual import GasNodePressure


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorUnknownState:
    """Valeurs physiques des inconnues du problème mixte."""

    state_ref: str
    unknown_node_pressures: tuple[GasNodePressure, ...]
    pipe_flows: tuple[GasPipeMassFlow, ...]
    compressor_flows: tuple[GasCompressorMassFlow, ...]
    slack_external_flows: tuple[GasBoundaryMassFlow, ...]

    def __post_init__(self) -> None:
        if not self.state_ref.strip():
            raise ValueError("La provenance de l'état inconnu mixte est obligatoire.")

        groups = (
            (tuple(item.node_id for item in self.unknown_node_pressures), "pressions inconnues"),
            (tuple(item.pipe_id for item in self.pipe_flows), "débits de conduites"),
            (tuple(item.compressor_id for item in self.compressor_flows), "débits compresseurs"),
            (tuple(item.boundary_id for item in self.slack_external_flows), "frontières slack"),
            (tuple(item.node_id for item in self.slack_external_flows), "noeuds slack"),
        )
        for identifiers, label in groups:
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"Les identifiants des {label} doivent être uniques.")


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorCandidateState:
    """État physique complet du réseau mixte prêt à être évalué."""

    candidate_ref: str
    node_pressures: tuple[GasNodePressure, ...]
    pipe_flows: tuple[GasPipeMassFlow, ...]
    compressor_inputs: tuple[StationaryCompressorOperatingInput, ...]
    boundary_flows: tuple[GasBoundaryMassFlow, ...]

    def __post_init__(self) -> None:
        if not self.candidate_ref.strip():
            raise ValueError("La provenance de l'état candidat mixte est obligatoire.")


def materialize_stationary_active_compressor_candidate(
    problem: StationaryActiveCompressorProblem,
    layout: StationaryActiveCompressorUnknownLayout,
    unknown_state: StationaryActiveCompressorUnknownState,
) -> StationaryActiveCompressorCandidateState:
    """Reconstruit l'état physique complet sans déduire de valeur absente."""

    expected_layout = build_stationary_active_compressor_unknown_layout(problem)
    if layout != expected_layout:
        raise ValueError("Le layout mixte ne correspond pas au problème stationnaire fourni.")

    pressure_by_node = {item.node_id: item for item in unknown_state.unknown_node_pressures}
    if set(pressure_by_node) != set(layout.unknown_pressure_node_ids):
        raise ValueError("Les pressions inconnues doivent couvrir exactement le layout mixte.")

    flow_by_pipe = {item.pipe_id: item for item in unknown_state.pipe_flows}
    if set(flow_by_pipe) != set(layout.pipe_flow_ids):
        raise ValueError("Les débits de conduite doivent couvrir exactement le layout mixte.")

    compressor_flow_by_id = {item.compressor_id: item for item in unknown_state.compressor_flows}
    if set(compressor_flow_by_id) != set(layout.compressor_flow_ids):
        raise ValueError("Les débits compresseurs doivent couvrir exactement le layout mixte.")

    slack_flow_by_node = {item.node_id: item for item in unknown_state.slack_external_flows}
    if set(slack_flow_by_node) != set(layout.slack_external_flow_node_ids):
        raise ValueError("Les débits externes slack doivent couvrir exactement les noeuds slack.")

    specified_boundary_ids = {item.boundary_id for item in problem.specified_boundary_flows}
    slack_boundary_ids = {item.boundary_id for item in unknown_state.slack_external_flows}
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
    speed_by_compressor = {item.compressor_id: item for item in problem.compressor_speed_controls}

    node_pressures = tuple(
        fixed_pressure_by_node[node.node_id]
        if node.node_id in fixed_pressure_by_node
        else pressure_by_node[node.node_id]
        for node in problem.network.nodes
    )
    pipe_flows = tuple(flow_by_pipe[pipe.pipe_id] for pipe in problem.network.pipes)
    compressor_inputs = tuple(
        StationaryCompressorOperatingInput(
            compressor_id=edge.compressor_id,
            mass_flow_kg_s=compressor_flow_by_id[edge.compressor_id].mass_flow_kg_s,
            speed_rpm=speed_by_compressor[edge.compressor_id].speed_rpm,
            source_ref=compressor_flow_by_id[edge.compressor_id].source_ref,
        )
        for edge in problem.compressor_edges
    )
    ordered_slack_flows = tuple(
        slack_flow_by_node[node_id] for node_id in layout.slack_external_flow_node_ids
    )

    return StationaryActiveCompressorCandidateState(
        candidate_ref=unknown_state.state_ref,
        node_pressures=node_pressures,
        pipe_flows=pipe_flows,
        compressor_inputs=compressor_inputs,
        boundary_flows=problem.specified_boundary_flows + ordered_slack_flows,
    )


__all__ = [
    "StationaryActiveCompressorCandidateState",
    "StationaryActiveCompressorUnknownState",
    "materialize_stationary_active_compressor_candidate",
]
