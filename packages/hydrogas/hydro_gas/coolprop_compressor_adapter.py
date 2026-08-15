"""États thermodynamiques compresseur via CoolProp, avec provenance explicite.

Les fluides purs restent supportés par ``PropsSI``. Les mélanges sont fournis
comme compositions molaires PETROLE explicites et sont évalués avec l'interface
bas niveau ``AbstractState`` de CoolProp. Aucune composition, aucun mapping de
composant et aucun rendement n'est injecté par défaut.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from hydro_gas.composition import GasComposition


@dataclass(frozen=True, slots=True)
class CoolPropCompressorFluidDefinition:
    """Identité exacte d'un fluide pur/pseudo-pur envoyé à ``PropsSI``."""

    fluid_name: str
    source_ref: str

    def __post_init__(self) -> None:
        if not self.fluid_name.strip() or not self.source_ref.strip():
            raise ValueError("Le fluide CoolProp et sa provenance sont obligatoires.")
        forbidden = ("&", "[", "]")
        if any(token in self.fluid_name for token in forbidden) or self.fluid_name.lower().endswith(
            ".mix"
        ):
            raise ValueError(
                "La définition fluide simple ne peut pas masquer une syntaxe de mélange CoolProp."
            )


@dataclass(frozen=True, slots=True)
class CoolPropCompressorMixtureComponentBinding:
    """Correspondance explicite entre un composant PETROLE et un fluide CoolProp."""

    composition_component: str
    coolprop_fluid: str

    def __post_init__(self) -> None:
        if not self.composition_component.strip() or not self.coolprop_fluid.strip():
            raise ValueError("Le composant PETROLE et son identifiant CoolProp sont obligatoires.")
        forbidden = ("::", "&", "[", "]")
        if any(
            token in self.coolprop_fluid for token in forbidden
        ) or self.coolprop_fluid.lower().endswith(".mix"):
            raise ValueError(
                "Un binding de composant doit viser un fluide CoolProp simple, sans syntaxe de mélange."
            )


@dataclass(frozen=True, slots=True)
class CoolPropCompressorMixtureDefinition:
    """Mélange CoolProp construit à partir d'une composition molaire traçable."""

    composition: GasComposition
    component_bindings: tuple[CoolPropCompressorMixtureComponentBinding, ...]
    backend: str
    source_ref: str
    mapping_source_ref: str

    def __post_init__(self) -> None:
        required = (self.backend, self.source_ref, self.mapping_source_ref)
        if any(not value.strip() for value in required):
            raise ValueError(
                "Le backend, la provenance du mélange et la provenance du mapping sont obligatoires."
            )
        if "::" in self.backend:
            raise ValueError("Le backend CoolProp doit être fourni sans séparateur '::'.")
        if not self.component_bindings:
            raise ValueError("Le mélange CoolProp exige un binding pour chaque composant.")

        composition_names = tuple(component.component for component in self.composition.components)
        binding_names = tuple(binding.composition_component for binding in self.component_bindings)
        if len(binding_names) != len(set(binding_names)):
            raise ValueError("Les composants PETROLE du mapping CoolProp doivent être uniques.")
        if set(binding_names) != set(composition_names):
            raise ValueError(
                "Le mapping CoolProp doit couvrir exactement les composants de la composition gaz."
            )

        coolprop_names = tuple(binding.coolprop_fluid for binding in self.component_bindings)
        if len(coolprop_names) != len(set(coolprop_names)):
            raise ValueError("Chaque composant PETROLE doit viser un fluide CoolProp distinct.")

    @property
    def composition_component_names(self) -> tuple[str, ...]:
        return tuple(component.component for component in self.composition.components)

    @property
    def coolprop_component_names(self) -> tuple[str, ...]:
        by_component = {
            binding.composition_component: binding.coolprop_fluid
            for binding in self.component_bindings
        }
        return tuple(by_component[name] for name in self.composition_component_names)

    @property
    def mole_fractions(self) -> tuple[float, ...]:
        return tuple(component.mole_fraction for component in self.composition.components)

    @property
    def fluid_name(self) -> str:
        """Identité déterministe du backend et des composants, fractions publiées séparément."""

        return f"{self.backend}::{'&'.join(self.coolprop_component_names)}"


CoolPropCompressorFluid = CoolPropCompressorFluidDefinition | CoolPropCompressorMixtureDefinition


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
            raise ValueError(
                "La requête thermodynamique compresseur doit être entièrement référencée."
            )
        values = (
            self.inlet_pressure_pa,
            self.inlet_temperature_k,
            self.outlet_pressure_pa,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in values):
            raise ValueError(
                "Pressions et température compresseur doivent être finies et positives."
            )
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
    """États calculés et identité exacte du backend/propriétés réellement utilisés."""

    compressor_id: str
    fluid_name: str
    coolprop_version: str
    coolprop_gitrevision: str
    coolprop_backend: str | None
    composition_source_ref: str | None
    component_mapping_source_ref: str | None
    composition_component_names: tuple[str, ...]
    coolprop_component_names: tuple[str, ...]
    mole_fractions: tuple[float, ...]
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
        raise RuntimeError(
            "CoolProp doit être installé pour évaluer les états compresseur."
        ) from exc
    return CoolProp, PropsSI


def _finite_property(value: Any, *, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"CoolProp a retourné une propriété non finie pour {label}.")
    return result


def _runtime_identity(coolprop_module: Any) -> tuple[str, str]:
    return (
        str(getattr(coolprop_module, "__version__", "unknown")),
        str(getattr(coolprop_module, "__gitrevision__", "unknown")),
    )


