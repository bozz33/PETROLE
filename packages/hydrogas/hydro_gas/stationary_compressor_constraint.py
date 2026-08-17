"""Contrainte stationnaire P6-D issue d'une carte compresseur fournisseur.

Cette brique relie un état pression/débit/vitesse à la carte de performance déjà
versionnée. Elle n'introduit ni loi de puissance, ni température de refoulement,
ni marge anti-surge, ni tolérance de validation implicite.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.compressor_limits import (
    CompressorEnvelopeAssessment,
    CompressorOperatingEnvelope,
    assess_compressor_envelope,
)
from hydro_gas.compressor_map import (
    CompressorMap,
    CompressorOperatingPoint,
    interpolate_compressor_map,
)


@dataclass(frozen=True, slots=True)
class StationaryCompressorState:
    """État physique candidat d'un compresseur en régime stationnaire."""

    compressor_id: str
    inlet_pressure_pa: float
    outlet_pressure_pa: float
    mass_flow_kg_s: float
    speed_rpm: float
    source_ref: str

    def __post_init__(self) -> None:
        if not self.compressor_id.strip() or not self.source_ref.strip():
            raise ValueError(
                "L'identifiant compresseur et la provenance de l'état sont obligatoires."
            )
        positive_values = (
            self.inlet_pressure_pa,
            self.outlet_pressure_pa,
            self.mass_flow_kg_s,
            self.speed_rpm,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in positive_values):
            raise ValueError(
                "Pressions, débit massique et vitesse compresseur doivent être finis et positifs."
            )


@dataclass(frozen=True, slots=True)
class StationaryCompressorMapConstraint:
    """Résidu brut du rapport de pression publié par la carte fournisseur."""

    compressor_id: str
    state_source_ref: str
    operating_point: CompressorOperatingPoint
    expected_outlet_pressure_pa: float
    pressure_ratio_residual_pa: float
    envelope_assessment: CompressorEnvelopeAssessment | None


def evaluate_stationary_compressor_map_constraint(
    compressor_map: CompressorMap,
    state: StationaryCompressorState,
    *,
    envelope: CompressorOperatingEnvelope | None = None,
) -> StationaryCompressorMapConstraint:
    """Évalue ``p_out - ratio_carte * p_in`` sans seuil de réussite implicite."""

    operating_point = interpolate_compressor_map(
        compressor_map,
        speed_rpm=state.speed_rpm,
        mass_flow_kg_s=state.mass_flow_kg_s,
    )
    expected_outlet_pressure_pa = operating_point.pressure_ratio * state.inlet_pressure_pa
    residual_pa = state.outlet_pressure_pa - expected_outlet_pressure_pa
    envelope_assessment = (
        None
        if envelope is None
        else assess_compressor_envelope(
            envelope,
            speed_rpm=state.speed_rpm,
            mass_flow_kg_s=state.mass_flow_kg_s,
        )
    )
    return StationaryCompressorMapConstraint(
        compressor_id=state.compressor_id,
        state_source_ref=state.source_ref,
        operating_point=operating_point,
        expected_outlet_pressure_pa=expected_outlet_pressure_pa,
        pressure_ratio_residual_pa=residual_pa,
        envelope_assessment=envelope_assessment,
    )


__all__ = [
    "StationaryCompressorMapConstraint",
    "StationaryCompressorState",
    "evaluate_stationary_compressor_map_constraint",
]
