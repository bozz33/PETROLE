from __future__ import annotations

import math

import pytest

import hydro_gas


_CONTEXT = hydro_gas.GasBenchmarkProtocolContext(
    protocol_ref="protocol://gas/weymouth/case-6/v1",
    model_id="weymouth-si",
    model_version="gasmodels-0.13.4-reference-v1",
    formulation_ref=(
        "GasModels.jl/docs/src/math-model.md@"
        "21422f18e7e328732ec8edd7995446d33f58e789#steady-state-weymouth"
    ),
    case_ref=("GasModels.jl/test/data/matgas/case-6-gf.m@21422f18e7e328732ec8edd7995446d33f58e789"),
)


def _observation(
    observation_id: str = "pipe-1-residual",
    *,
    quantity_ref: str = "weymouth-residual",
    unit: str = "Pa2",
) -> hydro_gas.GasBenchmarkObservation:
    return hydro_gas.GasBenchmarkObservation(
        observation_id=observation_id,
        quantity_ref=quantity_ref,
        location_ref="pipe://1",
        unit=unit,
        petrole_value=1.0,
        reference_value=1.0,
        petrole_source_ref="result://petrole/case-6/pipe-1",
        reference_source_ref="result://gasmodels/case-6/pipe-1",
    )


def _criterion(
    criterion_id: str = "criterion-pipe-1",
    *,
    observation_id: str = "pipe-1-residual",
    state: hydro_gas.GasBenchmarkCriterionState = hydro_gas.GasBenchmarkCriterionState.APPROVED,
    approval_ref: str | None = "approval://thermofluids/review-17",
    quantity_ref: str = "weymouth-residual",
    unit: str = "Pa2",
    maximum_absolute_error: float | None = 2.0,
    maximum_relative_error_fraction: float | None = None,
    protocol_ref: str = _CONTEXT.protocol_ref,
    model_id: str = _CONTEXT.model_id,
    model_version: str = _CONTEXT.model_version,
    formulation_ref: str = _CONTEXT.formulation_ref,
    case_ref: str = _CONTEXT.case_ref,
) -> hydro_gas.PreRegisteredGasBenchmarkCriterion:
    return hydro_gas.PreRegisteredGasBenchmarkCriterion(
        criterion_id=criterion_id,
        criterion_version="1",
        protocol_ref=protocol_ref,
        model_id=model_id,
        model_version=model_version,
        formulation_ref=formulation_ref,
        case_ref=case_ref,
        observation_id=observation_id,
        quantity_ref=quantity_ref,
        unit=unit,
        source_ref="criterion-source://gas/weymouth/review-dossier-17",
        registration_ref="git://PETROLE/protocols/weymouth/case-6/v1@pre-comparison",
        state=state,
        approval_ref=approval_ref,
        maximum_absolute_error=maximum_absolute_error,
        maximum_relative_error_fraction=maximum_relative_error_fraction,
    )


def test_approved_criterion_materializes_without_creating_new_thresholds() -> None:
    approved = _criterion(maximum_absolute_error=2.0, maximum_relative_error_fraction=0.01)

    result = hydro_gas.materialize_approved_gas_benchmark_criteria(
        context=_CONTEXT,
        criteria=(approved,),
        observations=(_observation(),),
    )

    assert result.protocol_ref == _CONTEXT.protocol_ref
    assert result.criterion_ids == ("criterion-pipe-1",)
    assert result.approval_refs == ("approval://thermofluids/review-17",)
    assert result.registration_refs == (
        "git://PETROLE/protocols/weymouth/case-6/v1@pre-comparison",
    )
    assert len(result.criteria) == 1
    runtime = result.criteria[0]
    assert runtime.observation_id == "pipe-1-residual"
    assert runtime.maximum_absolute_error == 2.0
    assert runtime.maximum_relative_error_fraction == 0.01
    assert runtime.source_ref == "criterion-source://gas/weymouth/review-dossier-17"


def test_draft_criterion_cannot_be_materialized() -> None:
    draft = _criterion(
        state=hydro_gas.GasBenchmarkCriterionState.DRAFT,
        approval_ref=None,
    )

    with pytest.raises(PermissionError, match="n'est pas APPROVED"):
        hydro_gas.materialize_approved_gas_benchmark_criteria(
            context=_CONTEXT,
            criteria=(draft,),
            observations=(_observation(),),
        )


def test_approved_state_requires_approval_and_draft_rejects_active_approval() -> None:
    with pytest.raises(ValueError, match=r"APPROVED.*approbation"):
        _criterion(approval_ref=None)

    with pytest.raises(ValueError, match=r"DRAFT.*approbation"):
        _criterion(state=hydro_gas.GasBenchmarkCriterionState.DRAFT)


def test_criterion_requires_explicit_nonnegative_finite_limit() -> None:
    with pytest.raises(ValueError, match="au moins une limite"):
        _criterion(maximum_absolute_error=None, maximum_relative_error_fraction=None)

    with pytest.raises(ValueError, match="finies"):
        _criterion(maximum_absolute_error=-1.0)

    with pytest.raises(ValueError, match="finies"):
        _criterion(maximum_absolute_error=math.inf)


def test_materialization_rejects_context_mismatch() -> None:
    mismatched = _criterion(model_version="another-model-version")

    with pytest.raises(ValueError, match="contexte de benchmark"):
        hydro_gas.materialize_approved_gas_benchmark_criteria(
            context=_CONTEXT,
            criteria=(mismatched,),
            observations=(_observation(),),
        )


def test_materialization_rejects_missing_observation_quantity_or_unit_mismatch() -> None:
    with pytest.raises(ValueError, match="observation absente"):
        hydro_gas.materialize_approved_gas_benchmark_criteria(
            context=_CONTEXT,
            criteria=(_criterion(observation_id="missing"),),
            observations=(_observation(),),
        )

    with pytest.raises(ValueError, match="autre grandeur"):
        hydro_gas.materialize_approved_gas_benchmark_criteria(
            context=_CONTEXT,
            criteria=(_criterion(quantity_ref="pressure"),),
            observations=(_observation(),),
        )

    with pytest.raises(ValueError, match="autre unité"):
        hydro_gas.materialize_approved_gas_benchmark_criteria(
            context=_CONTEXT,
            criteria=(_criterion(unit="bar"),),
            observations=(_observation(),),
        )


def test_materialization_rejects_duplicate_criteria_or_observation_assignment() -> None:
    first = _criterion(criterion_id="criterion-a")
    duplicate_id = _criterion(criterion_id="criterion-a", observation_id="pipe-2-residual")
    with pytest.raises(ValueError, match=r"identifiants de critères.*uniques"):
        hydro_gas.materialize_approved_gas_benchmark_criteria(
            context=_CONTEXT,
            criteria=(first, duplicate_id),
            observations=(
                _observation(),
                _observation("pipe-2-residual"),
            ),
        )

    second_same_observation = _criterion(criterion_id="criterion-b")
    with pytest.raises(ValueError, match="observation ne peut recevoir qu'un critère"):
        hydro_gas.materialize_approved_gas_benchmark_criteria(
            context=_CONTEXT,
            criteria=(first, second_same_observation),
            observations=(_observation(),),
        )


def test_materialization_rejects_empty_protocol_slice() -> None:
    with pytest.raises(ValueError, match="Au moins un critère"):
        hydro_gas.materialize_approved_gas_benchmark_criteria(
            context=_CONTEXT,
            criteria=(),
            observations=(_observation(),),
        )
