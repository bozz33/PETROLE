"""Propriétés P6-A d'un mélange gaz explicite via CoolProp.

Cette couche évalue un état P/T déjà défini et publie uniquement des propriétés
thermodynamiques traçables. Elle ne modifie aucun paramètre Weymouth, ne choisit
aucune composition et n'applique aucun seuil de validation implicite.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from hydro_gas.coolprop_adapter import CoolPropEvaluationEnvelope
from hydro_gas.coolprop_gas_mixture import CoolPropGasMixtureDefinition


@dataclass(frozen=True, slots=True)
class CoolPropGasMixtureStateRequest:
    """État P/T et domaine projet explicitement approuvé en amont."""

    temperature_k: float
    pressure_pa: float
    envelope: CoolPropEvaluationEnvelope
    state_source_ref: str
    property_method_ref: str

    def __post_init__(self) -> None:
        if not self.state_source_ref.strip() or not self.property_method_ref.strip():
            raise ValueError("L'état gaz et la méthode de propriétés doivent être référencés.")
        self.envelope.validate_state(
            temperature_k=self.temperature_k,
            pressure_pa=self.pressure_pa,
        )


@dataclass(frozen=True, slots=True)
class CoolPropGasMixturePropertyResult:
    """Propriétés réseau factuelles et provenance de l'état CoolProp exécuté."""

    temperature_k: float
    pressure_pa: float
    density_kg_m3: float
    compressibility_factor: float
    molar_mass_kg_mol: float
    speed_of_sound_m_s: float
    gas_constant_j_mol_k: float
    density_from_eos_kg_m3: float
    density_eos_residual_kg_m3: float
    fluid_name: str
    coolprop_backend: str
    coolprop_version: str
    coolprop_gitrevision: str
    composition_source_ref: str
    component_mapping_source_ref: str
    composition_component_names: tuple[str, ...]
    coolprop_component_names: tuple[str, ...]
    mole_fractions: tuple[float, ...]
    mixture_definition_source_ref: str
    envelope_source_ref: str
    state_source_ref: str
    property_method_ref: str
    qualification_claim: bool = False
    certification_claim: bool = False


def _load_coolprop() -> Any:
    try:
        import CoolProp  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement d'installation
        raise RuntimeError("CoolProp doit être installé pour évaluer le mélange gaz.") from exc
    return CoolProp


def _positive_finite(value: Any, *, label: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"CoolProp a retourné une valeur invalide pour {label}.")
    return result


def evaluate_coolprop_gas_mixture_properties(
    definition: CoolPropGasMixtureDefinition,
    request: CoolPropGasMixtureStateRequest,
) -> CoolPropGasMixturePropertyResult:
    """Évalue ρ, Z, M et a sans couplage automatique au solveur réseau."""

    coolprop_module = _load_coolprop()
    try:
        state = coolprop_module.AbstractState(definition.backend, definition.component_key)
        state.set_mole_fractions(list(definition.mole_fractions))
        state.update(
            coolprop_module.PT_INPUTS,
            request.pressure_pa,
            request.temperature_k,
        )
        density = _positive_finite(state.rhomass(), label="density")
        compressibility = _positive_finite(
            state.compressibility_factor(),
            label="compressibility_factor",
        )
        molar_mass = _positive_finite(state.molar_mass(), label="molar_mass")
        speed_of_sound = _positive_finite(state.speed_sound(), label="speed_of_sound")
        gas_constant = _positive_finite(state.gas_constant(), label="gas_constant")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Échec de l'évaluation CoolProp du mélange au point P/T demandé.") from exc

    density_from_eos = (
        request.pressure_pa * molar_mass / (compressibility * gas_constant * request.temperature_k)
    )
    density_residual = density - density_from_eos
    if not math.isfinite(density_from_eos) or density_from_eos <= 0.0:
        raise ValueError("La reconstruction de densité depuis Z/M/R/T doit être finie et positive.")
    if not math.isfinite(density_residual):
        raise ValueError("Le résidu brut de cohérence EOS doit être fini.")

    return CoolPropGasMixturePropertyResult(
        temperature_k=request.temperature_k,
        pressure_pa=request.pressure_pa,
        density_kg_m3=density,
        compressibility_factor=compressibility,
        molar_mass_kg_mol=molar_mass,
        speed_of_sound_m_s=speed_of_sound,
        gas_constant_j_mol_k=gas_constant,
        density_from_eos_kg_m3=density_from_eos,
        density_eos_residual_kg_m3=density_residual,
        fluid_name=definition.fluid_name,
        coolprop_backend=definition.backend,
        coolprop_version=str(getattr(coolprop_module, "__version__", "unknown")),
        coolprop_gitrevision=str(getattr(coolprop_module, "__gitrevision__", "unknown")),
        composition_source_ref=definition.composition.source_ref,
        component_mapping_source_ref=definition.mapping_source_ref,
        composition_component_names=definition.composition_component_names,
        coolprop_component_names=definition.coolprop_component_names,
        mole_fractions=definition.mole_fractions,
        mixture_definition_source_ref=definition.source_ref,
        envelope_source_ref=request.envelope.source_ref,
        state_source_ref=request.state_source_ref,
        property_method_ref=request.property_method_ref,
    )


__all__ = [
    "CoolPropGasMixturePropertyResult",
    "CoolPropGasMixtureStateRequest",
    "evaluate_coolprop_gas_mixture_properties",
]
