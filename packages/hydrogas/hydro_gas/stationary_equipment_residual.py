"""Assemblage P6-D des résidus stationnaires conduites + compresseurs.

Cette couche relie la topologie réseau, les pressions nodales et les cartes
compresseur déjà versionnées. Elle ne résout pas le réseau mixte et n'ajoute
aucun seuil de conformité : elle expose uniquement les résidus physiques bruts
nécessaires à une future résolution couplée qualifiée.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.compressor_limits import CompressorOperatingEnvelope
from hydro_gas.compressor_map import CompressorMap
from hydro_gas.network_balance import GasBoundaryMassFlow, GasPipeMassFlow, SteadyGasNetwork
from hydro_gas.stationary_compressor_constraint import (
    StationaryCompressorMapConstraint,
    StationaryCompressorState,
    evaluate_stationary_compressor_map_constraint,
)
from hydro_gas.stationary_equipment_balance import (
    GasCompressorMassFlow,
    GasNetworkEquipmentMassBalanceResult,
    SteadyGasCompressorEdge,
    assess_stationary_equipment_mass_balance,
)
from hydro_gas.weymouth_network_residual import GasNodePressure


@dataclass(frozen=True, slots=True)
class StationaryCompressorOperatingInput:
    """Commande candidate minimale nécessaire à l'évaluation d'une carte."""

    compressor_id: str
    mass_flow_kg_s: float
    speed_rpm: float
    source_ref: str

    def __post_init__(self) -> None:
        if not self.compressor_id.strip() or not self.source_ref.strip():
            raise ValueError("Le compresseur et la provenance de son état sont obligatoires.")
        values = (self.mass_flow_kg_s, self.speed_rpm)
        if any(not math.isfinite(value) or value <= 0.0 for value in values):
            raise ValueError(
                "Le débit et la vitesse d'un compresseur actif doivent être finis et positifs."
            )


@dataclass(frozen=True, slots=True)
class StationaryCompressorMapBinding:
    """Association explicite d'un compresseur à sa carte et son enveloppe."""

    compressor_id: str
    compressor_map: CompressorMap
    source_ref: str
    envelope: CompressorOperatingEnvelope | None = None

    def __post_init__(self) -> None:
        if not self.compressor_id.strip() or not self.source_ref.strip():
            raise ValueError("Le binding carte-compresseur et sa provenance sont obligatoires.")


@dataclass(frozen=True, slots=True)
class StationaryEquipmentResidualAssembly:
    """Résidus bruts d'un état candidat de réseau gaz avec compresseurs."""

    mass_balance: GasNetworkEquipmentMassBalanceResult
    compressor_constraints: tuple[StationaryCompressorMapConstraint, ...]
    node_pressure_source_refs: tuple[str, ...]
    operating_input_source_refs: tuple[str, ...]
    map_binding_source_refs: tuple[str, ...]


def _unique_ids(values: tuple[str, ...], *, label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"Les identifiants {label} doivent être uniques.")


def assemble_stationary_equipment_residuals(
    network: SteadyGasNetwork,
    pipe_flows: tuple[GasPipeMassFlow, ...],
    compressor_edges: tuple[SteadyGasCompressorEdge, ...],
    compressor_inputs: tuple[StationaryCompressorOperatingInput, ...],
    node_pressures: tuple[GasNodePressure, ...],
    map_bindings: tuple[StationaryCompressorMapBinding, ...],
    boundary_flows: tuple[GasBoundaryMassFlow, ...] = (),
) -> StationaryEquipmentResidualAssembly:
    """Assemble conservation de masse et résidus de cartes sans les résoudre."""

    node_ids = tuple(node.node_id for node in network.nodes)
    pressure_ids = tuple(item.node_id for item in node_pressures)
    _unique_ids(pressure_ids, label="de pression nodale")
    if set(pressure_ids) != set(node_ids):
        raise ValueError(
            "Les pressions doivent couvrir exactement tous les noeuds du réseau mixte."
        )

    edge_ids = tuple(edge.compressor_id for edge in compressor_edges)
    input_ids = tuple(item.compressor_id for item in compressor_inputs)
    binding_ids = tuple(item.compressor_id for item in map_bindings)
    _unique_ids(edge_ids, label="de compresseurs")
    _unique_ids(input_ids, label="d'états compresseurs")
    _unique_ids(binding_ids, label="de bindings cartes")
    if set(input_ids) != set(edge_ids):
        raise ValueError(
            "Les états compresseurs doivent couvrir exactement les compresseurs du réseau."
        )
    if set(binding_ids) != set(edge_ids):
        raise ValueError(
            "Les bindings de cartes doivent couvrir exactement les compresseurs du réseau."
        )

    pressure_by_node = {item.node_id: item for item in node_pressures}
    input_by_id = {item.compressor_id: item for item in compressor_inputs}
    binding_by_id = {item.compressor_id: item for item in map_bindings}
    compressor_flows = tuple(
        GasCompressorMassFlow(
            compressor_id=edge.compressor_id,
            mass_flow_kg_s=input_by_id[edge.compressor_id].mass_flow_kg_s,
            source_ref=input_by_id[edge.compressor_id].source_ref,
        )
        for edge in compressor_edges
    )
    mass_balance = assess_stationary_equipment_mass_balance(
        network,
        pipe_flows,
        compressor_edges,
        compressor_flows,
        boundary_flows,
    )

    constraints = []
    for edge in compressor_edges:
        operating_input = input_by_id[edge.compressor_id]
        binding = binding_by_id[edge.compressor_id]
        inlet = pressure_by_node[edge.from_node_id]
        outlet = pressure_by_node[edge.to_node_id]
        state = StationaryCompressorState(
            compressor_id=edge.compressor_id,
            inlet_pressure_pa=inlet.pressure_pa,
            outlet_pressure_pa=outlet.pressure_pa,
            mass_flow_kg_s=operating_input.mass_flow_kg_s,
            speed_rpm=operating_input.speed_rpm,
            source_ref=operating_input.source_ref,
        )
        constraints.append(
            evaluate_stationary_compressor_map_constraint(
                binding.compressor_map,
                state,
                envelope=binding.envelope,
            )
        )

    return StationaryEquipmentResidualAssembly(
        mass_balance=mass_balance,
        compressor_constraints=tuple(constraints),
        node_pressure_source_refs=tuple(item.source_ref for item in node_pressures),
        operating_input_source_refs=tuple(item.source_ref for item in compressor_inputs),
        map_binding_source_refs=tuple(item.source_ref for item in map_bindings),
    )


__all__ = [
    "StationaryCompressorMapBinding",
    "StationaryCompressorOperatingInput",
    "StationaryEquipmentResidualAssembly",
    "assemble_stationary_equipment_residuals",
]
