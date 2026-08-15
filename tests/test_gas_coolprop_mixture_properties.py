from __future__ import annotations

import math

import pytest

from hydro_gas.composition import GasComponentFraction, GasComposition
from hydro_gas.coolprop_adapter import CoolPropEvaluationEnvelope
from hydro_gas.coolprop_gas_mixture import (
    CoolPropGasMixtureComponentBinding,
    CoolPropGasMixtureDefinition,
)
from hydro_gas.coolprop_gas_properties import (
    CoolPropGasMixtureStateRequest,
    evaluate_coolprop_gas_mixture_properties,
)


def _definition() -> CoolPropGasMixtureDefinition:
    return CoolPropGasMixtureDefinition(
        composition=GasComposition(
            source_ref="composition://synthetic/network-property/test-only",
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
            CoolPropGasMixtureComponentBinding(
                composition_component="component-b",
                coolprop_fluid="Ethane",
            ),
            CoolPropGasMixtureComponentBinding(
                composition_component="component-a",
                coolprop_fluid="Methane",
            ),
        ),
        backend="HEOS",
        source_ref="property-definition://coolprop/network-mixture/test-only",
        mapping_source_ref="mapping://synthetic-network-components/coolprop/test-only",
    )


def _request(
    *,
    temperature_k: float = 300.0,
    pressure_pa: float = 100_000.0,
) -> CoolPropGasMixtureStateRequest:
    return CoolPropGasMixtureStateRequest(
        temperature_k=temperature_k,
        pressure_pa=pressure_pa,
        envelope=CoolPropEvaluationEnvelope(
            minimum_temperature_k=250.0,
            maximum_temperature_k=400.0,
            minimum_pressure_pa=50_000.0,
            maximum_pressure_pa=500_000.0,
            source_ref="envelope://gas-mixture-property/test-only",
        ),
        state_source_ref="state://gas-mixture-property/PT/test-only",
        property_method_ref="property-method://coolprop/AbstractState/PT/test-only",
    )


def test_explicit_mixture_properties_execute_real_coolprop_and_keep_provenance() -> None:
    definition = _definition()
    result = evaluate_coolprop_gas_mixture_properties(definition, _request())

    assert definition.composition_component_names == ("component-a", "component-b")
    assert definition.coolprop_component_names == ("Methane", "Ethane")
    assert definition.mole_fractions == (0.8, 0.2)
    assert result.fluid_name == "HEOS::Methane&Ethane"
    assert result.coolprop_backend == "HEOS"
    assert result.coolprop_version
    assert result.coolprop_gitrevision
    assert result.temperature_k == 300.0
    assert result.pressure_pa == 100_000.0
    assert result.density_kg_m3 > 0.0
    assert result.compressibility_factor > 0.0
    assert result.molar_mass_kg_mol > 0.0
    assert result.speed_of_sound_m_s > 0.0
    assert result.gas_constant_j_mol_k > 0.0
    assert result.density_from_eos_kg_m3 > 0.0
    assert math.isfinite(result.density_eos_residual_kg_m3)
    assert result.density_eos_residual_kg_m3 == (
        result.density_kg_m3 - result.density_from_eos_kg_m3
    )
    assert result.composition_source_ref == "composition://synthetic/network-property/test-only"
    assert (
        result.component_mapping_source_ref
        == "mapping://synthetic-network-components/coolprop/test-only"
    )
    assert result.mixture_definition_source_ref == (
        "property-definition://coolprop/network-mixture/test-only"
    )
    assert result.envelope_source_ref == "envelope://gas-mixture-property/test-only"
    assert result.state_source_ref == "state://gas-mixture-property/PT/test-only"
    assert result.property_method_ref == "property-method://coolprop/AbstractState/PT/test-only"
    assert result.qualification_claim is False
    assert result.certification_claim is False


def test_mixture_property_request_fails_before_coolprop_outside_project_envelope() -> None:
    with pytest.raises(ValueError, match="hors du domaine projet CoolProp"):
        _request(temperature_k=450.0)

    with pytest.raises(ValueError, match="hors du domaine projet CoolProp"):
        _request(pressure_pa=600_000.0)


def test_mixture_property_request_requires_state_and_method_provenance() -> None:
    envelope = CoolPropEvaluationEnvelope(
        minimum_temperature_k=250.0,
        maximum_temperature_k=400.0,
        minimum_pressure_pa=50_000.0,
        maximum_pressure_pa=500_000.0,
        source_ref="envelope://gas-mixture-property/test-only",
    )
    with pytest.raises(ValueError, match="doivent être référencés"):
        CoolPropGasMixtureStateRequest(
            temperature_k=300.0,
            pressure_pa=100_000.0,
            envelope=envelope,
            state_source_ref="",
            property_method_ref="property-method://coolprop/test-only",
        )
