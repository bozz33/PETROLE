from __future__ import annotations

from dataclasses import replace

import pytest

from hydro_gas.benchmark_protocol import (
    GasBenchmarkCriterionState,
    GasBenchmarkProtocolContext,
    PreRegisteredGasBenchmarkCriterion,
    materialize_approved_gas_benchmark_criteria,
)
from hydro_gas.coolprop_gas_property_artifact import (
    COOLPROP_GAS_MIXTURE_PROPERTY_EVIDENCE_REF_PREFIX,
    COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID,
    COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION,
)
from hydro_gas.coolprop_gas_property_benchmark_adapter import (
    GasMixturePropertyBenchmarkObservationBundle,
)
from hydro_gas.coolprop_gas_property_benchmark_assessment import (
    assess_coolprop_gas_property_benchmark_evidence,
)
from hydro_gas.coolprop_gas_property_benchmark_evidence import (
    export_coolprop_gas_property_benchmark_evidence,
)
from hydro_gas.external_benchmark import ExternalGasSolverEvidence, GasBenchmarkObservation


def _context() -> GasBenchmarkProtocolContext:
    return GasBenchmarkProtocolContext(
        protocol_ref="protocol://gas/properties/synthetic-assessment-test/v1",
        model_id=COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_ID,
        model_version=COOLPROP_GAS_MIXTURE_PROPERTY_MODEL_VERSION,
        formulation_ref="formulation://coolprop/AbstractState/PT/synthetic-assessment-test-only",
        case_ref="case://gas/properties/synthetic-assessment-test-only",
    )


def _bundle() -> GasMixturePropertyBenchmarkObservationBundle:
    source_ref = f"{COOLPROP_GAS_MIXTURE_PROPERTY_EVIDENCE_REF_PREFIX}{'a' * 64}"
    state_ref = "property-state://gas/synthetic-assessment-test-only"
    observations = (
        GasBenchmarkObservation(
            observation_id="density",
            quantity_ref="quantity://gas/mixture-property/density",
            location_ref=state_ref,
            unit="kg/m3",
            petrole_value=0.8,
            reference_value=0.75,
            petrole_source_ref=source_ref,
            reference_source_ref="reference://synthetic/density/test-only",
        ),
        GasBenchmarkObservation(
            observation_id="z",
            quantity_ref="quantity://gas/mixture-property/compressibility_factor",
            location_ref=state_ref,
            unit="1",
            petrole_value=1.0,
            reference_value=0.99,
            petrole_source_ref=source_ref,
            reference_source_ref="reference://synthetic/z/test-only",
        ),
    )
    return GasMixturePropertyBenchmarkObservationBundle(
        property_state_ref=state_ref,
        petrole_source_ref=source_ref,
        composition_source_ref="composition://synthetic/assessment/test-only",
        coolprop_version="synthetic-version-test-only",
        coolprop_gitrevision="synthetic-gitrevision-test-only",
        observations=observations,
    )


def _criterion(
    observation: GasBenchmarkObservation,
    *,
    maximum_absolute_error: float | None = None,
    maximum_relative_error_fraction: float | None = None,
) -> PreRegisteredGasBenchmarkCriterion:
    context = _context()
    return PreRegisteredGasBenchmarkCriterion(
        criterion_id=f"criterion-{observation.observation_id}-synthetic-assessment-test",
        criterion_version="1",
        protocol_ref=context.protocol_ref,
        model_id=context.model_id,
        model_version=context.model_version,
        formulation_ref=context.formulation_ref,
        case_ref=context.case_ref,
        observation_id=observation.observation_id,
        quantity_ref=observation.quantity_ref,
        unit=observation.unit,
        source_ref=f"criterion-source://synthetic/{observation.observation_id}/test-only",
        registration_ref=f"registration://synthetic/{observation.observation_id}/test-only",
        state=GasBenchmarkCriterionState.APPROVED,
        approval_ref=f"approval://synthetic/{observation.observation_id}/test-only",
        maximum_absolute_error=maximum_absolute_error,
        maximum_relative_error_fraction=maximum_relative_error_fraction,
    )


def _approved(*, failing_density: bool = False):
    bundle = _bundle()
    density, z = bundle.observations
    return materialize_approved_gas_benchmark_criteria(
        context=_context(),
        criteria=(
            _criterion(
                density,
                maximum_absolute_error=0.01 if failing_density else 0.1,
            ),
            _criterion(z, maximum_relative_error_fraction=0.02),
        ),
        observations=bundle.observations,
    )


def _external_solver() -> ExternalGasSolverEvidence:
    return ExternalGasSolverEvidence(
        solver_name="synthetic-property-reference",
        solver_version="test-only-v1",
        formulation_ref="reference-formulation://synthetic/property/test-only",
        data_format_ref="format://synthetic/property-json/test-only",
        input_sha256="b" * 64,
        output_sha256="c" * 64,
        source_ref="reference-system://synthetic/property-assessment/test-only",
    )


