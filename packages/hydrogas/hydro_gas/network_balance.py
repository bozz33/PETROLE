"""Bilan massique stationnaire d'un réseau gaz sans loi de conduite implicite.

D07 impose la conservation de masse aux noeuds et précise que le futur solveur
gaz doit être compressible. Cette brique traite uniquement la topologie et le
bilan massique à partir de débits massiques déjà calculés ou mesurés. Elle ne
choisit aucune corrélation de perte de charge et ne constitue donc pas le
solveur P6-B complet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SteadyGasNode:
    """Noeud gaz stationnaire avec provenance obligatoire."""

    node_id: str
    source_ref: str

    def __post_init__(self) -> None:
        if not self.node_id.strip() or not self.source_ref.strip():
            raise ValueError("Le noeud gaz et sa provenance sont obligatoires.")


@dataclass(frozen=True, slots=True)
class SteadyGasPipe:
    """Arc orienté du réseau ; le débit positif suit ``from_node -> to_node``."""

    pipe_id: str
    from_node_id: str
    to_node_id: str
    source_ref: str

    def __post_init__(self) -> None:
        values = (self.pipe_id, self.from_node_id, self.to_node_id, self.source_ref)
        if any(not value.strip() for value in values):
            raise ValueError("La conduite, ses extrémités et sa provenance sont obligatoires.")
        if self.from_node_id == self.to_node_id:
            raise ValueError("Une conduite ne peut pas relier un noeud à lui-même.")


@dataclass(frozen=True, slots=True)
class SteadyGasNetwork:
    """Topologie minimale vérifiée indépendamment de toute équation de conduite."""

    nodes: tuple[SteadyGasNode, ...]
    pipes: tuple[SteadyGasPipe, ...]

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("Le réseau gaz doit contenir au moins un noeud.")

        node_ids = tuple(node.node_id for node in self.nodes)
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Les identifiants de noeuds gaz doivent être uniques.")

        pipe_ids = tuple(pipe.pipe_id for pipe in self.pipes)
        if len(pipe_ids) != len(set(pipe_ids)):
            raise ValueError("Les identifiants de conduites gaz doivent être uniques.")

        known_nodes = set(node_ids)
        for pipe in self.pipes:
            if pipe.from_node_id not in known_nodes or pipe.to_node_id not in known_nodes:
                raise ValueError(
                    "Chaque conduite doit référencer deux noeuds présents dans le réseau."
                )


@dataclass(frozen=True, slots=True)
class GasPipeMassFlow:
    """Débit massique signé associé à une conduite et à sa provenance."""

    pipe_id: str
    mass_flow_kg_s: float
    source_ref: str

    def __post_init__(self) -> None:
        if not self.pipe_id.strip() or not self.source_ref.strip():
            raise ValueError("Le débit de conduite et sa provenance sont obligatoires.")
        if not math.isfinite(self.mass_flow_kg_s):
            raise ValueError("Le débit massique doit être fini.")


@dataclass(frozen=True, slots=True)
class GasBoundaryMassFlow:
    """Injection (>0) ou soutirage (<0) externe appliqué à un noeud."""

    boundary_id: str
    node_id: str
    mass_flow_kg_s: float
    source_ref: str

    def __post_init__(self) -> None:
        values = (self.boundary_id, self.node_id, self.source_ref)
        if any(not value.strip() for value in values):
            raise ValueError("La frontière gaz, son noeud et sa provenance sont obligatoires.")
        if not math.isfinite(self.mass_flow_kg_s):
            raise ValueError("Le débit massique de frontière doit être fini.")


@dataclass(frozen=True, slots=True)
class GasNodeMassBalance:
    node_id: str
    incoming_mass_flow_kg_s: float
    outgoing_mass_flow_kg_s: float
    external_mass_flow_kg_s: float
    residual_kg_s: float


@dataclass(frozen=True, slots=True)
class GasNetworkMassBalanceResult:
    """Résidus factuels ; aucune tolérance PASS/FAIL n'est codée en dur."""

    node_balances: tuple[GasNodeMassBalance, ...]
    global_residual_kg_s: float
    max_abs_node_residual_kg_s: float
    pipe_flow_source_refs: tuple[str, ...]
    boundary_source_refs: tuple[str, ...]


