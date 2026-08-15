from __future__ import annotations

from dataclasses import replace

import pytest

from hydro_gas.energy_optimization import (
    GasDispatchConstraintEvidence,
    GasEnergyDispatchCandidate,
    GasEnergySelectionStatus,
    select_minimum_energy_dispatch,
)
from hydro_gas.result_export import GasResultExportArtifact, export_gas_results_json
from hydro_gas.stationary_compressor_thermodynamic_limits import (
    CompressorThermodynamicLimitAssessment,
    StationaryActiveCompressorThermodynamicLimitAssessment,
)
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus
from hydro_gas.stationary_thermodynamic_result_export import (
    STATIONARY_COMPRESSOR_THERMODYNAMIC_EXPORT_VERSION,
    STATIONARY_COMPRESSOR_THERMODYNAMIC_RESULT_MODEL_VERSION,
)
from hydro_gas.thermodynamic_dispatch_evidence import (
    THERMODYNAMIC_LIMIT_DISPATCH_CONSTRAINT_ID,
    THERMODYNAMIC_LIMIT_EVIDENCE_REF_PREFIX,
    build_thermodynamic_limit_dispatch_constraint_evidence,
)


def _compressor_limit(
    *,
    passed: bool | None = True,
    status: StationaryWeymouthSolverStatus = StationaryWeymouthSolverStatus.CONVERGED,
) -> CompressorThermodynamicLimitAssessment:
    return CompressorThermodynamicLimitAssessment(
        compressor_id="C1",
        solver_status=status,
        limit_set_id="limits-C1",
        limit_set_version="1",
        observed_shaft_power_input_w=180_000.0,
        maximum_shaft_power_input_w=200_000.0,
        shaft_power_margin_w=20_000.0 if passed is not None else None,
        shaft_power_within_limit=passed,
        observed_actual_outlet_temperature_k=340.0,
        maximum_actual_outlet_temperature_k=350.0,
        outlet_temperature_margin_k=10.0 if passed is not None else None,
        outlet_temperature_within_limit=passed,
        all_approved_limits_passed=passed,
        evaluation_reason=None if passed is not None else "source_solver_status:non_converged",
        non_positive_shaft_power_observed=False,
        source_ref="supplier://limits/C1/v1",
        registration_ref="registration://limits/C1/v1",
        approval_ref="approval://limits/C1/v1",
    )


def _assessment(
    *,
    passed: bool | None = True,
) -> StationaryActiveCompressorThermodynamicLimitAssessment:
    status = (
        StationaryWeymouthSolverStatus.CONVERGED
        if passed is not None
        else StationaryWeymouthSolverStatus.NON_CONVERGED
    )
    return StationaryActiveCompressorThermodynamicLimitAssessment(
        solve_ref="solve://mixed/dispatch-proof/v1",
        solver_status=status,
        compressors=(_compressor_limit(passed=passed, status=status),),
        all_limits_evaluable=passed is not None,
        all_approved_limits_passed=passed,
    )


def _artifact(
    assessment: StationaryActiveCompressorThermodynamicLimitAssessment,
    *,
    calculation_ref: str | None = None,
    exported_passed: bool | None | object = Ellipsis,
    approval_ref: str = "approval://limits/C1/v1",
    export_version: str = STATIONARY_COMPRESSOR_THERMODYNAMIC_EXPORT_VERSION,
    model_version: str = STATIONARY_COMPRESSOR_THERMODYNAMIC_RESULT_MODEL_VERSION,
) -> GasResultExportArtifact:
    compressor = assessment.compressors[0]
    all_passed = (
        assessment.all_approved_limits_passed
        if exported_passed is Ellipsis
        else exported_passed
    )
    return export_gas_results_json(
        {
            "calculation_ref": calculation_ref or assessment.solve_ref,
            "model_version": model_version,
            "composition_source_ref": "composition://synthetic/test-only",
            "property_method_ref": "property://coolprop/test-only",
            "results": {"status": assessment.solver_status.value},
            "diagnostics": {
                "thermodynamic_limits": {
                    "solver_status": assessment.solver_status.value,
                    "all_limits_evaluable": assessment.all_limits_evaluable,
                    "all_approved_limits_passed": all_passed,
                    "qualification_claim": False,
                    "certification_claim": False,
                    "compressors": [
                        {
                            "compressor_id": compressor.compressor_id,
                            "solver_status": compressor.solver_status.value,
                            "limit_set_id": compressor.limit_set_id,
                            "limit_set_version": compressor.limit_set_version,
                            "all_approved_limits_passed": compressor.all_approved_limits_passed,
                            "source_ref": compressor.source_ref,
                            "registration_ref": compressor.registration_ref,
                            "approval_ref": approval_ref,
                            "qualification_claim": False,
                            "certification_claim": False,
                        }
                    ],
                }
            },
        },
        export_version=export_version,
    )


