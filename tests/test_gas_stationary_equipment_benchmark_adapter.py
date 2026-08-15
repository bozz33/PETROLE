from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from hydro_gas.stationary_equipment_benchmark_adapter import (
    StationaryEquipmentBenchmarkBinding,
    StationaryEquipmentBenchmarkQuantity,
    build_stationary_equipment_benchmark_observations,
)
from hydro_gas.stationary_equipment_solver import StationaryActiveCompressorGovernedSolveResult
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus


def _namespace(**values: object) -> SimpleNamespace:
    return SimpleNamespace(**values)


def _governed_result(
    *,
    status: StationaryWeymouthSolverStatus = StationaryWeymouthSolverStatus.CONVERGED,
) -> StationaryActiveCompressorGovernedSolveResult:
    candidate = _namespace(
        node_pressures=(
            _namespace(node_id="A", pressure_pa=2_000_000.0),
            _namespace(node_id="B", pressure_pa=2_600_000.0),
        ),
        pipe_flows=(_namespace(pipe_id="P1", mass_flow_kg_s=-1.2),),
        compressor_inputs=(
            _namespace(compressor_id="C1", mass_flow_kg_s=1.5, speed_rpm=1000.0),
        ),
        boundary_flows=(
            _namespace(boundary_id="SUPPLY-A", node_id="A", mass_flow_kg_s=1.5),
        ),
    )
    physical = _namespace(
        candidate=candidate,
        equipment_residuals=_namespace(
            compressor_constraints=(
                _namespace(
                    compressor_id="C1",
                    operating_point=_namespace(pressure_ratio=1.3),
                ),
            ),
        ),
    )
    solve = _namespace(
        solve_ref="solve://mixed/benchmark-test",
        status=status,
        final_evaluation=_namespace(physical_evaluation=physical),
    )
    return cast(StationaryActiveCompressorGovernedSolveResult, _namespace(solve=solve))


def test_mixed_benchmark_adapter_extracts_all_supported_quantities_without_conversion() -> None:
    bindings = (
        StationaryEquipmentBenchmarkBinding(
            observation_id="pressure-A",
            quantity=StationaryEquipmentBenchmarkQuantity.NODE_ABSOLUTE_PRESSURE,
            entity_id="A",
            unit="Pa",
            reference_value=2_000_100.0,
            reference_source_ref="external://reference/pressure-A",
        ),
        StationaryEquipmentBenchmarkBinding(
            observation_id="pipe-P1",
            quantity=StationaryEquipmentBenchmarkQuantity.PIPE_SIGNED_MASS_FLOW,
            entity_id="P1",
            unit="kg/s",
            reference_value=-1.19,
            reference_source_ref="external://reference/pipe-P1",
        ),
        StationaryEquipmentBenchmarkBinding(
            observation_id="compressor-flow-C1",
            quantity=StationaryEquipmentBenchmarkQuantity.COMPRESSOR_MASS_FLOW,
            entity_id="C1",
            unit="kg/s",
            reference_value=1.49,
            reference_source_ref="external://reference/compressor-flow-C1",
        ),
        StationaryEquipmentBenchmarkBinding(
            observation_id="compressor-ratio-C1",
            quantity=StationaryEquipmentBenchmarkQuantity.COMPRESSOR_PRESSURE_RATIO,
            entity_id="C1",
            unit="1",
            reference_value=1.31,
            reference_source_ref="external://reference/compressor-ratio-C1",
        ),
        StationaryEquipmentBenchmarkBinding(
            observation_id="boundary-SUPPLY-A",
            quantity=StationaryEquipmentBenchmarkQuantity.BOUNDARY_SIGNED_MASS_FLOW,
            entity_id="SUPPLY-A",
            unit="kg/s",
            reference_value=1.5,
            reference_source_ref="external://reference/boundary-SUPPLY-A",
        ),
    )

    bundle = build_stationary_equipment_benchmark_observations(
        _governed_result(),
        bindings,
        petrole_source_ref="petrole://solve/mixed/benchmark-test",
    )

    assert bundle.solve_ref == "solve://mixed/benchmark-test"
    assert bundle.solver_status is StationaryWeymouthSolverStatus.CONVERGED
    assert tuple(item.observation_id for item in bundle.observations) == tuple(
        item.observation_id for item in bindings
    )
    assert tuple(item.petrole_value for item in bundle.observations) == (
        2_000_000.0,
        -1.2,
        1.5,
        1.3,
        1.5,
    )
    assert tuple(item.unit for item in bundle.observations) == (
        "Pa",
        "kg/s",
        "kg/s",
        "1",
        "kg/s",
    )
    assert bundle.observations[3].location_ref == "compressor://C1"
    assert bundle.observations[3].quantity_ref == "quantity://gas/compressor_pressure_ratio"


