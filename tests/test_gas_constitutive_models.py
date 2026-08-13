from __future__ import annotations

import pytest

from hydro_gas.constitutive_models import (
    GasConstitutiveManifest,
    GasConstitutiveQualification,
    GasPipeConstitutiveBinding,
    GasPipeConstitutiveModelDescriptor,
    assess_constitutive_manifest,
)
from hydro_gas.network_balance import SteadyGasNetwork, SteadyGasNode, SteadyGasPipe

_SHA = "a" * 64


def _network() -> SteadyGasNetwork:
    return SteadyGasNetwork(
        nodes=(
            SteadyGasNode("N1", "engineering://gas/nodes/rev-2"),
            SteadyGasNode("N2", "engineering://gas/nodes/rev-2"),
            SteadyGasNode("N3", "engineering://gas/nodes/rev-2"),
        ),
        pipes=(
            SteadyGasPipe("P1", "N1", "N2", "engineering://gas/pipes/rev-4"),
            SteadyGasPipe("P2", "N2", "N3", "engineering://gas/pipes/rev-4"),
        ),
    )


def _descriptor(
    *,
    model_id: str = "steady-model-a",
    version: str = "1.0",
    qualification: GasConstitutiveQualification = (
        GasConstitutiveQualification.BENCHMARK_READY
    ),
    evidence: tuple[str, ...] = (),
) -> GasPipeConstitutiveModelDescriptor:
    return GasPipeConstitutiveModelDescriptor(
        model_id=model_id,
        version=version,
        formulation_ref=f"formulation://gas/{model_id}/{version}",
        equation_ref=f"equation://gas/{model_id}/{version}",
        source_ref=f"reference://gas/{model_id}/{version}",
        parameter_schema_ref=f"schema://gas/{model_id}/{version}",
        domain_refs=(f"domain://gas/{model_id}/{version}",),
        assumptions=("steady-state", "single-phase-gas"),
        qualification=qualification,
        qualification_evidence_refs=evidence,
    )


def _binding(
    pipe_id: str,
    *,
    model_id: str = "steady-model-a",
    version: str = "1.0",
) -> GasPipeConstitutiveBinding:
    return GasPipeConstitutiveBinding(
        pipe_id=pipe_id,
        model_id=model_id,
        model_version=version,
        parameter_set_ref=f"parameters://gas/{pipe_id}/rev-3",
        parameter_set_sha256=_SHA,
        geometry_ref=f"geometry://gas/{pipe_id}/rev-5",
        gas_property_ref="properties://gas/case-01/rev-2",
        source_ref=f"config://gas/{pipe_id}/rev-6",
    )


def test_complete_benchmark_ready_manifest_is_reported_without_running_physics() -> None:
    manifest = GasConstitutiveManifest(
        descriptors=(_descriptor(),),
        bindings=(_binding("P1"), _binding("P2")),
        source_ref="manifest://gas/network-A/rev-1",
    )

    assessment = assess_constitutive_manifest(_network(), manifest)

    assert assessment.complete is True
    assert assessment.benchmark_ready is True
    assert assessment.violations == ()
    assert assessment.unbound_pipe_ids == ()
    assert assessment.unknown_pipe_ids == ()
    assert assessment.unknown_model_keys == ()
    assert assessment.not_benchmark_ready_model_keys == ()


def test_declared_model_is_complete_but_not_benchmark_ready() -> None:
    descriptor = _descriptor(qualification=GasConstitutiveQualification.DECLARED)
    manifest = GasConstitutiveManifest(
        descriptors=(descriptor,),
        bindings=(_binding("P1"), _binding("P2")),
        source_ref="manifest://gas/network-A/rev-1",
    )

    assessment = assess_constitutive_manifest(_network(), manifest)

    assert assessment.complete is True
    assert assessment.benchmark_ready is False
    assert assessment.not_benchmark_ready_model_keys == (("steady-model-a", "1.0"),)
    assert assessment.violations == ("model_not_benchmark_ready:steady-model-a@1.0",)


def test_manifest_reports_missing_unknown_pipe_and_unknown_model_separately() -> None:
    manifest = GasConstitutiveManifest(
        descriptors=(_descriptor(),),
        bindings=(
            _binding("P1"),
            _binding("P-extra"),
            _binding("P2", model_id="missing-model", version="9"),
        ),
        source_ref="manifest://gas/network-A/rev-2",
    )

    assessment = assess_constitutive_manifest(_network(), manifest)

    assert assessment.complete is False
    assert assessment.benchmark_ready is False
    assert assessment.unbound_pipe_ids == ()
    assert assessment.unknown_pipe_ids == ("P-extra",)
    assert assessment.unknown_model_keys == (("missing-model", "9"),)
    assert "unknown_pipe:P-extra" in assessment.violations
    assert "unknown_model:missing-model@9" in assessment.violations


def test_manifest_reports_unbound_network_pipe() -> None:
    manifest = GasConstitutiveManifest(
        descriptors=(_descriptor(),),
        bindings=(_binding("P1"),),
        source_ref="manifest://gas/network-A/rev-2",
    )

    assessment = assess_constitutive_manifest(_network(), manifest)

    assert assessment.complete is False
    assert assessment.unbound_pipe_ids == ("P2",)
    assert assessment.violations == ("unbound_pipe:P2",)


def test_benchmarked_descriptor_requires_qualification_evidence() -> None:
    with pytest.raises(ValueError, match=r"benchmark.*preuves"):
        _descriptor(qualification=GasConstitutiveQualification.BENCHMARKED)

    descriptor = _descriptor(
        qualification=GasConstitutiveQualification.BENCHMARKED,
        evidence=("benchmark://gas/case-set-A/rev-4",),
    )
    assert descriptor.qualification_evidence_refs == ("benchmark://gas/case-set-A/rev-4",)


def test_descriptor_requires_domain_and_assumptions() -> None:
    kwargs = {
        "model_id": "model-a",
        "version": "1",
        "formulation_ref": "formulation://a",
        "equation_ref": "equation://a",
        "source_ref": "reference://a",
        "parameter_schema_ref": "schema://a",
    }
    with pytest.raises(ValueError, match="domaine de validité"):
        GasPipeConstitutiveModelDescriptor(
            domain_refs=(), assumptions=("steady",), **kwargs
        )
    with pytest.raises(ValueError, match="hypothèses"):
        GasPipeConstitutiveModelDescriptor(
            domain_refs=("domain://a",), assumptions=(), **kwargs
        )


def test_binding_requires_sha256_parameter_fingerprint() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        GasPipeConstitutiveBinding(
            pipe_id="P1",
            model_id="model-a",
            model_version="1",
            parameter_set_ref="parameters://P1",
            parameter_set_sha256="not-a-sha",
            geometry_ref="geometry://P1",
            gas_property_ref="properties://case-A",
            source_ref="config://P1",
        )


def test_manifest_rejects_duplicate_model_version_or_pipe_binding() -> None:
    with pytest.raises(ValueError, match=r"modèle/version.*uniques"):
        GasConstitutiveManifest(
            descriptors=(_descriptor(), _descriptor()),
            bindings=(_binding("P1"),),
            source_ref="manifest://gas/A",
        )

    with pytest.raises(ValueError, match="qu'un binding"):
        GasConstitutiveManifest(
            descriptors=(_descriptor(),),
            bindings=(_binding("P1"), _binding("P1")),
            source_ref="manifest://gas/A",
        )
