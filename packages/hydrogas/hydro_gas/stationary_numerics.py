"""Coordonnées numériques P6-B pour le futur solveur Weymouth stationnaire.

Le domaine physique PETROLE reste en pression absolue Pa et débit kg/s. Cette
couche fournit une représentation adimensionnée de solveur avec pression au
carré, cohérente avec la formulation Weymouth de référence. Toutes les échelles
sont explicites et sourcées : aucune valeur par défaut, tolérance ou solveur
n'est introduit ici.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.network_balance import GasBoundaryMassFlow, GasPipeMassFlow
from hydro_gas.stationary_candidate import StationaryWeymouthUnknownState
from hydro_gas.stationary_problem import StationaryWeymouthUnknownLayout
from hydro_gas.weymouth_network_residual import GasNodePressure, WeymouthNetworkResidualAssembly


@dataclass(frozen=True, slots=True)
class StationaryWeymouthNumericalScale:
    """Échelles explicites des variables et résidus du problème numérique."""

    pressure_squared_scale_pa2: float
    mass_flow_scale_kg_s: float
    mass_residual_scale_kg_s: float
    pipe_residual_scale_pa2: float
    source_ref: str

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("La provenance des échelles numériques est obligatoire.")
        values = (
            self.pressure_squared_scale_pa2,
            self.mass_flow_scale_kg_s,
            self.mass_residual_scale_kg_s,
            self.pipe_residual_scale_pa2,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in values):
            raise ValueError(
                "Toutes les échelles numériques doivent être finies et strictement positives."
            )


@dataclass(frozen=True, slots=True)
class StationaryWeymouthNumericalVector:
    """Vecteur adimensionné ordonné selon ``StationaryWeymouthUnknownLayout``."""

    values: tuple[float, ...]
    source_ref: str

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("La provenance du vecteur numérique est obligatoire.")
        if any(not math.isfinite(value) for value in self.values):
            raise ValueError("Le vecteur numérique doit contenir uniquement des valeurs finies.")


def _validate_state_layout(
    layout: StationaryWeymouthUnknownLayout,
    state: StationaryWeymouthUnknownState,
) -> None:
    pressure_ids = {item.node_id for item in state.unknown_node_pressures}
    if pressure_ids != set(layout.unknown_pressure_node_ids):
        raise ValueError("Les pressions de l'état doivent couvrir exactement le layout numérique.")

    pipe_ids = {item.pipe_id for item in state.pipe_flows}
    if pipe_ids != set(layout.pipe_flow_ids):
        raise ValueError("Les débits de l'état doivent couvrir exactement le layout numérique.")

    slack_node_ids = {item.node_id for item in state.slack_external_flows}
    if slack_node_ids != set(layout.slack_external_flow_node_ids):
        raise ValueError("Les débits slack de l'état doivent couvrir exactement le layout numérique.")


def encode_stationary_weymouth_unknown_state(
    layout: StationaryWeymouthUnknownLayout,
    state: StationaryWeymouthUnknownState,
    scale: StationaryWeymouthNumericalScale,
) -> StationaryWeymouthNumericalVector:
    """Encode l'état physique en coordonnées adimensionnées ``p², f, f_slack``."""

    _validate_state_layout(layout, state)
    pressure_by_node = {item.node_id: item for item in state.unknown_node_pressures}
    flow_by_pipe = {item.pipe_id: item for item in state.pipe_flows}
    slack_flow_by_node = {item.node_id: item for item in state.slack_external_flows}

    pressure_values = tuple(
        pressure_by_node[node_id].pressure_pa**2 / scale.pressure_squared_scale_pa2
        for node_id in layout.unknown_pressure_node_ids
    )
    flow_values = tuple(
        flow_by_pipe[pipe_id].mass_flow_kg_s / scale.mass_flow_scale_kg_s
        for pipe_id in layout.pipe_flow_ids
    )
    slack_values = tuple(
        slack_flow_by_node[node_id].mass_flow_kg_s / scale.mass_flow_scale_kg_s
        for node_id in layout.slack_external_flow_node_ids
    )
    return StationaryWeymouthNumericalVector(
        values=pressure_values + flow_values + slack_values,
        source_ref=state.state_ref,
    )


