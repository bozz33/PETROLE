"""Coordonnées numériques du problème stationnaire conduites + compresseurs.

Le domaine physique reste exprimé en Pa et kg/s. Cette couche encode les
pressions inconnues en p² adimensionné et conserve des échelles explicites pour
les variables et chacune des trois familles de résidus. Aucun solveur ni seuil
de convergence n'est activé ici.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.network_balance import GasBoundaryMassFlow, GasPipeMassFlow
from hydro_gas.stationary_equipment_balance import GasCompressorMassFlow
from hydro_gas.stationary_equipment_candidate import StationaryActiveCompressorUnknownState
from hydro_gas.stationary_equipment_evaluation import StationaryActiveCompressorEvaluation
from hydro_gas.stationary_equipment_problem import StationaryActiveCompressorUnknownLayout
from hydro_gas.weymouth_network_residual import GasNodePressure


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorNumericalScale:
    """Échelles explicites des variables et résidus du problème mixte."""

    pressure_squared_scale_pa2: float
    mass_flow_scale_kg_s: float
    mass_residual_scale_kg_s: float
    pipe_residual_scale_pa2: float
    compressor_residual_scale_pa: float
    source_ref: str

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("La provenance des échelles numériques mixtes est obligatoire.")
        values = (
            self.pressure_squared_scale_pa2,
            self.mass_flow_scale_kg_s,
            self.mass_residual_scale_kg_s,
            self.pipe_residual_scale_pa2,
            self.compressor_residual_scale_pa,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in values):
            raise ValueError(
                "Toutes les échelles numériques mixtes doivent être finies et strictement positives."
            )


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorNumericalVector:
    """Vecteur adimensionné ordonné selon le layout mixte."""

    values: tuple[float, ...]
    source_ref: str

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("La provenance du vecteur numérique mixte est obligatoire.")
        if any(not math.isfinite(value) for value in self.values):
            raise ValueError(
                "Le vecteur numérique mixte doit contenir uniquement des valeurs finies."
            )


def _validate_state_layout(
    layout: StationaryActiveCompressorUnknownLayout,
    state: StationaryActiveCompressorUnknownState,
) -> None:
    pressure_ids = {item.node_id for item in state.unknown_node_pressures}
    if pressure_ids != set(layout.unknown_pressure_node_ids):
        raise ValueError("Les pressions de l'état doivent couvrir exactement le layout mixte.")

    pipe_ids = {item.pipe_id for item in state.pipe_flows}
    if pipe_ids != set(layout.pipe_flow_ids):
        raise ValueError("Les débits de conduite doivent couvrir exactement le layout mixte.")

    compressor_ids = {item.compressor_id for item in state.compressor_flows}
    if compressor_ids != set(layout.compressor_flow_ids):
        raise ValueError("Les débits compresseurs doivent couvrir exactement le layout mixte.")

    slack_node_ids = {item.node_id for item in state.slack_external_flows}
    if slack_node_ids != set(layout.slack_external_flow_node_ids):
        raise ValueError("Les débits slack doivent couvrir exactement le layout mixte.")


def encode_stationary_active_compressor_unknown_state(
    layout: StationaryActiveCompressorUnknownLayout,
    state: StationaryActiveCompressorUnknownState,
    scale: StationaryActiveCompressorNumericalScale,
) -> StationaryActiveCompressorNumericalVector:
    """Encode ``p², f_pipe, f_compressor, f_slack`` dans l'ordre du layout."""

    _validate_state_layout(layout, state)
    pressure_by_node = {item.node_id: item for item in state.unknown_node_pressures}
    pipe_flow_by_id = {item.pipe_id: item for item in state.pipe_flows}
    compressor_flow_by_id = {item.compressor_id: item for item in state.compressor_flows}
    slack_flow_by_node = {item.node_id: item for item in state.slack_external_flows}

    pressure_values = tuple(
        pressure_by_node[node_id].pressure_pa ** 2 / scale.pressure_squared_scale_pa2
        for node_id in layout.unknown_pressure_node_ids
    )
    pipe_values = tuple(
        pipe_flow_by_id[pipe_id].mass_flow_kg_s / scale.mass_flow_scale_kg_s
        for pipe_id in layout.pipe_flow_ids
    )
    compressor_values = tuple(
        compressor_flow_by_id[compressor_id].mass_flow_kg_s / scale.mass_flow_scale_kg_s
        for compressor_id in layout.compressor_flow_ids
    )
    slack_values = tuple(
        slack_flow_by_node[node_id].mass_flow_kg_s / scale.mass_flow_scale_kg_s
        for node_id in layout.slack_external_flow_node_ids
    )
    return StationaryActiveCompressorNumericalVector(
        values=pressure_values + pipe_values + compressor_values + slack_values,
        source_ref=state.state_ref,
    )


