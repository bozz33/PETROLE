"""Bilan massique P6-D séparant conduites et compresseurs stationnaires.

Les compresseurs transportent de la masse entre deux noeuds mais ne doivent pas
être déguisés en conduites : leurs débits sont donc comptabilisés séparément des
débits de conduites dans chaque diagnostic nodal. Cette brique ne contient
aucune équation de rapport de pression, de puissance ou de température.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.network_balance import (
    GasBoundaryMassFlow,
    GasPipeMassFlow,
    SteadyGasNetwork,
)


@dataclass(frozen=True, slots=True)
class SteadyGasCompressorEdge:
    """Connexion orientée d'un compresseur entre deux noeuds du réseau."""

    compressor_id: str
    from_node_id: str
    to_node_id: str
    source_ref: str

    def __post_init__(self) -> None:
        values = (self.compressor_id, self.from_node_id, self.to_node_id, self.source_ref)
        if any(not value.strip() for value in values):
            raise ValueError(
                "Le compresseur, ses extrémités et sa provenance sont obligatoires."
            )
        if self.from_node_id == self.to_node_id:
            raise ValueError("Un compresseur ne peut pas relier un noeud à lui-même.")


@dataclass(frozen=True, slots=True)
class GasCompressorMassFlow:
    """Débit massique transporté dans le sens documentaire du compresseur."""

    compressor_id: str
    mass_flow_kg_s: float
    source_ref: str

    def __post_init__(self) -> None:
        if not self.compressor_id.strip() or not self.source_ref.strip():
            raise ValueError("Le débit compresseur et sa provenance sont obligatoires.")
        if not math.isfinite(self.mass_flow_kg_s) or self.mass_flow_kg_s < 0.0:
            raise ValueError(
                "Le débit massique compresseur doit être fini et positif ou nul dans son sens actif."
            )


@dataclass(frozen=True, slots=True)
class GasNodeEquipmentMassBalance:
    """Contribution massique détaillée par famille d'équipement."""

    node_id: str
    incoming_pipe_mass_flow_kg_s: float
    outgoing_pipe_mass_flow_kg_s: float
    incoming_compressor_mass_flow_kg_s: float
    outgoing_compressor_mass_flow_kg_s: float
    external_mass_flow_kg_s: float
    residual_kg_s: float


@dataclass(frozen=True, slots=True)
class GasNetworkEquipmentMassBalanceResult:
    """Résidus bruts d'un réseau mixte, sans tolérance de conformité."""

    node_balances: tuple[GasNodeEquipmentMassBalance, ...]
    global_residual_kg_s: float
    max_abs_node_residual_kg_s: float
    pipe_flow_source_refs: tuple[str, ...]
    compressor_flow_source_refs: tuple[str, ...]
    boundary_source_refs: tuple[str, ...]


