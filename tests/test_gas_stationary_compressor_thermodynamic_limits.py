from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from hydro_gas.stationary_compressor_thermodynamic_limits import (
    ApprovedCompressorThermodynamicLimits,
    CompressorThermodynamicLimitState,
    PreRegisteredCompressorThermodynamicLimits,
    assess_compressor_thermodynamic_limits,
    assess_stationary_active_compressor_thermodynamic_limits,
    materialize_approved_compressor_thermodynamic_limits,
)
from hydro_gas.stationary_compressor_thermodynamics import (
    StationaryActiveCompressorThermodynamicAssessment,
    StationaryCompressorThermodynamicResult,
)
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus


def _approved_limits(
    compressor_id: str = "C1",
    *,
    maximum_power_w: float | None = 200_000.0,
    maximum_temperature_k: float | None = 350.0,
) -> ApprovedCompressorThermodynamicLimits:
    return materialize_approved_compressor_thermodynamic_limits(
        PreRegisteredCompressorThermodynamicLimits(
            limit_set_id=f"limits-{compressor_id}",
            limit_set_version="1",
            compressor_id=compressor_id,
            source_ref=f"supplier://limits/{compressor_id}/v1",
            registration_ref=f"registration://limits/{compressor_id}/v1",
            state=CompressorThermodynamicLimitState.APPROVED,
            approval_ref=f"approval://limits/{compressor_id}/v1",
            maximum_shaft_power_input_w=maximum_power_w,
            maximum_actual_outlet_temperature_k=maximum_temperature_k,
        )
    )


def _result(
    compressor_id: str = "C1",
    *,
    status: StationaryWeymouthSolverStatus = StationaryWeymouthSolverStatus.CONVERGED,
    shaft_power_w: float = 180_000.0,
    outlet_temperature_k: float = 340.0,
) -> StationaryCompressorThermodynamicResult:
    value = SimpleNamespace(
        compressor_id=compressor_id,
        solver_status=status,
        energy_balance=SimpleNamespace(shaft_power_input_w=shaft_power_w),
        property_state=SimpleNamespace(actual_outlet_temperature_k=outlet_temperature_k),
    )
    return cast(StationaryCompressorThermodynamicResult, value)


def _assessment(
    *results: StationaryCompressorThermodynamicResult,
    status: StationaryWeymouthSolverStatus = StationaryWeymouthSolverStatus.CONVERGED,
) -> StationaryActiveCompressorThermodynamicAssessment:
    value = SimpleNamespace(
        solve_ref="solve://mixed/thermo-limits/v1",
        solver_status=status,
        compressors=results,
    )
    return cast(StationaryActiveCompressorThermodynamicAssessment, value)


def test_approved_thermodynamic_limits_preserve_only_explicit_registered_values() -> None:
    limits = _approved_limits()

    assert limits.compressor_id == "C1"
    assert limits.limit_set_id == "limits-C1"
    assert limits.limit_set_version == "1"
    assert limits.maximum_shaft_power_input_w == 200_000.0
    assert limits.maximum_actual_outlet_temperature_k == 350.0
    assert limits.source_ref == "supplier://limits/C1/v1"
    assert limits.registration_ref == "registration://limits/C1/v1"
    assert limits.approval_ref == "approval://limits/C1/v1"


