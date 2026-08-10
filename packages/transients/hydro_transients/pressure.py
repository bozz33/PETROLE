"""Reconstruction de pression à partir de la charge totale définie par D07.

D07 fixe H = z + p/(rho*g) + alpha*v^2/(2g). Cette brique inverse uniquement
cette relation avec des entrées explicites. Elle ne suppose ni altitude,
densité, coefficient cinétique ni propriétés transitoires cachées.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

STANDARD_GRAVITY_M_S2 = 9.80665


@dataclass(frozen=True, slots=True)
class TotalHeadPressureResult:
    """Décomposition utilisée pour reconstruire une pression absolue candidate."""

    total_head_m: float
    elevation_m: float
    kinetic_head_m: float
    static_pressure_head_m: float
    pressure_pa: float
    nonphysical_negative_absolute: bool


def mean_velocity_full_pipe(*, flow_m3_s: float, diameter_m: float) -> float:
    """Applique v = 4Q/(pi*D^2) pour une conduite circulaire pleine."""

    if not math.isfinite(flow_m3_s):
        raise ValueError("Le débit doit être fini.")
    if not math.isfinite(diameter_m) or diameter_m <= 0:
        raise ValueError("Le diamètre doit être fini et strictement positif.")
    return 4.0 * flow_m3_s / (math.pi * diameter_m**2)


def pressure_from_total_head(
    *,
    total_head_m: float,
    elevation_m: float,
    density_kg_m3: float,
    velocity_m_s: float,
    kinetic_correction_alpha: float,
    gravity_m_s2: float = STANDARD_GRAVITY_M_S2,
) -> TotalHeadPressureResult:
    """Inverse la définition de charge totale de D07 sans corriger le résultat.

    Une pression calculée négative en convention absolue est retournée avec un
    drapeau explicite. Le post-traitement ne la rabat pas à zéro : un tel état
    doit être traité par les diagnostics/modèles de cavitation appropriés.
    """

    values = (total_head_m, elevation_m, velocity_m_s, kinetic_correction_alpha)
    if any(not math.isfinite(value) for value in values):
        raise ValueError("H, z, v et alpha doivent être finis.")
    if not math.isfinite(density_kg_m3) or density_kg_m3 <= 0:
        raise ValueError("La densité doit être finie et strictement positive.")
    if not math.isfinite(gravity_m_s2) or gravity_m_s2 <= 0:
        raise ValueError("La gravité doit être finie et strictement positive.")
    if kinetic_correction_alpha <= 0:
        raise ValueError("Le coefficient alpha doit être strictement positif.")

    kinetic_head = kinetic_correction_alpha * velocity_m_s**2 / (2.0 * gravity_m_s2)
    static_pressure_head = total_head_m - elevation_m - kinetic_head
    pressure = density_kg_m3 * gravity_m_s2 * static_pressure_head
    if not math.isfinite(pressure):
        raise ValueError("La reconstruction de pression a produit une valeur non finie.")
    return TotalHeadPressureResult(
        total_head_m=total_head_m,
        elevation_m=elevation_m,
        kinetic_head_m=kinetic_head,
        static_pressure_head_m=static_pressure_head,
        pressure_pa=pressure,
        nonphysical_negative_absolute=pressure < 0,
    )


__all__ = [
    "STANDARD_GRAVITY_M_S2",
    "TotalHeadPressureResult",
    "mean_velocity_full_pipe",
    "pressure_from_total_head",
]
