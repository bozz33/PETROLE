from __future__ import annotations

import pytest

from hydro_gas.compressor_map import CompressorOperatingPoint
from hydro_gas.compressor_thermodynamics import (
    IsentropicCompressorEnthalpyClosure,
    SteadyCompressorEnergyObservation,
    build_isentropic_closure_from_map,
    evaluate_isentropic_compressor_enthalpy_closure,
    evaluate_steady_compressor_energy_balance,
)


def test_steady_energy_balance_keeps_all_supplied_terms_and_sign_convention() -> None:
    result = evaluate_steady_compressor_energy_balance(
        SteadyCompressorEnergyObservation(
            compressor_id="C1",
            mass_flow_kg_s=2.0,
            inlet_enthalpy_j_kg=100_000.0,
            outlet_enthalpy_j_kg=130_000.0,
            inlet_kinetic_energy_j_kg=50.0,
            outlet_kinetic_energy_j_kg=70.0,
            inlet_potential_energy_j_kg=10.0,
            outlet_potential_energy_j_kg=15.0,
            heat_transfer_to_gas_w=1_000.0,
            state_source_ref="state://compressor/C1/energy",
            equation_ref="equation://steady-flow-energy/test",
        )
    )

    assert result.enthalpy_rise_j_kg == 30_000.0
    assert result.kinetic_energy_change_j_kg == 20.0
    assert result.potential_energy_change_j_kg == 5.0
    assert result.total_specific_energy_rise_j_kg == 30_025.0
    assert result.shaft_power_input_w == 59_050.0
    assert result.heat_transfer_to_gas_w == 1_000.0


def test_isentropic_closure_uses_explicit_efficiency_without_property_lookup() -> None:
    result = evaluate_isentropic_compressor_enthalpy_closure(
        IsentropicCompressorEnthalpyClosure(
            compressor_id="C1",
            inlet_enthalpy_j_kg=100_000.0,
            isentropic_outlet_enthalpy_j_kg=120_000.0,
            isentropic_efficiency=0.8,
            property_source_ref="property://synthetic/test",
            efficiency_source_ref="map://synthetic/test",
            equation_ref="equation://isentropic-efficiency/test",
        )
    )

    assert result.isentropic_specific_work_j_kg == 20_000.0
    assert result.actual_specific_work_j_kg == 25_000.0
    assert result.actual_outlet_enthalpy_j_kg == 125_000.0
    assert result.isentropic_efficiency == 0.8


def test_isentropic_closure_can_use_efficiency_from_exact_map_operating_point() -> None:
    operating_point = CompressorOperatingPoint(
        speed_rpm=10_000.0,
        mass_flow_kg_s=5.0,
        pressure_ratio=1.8,
        isentropic_efficiency=0.75,
        source_ref="supplier://map/C1",
        map_version="v7",
    )
    closure = build_isentropic_closure_from_map(
        operating_point,
        compressor_id="C1",
        inlet_enthalpy_j_kg=200_000.0,
        isentropic_outlet_enthalpy_j_kg=230_000.0,
        property_source_ref="property://gas/state/v1",
        equation_ref="equation://isentropic-efficiency/v1",
    )

    assert closure.isentropic_efficiency == 0.75
    assert closure.efficiency_source_ref == "supplier://map/C1#map-version/v7"
    result = evaluate_isentropic_compressor_enthalpy_closure(closure)
    assert result.actual_outlet_enthalpy_j_kg == 240_000.0


def test_thermodynamic_inputs_fail_closed_on_invalid_efficiency_or_energy() -> None:
    with pytest.raises(ValueError, match="rendement isentropique"):
        IsentropicCompressorEnthalpyClosure(
            compressor_id="C1",
            inlet_enthalpy_j_kg=100_000.0,
            isentropic_outlet_enthalpy_j_kg=120_000.0,
            isentropic_efficiency=0.0,
            property_source_ref="property://synthetic/test",
            efficiency_source_ref="map://synthetic/test",
            equation_ref="equation://isentropic-efficiency/test",
        )

    with pytest.raises(ValueError, match="ne peut pas être inférieure"):
        IsentropicCompressorEnthalpyClosure(
            compressor_id="C1",
            inlet_enthalpy_j_kg=120_000.0,
            isentropic_outlet_enthalpy_j_kg=100_000.0,
            isentropic_efficiency=0.8,
            property_source_ref="property://synthetic/test",
            efficiency_source_ref="map://synthetic/test",
            equation_ref="equation://isentropic-efficiency/test",
        )

    with pytest.raises(ValueError, match="énergies cinétiques"):
        SteadyCompressorEnergyObservation(
            compressor_id="C1",
            mass_flow_kg_s=1.0,
            inlet_enthalpy_j_kg=100_000.0,
            outlet_enthalpy_j_kg=110_000.0,
            inlet_kinetic_energy_j_kg=-1.0,
            outlet_kinetic_energy_j_kg=0.0,
            inlet_potential_energy_j_kg=0.0,
            outlet_potential_energy_j_kg=0.0,
            heat_transfer_to_gas_w=0.0,
            state_source_ref="state://compressor/C1/energy",
            equation_ref="equation://steady-flow-energy/test",
        )