def test_mixed_benchmark_adapter_preserves_non_converged_source_status_without_pass_fail() -> None:
    binding = StationaryEquipmentBenchmarkBinding(
        observation_id="pressure-A",
        quantity=StationaryEquipmentBenchmarkQuantity.NODE_ABSOLUTE_PRESSURE,
        entity_id="A",
        unit="Pa",
        reference_value=2_000_000.0,
        reference_source_ref="external://reference/pressure-A",
    )

    bundle = build_stationary_equipment_benchmark_observations(
        _governed_result(status=StationaryWeymouthSolverStatus.NON_CONVERGED),
        (binding,),
        petrole_source_ref="petrole://solve/non-converged",
    )

    assert bundle.solver_status is StationaryWeymouthSolverStatus.NON_CONVERGED
    assert bundle.observations[0].petrole_value == 2_000_000.0


def test_mixed_benchmark_binding_rejects_implicit_unit_conversion() -> None:
    with pytest.raises(ValueError, match="aucune conversion implicite"):
        StationaryEquipmentBenchmarkBinding(
            observation_id="pressure-A",
            quantity=StationaryEquipmentBenchmarkQuantity.NODE_ABSOLUTE_PRESSURE,
            entity_id="A",
            unit="bar",
            reference_value=20.0,
            reference_source_ref="external://reference/pressure-A-bar",
        )


def test_mixed_benchmark_adapter_rejects_missing_entity_duplicate_ids_and_empty_bindings() -> None:
    missing = StationaryEquipmentBenchmarkBinding(
        observation_id="missing-node",
        quantity=StationaryEquipmentBenchmarkQuantity.NODE_ABSOLUTE_PRESSURE,
        entity_id="UNKNOWN",
        unit="Pa",
        reference_value=1.0,
        reference_source_ref="external://reference/missing-node",
    )
    with pytest.raises(ValueError, match="n'existe pas"):
        build_stationary_equipment_benchmark_observations(
            _governed_result(),
            (missing,),
            petrole_source_ref="petrole://solve/mixed/benchmark-test",
        )

    first = StationaryEquipmentBenchmarkBinding(
        observation_id="duplicate",
        quantity=StationaryEquipmentBenchmarkQuantity.NODE_ABSOLUTE_PRESSURE,
        entity_id="A",
        unit="Pa",
        reference_value=2_000_000.0,
        reference_source_ref="external://reference/A",
    )
    second = StationaryEquipmentBenchmarkBinding(
        observation_id="duplicate",
        quantity=StationaryEquipmentBenchmarkQuantity.PIPE_SIGNED_MASS_FLOW,
        entity_id="P1",
        unit="kg/s",
        reference_value=-1.2,
        reference_source_ref="external://reference/P1",
    )
    with pytest.raises(ValueError, match="identifiants d'observation.*uniques"):
        build_stationary_equipment_benchmark_observations(
            _governed_result(),
            (first, second),
            petrole_source_ref="petrole://solve/mixed/benchmark-test",
        )

    with pytest.raises(ValueError, match="Au moins une liaison"):
        build_stationary_equipment_benchmark_observations(
            _governed_result(),
            (),
            petrole_source_ref="petrole://solve/mixed/benchmark-test",
        )
