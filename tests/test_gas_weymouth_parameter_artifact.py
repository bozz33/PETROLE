from __future__ import annotations

import json

import pytest

from hydro_gas.constitutive_models import (
    GasConstitutiveManifest,
    GasConstitutiveQualification,
    assess_constitutive_manifest,
)
from hydro_gas.network_balance import SteadyGasNetwork, SteadyGasNode, SteadyGasPipe
from hydro_gas.weymouth_parameter_artifact import (
    WEYMOUTH_SI_MODEL_ID,
    WEYMOUTH_SI_MODEL_VERSION,
    WEYMOUTH_SI_PARAMETER_SCHEMA_VERSION,
    WeymouthSiParameterArtifact,
    build_weymouth_si_binding,
    export_weymouth_si_parameter_artifact,
    weymouth_si_reference_descriptor,
)
from hydro_gas.weymouth_si import WeymouthSiPipeParameters

_COMMIT = "21422f18e7e328732ec8edd7995446d33f58e789"
_EQUATION_REF = f"GasModels.jl/docs/src/math-model.md@{_COMMIT}#steady-state-weymouth"
_CASE_REF = f"GasModels.jl/test/data/matgas/case-6-gf.m@{_COMMIT}"
_EXPECTED_CASE_HASHES = {
    "1": "8750cdf95bbc1b2b73a4dab6881c736b29ef3ad6de19d69d03c2565fcf00f3ed",
    "2": "f83d3607d95e6175daf037967214749899bedb21ea360407dee7d8fc588ab31b",
    "3": "ed5a742fd5ef6e129f6ebbacdc99d3202487685cc784fca18e8bbe9698cdf998",
    "4": "245cf1ab92e9030493e13be3464fd4418e8d42b59ffb2ff681271bfdfc8169a5",
}
_CASE_PIPE_DATA = {
    "1": ("5", "2", 0.6, 50_000.0, 0.01),
    "2": ("2", "3", 0.6, 80_000.0, 0.01),
    "3": ("6", "4", 0.6, 80_000.0, 0.01),
    "4": ("3", "4", 0.3, 80_000.0, 0.01),
}


def _parameters(
    pipe_id: str,
    *,
    diameter_m: float,
    length_m: float,
    friction_factor: float,
) -> WeymouthSiPipeParameters:
    return WeymouthSiPipeParameters(
        pipe_id=pipe_id,
        length_m=length_m,
        diameter_m=diameter_m,
        friction_factor=friction_factor,
        sound_speed_m_s=371.6643,
        equation_ref=_EQUATION_REF,
        parameter_source_ref=_CASE_REF,
    )


def _artifact(pipe_id: str) -> WeymouthSiParameterArtifact:
    _, _, diameter_m, length_m, friction_factor = _CASE_PIPE_DATA[pipe_id]
    return export_weymouth_si_parameter_artifact(
        _parameters(
            pipe_id,
            diameter_m=diameter_m,
            length_m=length_m,
            friction_factor=friction_factor,
        ),
        parameter_set_ref=f"reference://gasmodels/case-6-gf/weymouth/pipe-{pipe_id}/v1",
        geometry_ref=f"{_CASE_REF}#pipe/{pipe_id}",
        gas_property_ref=f"{_CASE_REF}#gas-properties",
    )


def _network() -> SteadyGasNetwork:
    return SteadyGasNetwork(
        nodes=tuple(
            SteadyGasNode(node_id, f"{_CASE_REF}#junction/{node_id}")
            for node_id in ("1", "2", "3", "4", "5", "6")
        ),
        pipes=tuple(
            SteadyGasPipe(
                pipe_id,
                from_node,
                to_node,
                f"{_CASE_REF}#pipe/{pipe_id}",
            )
            for pipe_id, (from_node, to_node, _, _, _) in _CASE_PIPE_DATA.items()
        ),
    )