def test_thermodynamic_limit_governance_blocks_drafts_missing_approval_and_missing_limits() -> None:
    draft = PreRegisteredCompressorThermodynamicLimits(
        limit_set_id="limits-C1",
        limit_set_version="1",
        compressor_id="C1",
        source_ref="supplier://limits/C1/v1",
        registration_ref="registration://limits/C1/v1",
        maximum_shaft_power_input_w=200_000.0,
    )
    with pytest.raises(PermissionError, match="n'est pas APPROVED"):
        materialize_approved_compressor_thermodynamic_limits(draft)

    with pytest.raises(ValueError, match="APPROVED doit référencer son approbation"):
        PreRegisteredCompressorThermodynamicLimits(
            limit_set_id="limits-C1",
            limit_set_version="1",
            compressor_id="C1",
            source_ref="supplier://limits/C1/v1",
            registration_ref="registration://limits/C1/v1",
            state=CompressorThermodynamicLimitState.APPROVED,
            maximum_shaft_power_input_w=200_000.0,
        )

    with pytest.raises(ValueError, match="DRAFT ne peut pas porter une approbation"):
        PreRegisteredCompressorThermodynamicLimits(
            limit_set_id="limits-C1",
            limit_set_version="1",
            compressor_id="C1",
            source_ref="supplier://limits/C1/v1",
            registration_ref="registration://limits/C1/v1",
            approval_ref="approval://limits/C1/v1",
            maximum_shaft_power_input_w=200_000.0,
        )

    with pytest.raises(ValueError, match="Au moins une limite thermodynamique"):
        PreRegisteredCompressorThermodynamicLimits(
            limit_set_id="limits-C1",
            limit_set_version="1",
            compressor_id="C1",
            source_ref="supplier://limits/C1/v1",
            registration_ref="registration://limits/C1/v1",
        )


def test_converged_thermodynamic_limit_assessment_reports_margins_and_pass_fail() -> None:
    passed = assess_compressor_thermodynamic_limits(_result(), _approved_limits())

    assert passed.shaft_power_margin_w == 20_000.0
    assert passed.shaft_power_within_limit is True
    assert passed.outlet_temperature_margin_k == 10.0
    assert passed.outlet_temperature_within_limit is True
    assert passed.all_approved_limits_passed is True
    assert passed.evaluation_reason is None
    assert passed.non_positive_shaft_power_observed is False
    assert passed.qualification_claim is False
    assert passed.certification_claim is False

    failed = assess_compressor_thermodynamic_limits(
        _result(shaft_power_w=210_000.0, outlet_temperature_k=355.0),
        _approved_limits(),
    )
    assert failed.shaft_power_margin_w == -10_000.0
    assert failed.shaft_power_within_limit is False
    assert failed.outlet_temperature_margin_k == -5.0
    assert failed.outlet_temperature_within_limit is False
    assert failed.all_approved_limits_passed is False


def test_non_converged_thermodynamic_result_is_never_marked_within_limits() -> None:
    result = assess_compressor_thermodynamic_limits(
        _result(status=StationaryWeymouthSolverStatus.NON_CONVERGED),
        _approved_limits(),
    )

    assert result.observed_shaft_power_input_w == 180_000.0
    assert result.observed_actual_outlet_temperature_k == 340.0
    assert result.shaft_power_margin_w is None
    assert result.shaft_power_within_limit is None
    assert result.outlet_temperature_margin_k is None
    assert result.outlet_temperature_within_limit is None
    assert result.all_approved_limits_passed is None
    assert result.evaluation_reason == "source_solver_status:non_converged"


def test_active_compressor_limit_assessment_requires_exact_unique_coverage() -> None:
    first = _result("C1")
    second = _result("C2", shaft_power_w=150_000.0, outlet_temperature_k=330.0)
    assessment = _assessment(first, second)
    limits_c1 = _approved_limits("C1")
    limits_c2 = _approved_limits("C2", maximum_power_w=180_000.0, maximum_temperature_k=345.0)

    bundle = assess_stationary_active_compressor_thermodynamic_limits(
        assessment,
        (limits_c1, limits_c2),
    )
    assert bundle.solve_ref == "solve://mixed/thermo-limits/v1"
    assert bundle.all_limits_evaluable is True
    assert bundle.all_approved_limits_passed is True
    assert tuple(item.compressor_id for item in bundle.compressors) == ("C1", "C2")
    assert bundle.qualification_claim is False
    assert bundle.certification_claim is False

    with pytest.raises(ValueError, match="couvrir exactement les compresseurs actifs"):
        assess_stationary_active_compressor_thermodynamic_limits(assessment, (limits_c1,))

    with pytest.raises(ValueError, match="Un seul jeu de limites thermo APPROVED"):
        assess_stationary_active_compressor_thermodynamic_limits(
            assessment,
            (limits_c1, limits_c1),
        )
