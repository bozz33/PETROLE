from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from typing import cast

import pytest

from hydro_gas.benchmark_protocol import ApprovedGasBenchmarkCriteria
from hydro_gas.external_benchmark import GasBenchmarkObservation
from hydro_gas.stationary_equipment_benchmark_adapter import (
    StationaryEquipmentBenchmarkObservationBundle,
)
from hydro_gas.stationary_equipment_benchmark_evidence import (
    STATIONARY_EQUIPMENT_BENCHMARK_EVIDENCE_SCHEMA_VERSION,
    StationaryEquipmentBenchmarkEvidenceArtifact,
    export_stationary_equipment_benchmark_evidence,
)
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus


def _approved_criteria(*, observation_ids: tuple[str, ...]) -> ApprovedGasBenchmarkCriteria:
    runtime_criteria = tuple(
        SimpleNamespace(observation_id=observation_id) for observation_id in observation_ids
    )
    value = SimpleNamespace(
        protocol_ref="protocol://mixed/benchmark/v1",
        runtime_criteria=runtime_criteria,
        criterion_ids=tuple(f"criterion-{index}" for index, _ in enumerate(observation_ids, start=1)),
        approval_refs=tuple(
            f"approval://criterion/{index}" for index, _ in enumerate(observation_ids, start=1)
        ),
        registration_refs=tuple(
            f"registration://criterion/{index}" for index, _ in enumerate(observation_ids, start=1)
        ),
    )
    return cast(ApprovedGasBenchmarkCriteria, value)


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
        _approved_criteria(observation_ids=tuple(item.observation_id for item in bundle.observations)),
        case_ref="case://mixed/reference/v1",
        formulation_ref="formulation://gas/mixed/weymouth-map/v1",
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
    assert document["petrole"]["solver_status"] == "converged"
    assert document["petrole"]["result_sha256"] == "1" * 64
    assert document["external"]["input_sha256"] == "2" * 64
    assert document["external"]["output_sha256"] == "3" * 64
    assert [item["observation_id"] for item in document["criteria"]] == [
        "pressure-A",
        "compressor-ratio-C1",
    ]
    assert document["review_ref"] is None
    assert document["qualification_claim"] is False
    assert document["certification_claim"] is False


def test_mixed_benchmark_evidence_preserves_non_converged_status_without_acceptance_claim() -> None:
    artifact = _export(status=StationaryWeymouthSolverStatus.NON_CONVERGED)
    document = json.loads(artifact.content)

    assert document["petrole"]["solver_status"] == "non_converged"
    assert document["qualification_claim"] is False


def test_mixed_benchmark_evidence_requires_exact_criterion_coverage() -> None:
    bundle = _bundle()
    criteria = _approved_criteria(observation_ids=("pressure-A",))

    with pytest.raises(ValueError, match=r"couvrir exactement.*observations"):
        export_stationary_equipment_benchmark_evidence(
            bundle,
            criteria,
            case_ref="case://mixed/reference/v1",
            formulation_ref="formulation://gas/mixed/weymouth-map/v1",
            petrole_result_sha256="1" * 64,
            external_solver_ref="external-solver://reference/v1",
            external_input_sha256="2" * 64,
            external_output_sha256="3" * 64,
            evidence_source_ref="evidence://mixed/benchmark/v1",
        )


def test_mixed_benchmark_evidence_rejects_invalid_hashes_and_tampering() -> None:
    bundle = _bundle()
    criteria = _approved_criteria(observation_ids=tuple(item.observation_id for item in bundle.observations))

    with pytest.raises(ValueError, match="SHA-256"):
        export_stationary_equipment_benchmark_evidence(
            bundle,
            criteria,
            case_ref="case://mixed/reference/v1",
            formulation_ref="formulation://gas/mixed/weymouth-map/v1",
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