def decode_stationary_active_compressor_numerical_vector(
    layout: StationaryActiveCompressorUnknownLayout,
    template_state: StationaryActiveCompressorUnknownState,
    vector: StationaryActiveCompressorNumericalVector,
    scale: StationaryActiveCompressorNumericalScale,
    *,
    state_ref: str,
) -> StationaryActiveCompressorUnknownState:
    """Décode un vecteur en état physique sans modifier les identités du template."""

    if not state_ref.strip():
        raise ValueError("La provenance de l'état mixte décodé est obligatoire.")
    _validate_state_layout(layout, template_state)
    if len(vector.values) != layout.unknown_count:
        raise ValueError("La taille du vecteur doit correspondre exactement au layout mixte.")

    pressure_count = len(layout.unknown_pressure_node_ids)
    pipe_count = len(layout.pipe_flow_ids)
    compressor_count = len(layout.compressor_flow_ids)
    pressure_end = pressure_count
    pipe_end = pressure_end + pipe_count
    compressor_end = pipe_end + compressor_count

    pressure_coordinates = vector.values[:pressure_end]
    pipe_coordinates = vector.values[pressure_end:pipe_end]
    compressor_coordinates = vector.values[pipe_end:compressor_end]
    slack_coordinates = vector.values[compressor_end:]
    if any(value < 0.0 for value in pressure_coordinates):
        raise ValueError("Une coordonnée p² du problème mixte ne peut pas être négative.")
    if any(value <= 0.0 for value in compressor_coordinates):
        raise ValueError("Un débit numérique de compresseur actif doit être strictement positif.")

    template_slack_by_node = {item.node_id: item for item in template_state.slack_external_flows}

    pressures = tuple(
        GasNodePressure(
            node_id=node_id,
            pressure_pa=math.sqrt(coordinate * scale.pressure_squared_scale_pa2),
            source_ref=f"{vector.source_ref}#pressure-squared/{node_id}",
        )
        for node_id, coordinate in zip(
            layout.unknown_pressure_node_ids,
            pressure_coordinates,
            strict=True,
        )
    )
    pipe_flows = tuple(
        GasPipeMassFlow(
            pipe_id=pipe_id,
            mass_flow_kg_s=coordinate * scale.mass_flow_scale_kg_s,
            source_ref=f"{vector.source_ref}#pipe-flow/{pipe_id}",
        )
        for pipe_id, coordinate in zip(layout.pipe_flow_ids, pipe_coordinates, strict=True)
    )
    compressor_flows = tuple(
        GasCompressorMassFlow(
            compressor_id=compressor_id,
            mass_flow_kg_s=coordinate * scale.mass_flow_scale_kg_s,
            source_ref=f"{vector.source_ref}#compressor-flow/{compressor_id}",
        )
        for compressor_id, coordinate in zip(
            layout.compressor_flow_ids,
            compressor_coordinates,
            strict=True,
        )
    )
    slack_flows = tuple(
        GasBoundaryMassFlow(
            boundary_id=template_slack_by_node[node_id].boundary_id,
            node_id=node_id,
            mass_flow_kg_s=coordinate * scale.mass_flow_scale_kg_s,
            source_ref=f"{vector.source_ref}#slack-flow/{node_id}",
        )
        for node_id, coordinate in zip(
            layout.slack_external_flow_node_ids,
            slack_coordinates,
            strict=True,
        )
    )

    return StationaryActiveCompressorUnknownState(
        state_ref=state_ref,
        unknown_node_pressures=pressures,
        pipe_flows=pipe_flows,
        compressor_flows=compressor_flows,
        slack_external_flows=slack_flows,
    )


def encode_stationary_active_compressor_residuals(
    layout: StationaryActiveCompressorUnknownLayout,
    evaluation: StationaryActiveCompressorEvaluation,
    scale: StationaryActiveCompressorNumericalScale,
    *,
    source_ref: str,
) -> StationaryActiveCompressorNumericalVector:
    """Encode masse, Weymouth et cartes compresseurs en un seul vecteur explicite."""

    if not source_ref.strip():
        raise ValueError("La provenance du vecteur de résidus mixtes est obligatoire.")

    mass_by_node = {
        item.node_id: item.residual_kg_s
        for item in evaluation.equipment_residuals.mass_balance.node_balances
    }
    pipe_by_id = {item.pipe_id: item.residual_pa2 for item in evaluation.pipe_residuals}
    compressor_by_id = {
        item.compressor_id: item.pressure_ratio_residual_pa
        for item in evaluation.equipment_residuals.compressor_constraints
    }
    if set(mass_by_node) != set(layout.mass_equation_node_ids):
        raise ValueError("Les résidus massiques doivent couvrir exactement le layout mixte.")
    if set(pipe_by_id) != set(layout.pipe_equation_ids):
        raise ValueError("Les résidus Weymouth doivent couvrir exactement le layout mixte.")
    if set(compressor_by_id) != set(layout.compressor_equation_ids):
        raise ValueError("Les résidus compresseurs doivent couvrir exactement le layout mixte.")

    mass_values = tuple(
        mass_by_node[node_id] / scale.mass_residual_scale_kg_s
        for node_id in layout.mass_equation_node_ids
    )
    pipe_values = tuple(
        pipe_by_id[pipe_id] / scale.pipe_residual_scale_pa2 for pipe_id in layout.pipe_equation_ids
    )
    compressor_values = tuple(
        compressor_by_id[compressor_id] / scale.compressor_residual_scale_pa
        for compressor_id in layout.compressor_equation_ids
    )
    return StationaryActiveCompressorNumericalVector(
        values=mass_values + pipe_values + compressor_values,
        source_ref=source_ref,
    )


__all__ = [
    "StationaryActiveCompressorNumericalScale",
    "StationaryActiveCompressorNumericalVector",
    "decode_stationary_active_compressor_numerical_vector",
    "encode_stationary_active_compressor_residuals",
    "encode_stationary_active_compressor_unknown_state",
]