def decode_stationary_weymouth_numerical_vector(
    layout: StationaryWeymouthUnknownLayout,
    template_state: StationaryWeymouthUnknownState,
    vector: StationaryWeymouthNumericalVector,
    scale: StationaryWeymouthNumericalScale,
    *,
    state_ref: str,
) -> StationaryWeymouthUnknownState:
    """Décode un vecteur vers les unités physiques en conservant les identités du template.

    Le template fournit uniquement les identifiants de frontières et la
    structure de provenance. Les valeurs numériques du résultat viennent toutes
    du vecteur. Une coordonnée de pression au carré négative est hors domaine et
    est refusée au lieu d'être corrigée silencieusement.
    """

    if not state_ref.strip():
        raise ValueError("La provenance de l'état décodé est obligatoire.")
    _validate_state_layout(layout, template_state)
    if len(vector.values) != layout.unknown_count:
        raise ValueError("La taille du vecteur numérique doit correspondre exactement au layout.")

    pressure_count = len(layout.unknown_pressure_node_ids)
    pipe_count = len(layout.pipe_flow_ids)
    pressure_coordinates = vector.values[:pressure_count]
    flow_coordinates = vector.values[pressure_count : pressure_count + pipe_count]
    slack_coordinates = vector.values[pressure_count + pipe_count :]
    if any(value < 0.0 for value in pressure_coordinates):
        raise ValueError("Une coordonnée de pression au carré ne peut pas être négative.")

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
    flows = tuple(
        GasPipeMassFlow(
            pipe_id=pipe_id,
            mass_flow_kg_s=coordinate * scale.mass_flow_scale_kg_s,
            source_ref=f"{vector.source_ref}#pipe-flow/{pipe_id}",
        )
        for pipe_id, coordinate in zip(layout.pipe_flow_ids, flow_coordinates, strict=True)
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

    return StationaryWeymouthUnknownState(
        state_ref=state_ref,
        unknown_node_pressures=pressures,
        pipe_flows=flows,
        slack_external_flows=slack_flows,
    )


def encode_stationary_weymouth_residuals(
    layout: StationaryWeymouthUnknownLayout,
    residuals: WeymouthNetworkResidualAssembly,
    scale: StationaryWeymouthNumericalScale,
    *,
    source_ref: str,
) -> StationaryWeymouthNumericalVector:
    """Encode les résidus physiques séparés en un vecteur adimensionné explicite."""

    if not source_ref.strip():
        raise ValueError("La provenance du vecteur de résidus est obligatoire.")
    mass_by_node = {
        item.node_id: item.residual_kg_s for item in residuals.mass_balance.node_balances
    }
    pipe_by_id = {item.pipe_id: item.residual_pa2 for item in residuals.pipe_residuals}
    if set(mass_by_node) != set(layout.mass_equation_node_ids):
        raise ValueError("Les résidus massiques doivent couvrir exactement les équations nodales.")
    if set(pipe_by_id) != set(layout.pipe_equation_ids):
        raise ValueError("Les résidus de conduite doivent couvrir exactement les équations du layout.")

    mass_values = tuple(
        mass_by_node[node_id] / scale.mass_residual_scale_kg_s
        for node_id in layout.mass_equation_node_ids
    )
    pipe_values = tuple(
        pipe_by_id[pipe_id] / scale.pipe_residual_scale_pa2
        for pipe_id in layout.pipe_equation_ids
    )
    return StationaryWeymouthNumericalVector(
        values=mass_values + pipe_values,
        source_ref=source_ref,
    )


__all__ = [
    "StationaryWeymouthNumericalScale",
    "StationaryWeymouthNumericalVector",
    "decode_stationary_weymouth_numerical_vector",
    "encode_stationary_weymouth_residuals",
    "encode_stationary_weymouth_unknown_state",
]
