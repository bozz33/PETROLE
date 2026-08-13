from __future__ import annotations

import pytest

from hydro_gas.energy_optimization import (
    GasDispatchConstraintEvidence,
    GasEnergyDispatchCandidate,
    GasEnergySelectionStatus,
    select_minimum_energy_dispatch,
)


def _constraint(
    constraint_id: str = "compressor-envelope",
    *,
    passed: bool = True,
) -> GasDispatchConstraintEvidence:
    return GasDispatchConstraintEvidence(
        constraint_id=constraint_id,
        passed=passed,
        evidence_ref=f"evidence://gas/{constraint_id}/rev-2",
    )


def _candidate(
    candidate_id: str,
    energy_j: float,
    *,
    constraints: tuple[GasDispatchConstraintEvidence, ...] | None = None,
) -> GasEnergyDispatchCandidate:
    return GasEnergyDispatchCandidate(
        candidate_id=candidate_id,
        station_id="station://CS-01",
        interval_duration_s=3600.0,
        energy_j=energy_j,
        operating_point_refs=(f"operating-point://{candidate_id}/unit-A",),
        constraint_evidence=constraints or (_constraint(),),
        model_version="gas-dispatch-evaluation-v1",
        source_ref=f"scenario://gas/{candidate_id}/rev-3",
    )


def test_energy_selection_ranks_only_feasible_candidates_deterministically() -> None:
    result = select_minimum_energy_dispatch(
        (
            _candidate("plan-c", 12_000_000.0),
            _candidate("plan-b", 9_000_000.0),
            _candidate("plan-a", 9_000_000.0),
            _candidate(
                "plan-rejected",
                1_000_000.0,
                constraints=(
                    _constraint(),
                    _constraint("pressure-delivery", passed=False),
                ),
            ),
        )
    )

    assert result.status is GasEnergySelectionStatus.OPTIMAL_DISCRETE
    assert [candidate.candidate_id for candidate in result.ranked] == [
        "plan-a",
        "plan-b",
        "plan-c",
    ]
    assert result.selected is not None
    assert result.selected.energy_j == 9_000_000.0
    assert result.generated_count == 4
    assert result.feasible_count == 3
    assert result.complete is True
    assert result.optimality_gap == 0.0
    assert result.objective_name == "minimum_total_energy_j"
    assert result.rejected[0].candidate_id == "plan-rejected"
    assert result.rejected[0].violation_codes == ("pressure-delivery",)


def test_energy_selection_returns_infeasible_without_fallback() -> None:
    result = select_minimum_energy_dispatch(
        (
            _candidate(
                "plan-a",
                10.0,
                constraints=(_constraint("envelope", passed=False),),
            ),
            _candidate(
                "plan-b",
                20.0,
                constraints=(_constraint("mass-balance", passed=False),),
            ),
        )
    )

    assert result.status is GasEnergySelectionStatus.INFEASIBLE
    assert result.ranked == ()
    assert result.selected is None
    assert result.optimality_gap is None
    assert {item.candidate_id for item in result.rejected} == {"plan-a", "plan-b"}


def test_candidate_requires_explicit_constraint_evidence() -> None:
    with pytest.raises(ValueError, match="aucune faisabilité implicite"):
        GasEnergyDispatchCandidate(
            candidate_id="plan-a",
            station_id="station://CS-01",
            interval_duration_s=3600.0,
            energy_j=10.0,
            operating_point_refs=("operating-point://A",),
            constraint_evidence=(),
            model_version="v1",
            source_ref="scenario://A",
        )


def test_candidate_rejects_invalid_energy_duration_and_duplicate_constraints() -> None:
    with pytest.raises(ValueError, match="énergie"):
        _candidate("negative-energy", -1.0)

    with pytest.raises(ValueError, match="durée"):
        GasEnergyDispatchCandidate(
            candidate_id="zero-duration",
            station_id="station://CS-01",
            interval_duration_s=0.0,
            energy_j=10.0,
            operating_point_refs=("operating-point://A",),
            constraint_evidence=(_constraint(),),
            model_version="v1",
            source_ref="scenario://A",
        )

    duplicated = (_constraint("envelope"), _constraint("envelope"))
    with pytest.raises(ValueError, match=r"contraintes.*uniques"):
        _candidate("duplicate-constraint", 10.0, constraints=duplicated)


def test_selection_rejects_empty_space_and_duplicate_candidate_ids() -> None:
    with pytest.raises(ValueError, match="Au moins un candidat"):
        select_minimum_energy_dispatch(())

    with pytest.raises(ValueError, match=r"candidats énergétiques.*uniques"):
        select_minimum_energy_dispatch((_candidate("same", 10.0), _candidate("same", 20.0)))


def test_candidate_preserves_traceability_and_deduplicates_operating_refs() -> None:
    candidate = GasEnergyDispatchCandidate(
        candidate_id="plan-a",
        station_id="station://CS-01",
        interval_duration_s=1800.0,
        energy_j=5_000.0,
        operating_point_refs=(
            " operating-point://unit-A ",
            "operating-point://unit-A",
            "operating-point://unit-B",
        ),
        constraint_evidence=(
            _constraint("envelope"),
            _constraint("mass-balance"),
        ),
        model_version="gas-eval-v2",
        source_ref="scenario://dispatch/rev-5",
    )

    result = select_minimum_energy_dispatch((candidate,))
    selected = result.selected
    assert selected is not None
    assert selected.operating_point_refs == (
        "operating-point://unit-A",
        "operating-point://unit-B",
    )
    assert selected.constraint_evidence_refs == (
        "evidence://gas/envelope/rev-2",
        "evidence://gas/mass-balance/rev-2",
    )
    assert selected.model_version == "gas-eval-v2"
    assert selected.source_ref == "scenario://dispatch/rev-5"