def _evidence(*, failing_density: bool = False):
    bundle = _bundle()
    approved = _approved(failing_density=failing_density)
    solver = _external_solver()
    artifact = export_coolprop_gas_property_benchmark_evidence(
        bundle,
        approved,
        _context(),
        reference_system_ref=solver.source_ref,
        reference_input_sha256=solver.input_sha256,
        reference_output_sha256=solver.output_sha256,
        evidence_source_ref="evidence-source://synthetic/property-assessment/test-only",
        review_ref="review://synthetic/property-assessment/test-only",
    )
    return artifact, bundle, approved, solver


def test_governed_property_assessment_preserves_evidence_and_approvals() -> None:
    artifact, bundle, approved, solver = _evidence()

    result = assess_coolprop_gas_property_benchmark_evidence(
        artifact,
        bundle,
        approved,
        _context(),
        campaign_ref="campaign://synthetic/property-assessment/test-only",
        petrole_engine_version="petrole-test-only",
        external_solver=solver,
    )

    assert result.benchmark_evidence_ref == artifact.evidence_ref
    assert result.context == _context()
    assert result.criterion_ids == approved.criterion_ids
    assert result.approval_refs == approved.approval_refs
    assert result.registration_refs == approved.registration_refs
    assert result.assessment.protocol_ref == _context().protocol_ref
    assert result.assessment.all_evaluable_criteria_passed is True
    assert result.assessment.has_unevaluable_criteria is False
    assert result.qualification_claim is False
    assert result.certification_claim is False


def test_governed_property_assessment_returns_failed_criterion_without_qualification() -> None:
    artifact, bundle, approved, solver = _evidence(failing_density=True)

    result = assess_coolprop_gas_property_benchmark_evidence(
        artifact,
        bundle,
        approved,
        _context(),
        campaign_ref="campaign://synthetic/property-assessment/failure-test-only",
        petrole_engine_version="petrole-test-only",
        external_solver=solver,
    )

    assert result.assessment.all_evaluable_criteria_passed is False
    assert result.assessment.observations[0].passed is False
    assert result.assessment.observations[0].violations == (
        "absolute_error_above_criterion",
    )
    assert result.qualification_claim is False


def test_governed_property_assessment_rejects_bundle_or_approval_drift() -> None:
    artifact, bundle, approved, solver = _evidence()
    density, z = bundle.observations

    with pytest.raises(ValueError, match="observation runtime density"):
        assess_coolprop_gas_property_benchmark_evidence(
            artifact,
            replace(bundle, observations=(replace(density, petrole_value=0.81), z)),
            approved,
            _context(),
            campaign_ref="campaign://synthetic/property-assessment/drift-test-only",
            petrole_engine_version="petrole-test-only",
            external_solver=solver,
        )

    with pytest.raises(ValueError, match="critère APPROVED"):
        assess_coolprop_gas_property_benchmark_evidence(
            artifact,
            bundle,
            replace(approved, approval_refs=("approval://synthetic/other", approved.approval_refs[1])),
            _context(),
            campaign_ref="campaign://synthetic/property-assessment/drift-test-only",
            petrole_engine_version="petrole-test-only",
            external_solver=solver,
        )


def test_governed_property_assessment_rejects_external_reference_drift() -> None:
    artifact, bundle, approved, solver = _evidence()

    with pytest.raises(ValueError, match="référence externe fournie"):
        assess_coolprop_gas_property_benchmark_evidence(
            artifact,
            bundle,
            approved,
            _context(),
            campaign_ref="campaign://synthetic/property-assessment/external-test-only",
            petrole_engine_version="petrole-test-only",
            external_solver=replace(solver, source_ref="reference-system://synthetic/other"),
        )

    with pytest.raises(ValueError, match="hash de sortie"):
        assess_coolprop_gas_property_benchmark_evidence(
            artifact,
            bundle,
            approved,
            _context(),
            campaign_ref="campaign://synthetic/property-assessment/external-test-only",
            petrole_engine_version="petrole-test-only",
            external_solver=replace(solver, output_sha256="d" * 64),
        )


def test_governed_property_assessment_rejects_context_drift() -> None:
    artifact, bundle, approved, solver = _evidence()

    with pytest.raises(ValueError, match="contexte demandé"):
        assess_coolprop_gas_property_benchmark_evidence(
            artifact,
            bundle,
            approved,
            replace(_context(), case_ref="case://gas/properties/other"),
            campaign_ref="campaign://synthetic/property-assessment/context-test-only",
            petrole_engine_version="petrole-test-only",
            external_solver=solver,
        )
