from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from hydro_gas.stationary_equipment_result_tables import (
    build_stationary_active_compressor_result_tables,
)
from hydro_gas.stationary_equipment_solver import StationaryActiveCompressorGovernedSolveResult
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus


def _namespace(**values: object) -> SimpleNamespace:
    return SimpleNamespace(**values)


def _result(*, mismatched_pipe: bool = False) -> StationaryActiveCompressorGovernedSolveResult:
    candidate = _namespace(
        node_pressures=(
            _namespace(node_id="A", pressure_pa=2_000_000.0, source_ref="state://pressure/A"),
            _namespace(node_id="B", pressure_pa=2_500_000.0, source_ref="state://pressure/B"),
        ),
        pipe_flows=(
            _namespace(
                pipe_id="OTHER" if mismatched_pipe else "P1",
                mass_flow_kg_s=1.0,
                source_ref="state://pipe/P1",
            ),
        ),
        compressor_inputs=(
            _namespace(
                compressor_id="C1",
                mass_flow_kg_s=1.0,
                speed_rpm=1000.0,
                source_ref="state://compressor/C1",
            ),
        ),
        boundary_flows=(
            _namespace(
                boundary_id="SUPPLY-A",
                node_id="A",
                mass_flow_kg_s=1.0,
                source_ref="boundary://supply/A",
            ),
        ),
    )
    mass_balance = _namespace(
        node_balances=(
            _namespace(node_id="A", residual_kg_s=0.0),
            _namespace(node_id="B", residual_kg_s=0.0),
        ),
    )
    pipe_residual = _namespace(
        pipe_id="P1",
        residual_pa2=0.0,
        pressure_squared_difference_pa2=-1.0,
        friction_term_pa2=1.0,
        equation_ref="equation://weymouth/si",
        parameter_source_ref="parameters://P1",
    )
    envelope = _namespace(
        inside_envelope=True,
        minimum_mass_flow_kg_s=0.5,
        maximum_mass_flow_kg_s=2.0,
        source_ref="supplier://envelope/C1",
        envelope_version="env-v1",
    )
    constraint = _namespace(
        compressor_id="C1",
        expected_outlet_pressure_pa=2_500_000.0,
        pressure_ratio_residual_pa=0.0,
        state_source_ref="state://compressor/C1",
        operating_point=_namespace(
            pressure_ratio=1.25,
            isentropic_efficiency=0.8,
            source_ref="supplier://map/C1",
            map_version="map-v1",
        ),
        envelope_assessment=envelope,
    )
    physical = _namespace(
        candidate=candidate,
        pipe_residuals=(pipe_residual,),
        equipment_residuals=_namespace(
            mass_balance=mass_balance,
            compressor_constraints=(constraint,),
        ),
    )
    solve = _namespace(
        solve_ref="solve://mixed/tables-test",
        status=StationaryWeymouthSolverStatus.CONVERGED,
        final_evaluation=_namespace(physical_evaluation=physical),
        missing_operational_envelope_compressor_ids=("C2",),
    )
    return cast(StationaryActiveCompressorGovernedSolveResult, _namespace(solve=solve))


def test_result_tables_join_scientific_outputs_without_recalculation() -> None:
    tables = build_stationary_active_compressor_result_tables(_result())

    assert tables.solve_ref == "solve://mixed/tables-test"
    assert tables.status is StationaryWeymouthSolverStatus.CONVERGED
    assert tables.nodes[0].node_id == "A"
    assert tables.nodes[0].pressure_pa == 2_000_000.0
    assert tables.nodes[0].mass_residual_kg_s == 0.0
    assert tables.pipes[0].pipe_id == "P1"
    assert tables.pipes[0].mass_flow_kg_s == 1.0
    assert tables.pipes[0].pressure_squared_difference_pa2 == -1.0
    assert tables.compressors[0].compressor_id == "C1"
    assert tables.compressors[0].pressure_ratio == 1.25
    assert tables.compressors[0].isentropic_efficiency == 0.8
    assert tables.compressors[0].inside_envelope is True
    assert tables.compressors[0].envelope_source_ref == "supplier://envelope/C1"
    assert tables.boundaries[0].boundary_id == "SUPPLY-A"
    assert tables.warnings == ("operational_envelope_missing:C2",)


def test_result_tables_reject_misaligned_pipe_coverage() -> None:
    with pytest.raises(ValueError, match=r"débits de conduite.*mêmes conduites"):
        build_stationary_active_compressor_result_tables(_result(mismatched_pipe=True))
