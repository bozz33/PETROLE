from __future__ import annotations

import pytest

from hydro_gas.composition import GasComponentFraction, GasComposition
from hydro_gas.coolprop_compressor_adapter import (
    CoolPropCompressorFluidDefinition,
    CoolPropCompressorMixtureComponentBinding,
    CoolPropCompressorMixtureDefinition,
    CoolPropCompressorStateRequest,
    evaluate_coolprop_compressor_states,
)


def _request() -> CoolPropCompressorStateRequest:
    return CoolPropCompressorStateRequest(
        compressor_id="C1",
        inlet_pressure_pa=100_000.0,
        inlet_temperature_k=300.0,
        outlet_pressure_pa=200_000.0,
        isentropic_efficiency=0.8,
        state_source_ref="state://compressor/C1/test",
        efficiency_source_ref="map://compressor/C1/test",
        property_method_ref="property-method://coolprop/test",
    )


def _synthetic_mixture() -> CoolPropCompressorMixtureDefinition:
    return CoolPropCompressorMixtureDefinition(
        composition=GasComposition(
            source_ref="composition://synthetic/methane-ethane/test-only",
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
        ),
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
        source_ref="property-definition://coolprop/explicit-mixture/test-only",
        mapping_source_ref="mapping://synthetic-components/coolprop/test-only",
    )


def test_coolprop_compressor_states_compute_isentropic_and_actual_outlet() -> None:
    result = evaluate_coolprop_compressor_states(
        CoolPropCompressorFluidDefinition(
            fluid_name="Methane",
            source_ref="fluid://coolprop/Methane",
        ),
        _request(),
    )

    assert result.fluid_name == "Methane"
    assert result.coolprop_version
    assert result.coolprop_gitrevision
    assert result.coolprop_backend is None
    assert result.composition_source_ref is None
    assert result.component_mapping_source_ref is None
    assert result.composition_component_names == ()
    assert result.coolprop_component_names == ()
    assert result.mole_fractions == ()
    assert result.inlet_enthalpy_j_kg > 0.0
    assert result.isentropic_outlet_enthalpy_j_kg > result.inlet_enthalpy_j_kg
    assert result.actual_outlet_enthalpy_j_kg > result.isentropic_outlet_enthalpy_j_kg
    assert result.isentropic_outlet_temperature_k > result.inlet_temperature_k
    assert result.actual_outlet_temperature_k > result.isentropic_outlet_temperature_k
    assert result.isentropic_efficiency == 0.8


def test_coolprop_explicit_mixture_uses_exact_composition_and_component_mapping() -> None:
    mixture = _synthetic_mixture()

    result = evaluate_coolprop_compressor_states(mixture, _request())

    assert result.fluid_name == "HEOS::Methane&Ethane"
    assert result.coolprop_backend == "HEOS"
    assert result.composition_source_ref == "composition://synthetic/methane-ethane/test-only"
    assert (
        result.component_mapping_source_ref == "mapping://synthetic-components/coolprop/test-only"
    )
    assert result.composition_component_names == ("component-a", "component-b")
    assert result.coolprop_component_names == ("Methane", "Ethane")
    assert result.mole_fractions == (0.8, 0.2)
    assert result.fluid_source_ref == "property-definition://coolprop/explicit-mixture/test-only"
    assert result.coolprop_version
    assert result.coolprop_gitrevision
    assert result.isentropic_outlet_enthalpy_j_kg > result.inlet_enthalpy_j_kg
    assert result.actual_outlet_enthalpy_j_kg > result.isentropic_outlet_enthalpy_j_kg
    assert result.isentropic_outlet_temperature_k > result.inlet_temperature_k
    assert result.actual_outlet_temperature_k > result.isentropic_outlet_temperature_k


def test_coolprop_mixture_requires_exact_unique_component_mapping() -> None:
    composition = _synthetic_mixture().composition

    with pytest.raises(ValueError, match="couvrir exactement les composants"):
        CoolPropCompressorMixtureDefinition(
            composition=composition,
            component_bindings=(
                CoolPropCompressorMixtureComponentBinding(
                    composition_component="component-a",
                    coolprop_fluid="Methane",
                ),
            ),
            backend="HEOS",
            source_ref="property-definition://coolprop/invalid/test",
            mapping_source_ref="mapping://invalid/test",
        )

    with pytest.raises(ValueError, match=r"composants PETROLE du mapping.*uniques"):
        CoolPropCompressorMixtureDefinition(
            composition=composition,
            component_bindings=(
                CoolPropCompressorMixtureComponentBinding(
                    composition_component="component-a",
                    coolprop_fluid="Methane",
                ),
                CoolPropCompressorMixtureComponentBinding(
                    composition_component="component-a",
                    coolprop_fluid="Ethane",
                ),
            ),
            backend="HEOS",
            source_ref="property-definition://coolprop/invalid/test",
            mapping_source_ref="mapping://invalid/test",
        )

    with pytest.raises(ValueError, match="fluide CoolProp distinct"):
        CoolPropCompressorMixtureDefinition(
            composition=composition,
            component_bindings=(
                CoolPropCompressorMixtureComponentBinding(
                    composition_component="component-a",
                    coolprop_fluid="Methane",
                ),
                CoolPropCompressorMixtureComponentBinding(
                    composition_component="component-b",
                    coolprop_fluid="Methane",
                ),
            ),
            backend="HEOS",
            source_ref="property-definition://coolprop/invalid/test",
            mapping_source_ref="mapping://invalid/test",
        )


def test_coolprop_simple_fluid_and_component_binding_reject_hidden_mixture_syntax() -> None:
    with pytest.raises(ValueError, match="ne peut pas masquer une syntaxe de mélange"):
        CoolPropCompressorFluidDefinition(
            fluid_name="Methane&Ethane",
            source_ref="fluid://invalid/encoded-mixture",
        )

    with pytest.raises(ValueError, match="ne peut pas masquer une syntaxe de mélange"):
        CoolPropCompressorFluidDefinition(
            fluid_name="Amarillo.mix",
            source_ref="fluid://invalid/predefined-mixture",
        )

    with pytest.raises(ValueError, match="fluide CoolProp simple"):
        CoolPropCompressorMixtureComponentBinding(
            composition_component="component-a",
            coolprop_fluid="HEOS::Methane",
        )


def test_coolprop_mixture_requires_explicit_backend_and_mapping_provenance() -> None:
    composition = _synthetic_mixture().composition
    bindings = _synthetic_mixture().component_bindings

    with pytest.raises(ValueError, match=r"backend.*provenance"):
        CoolPropCompressorMixtureDefinition(
            composition=composition,
            component_bindings=bindings,
            backend="",
            source_ref="property-definition://coolprop/test",
            mapping_source_ref="mapping://test",
        )

    with pytest.raises(ValueError, match="sans séparateur"):
        CoolPropCompressorMixtureDefinition(
            composition=composition,
            component_bindings=bindings,
            backend="HEOS::",
            source_ref="property-definition://coolprop/test",
            mapping_source_ref="mapping://test",
        )


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
            property_method_ref="property-method://coolprop/test",
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
            property_method_ref="property-method://coolprop/test",
        )


def test_coolprop_compressor_fluid_requires_exact_identity_and_source() -> None:
    with pytest.raises(ValueError, match="fluide CoolProp"):
        CoolPropCompressorFluidDefinition(fluid_name="", source_ref="fluid://missing")
