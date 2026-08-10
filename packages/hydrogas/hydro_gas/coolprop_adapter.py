"""Adaptateur CoolProp traçable pour fluides purs/pseudo-purs couverts.

D07 autorise un backend thermodynamique tel que CoolProp lorsque le fluide est
couvert et que le backend, la version et le domaine d'emploi sont publiés.
Cette brique utilise l'interface SI de CoolProp et exige une enveloppe projet
explicite ; elle ne choisit aucun fluide, backend ou domaine par défaut.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import CoolProp.CoolProp as coolprop


@dataclass(frozen=True, slots=True)
class CoolPropEvaluationEnvelope:
    """Domaine d'emploi approuvé pour une définition thermodynamique."""

    minimum_temperature_k: float
    maximum_temperature_k: float
    minimum_pressure_pa: float
    maximum_pressure_pa: float
    source_ref: str

    def __post_init__(self) -> None:
        values = (
            self.minimum_temperature_k,
            self.maximum_temperature_k,
            self.minimum_pressure_pa,
            self.maximum_pressure_pa,
        )
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError("Les bornes thermodynamiques doivent être finies et positives.")
        if self.minimum_temperature_k >= self.maximum_temperature_k:
            raise ValueError("La borne Tmin doit être strictement inférieure à Tmax.")
        if self.minimum_pressure_pa >= self.maximum_pressure_pa:
            raise ValueError("La borne Pmin doit être strictement inférieure à Pmax.")
        if not self.source_ref.strip():
            raise ValueError("La provenance du domaine thermodynamique est obligatoire.")

    def validate_state(self, *, temperature_k: float, pressure_pa: float) -> None:
        if not math.isfinite(temperature_k) or not math.isfinite(pressure_pa):
            raise ValueError("T et P doivent être finies.")
        if not self.minimum_temperature_k <= temperature_k <= self.maximum_temperature_k:
            raise ValueError("La température demandée est hors du domaine projet CoolProp.")
        if not self.minimum_pressure_pa <= pressure_pa <= self.maximum_pressure_pa:
            raise ValueError("La pression demandée est hors du domaine projet CoolProp.")


@dataclass(frozen=True, slots=True)
class CoolPropPureFluidDefinition:
    """Fluide et backend explicitement retenus par le projet."""

    fluid: str
    backend: str
    source_ref: str
    envelope: CoolPropEvaluationEnvelope

    def __post_init__(self) -> None:
        if not self.fluid.strip() or not self.backend.strip() or not self.source_ref.strip():
            raise ValueError("Fluide, backend et provenance sont obligatoires.")
        forbidden = ("::", "&", "[", "]")
        if any(token in self.fluid for token in forbidden) or self.fluid.lower().endswith(".mix"):
            raise ValueError(
                "Cet adaptateur est réservé aux fluides purs/pseudo-purs sans syntaxe de mélange."
            )
        if "::" in self.backend:
            raise ValueError("Le backend CoolProp doit être fourni sans séparateur '::'.")

    @property
    def coolprop_fluid_key(self) -> str:
        return f"{self.backend}::{self.fluid}"


@dataclass(frozen=True, slots=True)
class CoolPropPropertyResult:
    """Propriétés SI et provenance exacte du backend réellement exécuté."""

    temperature_k: float
    pressure_pa: float
    density_kg_m3: float
    dynamic_viscosity_pa_s: float
    kinematic_viscosity_m2_s: float
    vapor_pressure_pa: float
    coolprop_fluid_key: str
    coolprop_version: str
    coolprop_gitrevision: str
    definition_source_ref: str
    envelope_source_ref: str


def _positive_finite(value: float, property_name: str) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"CoolProp a retourné une valeur invalide pour {property_name}.")
    return value


def evaluate_coolprop_properties(
    definition: CoolPropPureFluidDefinition,
    *,
    temperature_k: float,
    pressure_pa: float,
) -> CoolPropPropertyResult:
    """Évalue ρ, μ, ν et la pression de saturation liquide à T donnée.

    La pression de vapeur est demandée à CoolProp avec ``Q=0``. Si le backend
    ou le fluide ne supporte pas cette propriété à la température considérée,
    l'évaluation échoue explicitement au lieu de substituer une corrélation.
    """

    definition.envelope.validate_state(temperature_k=temperature_k, pressure_pa=pressure_pa)
    key = definition.coolprop_fluid_key
    try:
        density = float(coolprop.PropsSI("DMASS", "T", temperature_k, "P", pressure_pa, key))
        dynamic_viscosity = float(
            coolprop.PropsSI("VISCOSITY", "T", temperature_k, "P", pressure_pa, key)
        )
        vapor_pressure = float(coolprop.PropsSI("P", "T", temperature_k, "Q", 0, key))
        version = coolprop.get_global_param_string("version")
        gitrevision = coolprop.get_global_param_string("gitrevision")
    except Exception as exc:  # CoolProp expose plusieurs exceptions backend selon l'état.
        raise ValueError(
            f"Échec de l'évaluation CoolProp pour {key} au point T/P demandé."
        ) from exc

    density = _positive_finite(density, "density")
    dynamic_viscosity = _positive_finite(dynamic_viscosity, "dynamic_viscosity")
    vapor_pressure = _positive_finite(vapor_pressure, "vapor_pressure")
    kinematic_viscosity = dynamic_viscosity / density
    return CoolPropPropertyResult(
        temperature_k=temperature_k,
        pressure_pa=pressure_pa,
        density_kg_m3=density,
        dynamic_viscosity_pa_s=dynamic_viscosity,
        kinematic_viscosity_m2_s=kinematic_viscosity,
        vapor_pressure_pa=vapor_pressure,
        coolprop_fluid_key=key,
        coolprop_version=version,
        coolprop_gitrevision=gitrevision,
        definition_source_ref=definition.source_ref,
        envelope_source_ref=definition.envelope.source_ref,
    )


__all__ = [
    "CoolPropEvaluationEnvelope",
    "CoolPropPropertyResult",
    "CoolPropPureFluidDefinition",
    "evaluate_coolprop_properties",
]
