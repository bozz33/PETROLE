from __future__ import annotations

import json
from dataclasses import replace

import pytest

from hydro_gas.benchmark_protocol import (
    GasBenchmarkCriterionState,
    GasBenchmarkProtocolContext,
    PreRegisteredGasBenchmarkCriterion,
    materialize_approved_gas_benchmark_criteria,
)
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
from hydro_gas.coolprop_gas_property_artifact import (
    CoolPropGasMixturePropertyArtifact,
    export_coolprop_gas_mixture_property_artifact,
)
from hydro_gas.coolprop_gas_property_benchmark_adapter import (
    GasMixturePropertyBenchmarkBinding,
    GasMixturePropertyBenchmarkQuantity,
    build_coolprop_gas_property_benchmark_observations,
)


def _artifact() -> CoolPropGasMixturePropertyArtifact:
    definition = CoolPropGasMixtureDefinition(
        composition=GasComposition(
            source_ref="composition://synthetic/property-benchmark/test-only",
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
        source_ref="property-definition://coolprop/property-benchmark/test-only",
        mapping_source_ref="mapping://property-benchmark/coolprop/test-only",
    )
    result = evaluate_coolprop_gas_mixture_properties(
        definition,
        CoolPropGasMixtureStateRequest(
            temperature_k=300.0,
            pressure_pa=100_000.0,
            envelope=CoolPropEvaluationEnvelope(
                minimum_temperature_k=250.0,
                maximum_temperature_k=400.0,
                minimum_pressure_pa=50_000.0,
                maximum_pressure_pa=500_000.0,
                source_ref="envelope://property-benchmark/test-only",
            ),
            state_source_ref="state://property-benchmark/PT/test-only",
            property_method_ref="property-method://coolprop/AbstractState/PT/test-only",
        ),
    )
    return export_coolprop_gas_mixture_property_artifact(
        result,
        property_state_ref="property-state://gas/property-benchmark/test-only",
    )


def _binding(
    observation_id: str,
    quantity: GasMixturePropertyBenchmarkQuantity,
    reference_value: float,
    unit: str,
) -> GasMixturePropertyBenchmarkBinding:
    return GasMixturePropertyBenchmarkBinding(
        observation_id=observation_id,
        quantity=quantity,
        reference_value=reference_value,
        unit=unit,
        reference_source_ref=f"reference://synthetic/property-benchmark/{observation_id}",
    )


def test_property_benchmark_adapter_reads_exact_artifact_values_without_conversion() -> None:
    artifact = _artifact()
    bundle = build_coolprop_gas_property_benchmark_observations(
        artifact,
        (
            _binding("density", GasMixturePropertyBenchmarkQuantity.DENSITY, 0.75, "kg/m3"),
            _binding(
                "z",
                GasMixturePropertyBenchmarkQuantity.COMPRESSIBILITY_FACTOR,
                0.99,
                "1",
            ),
            _binding(
                "molar-mass",
                GasMixturePropertyBenchmarkQuantity.MOLAR_MASS,
                0.018,
                "kg/mol",
            ),
            _binding(
                "sound-speed",
                GasMixturePropertyBenchmarkQuantity.SPEED_OF_SOUND,
                420.0,
                "m/s",
            ),
            _binding(
                "eos-coefficient",
                GasMixturePropertyBenchmarkQuantity.EOS_PRESSURE_DENSITY_COEFFICIENT,
                130_000.0,
                "m2/s2",
            ),
        ),
    )

    assert bundle.property_state_ref == artifact.property_state_ref
    assert bundle.petrole_source_ref == artifact.evidence_ref
    assert bundle.composition_source_ref == artifact.composition_source_ref
    assert bundle.coolprop_version
    assert bundle.coolprop_gitrevision
    assert tuple(item.observation_id for item in bundle.observations) == (
        "density",
        "z",
        "molar-mass",
        "sound-speed",
        "eos-coefficient",
    )

    document = json.loads(artifact.content)
    expected_values = (
        document["properties"]["density_kg_m3"],
        document["properties"]["compressibility_factor"],
        document["properties"]["molar_mass_kg_mol"],
        document["properties"]["speed_of_sound_m_s"],
        document["diagnostics"]["eos_pressure_density_coefficient_m2_s2"],
    )
    for observation, expected_value in zip(bundle.observations, expected_values, strict=True):
        assert observation.petrole_value == expected_value
        assert observation.location_ref == artifact.property_state_ref
        assert observation.petrole_source_ref == artifact.evidence_ref
        assert observation.reference_source_ref.startswith("reference://synthetic/")


def test_property_benchmark_adapter_enforces_exact_units_and_unique_observation_ids() -> None:
    artifact = _artifact()
    with pytest.raises(ValueError, match="doit être exactement kg/m3"):
        build_coolprop_gas_property_benchmark_observations(
            artifact,
            (_binding("density", GasMixturePropertyBenchmarkQuantity.DENSITY, 0.75, "g/L"),),
        )

    duplicate = _binding("same", GasMixturePropertyBenchmarkQuantity.DENSITY, 0.75, "kg/m3")
    with pytest.raises(ValueError, match=r"identifiants d'observations.*uniques"):
        build_coolprop_gas_property_benchmark_observations(
            artifact,
            (
                duplicate,
                _binding(
                    "same",
                    GasMixturePropertyBenchmarkQuantity.COMPRESSIBILITY_FACTOR,
                    0.99,
                    "1",
                ),
            ),
        )

    with pytest.raises(ValueError, match="Au moins une référence externe"):
        build_coolprop_gas_property_benchmark_observations(artifact, ())


def test_property_benchmark_adapter_rejects_nonfinite_reference_and_tampered_artifact() -> None:
    with pytest.raises(ValueError, match="doit être finie"):
        _binding(
            "density",
            GasMixturePropertyBenchmarkQuantity.DENSITY,
            float("inf"),
            "kg/m3",
        )

    artifact = _artifact()
    with pytest.raises(ValueError, match="SHA-256"):
        replace(artifact, content=artifact.content + b" ")


def test_property_observation_can_only_become_evaluable_through_explicit_approved_criterion() -> None:
    artifact = _artifact()
    bundle = build_coolprop_gas_property_benchmark_observations(
        artifact,
        (_binding("density", GasMixturePropertyBenchmarkQuantity.DENSITY, 0.75, "kg/m3"),),
    )
    observation = bundle.observations[0]
    context = GasBenchmarkProtocolContext(
        protocol_ref="protocol://gas/properties/synthetic-test/v1",
        model_id="coolprop-explicit-mixture-properties",
        model_version="abstractstate-pt-runtime-v1",
        formulation_ref="formulation://coolprop/AbstractState/PT/test-only",
        case_ref="case://gas/properties/synthetic-test-only",
    )
    criterion = PreRegisteredGasBenchmarkCriterion(
        criterion_id="criterion-density-synthetic-test",
        criterion_version="1",
        protocol_ref=context.protocol_ref,
        model_id=context.model_id,
        model_version=context.model_version,
        formulation_ref=context.formulation_ref,
        case_ref=context.case_ref,
        observation_id=observation.observation_id,
        quantity_ref=observation.quantity_ref,
        unit=observation.unit,
        source_ref="criterion-source://synthetic/property-benchmark/test-only",
        registration_ref="registration://synthetic/property-benchmark/test-only",
        state=GasBenchmarkCriterionState.APPROVED,
        approval_ref="approval://synthetic/property-benchmark/test-only",
        maximum_absolute_error=0.1,
    )

    approved = materialize_approved_gas_benchmark_criteria(
        context=context,
        criteria=(criterion,),
        observations=bundle.observations,
    )

    assert approved.criterion_ids == ("criterion-density-synthetic-test",)
    assert approved.criteria[0].observation_id == "density"
    assert approved.criteria[0].maximum_absolute_error == 0.1
    assert approved.approval_refs == ("approval://synthetic/property-benchmark/test-only",)