def assess_stationary_equipment_mass_balance(
    network: SteadyGasNetwork,
    pipe_flows: tuple[GasPipeMassFlow, ...],
    compressor_edges: tuple[SteadyGasCompressorEdge, ...],
    compressor_flows: tuple[GasCompressorMassFlow, ...],
    boundary_flows: tuple[GasBoundaryMassFlow, ...] = (),
) -> GasNetworkEquipmentMassBalanceResult:
    """Évalue la conservation de masse avec contributions séparées.

    Les conduites conservent leur convention de débit signé. Le débit d'un
    compresseur est non négatif et suit ``from_node -> to_node`` ; les modes
    bypass, arrêt ou flux inverse doivent être représentés explicitement par la
    configuration station/réseau plutôt que par un débit compresseur négatif.
    """

    known_node_ids = {node.node_id for node in network.nodes}

    expected_pipe_ids = {pipe.pipe_id for pipe in network.pipes}
    supplied_pipe_ids = tuple(flow.pipe_id for flow in pipe_flows)
    if len(supplied_pipe_ids) != len(set(supplied_pipe_ids)):
        raise ValueError("Un seul débit massique doit être fourni par conduite.")
    if set(supplied_pipe_ids) != expected_pipe_ids:
        raise ValueError("Les débits fournis doivent couvrir exactement les conduites du réseau.")

    compressor_ids = tuple(edge.compressor_id for edge in compressor_edges)
    if len(compressor_ids) != len(set(compressor_ids)):
        raise ValueError("Les identifiants de compresseurs stationnaires doivent être uniques.")
    for edge in compressor_edges:
        if edge.from_node_id not in known_node_ids or edge.to_node_id not in known_node_ids:
            raise ValueError(
                "Chaque compresseur doit référencer deux noeuds présents dans le réseau."
            )

    supplied_compressor_ids = tuple(flow.compressor_id for flow in compressor_flows)
    if len(supplied_compressor_ids) != len(set(supplied_compressor_ids)):
        raise ValueError("Un seul débit massique doit être fourni par compresseur.")
    if set(supplied_compressor_ids) != set(compressor_ids):
        raise ValueError(
            "Les débits compresseurs doivent couvrir exactement les compresseurs du réseau mixte."
        )

    boundary_ids = tuple(flow.boundary_id for flow in boundary_flows)
    if len(boundary_ids) != len(set(boundary_ids)):
        raise ValueError("Les identifiants de frontières gaz doivent être uniques.")
    if any(flow.node_id not in known_node_ids for flow in boundary_flows):
        raise ValueError("Chaque frontière gaz doit référencer un noeud présent dans le réseau.")

    pipe_flow_by_id = {flow.pipe_id: flow.mass_flow_kg_s for flow in pipe_flows}
    compressor_flow_by_id = {
        flow.compressor_id: flow.mass_flow_kg_s for flow in compressor_flows
    }

    incoming_pipe = dict.fromkeys(known_node_ids, 0.0)
    outgoing_pipe = dict.fromkeys(known_node_ids, 0.0)
    for pipe in network.pipes:
        mass_flow = pipe_flow_by_id[pipe.pipe_id]
        if mass_flow >= 0.0:
            outgoing_pipe[pipe.from_node_id] += mass_flow
            incoming_pipe[pipe.to_node_id] += mass_flow
        else:
            reverse_flow = -mass_flow
            incoming_pipe[pipe.from_node_id] += reverse_flow
            outgoing_pipe[pipe.to_node_id] += reverse_flow

    incoming_compressor = dict.fromkeys(known_node_ids, 0.0)
    outgoing_compressor = dict.fromkeys(known_node_ids, 0.0)
    for edge in compressor_edges:
        mass_flow = compressor_flow_by_id[edge.compressor_id]
        outgoing_compressor[edge.from_node_id] += mass_flow
        incoming_compressor[edge.to_node_id] += mass_flow

    external = dict.fromkeys(known_node_ids, 0.0)
    for boundary in boundary_flows:
        external[boundary.node_id] += boundary.mass_flow_kg_s

    balances = tuple(
        GasNodeEquipmentMassBalance(
            node_id=node.node_id,
            incoming_pipe_mass_flow_kg_s=incoming_pipe[node.node_id],
            outgoing_pipe_mass_flow_kg_s=outgoing_pipe[node.node_id],
            incoming_compressor_mass_flow_kg_s=incoming_compressor[node.node_id],
            outgoing_compressor_mass_flow_kg_s=outgoing_compressor[node.node_id],
            external_mass_flow_kg_s=external[node.node_id],
            residual_kg_s=(
                incoming_pipe[node.node_id]
                - outgoing_pipe[node.node_id]
                + incoming_compressor[node.node_id]
                - outgoing_compressor[node.node_id]
                + external[node.node_id]
            ),
        )
        for node in network.nodes
    )
    residuals = tuple(balance.residual_kg_s for balance in balances)
    return GasNetworkEquipmentMassBalanceResult(
        node_balances=balances,
        global_residual_kg_s=math.fsum(residuals),
        max_abs_node_residual_kg_s=max((abs(value) for value in residuals), default=0.0),
        pipe_flow_source_refs=tuple(flow.source_ref for flow in pipe_flows),
        compressor_flow_source_refs=tuple(flow.source_ref for flow in compressor_flows),
        boundary_source_refs=tuple(flow.source_ref for flow in boundary_flows),
    )


__all__ = [
    "GasCompressorMassFlow",
    "GasNetworkEquipmentMassBalanceResult",
    "GasNodeEquipmentMassBalance",
    "SteadyGasCompressorEdge",
    "assess_stationary_equipment_mass_balance",
]