def test_parameter_artifact_is_canonical_and_preserves_explicit_references() -> None:
    artifact = _artifact("1")
    document = json.loads(artifact.content)

    assert artifact.sha256 == _EXPECTED_CASE_HASHES["1"]
    assert document["schema_version"] == WEYMOUTH_SI_PARAMETER_SCHEMA_VERSION
    assert document["unit_system"] == "SI"
    assert document["pipe_id"] == "1"
    assert document["length_m"] == 50_000.0
    assert document["diameter_m"] == 0.6
    assert document["friction_factor"] == 0.01
    assert document["sound_speed_m_s"] == 371.6643
    assert document["equation_ref"] == _EQUATION_REF
    assert document["geometry_ref"] == f"{_CASE_REF}#pipe/1"
    assert document["gas_property_ref"] == f"{_CASE_REF}#gas-properties"


def test_case6_parameter_hashes_are_frozen_per_pipe() -> None:
    hashes = {pipe_id: _artifact(pipe_id).sha256 for pipe_id in _CASE_PIPE_DATA}

    assert hashes == _EXPECTED_CASE_HASHES


def test_binding_uses_exact_parameter_artifact_hash_without_recalculation() -> None:
    artifact = _artifact("2")
    binding = build_weymouth_si_binding(
        artifact,
        source_ref="benchmark-config://gasmodels/case-6-gf/weymouth/v1",
    )

    assert binding.pipe_id == "2"
    assert binding.model_id == WEYMOUTH_SI_MODEL_ID
    assert binding.model_version == WEYMOUTH_SI_MODEL_VERSION
    assert binding.parameter_set_ref == artifact.parameter_set_ref
    assert binding.parameter_set_sha256 == _EXPECTED_CASE_HASHES["2"]
    assert binding.geometry_ref == artifact.geometry_ref
    assert binding.gas_property_ref == artifact.gas_property_ref


def test_reference_descriptor_is_benchmark_ready_but_not_benchmarked() -> None:
    descriptor = weymouth_si_reference_descriptor()

    assert descriptor.model_id == WEYMOUTH_SI_MODEL_ID
    assert descriptor.version == WEYMOUTH_SI_MODEL_VERSION
    assert descriptor.qualification is GasConstitutiveQualification.BENCHMARK_READY
    assert descriptor.qualification_evidence_refs == ()
    assert "steady-state" in descriptor.assumptions
    assert "constant-cross-section" in descriptor.assumptions
    assert descriptor.equation_ref == _EQUATION_REF


def test_case6_manifest_is_complete_and_benchmark_ready_without_certification_claim() -> None:
    bindings = tuple(
        build_weymouth_si_binding(
            _artifact(pipe_id),
            source_ref="benchmark-config://gasmodels/case-6-gf/weymouth/v1",
        )
        for pipe_id in _CASE_PIPE_DATA
    )
    manifest = GasConstitutiveManifest(
        descriptors=(weymouth_si_reference_descriptor(),),
        bindings=bindings,
        source_ref="benchmark-manifest://gasmodels/case-6-gf/weymouth/v1",
    )

    assessment = assess_constitutive_manifest(_network(), manifest)

    assert assessment.complete is True
    assert assessment.benchmark_ready is True
    assert assessment.violations == ()
    assert manifest.descriptors[0].qualification is GasConstitutiveQualification.BENCHMARK_READY
    assert manifest.descriptors[0].qualification_evidence_refs == ()


def test_parameter_artifact_rejects_missing_external_references() -> None:
    parameters = _parameters(
        "1",
        diameter_m=0.6,
        length_m=50_000.0,
        friction_factor=0.01,
    )

    with pytest.raises(ValueError, match="références"):
        export_weymouth_si_parameter_artifact(
            parameters,
            parameter_set_ref="",
            geometry_ref=f"{_CASE_REF}#pipe/1",
            gas_property_ref=f"{_CASE_REF}#gas-properties",
        )


def test_binding_requires_its_own_provenance() -> None:
    with pytest.raises(ValueError, match="provenance"):
        build_weymouth_si_binding(_artifact("1"), source_ref="")
