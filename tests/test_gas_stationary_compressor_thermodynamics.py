from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from hydro_gas.composition import GasComponentFraction, GasComposition
from hydro_gas.coolprop_compressor_adapter import (
    CoolPropCompressorFluidDefinition,
    CoolPropCompressorMixtureComponentBinding,
    CoolPropCompressorMixtureDefinition,
)
from hydro_gas.stationary_compressor_thermodynamics import (
    StationaryCompressorThermodynamicInput,
    evaluate_stationary_active_compressor_thermodynamics,
)
from hydro_gas.stationary_equipment_problem import StationaryActiveCompressorProblem
from hydro_gas.stationary_equipment_solver import StationaryActiveCompressorGovernedSolveResult
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus


def _namespace(**values: object) -> SimpleNamespace:
    return SimpleNamespace(**values)


def _problem() -> StationaryActiveCompressorProblem:
    return cast(
        StationaryActiveCompressorProblem,
        _namespace(
            compressor_edges=(_namespace(compressor_id="C1", from_node_id="A", to_node_id="B"),)
        ),
    )


def _result(
    *,
    status: StationaryWeymouthSolverStatus = StationaryWeymouthSolverStatus.CONVERGED,
) -> StationaryActiveCompressorGovernedSolveResult:
    candidate = _namespace(
        node_pressures=(
            _namespace(node_id="A", pressure_pa=100_000.0),
            _namespace(node_id="B", pressure_pa=200_000.0),
        ),
        compressor_inputs=(_namespace(compressor_id="C1", mass_flow_kg_s=1.5),),
    )
    constraint = _namespace(
        compressor_id="C1",
        operating_point=_namespace(
            isentropic_efficiency=0.8,
            source_ref="supplier://map/C1",
            map_version="v1",
        ),
    )
    physical = _namespace(
        candidate=candidate,
        equipment_residuals=_namespace(compressor_constraints=(constraint,)),
    )
    solve = _namespace(
        solve_ref="solve://mixed/thermodynamic-test",
        status=status,
        final_evaluation=_namespace(physical_evaluation=physical),
    )
    return cast(StationaryActiveCompressorGovernedSolveResult, _namespace(solve=solve))


def _input() -> StationaryCompressorThermodynamicInput:
    return StationaryCompressorThermodynamicInput(
        compressor_id="C1",
        inlet_temperature_k=300.0,
        fluid=CoolPropCompressorFluidDefinition(
            fluid_name="Methane",
            source_ref="fluid://coolprop/Methane",
        ),
        inlet_kinetic_energy_j_kg=0.0,
        outlet_kinetic_energy_j_kg=0.0,
        inlet_potential_energy_j_kg=0.0,
        outlet_potential_energy_j_kg=0.0,
        heat_transfer_to_gas_w=0.0,
        state_source_ref="state://compressor/C1/thermal-input",
        property_method_ref="property-method://coolprop/PropsSI/test",
        energy_equation_ref="equation://steady-flow-energy/test",
    )


def _mixture_input() -> StationaryCompressorThermodynamicInput:
    composition = GasComposition(
        source_ref="composition://synthetic/methane-ethane/station-test-only",
        components=(
            GasComponentFraction(
                component="component-a",
                mole_fraction=0.8,
                molar_mass_kg_mol=0.01,
            ),
            GasComponentFraction(
                component="component-b",
                mole_fraction=0.2,
                molar_mass_kg_mol=0.02,
            ),
        ),
    )
    return StationaryCompressorThermodynamicInput(
        compressor_id="C1",
        inlet_temperature_k=300.0,
        fluid=CoolPropCompressorMixtureDefinition(
            composition=composition,
            component_bindings=(
                CoolPropCompressorMixtureComponentBinding(
                    composition_component="component-a",
                    coolprop_fluid="Methane",
                ),
                CoolPropCompressorMixtureComponentBinding(
                    composition_component="component-b",
                    coolprop_fluid="Ethane",
                ),
            ),
            backend="HEOS",
            source_ref="property-definition://coolprop/explicit-mixture/station-test-only",
            mapping_source_ref="mapping://synthetic-components/coolprop/station-test-only",
        ),
        inlet_kinetic_energy_j_kg=0.0,
        outlet_kinetic_energy_j_kg=0.0,
        inlet_potential_energy_j_kg=0.0,
        outlet_potential_energy_j_kg=0.0,
        heat_transfer_to_gas_w=0.0,
        state_source_ref="state://compressor/C1/thermal-mixture-input",
        property_method_ref="property-method://coolprop/AbstractState/test",
        energy_equation_ref="equation://steady-flow-energy/test",
    )


def test_mixed_post_processing_uses_solver_pressures_map_efficiency_and_explicit_energy_terms() -> (
    None
):
    assessment = evaluate_stationary_active_compressor_thermodynamics(
        _problem(),
        _result(),
        (_input(),),
    )

    assert assessment.solve_ref == "solve://mixed/thermodynamic-test"
    assert assessment.solver_status is StationaryWeymouthSolverStatus.CONVERGED
    item = assessment.compressors[0]
    assert item.compressor_id == "C1"
    assert item.mass_flow_kg_s == 1.5
    assert item.inlet_node_id == "A"
    assert item.outlet_node_id == "B"
    assert item.property_state.inlet_pressure_pa == 100_000.0
    assert item.property_state.outlet_pressure_pa == 200_000.0
    assert item.property_state.isentropic_efficiency == 0.8
    assert item.property_state.actual_outlet_temperature_k > 300.0
    assert item.energy_balance.shaft_power_input_w > 0.0
    assert item.energy_balance.heat_transfer_to_gas_w == 0.0


def test_mixed_post_processing_accepts_explicit_coolprop_mixture_without_default_composition() -> None:
    assessment = evaluate_stationary_active_compressor_thermodynamics(
        _problem(),
        _result(),
        (_mixture_input(),),
    )

    item = assessment.compressors[0]
    assert item.property_state.fluid_name == "HEOS::Methane&Ethane"
    assert item.property_state.coolprop_backend == "HEOS"
    assert (
        item.property_state.composition_source_ref
        == "composition://synthetic/methane-ethane/station-test-only"
    )
    assert item.property_state.composition_component_names == ("component-a", "component-b")
    assert item.property_state.coolprop_component_names == ("Methane", "Ethane")
    assert item.property_state.mole_fractions == (0.8, 0.2)
    assert item.property_state.actual_outlet_temperature_k > 300.0
    assert item.energy_balance.shaft_power_input_w > 0.0


def test_mixed_post_processing_preserves_non_converged_source_status() -> None:
    assessment = evaluate_stationary_active_compressor_thermodynamics(
        _problem(),
        _result(status=StationaryWeymouthSolverStatus.NON_CONVERGED),
        (_input(),),
    )

    assert assessment.solver_status is StationaryWeymouthSolverStatus.NON_CONVERGED
    assert assessment.compressors[0].solver_status is StationaryWeymouthSolverStatus.NON_CONVERGED


def test_mixed_post_processing_requires_exact_compressor_input_coverage() -> None:
    with pytest.raises(ValueError, match=r"couvrir exactement.*compresseurs actifs"):
        evaluate_stationary_active_compressor_thermodynamics(
            _problem(),
            _result(),
            (),
        )
