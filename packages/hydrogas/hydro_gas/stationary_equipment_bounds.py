"""Bornes numériques dérivées des domaines publiés du problème gaz mixte.

Aucune borne de débit compresseur n'est inventée : elles proviennent du domaine
de la carte à la vitesse imposée, intersecté avec l'enveloppe fournisseur quand
elle est disponible. Les autres familles ne reçoivent ici que les bornes
structurelles déjà justifiées par leur représentation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.compressor_limits import compressor_envelope_flow_limits_at_speed
from hydro_gas.compressor_map import compressor_map_flow_domain_at_speed
from hydro_gas.stationary_equipment_numerics import StationaryActiveCompressorNumericalScale
from hydro_gas.stationary_equipment_problem import (
    StationaryActiveCompressorProblem,
    StationaryActiveCompressorUnknownLayout,
    build_stationary_active_compressor_unknown_layout,
)


@dataclass(frozen=True, slots=True)
class StationaryCompressorFlowBound:
    """Intervalle physique de débit d'un compresseur actif."""

    compressor_id: str
    speed_rpm: float
    minimum_mass_flow_kg_s: float
    maximum_mass_flow_kg_s: float
    map_source_ref: str
    map_version: str
    envelope_source_ref: str | None
    envelope_version: str | None

    def __post_init__(self) -> None:
        required = (self.compressor_id, self.map_source_ref, self.map_version)
        if any(not value.strip() for value in required):
            raise ValueError("La borne compresseur et sa provenance carte sont obligatoires.")
        values = (
            self.speed_rpm,
            self.minimum_mass_flow_kg_s,
            self.maximum_mass_flow_kg_s,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in values):
            raise ValueError("Vitesse et bornes de débit compresseur doivent être finies et positives.")
        if self.minimum_mass_flow_kg_s >= self.maximum_mass_flow_kg_s:
            raise ValueError("La borne compresseur doit définir un intervalle strictement non vide.")
        if (self.envelope_source_ref is None) != (self.envelope_version is None):
            raise ValueError("Source et version d'enveloppe doivent être fournies ensemble.")


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorNumericalBounds:
    """Bornes numériques ordonnées selon le layout mixte."""

    lower_values: tuple[float, ...]
    upper_values: tuple[float, ...]
    compressor_flow_bounds: tuple[StationaryCompressorFlowBound, ...]
    source_ref: str

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("La provenance des bornes numériques mixtes est obligatoire.")
        if len(self.lower_values) != len(self.upper_values):
            raise ValueError("Les vecteurs de bornes inférieures et supérieures doivent avoir même taille.")
        if any(math.isnan(value) for value in self.lower_values + self.upper_values):
            raise ValueError("Les bornes numériques ne peuvent pas contenir NaN.")
        if any(lower >= upper for lower, upper in zip(self.lower_values, self.upper_values, strict=True)):
            raise ValueError("Chaque borne inférieure doit être strictement inférieure à sa borne supérieure.")


def build_stationary_active_compressor_numerical_bounds(
    problem: StationaryActiveCompressorProblem,
    layout: StationaryActiveCompressorUnknownLayout,
    scale: StationaryActiveCompressorNumericalScale,
    *,
    source_ref: str,
) -> StationaryActiveCompressorNumericalBounds:
    """Construit les bornes du vecteur sans extrapolation ni marge ajoutée."""

    normalized_ref = source_ref.strip()
    if not normalized_ref:
        raise ValueError("La provenance des bornes numériques mixtes est obligatoire.")
    expected_layout = build_stationary_active_compressor_unknown_layout(problem)
    if layout != expected_layout:
        raise ValueError("Le layout fourni ne correspond pas au problème mixte.")

    speed_by_id = {item.compressor_id: item for item in problem.compressor_speed_controls}
    binding_by_id = {item.compressor_id: item for item in problem.map_bindings}
    physical_bounds: list[StationaryCompressorFlowBound] = []
    for compressor_id in layout.compressor_flow_ids:
        speed = speed_by_id[compressor_id].speed_rpm
        binding = binding_by_id[compressor_id]
        map_domain = compressor_map_flow_domain_at_speed(
            binding.compressor_map,
            speed_rpm=speed,
        )
        minimum_flow = map_domain.minimum_mass_flow_kg_s
        maximum_flow = map_domain.maximum_mass_flow_kg_s
        envelope_source_ref: str | None = None
        envelope_version: str | None = None
        if binding.envelope is not None:
            envelope_limits = compressor_envelope_flow_limits_at_speed(
                binding.envelope,
                speed_rpm=speed,
            )
            minimum_flow = max(minimum_flow, envelope_limits.minimum_mass_flow_kg_s)
            maximum_flow = min(maximum_flow, envelope_limits.maximum_mass_flow_kg_s)
            envelope_source_ref = envelope_limits.source_ref
            envelope_version = envelope_limits.envelope_version
        if minimum_flow >= maximum_flow:
            raise ValueError(
                f"Le compresseur {compressor_id} n'a aucun intervalle de débit actif commun carte/enveloppe."
            )
        physical_bounds.append(
            StationaryCompressorFlowBound(
                compressor_id=compressor_id,
                speed_rpm=speed,
                minimum_mass_flow_kg_s=minimum_flow,
                maximum_mass_flow_kg_s=maximum_flow,
                map_source_ref=map_domain.source_ref,
                map_version=map_domain.map_version,
                envelope_source_ref=envelope_source_ref,
                envelope_version=envelope_version,
            )
        )

    pressure_count = len(layout.unknown_pressure_node_ids)
    pipe_count = len(layout.pipe_flow_ids)
    slack_count = len(layout.slack_external_flow_node_ids)
    compressor_lower = tuple(
        bound.minimum_mass_flow_kg_s / scale.mass_flow_scale_kg_s for bound in physical_bounds
    )
    compressor_upper = tuple(
        bound.maximum_mass_flow_kg_s / scale.mass_flow_scale_kg_s for bound in physical_bounds
    )
    lower_values = (
        (0.0,) * pressure_count
        + (-math.inf,) * pipe_count
        + compressor_lower
        + (-math.inf,) * slack_count
    )
    upper_values = (
        (math.inf,) * pressure_count
        + (math.inf,) * pipe_count
        + compressor_upper
        + (math.inf,) * slack_count
    )
    if len(lower_values) != layout.unknown_count:
        raise RuntimeError("Les bornes construites ne couvrent pas exactement le layout mixte.")
    return StationaryActiveCompressorNumericalBounds(
        lower_values=lower_values,
        upper_values=upper_values,
        compressor_flow_bounds=tuple(physical_bounds),
        source_ref=normalized_ref,
    )


__all__ = [
    "StationaryActiveCompressorNumericalBounds",
    "StationaryCompressorFlowBound",
    "build_stationary_active_compressor_numerical_bounds",
]
