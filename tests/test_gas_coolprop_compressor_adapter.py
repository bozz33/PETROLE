from __future__ import annotations

import pytest

from hydro_gas.coolprop_compressor_adapter import (
    CoolPropCompressorFluidDefinition,
    CoolPropCompressorStateRequest,
    evaluate_coolprop_compressor_states,
)


def test_coolprop_compressor_states_compute_isentropic_and_actual_outlet() -> None:
    result = evaluate_coolprop_compressor_states(
        CoolPropCompressorFluidDefinition(
            fluid_name="Methane",
            source_ref="fluid://coolprop/Methane",
        ),
        CoolPropCompressorStateRequest(
            compressor_id="C1",
            inlet_pressure_pa=100_000.0,
            inlet_temperature_k=300.0,
            outlet_pressure_pa=200_000.0,
            isentropic_efficiency=0.8,
            state_source_ref="state://compressor/C1/test",
            efficiency_source_ref="map://compressor/C1/test",
            property_method_ref="property-method://coolprop/PropsSI/test",
        ),
    )

    assert result.fluid_name == "Methane"
    assert result.coolprop_version
    assert result.inlet_enthalpy_j_kg > 0.0
    assert result.isentropic_outlet_enthalpy_j_kg > result.inlet_enthalpy_j_kg
    assert result.actual_outlet_enthalpy_j_kg > result.isentropic_outlet_enthalpy_j_kg
    assert result.isentropic_outlet_temperature_k > result.inlet_temperature_k
    assert result.actual_outlet_temperature_k > result.isentropic_outlet_temperature_k
    assert result.isentropic_efficiency == 0.8


def test_coolprop_compressor_request_requires_active_compression_and_explicit_efficiency() -> None:
    with pytest.raises(ValueError, match="pression supérieure"):
        CoolPropCompressorStateRequest(
            compressor_id="C1",
            inlet_pressure_pa=200_000.0,
            inlet_temperature_k=300.0,
            outlet_pressure_pa=100_000.0,
            isentropic_efficiency=0.8,
            state_source_ref="state://compressor/C1/test",
            efficiency_source_ref="map://compressor/C1/test",
            property_method_ref="property-method://coolprop/PropsSI/test",
        )

    with pytest.raises(ValueError, match="rendement isentropique"):
        CoolPropCompressorStateRequest(
            compressor_id="C1",
            inlet_pressure_pa=100_000.0,
            inlet_temperature_k=300.0,
            outlet_pressure_pa=200_000.0,
            isentropic_efficiency=1.1,
            state_source_ref="state://compressor/C1/test",
            efficiency_source_ref="map://compressor/C1/test",
            property_method_ref="property-method://coolprop/PropsSI/test",
        )


def test_coolprop_compressor_fluid_requires_exact_identity_and_source() -> None:
    with pytest.raises(ValueError, match="fluide CoolProp"):
        CoolPropCompressorFluidDefinition(fluid_name="", source_ref="fluid://missing")
