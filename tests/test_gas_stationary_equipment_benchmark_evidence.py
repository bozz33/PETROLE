from __future__ import annotations

import hashlib
import json

import pytest

from hydro_gas.benchmark_protocol import ApprovedGasBenchmarkCriteria
from hydro_gas.external_benchmark import GasBenchmarkCriterion, GasBenchmarkObservation
from hydro_gas.stationary_equipment_benchmark_adapter import (
    StationaryEquipmentBenchmarkObservationBundle,
)
from hydro_gas.stationary_equipment_benchmark_evidence import (
    STATIONARY_EQUIPMENT_BENCHMARK_EVIDENCE_SCHEMA_VERSION,
    StationaryEquipmentBenchmarkEvidenceArtifact,
    export_stationary_equipment_benchmark_evidence,
)
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus

_PROTOCOL_REF = "protocol://mixed/benchmark/v1"
_MODEL_ID = "stationary-active-compressor-network"
_MODEL_VERSION = "mixed-weymouth-compressor-v1"
_CASE_REF = "case://mixed/reference/v1"
_FORMULATION_REF = "formulation://gas/mixed/weymouth-map/v1"


def _runtime_criterion(observation_id: str) -> GasBenchmarkCriterion:
    if observation_id == "pressure-A":
        return GasBenchmarkCriterion(
            observation_id=observation_id,
            maximum_absolute_error=500.0,
            source_ref="criterion-source://synthetic/mixed/pressure-A/test-only",
        )
    return GasBenchmarkCriterion(
        observation_id=observation_id,
        maximum_relative_error_fraction=0.02,
        source_ref=f"criterion-source://synthetic/mixed/{observation_id}/test-only",
    )


def _approved_criteria(*, observation_ids: tuple[str, ...]) -> ApprovedGasBenchmarkCriteria:
    return ApprovedGasBenchmarkCriteria(
        criteria=tuple(_runtime_criterion(observation_id) for observation_id in observation_ids),
        criterion_ids=tuple(
            f"criterion-{index}" for index, _ in enumerate(observation_ids, start=1)
        ),
        approval_refs=tuple(
            f"approval://synthetic/mixed/{index}/test-only"
            for index, _ in enumerate(observation_ids, start=1)
        ),
        registration_refs=tuple(
            f"registration://synthetic/mixed/{index}/test-only"
            for index, _ in enumerate(observation_ids, start=1)
        ),
        protocol_ref=_PROTOCOL_REF,
        model_id=_MODEL_ID,
        model_version=_MODEL_VERSION,
        case_ref=_CASE_REF,
        formulation_ref=_FORMULATION_REF,
    )


def _bundle(
    *,
    status: StationaryWeymouthSolverStatus = StationaryWeymouthSolverStatus.CONVERGED,
) -> StationaryEquipmentBenchmarkObservationBundle:
    observations = (
        GasBenchmarkObservation(
            observation_id="pressure-A",
            quantity_ref="quantity://gas/node_absolute_pressure",
            location_ref="node://A",
            unit="Pa",
            petrole_value=2_000_000.0,
            reference_value=2_000_100.0,
            petrole_source_ref="petrole://solve/mixed/v1",
            reference_source_ref="external://reference/pressure-A",
        ),
        GasBenchmarkObservation(
            observation_id="compressor-ratio-C1",
            quantity_ref="quantity://gas/compressor_pressure_ratio",
            location_ref="compressor://C1",
            unit="1",
            petrole_value=1.3,
            reference_value=1.31,
            petrole_source_ref="petrole://solve/mixed/v1",
            reference_source_ref="external://reference/compressor-ratio-C1",
        ),
    )
    return StationaryEquipmentBenchmarkObservationBundle(
        solve_ref="solve://mixed/benchmark/v1",
        solver_status=status,
        petrole_source_ref="petrole://solve/mixed/v1",
        observations=observations,
    )


def _export(
    *,
    status: StationaryWeymouthSolverStatus = StationaryWeymouthSolverStatus.CONVERGED,
) -> StationaryEquipmentBenchmarkEvidenceArtifact:
    bundle = _bundle(status=status)
    return export_stationary_equipment_benchmark_evidence(
        bundle,
        _approved_criteria(
            observation_ids=tuple(item.observation_id for item in bundle.observations)
        ),
        case_ref=_CASE_REF,
        formulation_ref=_FORMULATION_REF,
        petrole_result_sha256="1" * 64,
        external_solver_ref="external-solver://reference/v1",
        external_input_sha256="2" * 64,
        external_output_sha256="3" * 64,
        evidence_source_ref="evidence://mixed/benchmark/v1",
        review_ref=None,
    )


