"""Bilans thermodynamiques stationnaires traçables pour compresseurs gaz.

Les fonctions de ce module n'inventent aucune propriété thermodynamique. Les
enthalpies, contributions cinétique/potentielle, chaleur et rendements sont des
entrées explicites accompagnées de références. La température de refoulement
reste du ressort d'une méthode de propriétés séparée.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.compressor_map import CompressorOperatingPoint


@dataclass(frozen=True, slots=True)
class SteadyCompressorEnergyObservation:
    """État énergétique explicite d'un volume de contrôle compresseur."""

    compressor_id: str
    mass_flow_kg_s: float
    inlet_enthalpy_j_kg: float
    outlet_enthalpy_j_kg: float
    inlet_kinetic_energy_j_kg: float
    outlet_kinetic_energy_j_kg: float
    inlet_potential_energy_j_kg: float
    outlet_potential_energy_j_kg: float
    heat_transfer_to_gas_w: float
    state_source_ref: str
    equation_ref: str

    def __post_init__(self) -> None:
        required = (self.compressor_id, self.state_source_ref, self.equation_ref)
        if any(not value.strip() for value in required):
            raise ValueError(
                "Le bilan énergétique compresseur et ses références sont obligatoires."
            )
        if not math.isfinite(self.mass_flow_kg_s) or self.mass_flow_kg_s <= 0.0:
            raise ValueError(
                "Le débit massique du compresseur doit être fini et strictement positif."
            )
        values = (
            self.inlet_enthalpy_j_kg,
            self.outlet_enthalpy_j_kg,
            self.inlet_kinetic_energy_j_kg,
            self.outlet_kinetic_energy_j_kg,
            self.inlet_potential_energy_j_kg,
            self.outlet_potential_energy_j_kg,
            self.heat_transfer_to_gas_w,
        )
        if any(not math.isfinite(value) for value in values):
            raise ValueError(
                "Toutes les grandeurs énergétiques du compresseur doivent être finies."
            )
        if any(
            value < 0.0
            for value in (
                self.inlet_kinetic_energy_j_kg,
                self.outlet_kinetic_energy_j_kg,
            )
        ):
            raise ValueError(
                "Les énergies cinétiques spécifiques doivent être positives ou nulles."
            )


@dataclass(frozen=True, slots=True)
class SteadyCompressorEnergyBalanceResult:
    """Puissance mécanique entrante issue du premier principe stationnaire."""

    compressor_id: str
    enthalpy_rise_j_kg: float
    kinetic_energy_change_j_kg: float
    potential_energy_change_j_kg: float
    total_specific_energy_rise_j_kg: float
    heat_transfer_to_gas_w: float
    shaft_power_input_w: float
    state_source_ref: str
    equation_ref: str


def evaluate_steady_compressor_energy_balance(
    observation: SteadyCompressorEnergyObservation,
) -> SteadyCompressorEnergyBalanceResult:
    """Calcule la puissance mécanique entrante avec une convention explicite.

    ``heat_transfer_to_gas_w`` est positif lorsque la chaleur entre dans le gaz.
    ``shaft_power_input_w`` est positif lorsque le travail mécanique entre dans
    le volume de contrôle. Aucun terme n'est supprimé implicitement.
    """

    enthalpy_rise = observation.outlet_enthalpy_j_kg - observation.inlet_enthalpy_j_kg
    kinetic_change = observation.outlet_kinetic_energy_j_kg - observation.inlet_kinetic_energy_j_kg
    potential_change = (
        observation.outlet_potential_energy_j_kg - observation.inlet_potential_energy_j_kg
    )
    total_specific_rise = enthalpy_rise + kinetic_change + potential_change
    shaft_power_input = (
        observation.mass_flow_kg_s * total_specific_rise - observation.heat_transfer_to_gas_w
    )
    return SteadyCompressorEnergyBalanceResult(
        compressor_id=observation.compressor_id,
        enthalpy_rise_j_kg=enthalpy_rise,
        kinetic_energy_change_j_kg=kinetic_change,
        potential_energy_change_j_kg=potential_change,
        total_specific_energy_rise_j_kg=total_specific_rise,
        heat_transfer_to_gas_w=observation.heat_transfer_to_gas_w,
        shaft_power_input_w=shaft_power_input,
        state_source_ref=observation.state_source_ref,
        equation_ref=observation.equation_ref,
    )


