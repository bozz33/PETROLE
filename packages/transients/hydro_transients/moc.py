"""Briques déterministes de méthode des caractéristiques (MOC).

Le module implémente uniquement les relations de compatibilité 1D associées
aux équations simplifiées de D07. Il ne constitue pas encore un solveur de
coup de bélier qualifié : cavitation, séparation de colonne, friction
instationnaire et dispositifs de protection nécessitent des modèles et des
benchmarks séparés.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

STANDARD_GRAVITY_M_S2 = 9.80665


@dataclass(frozen=True, slots=True)
class MocPipeGrid:
    """Paramètres d'une conduite MOC avec maillage respectant CFL≈1."""

    diameter_m: float
    wave_speed_m_s: float
    cell_length_m: float
    time_step_s: float
    friction_factor: float = 0.0
    gravity_m_s2: float = STANDARD_GRAVITY_M_S2

    def __post_init__(self) -> None:
        positive = (
            self.diameter_m,
            self.wave_speed_m_s,
            self.cell_length_m,
            self.time_step_s,
            self.gravity_m_s2,
        )
        if any(not math.isfinite(value) or value <= 0 for value in positive):
            raise ValueError("D, a, Δx, Δt et g doivent être finis et strictement positifs.")
        if not math.isfinite(self.friction_factor) or self.friction_factor < 0:
            raise ValueError("Le facteur de frottement doit être fini et positif ou nul.")
        if not math.isclose(self.courant_number, 1.0, rel_tol=1e-9, abs_tol=1e-12):
            raise ValueError("Ce noyau MOC de référence exige CFL=a·Δt/Δx égal à 1.")

    @property
    def area_m2(self) -> float:
        return math.pi * self.diameter_m**2 / 4.0

    @property
    def courant_number(self) -> float:
        return self.wave_speed_m_s * self.time_step_s / self.cell_length_m

    @property
    def characteristic_coefficient(self) -> float:
        """B = a/(gA), coefficient entre charge H et débit Q."""

        return self.wave_speed_m_s / (self.gravity_m_s2 * self.area_m2)

    @property
    def quasi_steady_friction_coefficient(self) -> float:
        """R = f Δx/(2 g D A²) pour le terme Q|Q| de compatibilité."""

        area = self.area_m2
        return (
            self.friction_factor
            * self.cell_length_m
            / (2.0 * self.gravity_m_s2 * self.diameter_m * area**2)
        )


def _validate_state(head_m: float, flow_m3_s: float) -> None:
    if not math.isfinite(head_m) or not math.isfinite(flow_m3_s):
        raise ValueError("Charge et débit doivent être finis.")


def interior_characteristic_step(
    *,
    left_head_m: float,
    left_flow_m3_s: float,
    right_head_m: float,
    right_flow_m3_s: float,
    grid: MocPipeGrid,
) -> tuple[float, float]:
    """Résout l'intersection C+ / C- d'un nœud intérieur au pas suivant."""

    _validate_state(left_head_m, left_flow_m3_s)
    _validate_state(right_head_m, right_flow_m3_s)
    coefficient = grid.characteristic_coefficient
    friction = grid.quasi_steady_friction_coefficient
    c_plus = (
        left_head_m
        + coefficient * left_flow_m3_s
        - friction * left_flow_m3_s * abs(left_flow_m3_s)
    )
    c_minus = (
        right_head_m
        - coefficient * right_flow_m3_s
        + friction * right_flow_m3_s * abs(right_flow_m3_s)
    )
    head = 0.5 * (c_plus + c_minus)
    flow = (c_plus - c_minus) / (2.0 * coefficient)
    return head, flow


def fixed_head_left_boundary(
    *,
    boundary_head_m: float,
    interior_head_m: float,
    interior_flow_m3_s: float,
    grid: MocPipeGrid,
) -> tuple[float, float]:
    """Condition de charge imposée à l'amont utilisant la caractéristique C-."""

    _validate_state(boundary_head_m, 0.0)
    _validate_state(interior_head_m, interior_flow_m3_s)
    coefficient = grid.characteristic_coefficient
    friction = grid.quasi_steady_friction_coefficient
    c_minus = (
        interior_head_m
        - coefficient * interior_flow_m3_s
        + friction * interior_flow_m3_s * abs(interior_flow_m3_s)
    )
    flow = (boundary_head_m - c_minus) / coefficient
    return boundary_head_m, flow


def fixed_head_right_boundary(
    *,
    boundary_head_m: float,
    interior_head_m: float,
    interior_flow_m3_s: float,
    grid: MocPipeGrid,
) -> tuple[float, float]:
    """Condition de charge imposée à l'aval utilisant la caractéristique C+."""

    _validate_state(boundary_head_m, 0.0)
    _validate_state(interior_head_m, interior_flow_m3_s)
    coefficient = grid.characteristic_coefficient
    friction = grid.quasi_steady_friction_coefficient
    c_plus = (
        interior_head_m
        + coefficient * interior_flow_m3_s
        - friction * interior_flow_m3_s * abs(interior_flow_m3_s)
    )
    flow = (c_plus - boundary_head_m) / coefficient
    return boundary_head_m, flow


__all__ = [
    "STANDARD_GRAVITY_M_S2",
    "MocPipeGrid",
    "fixed_head_left_boundary",
    "fixed_head_right_boundary",
    "interior_characteristic_step",
]