def _evaluate_pure_states(
    props_si: Any,
    fluid_name: str,
    request: CoolPropCompressorStateRequest,
) -> tuple[float, float, float, float]:
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
    return (
        inlet_enthalpy,
        inlet_entropy,
        isentropic_outlet_enthalpy,
        isentropic_outlet_temperature,
    )


def _evaluate_mixture_states(
    coolprop_module: Any,
    definition: CoolPropCompressorMixtureDefinition,
    request: CoolPropCompressorStateRequest,
) -> tuple[Any, float, float, float, float]:
    component_key = "&".join(definition.coolprop_component_names)
    try:
        state = coolprop_module.AbstractState(definition.backend, component_key)
        state.set_mole_fractions(list(definition.mole_fractions))
        state.update(
            coolprop_module.PT_INPUTS,
            request.inlet_pressure_pa,
            request.inlet_temperature_k,
        )
        inlet_enthalpy = _finite_property(state.hmass(), label="l'enthalpie d'entrée du mélange")
        inlet_entropy = _finite_property(state.smass(), label="l'entropie d'entrée du mélange")
        state.update(
            coolprop_module.PSmass_INPUTS,
            request.outlet_pressure_pa,
            inlet_entropy,
        )
        isentropic_outlet_enthalpy = _finite_property(
            state.hmass(),
            label="l'enthalpie de sortie isentropique du mélange",
        )
        isentropic_outlet_temperature = _finite_property(
            state.T(),
            label="la température de sortie isentropique du mélange",
        )
    except Exception as exc:
        raise ValueError(
            "Échec de l'évaluation CoolProp du mélange explicite au point compresseur demandé."
        ) from exc
    return (
        state,
        inlet_enthalpy,
        inlet_entropy,
        isentropic_outlet_enthalpy,
        isentropic_outlet_temperature,
    )


def evaluate_coolprop_compressor_states(
    fluid: CoolPropCompressorFluid,
    request: CoolPropCompressorStateRequest,
) -> CoolPropCompressorStateResult:
    """Évalue l'état isentropique puis réel sans rendement ou composition implicite."""

    coolprop_module, props_si = _load_coolprop()
    coolprop_version, coolprop_gitrevision = _runtime_identity(coolprop_module)

    if isinstance(fluid, CoolPropCompressorMixtureDefinition):
        (
            mixture_state,
            inlet_enthalpy,
            inlet_entropy,
            isentropic_outlet_enthalpy,
            isentropic_outlet_temperature,
        ) = _evaluate_mixture_states(coolprop_module, fluid, request)
        fluid_name = fluid.fluid_name
        coolprop_backend: str | None = fluid.backend
        composition_source_ref: str | None = fluid.composition.source_ref
        component_mapping_source_ref: str | None = fluid.mapping_source_ref
        composition_component_names = fluid.composition_component_names
        coolprop_component_names = fluid.coolprop_component_names
        mole_fractions = fluid.mole_fractions
        fluid_source_ref = fluid.source_ref
    else:
        fluid_name = fluid.fluid_name.strip()
        (
            inlet_enthalpy,
            inlet_entropy,
            isentropic_outlet_enthalpy,
            isentropic_outlet_temperature,
        ) = _evaluate_pure_states(props_si, fluid_name, request)
        mixture_state = None
        coolprop_backend = None
        composition_source_ref = None
        component_mapping_source_ref = None
        composition_component_names = ()
        coolprop_component_names = ()
        mole_fractions = ()
        fluid_source_ref = fluid.source_ref

    if isentropic_outlet_enthalpy < inlet_enthalpy:
        raise ValueError(
            "La propriété isentropique retournée est incompatible avec une compression active."
        )

    actual_outlet_enthalpy = _finite_property(
        inlet_enthalpy
        + (isentropic_outlet_enthalpy - inlet_enthalpy) / request.isentropic_efficiency,
        label="l'enthalpie de sortie réelle",
    )
    if mixture_state is not None:
        try:
            mixture_state.update(
                coolprop_module.HmassP_INPUTS,
                actual_outlet_enthalpy,
                request.outlet_pressure_pa,
            )
            actual_outlet_temperature = _finite_property(
                mixture_state.T(),
                label="la température de sortie réelle du mélange",
            )
        except Exception as exc:
            raise ValueError(
                "Échec de la fermeture H/P CoolProp du mélange explicite au refoulement."
            ) from exc
    else:
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

    return CoolPropCompressorStateResult(
        compressor_id=request.compressor_id,
        fluid_name=fluid_name,
        coolprop_version=coolprop_version,
        coolprop_gitrevision=coolprop_gitrevision,
        coolprop_backend=coolprop_backend,
        composition_source_ref=composition_source_ref,
        component_mapping_source_ref=component_mapping_source_ref,
        composition_component_names=composition_component_names,
        coolprop_component_names=coolprop_component_names,
        mole_fractions=mole_fractions,
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
        fluid_source_ref=fluid_source_ref,
        state_source_ref=request.state_source_ref,
        efficiency_source_ref=request.efficiency_source_ref,
        property_method_ref=request.property_method_ref,
    )


__all__ = [
    "CoolPropCompressorFluid",
    "CoolPropCompressorFluidDefinition",
    "CoolPropCompressorMixtureComponentBinding",
    "CoolPropCompressorMixtureDefinition",
    "CoolPropCompressorStateRequest",
    "CoolPropCompressorStateResult",
    "evaluate_coolprop_compressor_states",
]