@dataclass(frozen=True, slots=True)
class IsentropicCompressorEnthalpyClosure:
    """Fermeture par rendement isentropique avec enthalpies explicitement fournies."""

    compressor_id: str
    inlet_enthalpy_j_kg: float
    isentropic_outlet_enthalpy_j_kg: float
    isentropic_efficiency: float
    property_source_ref: str
    efficiency_source_ref: str
    equation_ref: str

    def __post_init__(self) -> None:
        required = (
            self.compressor_id,
            self.property_source_ref,
            self.efficiency_source_ref,
            self.equation_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError(
                "La fermeture isentropique et toutes ses références sont obligatoires."
            )
        if any(
            not math.isfinite(value)
            for value in (self.inlet_enthalpy_j_kg, self.isentropic_outlet_enthalpy_j_kg)
        ):
            raise ValueError("Les enthalpies de la fermeture isentropique doivent être finies.")
        if self.isentropic_outlet_enthalpy_j_kg < self.inlet_enthalpy_j_kg:
            raise ValueError(
                "L'enthalpie de sortie isentropique d'un compresseur actif ne peut pas être inférieure à l'entrée."
            )
        if (
            not math.isfinite(self.isentropic_efficiency)
            or self.isentropic_efficiency <= 0.0
            or self.isentropic_efficiency > 1.0
        ):
            raise ValueError("Le rendement isentropique doit appartenir à ]0, 1].")


@dataclass(frozen=True, slots=True)
class IsentropicCompressorEnthalpyResult:
    """Enthalpie réelle déduite de la fermeture explicitement fournie."""

    compressor_id: str
    inlet_enthalpy_j_kg: float
    isentropic_outlet_enthalpy_j_kg: float
    actual_outlet_enthalpy_j_kg: float
    isentropic_specific_work_j_kg: float
    actual_specific_work_j_kg: float
    isentropic_efficiency: float
    property_source_ref: str
    efficiency_source_ref: str
    equation_ref: str


def evaluate_isentropic_compressor_enthalpy_closure(
    closure: IsentropicCompressorEnthalpyClosure,
) -> IsentropicCompressorEnthalpyResult:
    """Applique ``eta = (h2s-h1)/(h2-h1)`` sans chercher les propriétés."""

    isentropic_work = closure.isentropic_outlet_enthalpy_j_kg - closure.inlet_enthalpy_j_kg
    actual_work = isentropic_work / closure.isentropic_efficiency
    actual_outlet = closure.inlet_enthalpy_j_kg + actual_work
    return IsentropicCompressorEnthalpyResult(
        compressor_id=closure.compressor_id,
        inlet_enthalpy_j_kg=closure.inlet_enthalpy_j_kg,
        isentropic_outlet_enthalpy_j_kg=closure.isentropic_outlet_enthalpy_j_kg,
        actual_outlet_enthalpy_j_kg=actual_outlet,
        isentropic_specific_work_j_kg=isentropic_work,
        actual_specific_work_j_kg=actual_work,
        isentropic_efficiency=closure.isentropic_efficiency,
        property_source_ref=closure.property_source_ref,
        efficiency_source_ref=closure.efficiency_source_ref,
        equation_ref=closure.equation_ref,
    )


def build_isentropic_closure_from_map(
    operating_point: CompressorOperatingPoint,
    *,
    compressor_id: str,
    inlet_enthalpy_j_kg: float,
    isentropic_outlet_enthalpy_j_kg: float,
    property_source_ref: str,
    equation_ref: str,
) -> IsentropicCompressorEnthalpyClosure:
    """Lie le rendement de carte au calcul enthalpique sans le modifier."""

    normalized_id = compressor_id.strip()
    if not normalized_id:
        raise ValueError("L'identifiant compresseur est obligatoire.")
    if not property_source_ref.strip() or not equation_ref.strip():
        raise ValueError("Les propriétés et l'équation de fermeture doivent être référencées.")
    return IsentropicCompressorEnthalpyClosure(
        compressor_id=normalized_id,
        inlet_enthalpy_j_kg=inlet_enthalpy_j_kg,
        isentropic_outlet_enthalpy_j_kg=isentropic_outlet_enthalpy_j_kg,
        isentropic_efficiency=operating_point.isentropic_efficiency,
        property_source_ref=property_source_ref,
        efficiency_source_ref=(
            f"{operating_point.source_ref}#map-version/{operating_point.map_version}"
        ),
        equation_ref=equation_ref,
    )


__all__ = [
    "IsentropicCompressorEnthalpyClosure",
    "IsentropicCompressorEnthalpyResult",
    "SteadyCompressorEnergyBalanceResult",
    "SteadyCompressorEnergyObservation",
    "build_isentropic_closure_from_map",
    "evaluate_isentropic_compressor_enthalpy_closure",
    "evaluate_steady_compressor_energy_balance",
]
