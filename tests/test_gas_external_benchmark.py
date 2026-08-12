from __future__ import annotations

import pytest

from hydro_gas.external_benchmark import (
    ExternalGasSolverEvidence,
    GasBenchmarkCriterion,
    GasBenchmarkObservation,
    assess_external_gas_benchmark,
)

INPUT_SHA = "11" * 32
OUTPUT_SHA = "22" * 32


def _solver(**overrides) -> ExternalGasSolverEvidence:
    payload = {
        "solver_name": "GasModels.jl",
        "solver_version": "explicit-version-from-run",
        "formulation_ref": "benchmark://gas/formulation/approved-case",
        "data_format_ref": "https://lanl-ansi.github.io/GasModels.jl/network-data",
        "input_sha256": INPUT_SHA,
        "output_sha256": OUTPUT_SHA,
        "source_ref": "evidence://gasmodels/run-001",
    }
    payload.update(overrides)
    return ExternalGasSolverEvidence(**payload)


def _observation(
    observation_id: str,
    *,
    petrole_value: float,
    reference_value: float,
) -> GasBenchmarkObservation:
    return GasBenchmarkObservation(
        observation_id=observation_id,
        quantity_ref="pressure",
        location_ref=f"node://{observation_id}",
        unit="Pa",
        petrole_value=petrole_value,
        reference_value=reference_value,
        petrole_source_ref="run://petrole/gas-001",
        reference_source_ref="evidence://external/gas-001",
    )


def test_external_benchmark_compares_values_without_hidden_threshold() -> None:
    assessment = assess_external_gas_benchmark(
        campaign_ref="benchmark://phase6/p6h/run-001",
        protocol_ref="protocol://phase6/p6h/v1",
        petrole_engine_version="gas-engine-test",
        external_solver=_solver(),
        observations=(_observation("J1", petrole_value=5_000_100.0, reference_value=5_000_000.0),),
    )

    result = assessment.observations[0]
    assert result.signed_error == pytest.approx(100.0)
    assert result.absolute_error == pytest.approx(100.0)
    assert result.relative_error_fraction == pytest.approx(0.00002)
    assert result.passed is None
    assert assessment.all_evaluable_criteria_passed is None
    assert assessment.has_unevaluable_criteria is True


def test_external_benchmark_applies_only_preregistered_criteria() -> None:
    observations = (
        _observation("J1", petrole_value=101.0, reference_value=100.0),
        _observation("J2", petrole_value=95.0, reference_value=100.0),
    )
    criteria = (
        GasBenchmarkCriterion(
            observation_id="J1",
            maximum_absolute_error=2.0,
            maximum_relative_error_fraction=0.02,
            source_ref="protocol://phase6/p6h/v1#J1",
        ),
        GasBenchmarkCriterion(
            observation_id="J2",
            maximum_absolute_error=2.0,
            source_ref="protocol://phase6/p6h/v1#J2",
        ),
    )

    assessment = assess_external_gas_benchmark(
        campaign_ref="benchmark://phase6/p6h/run-002",
        protocol_ref="protocol://phase6/p6h/v1",
        petrole_engine_version="gas-engine-test",
        external_solver=_solver(),
        observations=observations,
        criteria=criteria,
    )

    assert tuple(item.passed for item in assessment.observations) == (True, False)
    assert assessment.observations[1].violations == ("absolute_error_above_criterion",)
    assert assessment.all_evaluable_criteria_passed is False
    assert assessment.has_unevaluable_criteria is False


def test_relative_criterion_does_not_hide_zero_reference() -> None:
    assessment = assess_external_gas_benchmark(
        campaign_ref="benchmark://phase6/p6h/run-zero",
        protocol_ref="protocol://phase6/p6h/v1",
        petrole_engine_version="gas-engine-test",
        external_solver=_solver(),
        observations=(_observation("J0", petrole_value=1.0, reference_value=0.0),),
        criteria=(
            GasBenchmarkCriterion(
                observation_id="J0",
                maximum_relative_error_fraction=0.01,
                source_ref="protocol://phase6/p6h/v1#J0",
            ),
        ),
    )

    result = assessment.observations[0]
    assert result.relative_error_fraction is None
    assert result.passed is False
    assert result.violations == ("relative_error_undefined_reference_zero",)


def test_benchmark_rejects_duplicate_or_unknown_criteria() -> None:
    observation = _observation("J1", petrole_value=1.0, reference_value=1.0)
    criterion = GasBenchmarkCriterion(
        observation_id="J1",
        maximum_absolute_error=0.1,
        source_ref="protocol://criterion/J1",
    )

    with pytest.raises(ValueError, match="Un seul critère"):
        assess_external_gas_benchmark(
            campaign_ref="benchmark://duplicate",
            protocol_ref="protocol://phase6/p6h/v1",
            petrole_engine_version="gas-engine-test",
            external_solver=_solver(),
            observations=(observation,),
            criteria=(criterion, criterion),
        )

    with pytest.raises(ValueError, match="observation inconnue"):
        assess_external_gas_benchmark(
            campaign_ref="benchmark://unknown",
            protocol_ref="protocol://phase6/p6h/v1",
            petrole_engine_version="gas-engine-test",
            external_solver=_solver(),
            observations=(observation,),
            criteria=(
                GasBenchmarkCriterion(
                    observation_id="J2",
                    maximum_absolute_error=0.1,
                    source_ref="protocol://criterion/J2",
                ),
            ),
        )


def test_solver_evidence_requires_version_format_and_content_hashes() -> None:
    with pytest.raises(ValueError, match="version"):
        _solver(solver_version="")

    with pytest.raises(ValueError, match="input_sha256"):
        _solver(input_sha256="bad")


def test_criterion_requires_explicit_nonnegative_limit() -> None:
    with pytest.raises(ValueError, match="Au moins un critère"):
        GasBenchmarkCriterion(observation_id="J1", source_ref="protocol://J1")

    with pytest.raises(ValueError, match="positive ou nulle"):
        GasBenchmarkCriterion(
            observation_id="J1",
            source_ref="protocol://J1",
            maximum_absolute_error=-1.0,
        )
