"""Contrat structurel du premier problème stationnaire Weymouth P6-B.

La première classe supportée impose exactement un nœud de pression slack par
composante connexe. Les pressions des autres nœuds, les débits des conduites et
le débit externe de chaque slack sont des inconnues. Toutes les équations de
masse et de conduite sont conservées. Ce module ne choisit aucun solveur,
aucune échelle numérique et aucune tolérance de convergence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.network_balance import GasBoundaryMassFlow, SteadyGasNetwork


@dataclass(frozen=True, slots=True)
class GasPressureSlack:
    """Pression absolue imposée dont le débit externe reste une inconnue."""

    node_id: str
    pressure_pa: float
    source_ref: str

    def __post_init__(self) -> None:
        if not self.node_id.strip() or not self.source_ref.strip():
            raise ValueError("Le nœud slack et sa provenance sont obligatoires.")
        if not math.isfinite(self.pressure_pa) or self.pressure_pa < 0.0:
            raise ValueError("La pression slack doit être finie et positive ou nulle.")


@dataclass(frozen=True, slots=True)
class StationaryWeymouthProblem:
    """Frontières du premier type de problème stationnaire supporté."""

    problem_ref: str
    network: SteadyGasNetwork
    pressure_slacks: tuple[GasPressureSlack, ...]
    specified_boundary_flows: tuple[GasBoundaryMassFlow, ...] = ()

    def __post_init__(self) -> None:
        if not self.problem_ref.strip():
            raise ValueError("La provenance du problème stationnaire est obligatoire.")

        node_ids = {node.node_id for node in self.network.nodes}
        slack_node_ids = tuple(slack.node_id for slack in self.pressure_slacks)
        if len(slack_node_ids) != len(set(slack_node_ids)):
            raise ValueError("Un nœud ne peut porter qu'une seule pression slack.")
        if set(slack_node_ids) - node_ids:
            raise ValueError("Une pression slack référence un nœud absent du réseau.")

        boundary_ids = tuple(boundary.boundary_id for boundary in self.specified_boundary_flows)
        if len(boundary_ids) != len(set(boundary_ids)):
            raise ValueError("Les identifiants de frontières de débit doivent être uniques.")
        if any(boundary.node_id not in node_ids for boundary in self.specified_boundary_flows):
            raise ValueError("Une frontière de débit référence un nœud absent du réseau.")


@dataclass(frozen=True, slots=True)
class StationaryWeymouthUnknownLayout:
    """Ordre déterministe des inconnues et équations, sans valeur initiale."""

    connected_components: tuple[tuple[str, ...], ...]
    fixed_pressure_node_ids: tuple[str, ...]
    unknown_pressure_node_ids: tuple[str, ...]
    pipe_flow_ids: tuple[str, ...]
    slack_external_flow_node_ids: tuple[str, ...]
    mass_equation_node_ids: tuple[str, ...]
    pipe_equation_ids: tuple[str, ...]

    @property
    def unknown_count(self) -> int:
        return (
            len(self.unknown_pressure_node_ids)
            + len(self.pipe_flow_ids)
            + len(self.slack_external_flow_node_ids)
        )

    @property
    def equation_count(self) -> int:
        return len(self.mass_equation_node_ids) + len(self.pipe_equation_ids)

    @property
    def structurally_square(self) -> bool:
        return self.unknown_count == self.equation_count


def _connected_components(network: SteadyGasNetwork) -> tuple[tuple[str, ...], ...]:
    node_order = tuple(node.node_id for node in network.nodes)
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_order}
    for pipe in network.pipes:
        adjacency[pipe.from_node_id].add(pipe.to_node_id)
        adjacency[pipe.to_node_id].add(pipe.from_node_id)

    visited: set[str] = set()
    components: list[tuple[str, ...]] = []
    for root in node_order:
        if root in visited:
            continue
        stack = [root]
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


def build_stationary_weymouth_unknown_layout(
    problem: StationaryWeymouthProblem,
) -> StationaryWeymouthUnknownLayout:
    """Valide l'ancrage topologique et construit l'ordre structurel du système.

    Une et une seule pression slack est exigée dans chaque composante connexe.
    Le débit externe de ce slack reste inconnu ; il sera déterminé plus tard par
    l'équation de masse du nœud. Cette convention évite de supprimer une
    équation de conservation pour rendre artificiellement le système carré.
    """

    components = _connected_components(problem.network)
    slack_by_node = {slack.node_id: slack for slack in problem.pressure_slacks}

    for component in components:
        component_slacks = tuple(node_id for node_id in component if node_id in slack_by_node)
        if len(component_slacks) != 1:
            raise ValueError(
                "Chaque composante connexe doit contenir exactement une pression slack."
            )

    node_order = tuple(node.node_id for node in problem.network.nodes)
    fixed_pressure_node_ids = tuple(
        node_id for node_id in node_order if node_id in slack_by_node
    )
    unknown_pressure_node_ids = tuple(
        node_id for node_id in node_order if node_id not in slack_by_node
    )
    pipe_flow_ids = tuple(pipe.pipe_id for pipe in problem.network.pipes)

    layout = StationaryWeymouthUnknownLayout(
        connected_components=components,
        fixed_pressure_node_ids=fixed_pressure_node_ids,
        unknown_pressure_node_ids=unknown_pressure_node_ids,
        pipe_flow_ids=pipe_flow_ids,
        slack_external_flow_node_ids=fixed_pressure_node_ids,
        mass_equation_node_ids=node_order,
        pipe_equation_ids=pipe_flow_ids,
    )
    if not layout.structurally_square:
        raise RuntimeError("Le contrat pressure-slack doit produire un système structurellement carré.")
    return layout


__all__ = [
    "GasPressureSlack",
    "StationaryWeymouthProblem",
    "StationaryWeymouthUnknownLayout",
    "build_stationary_weymouth_unknown_layout",
]