def _candidate(
    candidate_id: str,
    energy_j: float,
    evidence: GasDispatchConstraintEvidence,
) -> GasEnergyDispatchCandidate:
    return GasEnergyDispatchCandidate(
        candidate_id=candidate_id,
        station_id="station://CS-01",
        interval_duration_s=3600.0,
        energy_j=energy_j,
        operating_point_refs=(f"operating-point://{candidate_id}/C1",),
        constraint_evidence=(evidence,),
        model_version="gas-dispatch-evaluation-v1",
        source_ref=f"scenario://gas/{candidate_id}/v1",
    )


def test_verified_thermodynamic_export_becomes_dispatch_constraint_evidence() -> None:
    assessment = _assessment(passed=True)
    artifact = _artifact(assessment)

    evidence = build_thermodynamic_limit_dispatch_constraint_evidence(assessment, artifact)

    assert evidence.constraint_id == THERMODYNAMIC_LIMIT_DISPATCH_CONSTRAINT_ID
    assert evidence.passed is True
    assert evidence.evidence_ref == f"{THERMODYNAMIC_LIMIT_EVIDENCE_REF_PREFIX}{artifact.sha256}"


def test_failed_or_unevaluable_thermodynamic_limits_fail_closed_for_dispatch() -> None:
    failed = _assessment(passed=False)
    failed_evidence = build_thermodynamic_limit_dispatch_constraint_evidence(
        failed,
        _artifact(failed),
    )
    assert failed_evidence.passed is False

    unevaluable = _assessment(passed=None)
    unevaluable_evidence = build_thermodynamic_limit_dispatch_constraint_evidence(
        unevaluable,
        _artifact(unevaluable),
    )
    assert unevaluable_evidence.passed is False


def test_dispatch_selection_rejects_cheaper_candidate_when_thermo_is_unevaluable() -> None:
    unevaluable = _assessment(passed=None)
    passed = _assessment(passed=True)
    rejected_evidence = build_thermodynamic_limit_dispatch_constraint_evidence(
        unevaluable,
        _artifact(unevaluable),
    )
    accepted_evidence = build_thermodynamic_limit_dispatch_constraint_evidence(
        passed,
        _artifact(passed),
    )

    result = select_minimum_energy_dispatch(
        (
            _candidate("cheap-unevaluable", 1_000.0, rejected_evidence),
            _candidate("higher-evaluable", 2_000.0, accepted_evidence),
        )
    )

    assert result.status is GasEnergySelectionStatus.OPTIMAL_DISCRETE
    assert result.selected is not None
    assert result.selected.candidate_id == "higher-evaluable"
    assert result.rejected[0].candidate_id == "cheap-unevaluable"
    assert result.rejected[0].violation_codes == (THERMODYNAMIC_LIMIT_DISPATCH_CONSTRAINT_ID,)


def test_dispatch_evidence_rejects_tampered_hash_and_context_mismatch() -> None:
    assessment = _assessment(passed=True)
    artifact = _artifact(assessment)
    tampered = replace(artifact, content=artifact.content + b" ")
    with pytest.raises(ValueError, match="SHA-256"):
        build_thermodynamic_limit_dispatch_constraint_evidence(assessment, tampered)

    with pytest.raises(ValueError, match="calcul évalué"):
        build_thermodynamic_limit_dispatch_constraint_evidence(
            assessment,
            _artifact(assessment, calculation_ref="solve://other/v1"),
        )


def test_dispatch_evidence_rejects_export_verdict_or_approval_drift() -> None:
    assessment = _assessment(passed=True)
    with pytest.raises(ValueError, match="verdict thermo exporté"):
        build_thermodynamic_limit_dispatch_constraint_evidence(
            assessment,
            _artifact(assessment, exported_passed=False),
        )

    with pytest.raises(ValueError, match="approval_ref"):
        build_thermodynamic_limit_dispatch_constraint_evidence(
            assessment,
            _artifact(assessment, approval_ref="approval://limits/C1/other"),
        )


def test_dispatch_evidence_rejects_wrong_export_or_model_version() -> None:
    assessment = _assessment(passed=True)
    with pytest.raises(ValueError, match="version thermo P6-G"):
        build_thermodynamic_limit_dispatch_constraint_evidence(
            assessment,
            _artifact(assessment, export_version="phase6-gas/other/1"),
        )

    with pytest.raises(ValueError, match="modèle thermo P6-G"):
        build_thermodynamic_limit_dispatch_constraint_evidence(
            assessment,
            _artifact(assessment, model_version="phase6/other/1"),
        )
