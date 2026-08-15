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
    COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID,
    COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION,
    CoolPropGasMixturePropertyArtifact,
    export_coolprop_gas_mixture_property_artifact,
)
from hydro_gas.coolprop_gas_property_benchmark_adapter import (
    GasMixturePropertyBenchmarkBinding,
    GasMixturePropertyBenchmarkObservationBundle,
    GasMixturePropertyBenchmarkQuantity,
    build_coolprop_gas_property_benchmark_observations,
)
from hydro_gas.coolprop_gas_property_benchmark_evidence import (
    COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_REF_PREFIX,
    COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_SCHEMA_VERSION,
    CoolPropGasPropertyBenchmarkEvidenceArtifact,
    export_coolprop_gas_property_benchmark_evidence,
)


def _artifact() -> CoolPropGasMixturePropertyArtifact:
    definition = CoolPropGasMixtureDefinition(
        composition=GasComposition(
            source_ref="composition://synthetic/property-evidence/test-only",
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
        source_ref="property-definition://coolprop/property-evidence/test-only",
        mapping_source_ref="mapping://property-evidence/coolprop/test-only",
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
                source_ref="envelope://property-evidence/test-only",
            ),
            state_source_ref="state://property-evidence/PT/test-only",
            property_method_ref="property-method://coolprop/AbstractState/PT/test-only",
        ),
    )
    return export_coolprop_gas_mixture_property_artifact(
        result,
        property_state_ref="property-state://gas/property-evidence/test-only",
    )


def _bundle(
    artifact: CoolPropGasMixturePropertyArtifact,
) -> GasMixturePropertyBenchmarkObservationBundle:
    return build_coolprop_gas_property_benchmark_observations(
        artifact,
        (
            GasMixturePropertyBenchmarkBinding(
                observation_id="density",
                quantity=GasMixturePropertyBenchmarkQuantity.DENSITY,
                reference_value=0.75,
                unit="kg/m3",
                reference_source_ref="reference://synthetic/property-evidence/density/test-only",
            ),
            GasMixturePropertyBenchmarkBinding(
                observation_id="z",
                quantity=GasMixturePropertyBenchmarkQuantity.COMPRESSIBILITY_FACTOR,
                reference_value=0.99,
                unit="1",
                reference_source_ref="reference://synthetic/property-evidence/z/test-only",
            ),
        ),
    )


def _context() -> GasBenchmarkProtocolContext:
    return GasBenchmarkProtocolContext(
        protocol_ref="protocol://gas/properties/synthetic-evidence-test/v1",
        model_id=COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID,
        model_version=COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION,
        formulation_ref="formulation://coolprop/AbstractState/PT/synthetic-test-only",
        case_ref="case://gas/properties/synthetic-evidence-test-only",
    )


def _criterion(
    observation_id: str,
    quantity_ref: str,
    unit: str,
    *,
    absolute_error: float | None = None,
    relative_error: float | None = None,
) -> PreRegisteredGasBenchmarkCriterion:
    context = _context()
    return PreRegisteredGasBenchmarkCriterion(
        criterion_id=f"criterion-{observation_id}-synthetic-test",
        criterion_version="1",
        protocol_ref=context.protocol_ref,
        model_id=context.model_id,
        model_version=context.model_version,
        formulation_ref=context.formulation_ref,
        case_ref=context.case_ref,
        observation_id=observation_id,
        quantity_ref=quantity_ref,
        unit=unit,
        source_ref=f"criterion-source://synthetic/property-evidence/{observation_id}/test-only",
        registration_ref=f"registration://synthetic/property-evidence/{observation_id}/test-only",
        state=GasBenchmarkCriterionState.APPROVED,
        approval_ref=f"approval://synthetic/property-evidence/{observation_id}/test-only",
        maximum_absolute_error=absolute_error,
        maximum_relative_error_fraction=relative_error,
    )


def _approved(bundle: GasMixturePropertyBenchmarkObservationBundle):
    density, z = bundle.observations
    return materialize_approved_gas_benchmark_criteria(
        context=_context(),
        criteria=(
            _criterion(
                density.observation_id,
                density.quantity_ref,
                density.unit,
                absolute_error=0.1,
            ),
            _criterion(
                z.observation_id,
                z.quantity_ref,
                z.unit,
                relative_error=0.02,
            ),
        ),
        observations=bundle.observations,
    )


def _export(
    artifact: CoolPropGasMixturePropertyArtifact,
    bundle: GasMixturePropertyBenchmarkObservationBundle,
) -> CoolPropGasPropertyBenchmarkEvidenceArtifact:
    return export_coolprop_gas_property_benchmark_evidence(
        bundle,
        _approved(bundle),
        _context(),
        reference_system_ref="reference-system://synthetic/property-evidence/test-only",
        reference_input_sha256="A" * 64,
        reference_output_sha256="B" * 64,
        evidence_source_ref="evidence-source://synthetic/property-evidence/test-only",
        review_ref="review://synthetic/property-evidence/test-only",
    )


