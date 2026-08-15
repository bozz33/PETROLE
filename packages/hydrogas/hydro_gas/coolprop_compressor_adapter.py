"""États thermodynamiques compresseur via CoolProp, avec provenance explicite.

Cette première brique de propriétés P6-D vise un fluide CoolProp explicitement
nommé. Elle calcule l'état d'entrée, la sortie isentropique à pression imposée,
puis la sortie réelle à partir d'un rendement isentropique fourni. Elle ne
suppose aucun mélange, aucune composition ni aucun rendement par défaut.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CoolPropCompressorFluidDefinition:
    """Identité exacte du fluide envoyé à CoolProp."""

    fluid_name: str
    source_ref: str

    def __post_init__(self) -> None:
        if not self.fluid_name.strip() or not self.source_ref.strip():
            raise ValueError("Le fluide CoolProp et sa provenance sont obligatoires.")


@dataclass(frozen=True, slots=True)
class CoolPropCompressorStateRequest:
    """Conditions nécessaires à la fermeture isentropique du compresseur."""

    compressor_id: str
    inlet_pressure_pa: float
    inlet_temperature_k: float
    outlet_pressure_pa: float
    isentropic_efficiency: float
    state_source_ref: str
    efficiency_source_ref: str
    property_method_ref: str

    def __post_init__(self) -> None:
        required = (
            self.compressor_id,
            self.state_source_ref,
            self.efficiency_source_ref,
            self.property_method_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError("La requête thermodynamique compresseur doit être entièrement référencée.")
        values = (
            self.inlet_pressure_pa,
            self.inlet_temperature_k,
            self.outlet_pressure_pa,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in values):
            raise ValueError("Pressions et température compresseur doivent être finies et positives.")
        if self.outlet_pressure_pa <= self.inlet_pressure_pa:
            raise ValueError(
                "La sortie d'un compresseur actif doit avoir une pression supérieure à l'entrée."
            )
        if (
            not math.isfinite(self.isentropic_efficiency)
            or self.isentropic_efficiency <= 0.0
            or self.isentropic_efficiency > 1.0
        ):
            raise ValueError("Le rendement isentropique doit appartenir à ]0, 1].")


@dataclass(frozen=True, slots=True)
class CoolPropCompressorStateResult:
    """États calculés et version du moteur de propriétés réellement utilisé."""

    compressor_id: str
    fluid_name: str
    coolprop_version: str
    inlet_pressure_pa: float
    inlet_temperature_k: float
    inlet_enthalpy_j_kg: float
    inlet_entropy_j_kg_k: float
    outlet_pressure_pa: float
    isentropic_outlet_temperature_k: float
    isentropic_outlet_enthalpy_j_kg: float
    actual_outlet_temperature_k: float
    actual_outlet_enthalpy_j_kg: float
    isentropic_efficiency: float
    fluid_source_ref: str
    state_source_ref: str
    efficiency_source_ref: str
    property_method_ref: str


def _load_coolprop() -> tuple[Any, Any]:
    try:
        import CoolProp  # type: ignore[import-not-found]
        from CoolProp.CoolProp import PropsSI  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement d'installation
        raise RuntimeError("CoolProp doit être installé pour évaluer les états compresseur.") from exc
    return CoolProp, PropsSI


def _finite_property(value: Any, *, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"CoolProp a retourné une propriété non finie pour {label}.")
    return result


def evaluate_coolprop_compressor_states(
    fluid: CoolPropCompressorFluidDefinition,
    request: CoolPropCompressorStateRequest,
) -> CoolPropCompressorStateResult:
    """Évalue l'état isentropique puis réel sans rendement ou composition implicite."""

    coolprop_module, props_si = _load_coolprop()
    fluid_name = fluid.fluid_name.strip()
    inlet_enthalpy = _finite_property(
        props_si(
            "Hmass",
            "P",
            request.inlet_pressure_pa,
            "T",
            request.inlet_temperature_k,
            fluid_name,
        ),
        label="l'enthalpie d'entrée",
    )
    inlet_entropy = _finite_property(
        props_si(
            "Smass",
            "P",
            request.inlet_pressure_pa,
            "T",
            request.inlet_temperature_k,
            fluid_name,
        ),
        label="l'entropie d'entrée",
    )
    isentropic_outlet_enthalpy = _finite_property(
        props_si(
            "Hmass",
            "P",
            request.outlet_pressure_pa,
            "Smass",
            inlet_entropy,
            fluid_name,
        ),
        label="l'enthalpie de sortie isentropique",
    )
    isentropic_outlet_temperature = _finite_property(
        props_si(
            "T",
            "P",
            request.outlet_pressure_pa,
            "Smass",
            inlet_entropy,
            fluid_name,
        ),
        label="la température de sortie isentropique",
    )
    if isentropic_outlet_enthalpy < inlet_enthalpy:
        raise ValueError(
            "La propriété isentropique retournée est incompatible avec une compression active."
        )

    actual_outlet_enthalpy = inlet_enthalpy + (
        isentropic_outlet_enthalpy - inlet_enthalpy
    ) / request.isentropic_efficiency
    actual_outlet_temperature = _finite_property(
        props_si(
            "T",
            "P",
            request.outlet_pressure_pa,
            "Hmass",
            actual_outlet_enthalpy,
            fluid_name,
        ),
        label="la température de sortie réelle",
    )

    version = str(getattr(coolprop_module, "__version__", "unknown"))
    return CoolPropCompressorStateResult(
        compressor_id=request.compressor_id,
        fluid_name=fluid_name,
        coolprop_version=version,
        inlet_pressure_pa=request.inlet_pressure_pa,
        inlet_temperature_k=request.inlet_temperature_k,
        inlet_enthalpy_j_kg=inlet_enthalpy,
        inlet_entropy_j_kg_k=inlet_entropy,
        outlet_pressure_pa=request.outlet_pressure_pa,
        isentropic_outlet_temperature_k=isentropic_outlet_temperature,
        isentropic_outlet_enthalpy_j_kg=isentropic_outlet_enthalpy,
        actual_outlet_temperature_k=actual_outlet_temperature,
        actual_outlet_enthalpy_j_kg=actual_outlet_enthalpy,
        isentropic_efficiency=request.isentropic_efficiency,
        fluid_source_ref=fluid.source_ref,
        state_source_ref=request.state_source_ref,
        efficiency_source_ref=request.efficiency_source_ref,
        property_method_ref=request.property_method_ref,
    )


__all__ = [
    "CoolPropCompressorFluidDefinition",
    "CoolPropCompressorStateRequest",
    "CoolPropCompressorStateResult",
    "evaluate_coolprop_compressor_states",
]
