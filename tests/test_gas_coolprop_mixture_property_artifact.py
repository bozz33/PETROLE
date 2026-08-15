from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from hydro_gas.composition import GasComponentFraction, GasComposition
from hydro_gas.coolprop_adapter import CoolPropEvaluationEnvelope
from hydro_gas.coolprop_gas_mixture import (
    CoolPropGasMixtureComponentBinding,
    CoolPropGasMixtureDefinition,
)
from hydro_gas.coolprop_gas_properties import (
    CoolPropGasMixturePropertyResult,
    CoolPropGasMixtureStateRequest,
    evaluate_coolprop_gas_mixture_properties,
)
from hydro_gas.coolprop_gas_property_artifact import (
    COOLPROP_GAS_MIXTURE_PROPERTY_EVIDENCE_REF_PREFIX,
    COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID,
    COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION,
    COOLPROP_GAS_MIXTURE_PROPERTY_SCHEMA_VERSION,
    export_coolprop_gas_mixture_property_artifact,
)


def _result() -> CoolPropGasMixturePropertyResult:
    definition = CoolPropGasMixtureDefinition(
        composition=GasComposition(
            source_ref="composition://synthetic/property-artifact/test-only",
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
                composition_component="component-a",
                coolprop_fluid="Methane",
            ),
            CoolPropGasMixtureComponentBinding(
                composition_component="component-b",
                coolprop_fluid="Ethane",
            ),
        ),
        backend="HEOS",
        source_ref="property-definition://coolprop/property-artifact/test-only",
        mapping_source_ref="mapping://property-artifact/coolprop/test-only",
    )
    request = CoolPropGasMixtureStateRequest(
        temperature_k=300.0,
        pressure_pa=100_000.0,
        envelope=CoolPropEvaluationEnvelope(
            minimum_temperature_k=250.0,
            maximum_temperature_k=400.0,
            minimum_pressure_pa=50_000.0,
            maximum_pressure_pa=500_000.0,
            source_ref="envelope://property-artifact/test-only",
        ),
        state_source_ref="state://property-artifact/PT/test-only",
        property_method_ref="property-method://coolprop/AbstractState/PT/test-only",
    )
    return evaluate_coolprop_gas_mixture_properties(definition, request)


def test_property_artifact_is_canonical_hashed_and_complete() -> None:
    result = _result()
    first = export_coolprop_gas_mixture_property_artifact(
        result,
        property_state_ref="property-state://gas/PT/test-only",
    )
    second = export_coolprop_gas_mixture_property_artifact(
        result,
        property_state_ref="property-state://gas/PT/test-only",
    )

    assert first.content == second.content
    assert first.sha256 == second.sha256
    assert first.sha256 == hashlib.sha256(first.content).hexdigest()
    assert first.schema_version == COOLPROP_GAS_MIXTURE_PROPERTY_SCHEMA_VERSION
    assert first.model_id == COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID
    assert first.model_version == COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION
    assert (
        first.evidence_ref
        == f"{COOLPROP_GAS_MIXTURE_PROPERTY_EVIDENCE_REF_PREFIX}{first.sha256}"
    )

    document = json.loads(first.content)
    assert document["property_state_ref"] == "property-state://gas/PT/test-only"
    assert document["state"]["temperature_k"] == 300.0
    assert document["state"]["pressure_pa"] == 100_000.0
    assert document["mixture"]["composition_source_ref"] == (
        "composition://synthetic/property-artifact/test-only"
    )
    assert document["mixture"]["coolprop_component_names"] == ["Methane", "Ethane"]
    assert document["mixture"]["mole_fractions"] == [0.8, 0.2]
    assert document["runtime"]["coolprop_version"] == result.coolprop_version
    assert document["runtime"]["coolprop_gitrevision"] == result.coolprop_gitrevision
    assert document["properties"]["density_kg_m3"] == result.density_kg_m3
    assert document["properties"]["speed_of_sound_m_s"] == result.speed_of_sound_m_s
    assert document["diagnostics"]["eos_pressure_density_scale_m_s"] == (
        result.eos_pressure_density_scale_m_s
    )
    assert document["diagnostics"]["molar_mass_residual_kg_mol"] == (
        result.molar_mass_residual_kg_mol
    )
    assert document["claims"]["qualification_claim"] is False
    assert document["claims"]["certification_claim"] is False
    assert "weymouth" not in first.content.decode("utf-8").lower()


def test_property_artifact_rejects_tampering_and_empty_state_reference() -> None:
    result = _result()
    artifact = export_coolprop_gas_mixture_property_artifact(
        result,
        property_state_ref="property-state://gas/PT/test-only",
    )

    with pytest.raises(ValueError, match="SHA-256"):
        replace(artifact, content=artifact.content + b" ")

    with pytest.raises(ValueError, match="référence de l'état"):
        export_coolprop_gas_mixture_property_artifact(result, property_state_ref="  ")


def test_property_artifact_rejects_claims_in_source_result() -> None:
    result = _result()
    with pytest.raises(ValueError, match="qualification/certification"):
        export_coolprop_gas_mixture_property_artifact(
            replace(result, qualification_claim=True),
            property_state_ref="property-state://gas/PT/test-only",
        )