def test_mixed_benchmark_evidence_is_canonical_deterministic_and_non_certifying() -> None:
    first = _export()
    second = _export()

    assert first.schema_version == STATIONARY_EQUIPMENT_BENCHMARK_EVIDENCE_SCHEMA_VERSION
    assert first.content == second.content
    assert first.sha256 == second.sha256
    assert first.sha256 == hashlib.sha256(first.content).hexdigest()

    document = json.loads(first.content)
    assert document["model_id"] == _MODEL_ID
    assert document["model_version"] == _MODEL_VERSION
    assert document["case_ref"] == _CASE_REF
    assert document["formulation_ref"] == _FORMULATION_REF
    assert document["petrole"]["solver_status"] == "converged"
    assert document["petrole"]["result_sha256"] == "1" * 64
    assert document["external"]["input_sha256"] == "2" * 64
    assert document["external"]["output_sha256"] == "3" * 64
    assert [item["observation_id"] for item in document["criteria"]] == [
        "pressure-A",
        "compressor-ratio-C1",
    ]
    assert document["criteria"][0]["maximum_absolute_error"] == 500.0
    assert document["criteria"][0]["maximum_relative_error_fraction"] is None
    assert document["criteria"][0]["criterion_source_ref"].endswith("/test-only")
    assert document["criteria"][1]["maximum_absolute_error"] is None
    assert document["criteria"][1]["maximum_relative_error_fraction"] == 0.02
    assert document["criteria"][1]["criterion_source_ref"].endswith("/test-only")
    assert document["criteria"][0]["approval_ref"].startswith("approval://synthetic/")
    assert document["criteria"][0]["registration_ref"].startswith("registration://synthetic/")
    assert document["review_ref"] is None
    assert document["qualification_claim"] is False
    assert document["certification_claim"] is False


def test_mixed_benchmark_evidence_preserves_non_converged_status_without_acceptance_claim() -> None:
    artifact = _export(status=StationaryWeymouthSolverStatus.NON_CONVERGED)
    document = json.loads(artifact.content)

    assert document["petrole"]["solver_status"] == "non_converged"
    assert document["qualification_claim"] is False


def test_mixed_benchmark_evidence_rejects_case_or_formulation_context_drift() -> None:
    bundle = _bundle()
    criteria = _approved_criteria(
        observation_ids=tuple(item.observation_id for item in bundle.observations)
    )

    with pytest.raises(ValueError, match=r"cas.*contexte APPROVED"):
        export_stationary_equipment_benchmark_evidence(
            bundle,
            criteria,
            case_ref="case://mixed/other",
            formulation_ref=_FORMULATION_REF,
            petrole_result_sha256="1" * 64,
            external_solver_ref="external-solver://reference/v1",
            external_input_sha256="2" * 64,
            external_output_sha256="3" * 64,
            evidence_source_ref="evidence://mixed/benchmark/v1",
        )

    with pytest.raises(ValueError, match=r"formulation.*contexte APPROVED"):
        export_stationary_equipment_benchmark_evidence(
            bundle,
            criteria,
            case_ref=_CASE_REF,
            formulation_ref="formulation://gas/mixed/other",
            petrole_result_sha256="1" * 64,
            external_solver_ref="external-solver://reference/v1",
            external_input_sha256="2" * 64,
            external_output_sha256="3" * 64,
            evidence_source_ref="evidence://mixed/benchmark/v1",
        )


def test_mixed_benchmark_evidence_requires_exact_criterion_coverage() -> None:
    bundle = _bundle()
    criteria = _approved_criteria(observation_ids=("pressure-A",))

    with pytest.raises(ValueError, match=r"couvrir exactement.*observations"):
        export_stationary_equipment_benchmark_evidence(
            bundle,
            criteria,
            case_ref=_CASE_REF,
            formulation_ref=_FORMULATION_REF,
            petrole_result_sha256="1" * 64,
            external_solver_ref="external-solver://reference/v1",
            external_input_sha256="2" * 64,
            external_output_sha256="3" * 64,
            evidence_source_ref="evidence://mixed/benchmark/v1",
        )


def test_mixed_benchmark_evidence_rejects_invalid_hashes_and_tampering() -> None:
    bundle = _bundle()
    criteria = _approved_criteria(
        observation_ids=tuple(item.observation_id for item in bundle.observations)
    )

    with pytest.raises(ValueError, match="SHA-256"):
        export_stationary_equipment_benchmark_evidence(
            bundle,
            criteria,
            case_ref=_CASE_REF,
            formulation_ref=_FORMULATION_REF,
            petrole_result_sha256="not-a-hash",
            external_solver_ref="external-solver://reference/v1",
            external_input_sha256="2" * 64,
            external_output_sha256="3" * 64,
            evidence_source_ref="evidence://mixed/benchmark/v1",
        )

    artifact = _export()
    with pytest.raises(ValueError, match="empreinte"):
        StationaryEquipmentBenchmarkEvidenceArtifact(
            schema_version=artifact.schema_version,
            content=artifact.content + b" ",
            sha256=artifact.sha256,
        )
