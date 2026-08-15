"""Contrat structurel P6-D/P6-E d'un réseau stationnaire mixte.

Le problème couvert ici contient des conduites Weymouth et des compresseurs
actifs dont la vitesse est imposée. Cette couche ne résout aucune inconnue :
elle vérifie uniquement les frontières, la connectivité et le comptage des
équations nécessaires à un futur solveur couplé.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.network_balance import GasBoundaryMassFlow, SteadyGasNetwork
from hydro_gas.stationary_equipment_balance import SteadyGasCompressorEdge
from hydro_gas.stationary_equipment_residual import StationaryCompressorMapBinding
from hydro_gas.stationary_problem import GasPressureSlack


@dataclass(frozen=True, slots=True)
class StationaryCompressorSpeedControl:
    """Vitesse active imposée à un compresseur du problème mixte."""

    compressor_id: str
    speed_rpm: float
    source_ref: str

    def __post_init__(self) -> None:
        if not self.compressor_id.strip() or not self.source_ref.strip():
            raise ValueError(
                "Le contrôle de vitesse compresseur et sa provenance sont obligatoires."
            )
        if not math.isfinite(self.speed_rpm) or self.speed_rpm <= 0.0:
            raise ValueError(
                "La vitesse compresseur imposée doit être finie et strictement positive."
            )


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorProblem:
    """Réseau mixte avec compresseurs actifs à vitesse imposée."""

    problem_ref: str
    network: SteadyGasNetwork
    compressor_edges: tuple[SteadyGasCompressorEdge, ...]
    pressure_slacks: tuple[GasPressureSlack, ...]
    compressor_speed_controls: tuple[StationaryCompressorSpeedControl, ...]
    map_bindings: tuple[StationaryCompressorMapBinding, ...]
    specified_boundary_flows: tuple[GasBoundaryMassFlow, ...] = ()

    def __post_init__(self) -> None:
        if not self.problem_ref.strip():
            raise ValueError("La provenance du problème réseau mixte est obligatoire.")


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorUnknownLayout:
    """Ordre déterministe des inconnues et équations du problème mixte."""

    connected_components: tuple[tuple[str, ...], ...]
    fixed_pressure_node_ids: tuple[str, ...]
    unknown_pressure_node_ids: tuple[str, ...]
    pipe_flow_ids: tuple[str, ...]
    compressor_flow_ids: tuple[str, ...]
    slack_external_flow_node_ids: tuple[str, ...]
    mass_equation_node_ids: tuple[str, ...]
    pipe_equation_ids: tuple[str, ...]
    compressor_equation_ids: tuple[str, ...]

    @property
    def unknown_count(self) -> int:
        return (
            len(self.unknown_pressure_node_ids)
            + len(self.pipe_flow_ids)
            + len(self.compressor_flow_ids)
            + len(self.slack_external_flow_node_ids)
        )

    @property
    def equation_count(self) -> int:
        return (
            len(self.mass_equation_node_ids)
            + len(self.pipe_equation_ids)
            + len(self.compressor_equation_ids)
        )

    @property
    def structurally_square(self) -> bool:
        return self.unknown_count == self.equation_count


def _require_unique(values: tuple[str, ...], *, label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"Les identifiants {label} doivent être uniques.")


def _combined_components(
    network: SteadyGasNetwork,
    compressor_edges: tuple[SteadyGasCompressorEdge, ...],
) -> tuple[tuple[str, ...], ...]:
    node_order = tuple(node.node_id for node in network.nodes)
    known_nodes = set(node_order)
    adjacency = {node_id: set() for node_id in node_order}
    for pipe in network.pipes:
        adjacency[pipe.from_node_id].add(pipe.to_node_id)
        adjacency[pipe.to_node_id].add(pipe.from_node_id)
    for edge in compressor_edges:
        if edge.from_node_id not in known_nodes or edge.to_node_id not in known_nodes:
            raise ValueError("Chaque compresseur doit relier deux noeuds présents dans le réseau.")
        adjacency[edge.from_node_id].add(edge.to_node_id)
        adjacency[edge.to_node_id].add(edge.from_node_id)

    visited: set[str] = set()
    components: list[tuple[str, ...]] = []
    for start in node_order:
        if start in visited:
            continue
        stack = [start]
        component_nodes: set[str] = set()
        while stack:
            node_id = stack.pop()
            if node_id in visited:
                continue
            visited.add(node_id)
            component_nodes.add(node_id)
            stack.extend(adjacency[node_id] - visited)
        components.append(tuple(node_id for node_id in node_order if node_id in component_nodes))
    return tuple(components)


def build_stationary_active_compressor_unknown_layout(
    problem: StationaryActiveCompressorProblem,
) -> StationaryActiveCompressorUnknownLayout:
    """Valide le problème et construit son système carré déterministe."""

    node_ids = tuple(node.node_id for node in problem.network.nodes)
    known_nodes = set(node_ids)
    pipe_ids = tuple(pipe.pipe_id for pipe in problem.network.pipes)
    compressor_ids = tuple(edge.compressor_id for edge in problem.compressor_edges)
    _require_unique(compressor_ids, label="de compresseurs")

    speed_ids = tuple(item.compressor_id for item in problem.compressor_speed_controls)
    binding_ids = tuple(item.compressor_id for item in problem.map_bindings)
    _require_unique(speed_ids, label="de contrôles de vitesse")
    _require_unique(binding_ids, label="de bindings cartes")
    if set(speed_ids) != set(compressor_ids):
        raise ValueError(
            "Les contrôles de vitesse doivent couvrir exactement les compresseurs actifs."
        )
    if set(binding_ids) != set(compressor_ids):
        raise ValueError(
            "Les bindings de cartes doivent couvrir exactement les compresseurs actifs."
        )

    boundary_ids = tuple(item.boundary_id for item in problem.specified_boundary_flows)
    _require_unique(boundary_ids, label="de frontières gaz")
    if any(item.node_id not in known_nodes for item in problem.specified_boundary_flows):
        raise ValueError("Chaque frontière gaz doit référencer un noeud présent dans le réseau.")

    slack_node_ids = tuple(item.node_id for item in problem.pressure_slacks)
    _require_unique(slack_node_ids, label="de noeuds slack")
    if any(node_id not in known_nodes for node_id in slack_node_ids):
        raise ValueError(
            "Chaque slack de pression doit référencer un noeud présent dans le réseau."
        )

    components = _combined_components(problem.network, problem.compressor_edges)
    for component in components:
        slacks = tuple(node_id for node_id in slack_node_ids if node_id in component)
        if len(slacks) != 1:
            raise ValueError(
                "Chaque composante connexe du réseau mixte doit posséder exactement un slack de pression."
            )

    fixed = tuple(node_id for node_id in node_ids if node_id in set(slack_node_ids))
    unknown_pressures = tuple(node_id for node_id in node_ids if node_id not in set(slack_node_ids))
    layout = StationaryActiveCompressorUnknownLayout(
        connected_components=components,
        fixed_pressure_node_ids=fixed,
        unknown_pressure_node_ids=unknown_pressures,
        pipe_flow_ids=pipe_ids,
        compressor_flow_ids=compressor_ids,
        slack_external_flow_node_ids=fixed,
        mass_equation_node_ids=node_ids,
        pipe_equation_ids=pipe_ids,
        compressor_equation_ids=compressor_ids,
    )
    if not layout.structurally_square:
        raise ValueError(
            "Le problème réseau mixte doit produire un système structurellement carré."
        )
    return layout


__all__ = [
    "StationaryActiveCompressorProblem",
    "StationaryActiveCompressorUnknownLayout",
    "StationaryCompressorSpeedControl",
    "build_stationary_active_compressor_unknown_layout",
]
