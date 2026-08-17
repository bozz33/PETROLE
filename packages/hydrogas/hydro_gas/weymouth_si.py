"""Évaluateur SI du résidu Weymouth pour P6-B.

Cette brique ne résout ni le débit ni les pressions d'un réseau. Elle évalue
uniquement l'équation constitutive sur une observation déjà fournie, avec des
paramètres explicites et sourcés. Aucun seuil de conformité n'est embarqué.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WeymouthSiPipeParameters:
    """Paramètres SI d'une conduite pour l'équation Weymouth stationnaire."""

    pipe_id: str
    length_m: float
    diameter_m: float
    friction_factor: float
    sound_speed_m_s: float
    equation_ref: str
    parameter_source_ref: str

    def __post_init__(self) -> None:
        if not self.pipe_id.strip():
            raise ValueError("L'identifiant de conduite est obligatoire.")
        if not self.equation_ref.strip() or not self.parameter_source_ref.strip():
            raise ValueError("Les références d'équation et de paramètres sont obligatoires.")

        positive = {
            "length_m": self.length_m,
            "diameter_m": self.diameter_m,
            "sound_speed_m_s": self.sound_speed_m_s,
        }
        for field_name, value in positive.items():
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{field_name} doit être fini et strictement positif.")
        if not math.isfinite(self.friction_factor) or self.friction_factor < 0.0:
            raise ValueError("friction_factor doit être fini et positif ou nul.")

    @property
    def area_m2(self) -> float:
        return math.pi * self.diameter_m * self.diameter_m / 4.0

    @property
    def resistance_coefficient_pa2_per_kg_s2(self) -> float:
        """Coefficient de ``f|f|`` dans la forme SI documentée de Weymouth."""

        area_m2 = self.area_m2
        return (
            self.friction_factor
            * self.length_m
            * self.sound_speed_m_s
            * self.sound_speed_m_s
            / (self.diameter_m * area_m2 * area_m2)
        )


@dataclass(frozen=True, slots=True)
class WeymouthSiObservation:
    """Observation SI à vérifier sans la modifier ni la résoudre."""

    pipe_id: str
    from_pressure_pa: float
    to_pressure_pa: float
    mass_flow_kg_s: float
    source_ref: str

    def __post_init__(self) -> None:
        if not self.pipe_id.strip() or not self.source_ref.strip():
            raise ValueError("La conduite et la provenance de l'observation sont obligatoires.")
        pressures = (self.from_pressure_pa, self.to_pressure_pa)
        if any(not math.isfinite(value) or value < 0.0 for value in pressures):
            raise ValueError("Les pressions absolues doivent être finies et positives ou nulles.")
        if not math.isfinite(self.mass_flow_kg_s):
            raise ValueError("Le débit massique doit être fini.")


@dataclass(frozen=True, slots=True)
class WeymouthSiResidual:
    """Diagnostic brut de l'équation, sans statut PASS/FAIL."""

    pipe_id: str
    pressure_squared_difference_pa2: float
    friction_term_pa2: float
    residual_pa2: float
    resistance_coefficient_pa2_per_kg_s2: float
    equation_ref: str
    parameter_source_ref: str
    observation_source_ref: str


def evaluate_weymouth_si_residual(
    parameters: WeymouthSiPipeParameters,
    observation: WeymouthSiObservation,
) -> WeymouthSiResidual:
    """Évalue ``p_to² - p_from² + K f|f|`` en unités SI.

    Un résidu nul satisfait algébriquement l'équation fournie, mais cette
    fonction n'associe aucun seuil numérique et ne conclut jamais à une
    validation industrielle ou scientifique du modèle.
    """

    if parameters.pipe_id != observation.pipe_id:
        raise ValueError("Les paramètres et l'observation doivent viser la même conduite.")

    pressure_squared_difference_pa2 = (
        observation.to_pressure_pa * observation.to_pressure_pa
        - observation.from_pressure_pa * observation.from_pressure_pa
    )
    coefficient = parameters.resistance_coefficient_pa2_per_kg_s2
    friction_term_pa2 = coefficient * observation.mass_flow_kg_s * abs(observation.mass_flow_kg_s)
    residual_pa2 = pressure_squared_difference_pa2 + friction_term_pa2

    return WeymouthSiResidual(
        pipe_id=parameters.pipe_id,
        pressure_squared_difference_pa2=pressure_squared_difference_pa2,
        friction_term_pa2=friction_term_pa2,
        residual_pa2=residual_pa2,
        resistance_coefficient_pa2_per_kg_s2=coefficient,
        equation_ref=parameters.equation_ref,
        parameter_source_ref=parameters.parameter_source_ref,
        observation_source_ref=observation.source_ref,
    )


__all__ = [
    "WeymouthSiObservation",
    "WeymouthSiPipeParameters",
    "WeymouthSiResidual",
    "evaluate_weymouth_si_residual",
]