def test_property_benchmark_evidence_is_canonical_and_preserves_approved_limits() -> None:
    artifact = _artifact()
    bundle = _bundle(artifact)

    first = _export(artifact, bundle)
    second = _export(artifact, bundle)

    assert first.schema_version == COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_SCHEMA_VERSION
    assert first.content == second.content
    assert first.sha256 == second.sha256
    assert (
        first.evidence_ref
        == f"{COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_REF_PREFIX}{first.sha256}"
    )

    document = json.loads(first.content)
    assert document["protocol"]["protocol_ref"] == _context().protocol_ref
    assert document["protocol"]["model_id"] == COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID
    assert document["petrole"]["property_artifact_sha256"] == artifact.sha256
    assert document["petrole"]["source_ref"] == artifact.evidence_ref
    assert document["petrole"]["coolprop_version"] == bundle.coolprop_version
    assert document["petrole"]["coolprop_gitrevision"] == bundle.coolprop_gitrevision
    assert document["reference"]["input_sha256"] == "a" * 64
    assert document["reference"]["output_sha256"] == "b" * 64
    assert document["criteria"][0]["maximum_absolute_error"] == 0.1
    assert document["criteria"][0]["maximum_relative_error_fraction"] is None
    assert document["criteria"][1]["maximum_absolute_error"] is None
    assert document["criteria"][1]["maximum_relative_error_fraction"] == 0.02
    assert document["criteria"][0]["approval_ref"].startswith("approval://synthetic/")
    assert document["criteria"][0]["registration_ref"].startswith("registration://synthetic/")
    assert document["criteria"][0]["criterion_source_ref"].startswith(
        "criterion-source://synthetic/"
    )
    assert document["claims"] == {
        "qualification_claim": False,
        "certification_claim": False,
    }


def test_property_benchmark_evidence_rejects_protocol_or_model_context_mismatch() -> None:
    artifact = _artifact()
    bundle = _bundle(artifact)
    approved = _approved(bundle)

    with pytest.raises(ValueError, match="protocole demandé"):
        export_coolprop_gas_property_benchmark_evidence(
            bundle,
            replace(approved, protocol_ref="protocol://other"),
            _context(),
            reference_system_ref="reference-system://synthetic/test-only",
            reference_input_sha256="a" * 64,
            reference_output_sha256="b" * 64,
            evidence_source_ref="evidence-source://synthetic/test-only",
        )

    with pytest.raises(ValueError, match="modèle de propriétés P6-A"):
        export_coolprop_gas_property_benchmark_evidence(
            bundle,
            approved,
            replace(_context(), model_id="other-model"),
            reference_system_ref="reference-system://synthetic/test-only",
            reference_input_sha256="a" * 64,
            reference_output_sha256="b" * 64,
            evidence_source_ref="evidence-source://synthetic/test-only",
        )

    with pytest.raises(ValueError, match="version du modèle P6-A"):
        export_coolprop_gas_property_benchmark_evidence(
            bundle,
            approved,
            replace(_context(), model_version="other-version"),
            reference_system_ref="reference-system://synthetic/test-only",
            reference_input_sha256="a" * 64,
            reference_output_sha256="b" * 64,
            evidence_source_ref="evidence-source://synthetic/test-only",
        )


def test_property_benchmark_evidence_rejects_bad_hash_blank_review_and_source_drift() -> None:
    artifact = _artifact()
    bundle = _bundle(artifact)
    approved = _approved(bundle)

    with pytest.raises(ValueError, match="SHA-256"):
        export_coolprop_gas_property_benchmark_evidence(
            bundle,
            approved,
            _context(),
            reference_system_ref="reference-system://synthetic/test-only",
            reference_input_sha256="bad-hash",
            reference_output_sha256="b" * 64,
            evidence_source_ref="evidence-source://synthetic/test-only",
        )

    with pytest.raises(ValueError, match="référence de revue"):
        export_coolprop_gas_property_benchmark_evidence(
            bundle,
            approved,
            _context(),
            reference_system_ref="reference-system://synthetic/test-only",
            reference_input_sha256="a" * 64,
            reference_output_sha256="b" * 64,
            evidence_source_ref="evidence-source://synthetic/test-only",
            review_ref=" ",
        )

    with pytest.raises(ValueError, match="artefact P6-A canonique"):
        export_coolprop_gas_property_benchmark_evidence(
            replace(bundle, petrole_source_ref="result://not-canonical"),
            approved,
            _context(),
            reference_system_ref="reference-system://synthetic/test-only",
            reference_input_sha256="a" * 64,
            reference_output_sha256="b" * 64,
            evidence_source_ref="evidence-source://synthetic/test-only",
        )


def test_property_benchmark_evidence_requires_exact_criterion_coverage() -> None:
    artifact = _artifact()
    bundle = _bundle(artifact)
    density = bundle.observations[0]
    partial = materialize_approved_gas_benchmark_criteria(
        context=_context(),
        criteria=(
            _criterion(
                density.observation_id,
                density.quantity_ref,
                density.unit,
                absolute_error=0.1,
            ),
        ),
        observations=bundle.observations,
    )

    with pytest.raises(ValueError, match="couvrir exactement"):
        export_coolprop_gas_property_benchmark_evidence(
            bundle,
            partial,
            _context(),
            reference_system_ref="reference-system://synthetic/test-only",
            reference_input_sha256="a" * 64,
            reference_output_sha256="b" * 64,
            evidence_source_ref="evidence-source://synthetic/test-only",
        )


def test_property_benchmark_evidence_artifact_detects_content_tampering() -> None:
    artifact = _artifact()
    exported = _export(artifact, _bundle(artifact))

    with pytest.raises(ValueError, match="empreinte"):
        replace(exported, content=exported.content + b" ")
