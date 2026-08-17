"""Post-traitement thermodynamique des compresseurs du solveur gaz mixte.

Les pressions, débits et rendements de carte proviennent du résultat scientifique
déjà calculé. Les températures d'aspiration, fluides/compositions et autres
termes du bilan d'énergie restent des entrées explicites. Cette couche ne
modifie pas le solveur réseau et ne déduit aucune limite machine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.compressor_thermodynamics import (
    SteadyCompressorEnergyBalanceResult,
    SteadyCompressorEnergyObservation,
    evaluate_steady_compressor_energy_balance,
)
from hydro_gas.coolprop_compressor_adapter import (
    CoolPropCompressorFluid,
    CoolPropCompressorStateRequest,
    CoolPropCompressorStateResult,
    evaluate_coolprop_compressor_states,
)
from hydro_gas.stationary_equipment_problem import StationaryActiveCompressorProblem
from hydro_gas.stationary_equipment_solver import StationaryActiveCompressorGovernedSolveResult
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus


@dataclass(frozen=True, slots=True)
class StationaryCompressorThermodynamicInput:
    """Données thermodynamiques externes nécessaires à un compresseur actif."""

    compressor_id: str
    inlet_temperature_k: float
    fluid: CoolPropCompressorFluid
    inlet_kinetic_energy_j_kg: float
    outlet_kinetic_energy_j_kg: float
    inlet_potential_energy_j_kg: float
    outlet_potential_energy_j_kg: float
    heat_transfer_to_gas_w: float
    state_source_ref: str
    property_method_ref: str
    energy_equation_ref: str

    def __post_init__(self) -> None:
        required = (
            self.compressor_id,
            self.state_source_ref,
            self.property_method_ref,
            self.energy_equation_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError("Le post-traitement thermodynamique doit être entièrement référencé.")
        if not math.isfinite(self.inlet_temperature_k) or self.inlet_temperature_k <= 0.0:
            raise ValueError("La température d'aspiration doit être finie et strictement positive.")
        values = (
            self.inlet_kinetic_energy_j_kg,
            self.outlet_kinetic_energy_j_kg,
            self.inlet_potential_energy_j_kg,
            self.outlet_potential_energy_j_kg,
            self.heat_transfer_to_gas_w,
        )
        if any(not math.isfinite(value) for value in values):
            raise ValueError("Les contributions énergétiques fournies doivent être finies.")
        if self.inlet_kinetic_energy_j_kg < 0.0 or self.outlet_kinetic_energy_j_kg < 0.0:
            raise ValueError(
                "Les énergies cinétiques spécifiques doivent être positives ou nulles."
            )


@dataclass(frozen=True, slots=True)
class StationaryCompressorThermodynamicResult:
    """État thermodynamique et puissance mécanique pour un compresseur."""

    compressor_id: str
    solver_status: StationaryWeymouthSolverStatus
    mass_flow_kg_s: float
    inlet_node_id: str
    outlet_node_id: str
    property_state: CoolPropCompressorStateResult
    energy_balance: SteadyCompressorEnergyBalanceResult


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorThermodynamicAssessment:
    """Post-traitement complet avec statut du solveur source conservé."""

    solve_ref: str
    solver_status: StationaryWeymouthSolverStatus
    compressors: tuple[StationaryCompressorThermodynamicResult, ...]


def evaluate_stationary_active_compressor_thermodynamics(
    problem: StationaryActiveCompressorProblem,
    governed_result: StationaryActiveCompressorGovernedSolveResult,
    inputs: tuple[StationaryCompressorThermodynamicInput, ...],
) -> StationaryActiveCompressorThermodynamicAssessment:
    """Calcule les états/propriétés sans modifier ni re-résoudre le réseau."""

    expected_ids = tuple(edge.compressor_id for edge in problem.compressor_edges)
    input_ids = tuple(item.compressor_id for item in inputs)
    if len(input_ids) != len(set(input_ids)):
        raise ValueError(
            "Les entrées thermodynamiques compresseurs doivent avoir des identifiants uniques."
        )
    if set(input_ids) != set(expected_ids):
        raise ValueError(
            "Les entrées thermodynamiques doivent couvrir exactement les compresseurs actifs."
        )

    solve = governed_result.solve
    physical = solve.final_evaluation.physical_evaluation
    candidate = physical.candidate
    pressure_by_node = {item.node_id: item.pressure_pa for item in candidate.node_pressures}
    compressor_input_by_id = {item.compressor_id: item for item in candidate.compressor_inputs}
    constraint_by_id = {
        item.compressor_id: item for item in physical.equipment_residuals.compressor_constraints
    }
    external_input_by_id = {item.compressor_id: item for item in inputs}
    if set(compressor_input_by_id) != set(expected_ids) or set(constraint_by_id) != set(
        expected_ids
    ):
        raise ValueError(
            "Le résultat réseau doit couvrir exactement les compresseurs actifs avant le post-traitement."
        )

    results: list[StationaryCompressorThermodynamicResult] = []
    for edge in problem.compressor_edges:
        external_input = external_input_by_id[edge.compressor_id]
        compressor_input = compressor_input_by_id[edge.compressor_id]
        constraint = constraint_by_id[edge.compressor_id]
        inlet_pressure = pressure_by_node[edge.from_node_id]
        outlet_pressure = pressure_by_node[edge.to_node_id]
        efficiency_source_ref = (
            f"{constraint.operating_point.source_ref}"
            f"#map-version/{constraint.operating_point.map_version}"
        )
        property_state = evaluate_coolprop_compressor_states(
            external_input.fluid,
            CoolPropCompressorStateRequest(
                compressor_id=edge.compressor_id,
                inlet_pressure_pa=inlet_pressure,
                inlet_temperature_k=external_input.inlet_temperature_k,
                outlet_pressure_pa=outlet_pressure,
                isentropic_efficiency=constraint.operating_point.isentropic_efficiency,
                state_source_ref=external_input.state_source_ref,
                efficiency_source_ref=efficiency_source_ref,
                property_method_ref=external_input.property_method_ref,
            ),
        )
        energy_balance = evaluate_steady_compressor_energy_balance(
            SteadyCompressorEnergyObservation(
                compressor_id=edge.compressor_id,
                mass_flow_kg_s=compressor_input.mass_flow_kg_s,
                inlet_enthalpy_j_kg=property_state.inlet_enthalpy_j_kg,
                outlet_enthalpy_j_kg=property_state.actual_outlet_enthalpy_j_kg,
                inlet_kinetic_energy_j_kg=external_input.inlet_kinetic_energy_j_kg,
                outlet_kinetic_energy_j_kg=external_input.outlet_kinetic_energy_j_kg,
                inlet_potential_energy_j_kg=external_input.inlet_potential_energy_j_kg,
                outlet_potential_energy_j_kg=external_input.outlet_potential_energy_j_kg,
                heat_transfer_to_gas_w=external_input.heat_transfer_to_gas_w,
                state_source_ref=external_input.state_source_ref,
                equation_ref=external_input.energy_equation_ref,
            )
        )
        results.append(
            StationaryCompressorThermodynamicResult(
                compressor_id=edge.compressor_id,
                solver_status=solve.status,
                mass_flow_kg_s=compressor_input.mass_flow_kg_s,
                inlet_node_id=edge.from_node_id,
                outlet_node_id=edge.to_node_id,
                property_state=property_state,
                energy_balance=energy_balance,
            )
        )

    return StationaryActiveCompressorThermodynamicAssessment(
        solve_ref=solve.solve_ref,
        solver_status=solve.status,
        compressors=tuple(results),
    )


__all__ = [
    "StationaryActiveCompressorThermodynamicAssessment",
    "StationaryCompressorThermodynamicInput",
    "StationaryCompressorThermodynamicResult",
    "evaluate_stationary_active_compressor_thermodynamics",
]
