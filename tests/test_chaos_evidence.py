from __future__ import annotations

import pytest

from hydro_shared.chaos_evidence import (
    ChaosExperimentEvidence,
    ChaosExperimentObjectives,
    assess_chaos_experiment,
)


def _objectives(**overrides) -> ChaosExperimentObjectives:
    payload = {
        "policy_ref": "policy://resilience/pilot-v1",
        "scenario_ref": "chaos://postgres-primary-unavailable",
        "target_ref": "deployment://pilot/staging",
        "maximum_recovery_time_s": 60.0,
        "maximum_error_fraction": 0.05,
    }
    payload.update(overrides)
    return ChaosExperimentObjectives(**payload)


def _evidence(**overrides) -> ChaosExperimentEvidence:
    payload = {
        "evidence_ref": "evidence://chaos/2026-08-12/run-001",
        "recovery_time_s": 35.0,
        "total_requests": 1000,
        "failed_requests": 20,
        "service_recovered": True,
        "data_integrity_preserved": True,
        "scope_isolation_preserved": True,
    }
    payload.update(overrides)
    return ChaosExperimentEvidence(**payload)


def test_chaos_assessment_passes_when_pre_registered_objectives_are_met() -> None:
    assessment = assess_chaos_experiment(_objectives(), _evidence())

    assert assessment.passed is True
    assert assessment.violations == ()
    assert assessment.error_fraction == pytest.approx(0.02)
    assert assessment.recovery_time_s == pytest.approx(35.0)
    assert assessment.scenario_ref == "chaos://postgres-primary-unavailable"


def test_chaos_assessment_reports_all_observed_violations() -> None:
    assessment = assess_chaos_experiment(
        _objectives(),
        _evidence(
            recovery_time_s=90.0,
            failed_requests=100,
            service_recovered=False,
            data_integrity_preserved=False,
            scope_isolation_preserved=False,
        ),
    )

    assert assessment.passed is False
    assert assessment.violations == (
        "service_not_recovered",
        "recovery_time_above_objective",
        "error_fraction_above_objective",
        "data_integrity_not_preserved",
        "scope_isolation_not_preserved",
    )


def test_data_integrity_and_scope_isolation_are_non_negotiable() -> None:
    data_failure = assess_chaos_experiment(
        _objectives(),
        _evidence(data_integrity_preserved=False),
    )
    scope_failure = assess_chaos_experiment(
        _objectives(),
        _evidence(scope_isolation_preserved=False),
    )

    assert data_failure.passed is False
    assert data_failure.violations == ("data_integrity_not_preserved",)
    assert scope_failure.passed is False
    assert scope_failure.violations == ("scope_isolation_not_preserved",)


def test_chaos_objectives_reject_invalid_references_and_bounds() -> None:
    with pytest.raises(ValueError, match="scénario"):
        _objectives(scenario_ref="")

    with pytest.raises(ValueError, match="temps maximal"):
        _objectives(maximum_recovery_time_s=-1.0)

    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        _objectives(maximum_error_fraction=1.1)


def test_chaos_evidence_rejects_incoherent_request_counts() -> None:
    with pytest.raises(ValueError, match="au moins une requête"):
        _evidence(total_requests=0, failed_requests=0)

    with pytest.raises(ValueError, match="incohérent"):
        _evidence(total_requests=10, failed_requests=11)