def assess_stationary_mass_balance(
    network: SteadyGasNetwork,
    pipe_flows: tuple[GasPipeMassFlow, ...],
    boundary_flows: tuple[GasBoundaryMassFlow, ...] = (),
) -> GasNetworkMassBalanceResult:
    """Évalue ``Σm_entrant - Σm_sortant + m_externe`` à chaque noeud.

    Un débit de conduite négatif est accepté et signifie que l'écoulement réel
    est opposé à l'orientation documentaire de la conduite. Le résultat expose
    les résidus bruts sans décider d'une conformité industrielle.
    """

    expected_pipe_ids = {pipe.pipe_id for pipe in network.pipes}
    supplied_pipe_ids = tuple(flow.pipe_id for flow in pipe_flows)
    if len(supplied_pipe_ids) != len(set(supplied_pipe_ids)):
        raise ValueError("Un seul débit massique doit être fourni par conduite.")
    if set(supplied_pipe_ids) != expected_pipe_ids:
        raise ValueError("Les débits fournis doivent couvrir exactement les conduites du réseau.")

    boundary_ids = tuple(flow.boundary_id for flow in boundary_flows)
    if len(boundary_ids) != len(set(boundary_ids)):
        raise ValueError("Les identifiants de frontières gaz doivent être uniques.")

    known_node_ids = {node.node_id for node in network.nodes}
    if any(flow.node_id not in known_node_ids for flow in boundary_flows):
        raise ValueError("Chaque frontière gaz doit référencer un noeud présent dans le réseau.")

    flows_by_pipe = {flow.pipe_id: flow for flow in pipe_flows}
    incoming = {node_id: 0.0 for node_id in known_node_ids}
    outgoing = {node_id: 0.0 for node_id in known_node_ids}

    for pipe in network.pipes:
        mass_flow = flows_by_pipe[pipe.pipe_id].mass_flow_kg_s
        if mass_flow >= 0.0:
            outgoing[pipe.from_node_id] += mass_flow
            incoming[pipe.to_node_id] += mass_flow
        else:
            reverse_flow = -mass_flow
            incoming[pipe.from_node_id] += reverse_flow
            outgoing[pipe.to_node_id] += reverse_flow

    external = {node_id: 0.0 for node_id in known_node_ids}
    for boundary in boundary_flows:
        external[boundary.node_id] += boundary.mass_flow_kg_s

    balances = tuple(
        GasNodeMassBalance(
            node_id=node.node_id,
            incoming_mass_flow_kg_s=incoming[node.node_id],
            outgoing_mass_flow_kg_s=outgoing[node.node_id],
            external_mass_flow_kg_s=external[node.node_id],
            residual_kg_s=(
                incoming[node.node_id] - outgoing[node.node_id] + external[node.node_id]
            ),
        )
        for node in network.nodes
    )
    residuals = tuple(balance.residual_kg_s for balance in balances)

    return GasNetworkMassBalanceResult(
        node_balances=balances,
        global_residual_kg_s=math.fsum(residuals),
        max_abs_node_residual_kg_s=max((abs(value) for value in residuals), default=0.0),
        pipe_flow_source_refs=tuple(flow.source_ref for flow in pipe_flows),
        boundary_source_refs=tuple(flow.source_ref for flow in boundary_flows),
    )


__all__ = [
    "GasBoundaryMassFlow",
    "GasNetworkMassBalanceResult",
    "GasNodeMassBalance",
    "GasPipeMassFlow",
    "SteadyGasNetwork",
    "SteadyGasNode",
    "SteadyGasPipe",
    "assess_stationary_mass_balance",
]
