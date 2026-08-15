from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from typing import cast

import pytest

from hydro_gas.stationary_equipment_result_export import (
    MIXED_STATIONARY_GAS_EXPORT_VERSION,
    MIXED_STATIONARY_GAS_RESULT_MODEL_VERSION,
    export_stationary_active_compressor_solve_result_json,
)
from hydro_gas.stationary_equipment_solver import StationaryActiveCompressorGovernedSolveResult
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus


def _namespace(**values: object) -> SimpleNamespace:
    return SimpleNamespace(**values)


def _governed_result() -> StationaryActiveCompressorGovernedSolveResult:
    candidate = _namespace(
        node_pressures=(
            _namespace(node_id="A", pressure_pa=2_000_000.0, source_ref="state://pressure/A"),
            _namespace(node_id="B", pressure_pa=3_000_000.0, source_ref="state://pressure/B"),
        ),
        pipe_flows=(
            _namespace(pipe_id="P1", mass_flow_kg_s=1.0, source_ref="state://pipe/P1"),
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
        global_residual_kg_s=0.0,
        max_abs_node_residual_kg_s=0.0,
        node_balances=(
            _namespace(
                node_id="A",
                incoming_pipe_mass_flow_kg_s=0.0,
                outgoing_pipe_mass_flow_kg_s=1.0,
                incoming_compressor_mass_flow_kg_s=0.0,
                outgoing_compressor_mass_flow_kg_s=0.0,
                external_mass_flow_kg_s=1.0,
                residual_kg_s=0.0,
            ),
            _namespace(
                node_id="B",
                incoming_pipe_mass_flow_kg_s=1.0,
                outgoing_pipe_mass_flow_kg_s=0.0,
                incoming_compressor_mass_flow_kg_s=0.0,
                outgoing_compressor_mass_flow_kg_s=1.0,
                external_mass_flow_kg_s=0.0,
                residual_kg_s=0.0,
            ),
        ),
    )
    pipe_residual = _namespace(
        pipe_id="P1",
        residual_pa2=0.0,
        pressure_squared_difference_pa2=-5_000_000_000_000.0,
        friction_term_pa2=5_000_000_000_000.0,
        resistance_coefficient_pa2_per_kg_s2=5_000_000_000_000.0,
        observation_source_ref="state://mixed/final",
        parameter_source_ref="parameters://pipe/P1",
        equation_ref="equation://weymouth/si",
    )
    operating_point = _namespace(
        speed_rpm=1000.0,
        mass_flow_kg_s=1.0,
        pressure_ratio=1.5,
        isentropic_efficiency=0.8,
        source_ref="supplier://map/C1",
        map_version="map-v1",
    )
    compressor_constraint = _namespace(
        compressor_id="C1",
        state_source_ref="state://compressor/C1",
        expected_outlet_pressure_pa=3_000_000.0,
        pressure_ratio_residual_pa=0.0,
        operating_point=operating_point,
        envelope_assessment=None,
    )
    physical_evaluation = _namespace(
        candidate=candidate,
        pipe_residuals=(pipe_residual,),
        equipment_residuals=_namespace(
            mass_balance=mass_balance,
            compressor_constraints=(compressor_constraint,),
        ),
    )
    final_evaluation = _namespace(physical_evaluation=physical_evaluation)
    convergence = _namespace(
        criterion_id="criterion-mixed-v1",
        criterion_version="1",
        approval_ref="approval://criterion/mixed/v1",
        scaled_residual_inf_norm=0.0,
        maximum_mass_residual_kg_s=0.0,
        maximum_pipe_residual_pa2=0.0,
        maximum_compressor_residual_pa=0.0,
        scaled_residual_passed=True,
        mass_residual_passed=True,
        pipe_residual_passed=True,
        compressor_residual_passed=True,
        all_approved_criteria_passed=True,
    )
    numerical_bounds = _namespace(
        source_ref="bounds://mixed/final",
        lower_values=(0.0, -float("inf"), 0.5, -float("inf")),
        upper_values=(float("inf"), float("inf"), 2.0, float("inf")),
        compressor_flow_bounds=(
            _namespace(
                compressor_id="C1",
                speed_rpm=1000.0,
                minimum_mass_flow_kg_s=0.5,
                maximum_mass_flow_kg_s=2.0,
                map_source_ref="supplier://map/C1",
                map_version="map-v1",
                envelope_source_ref=None,
                envelope_version=None,
            ),
        ),
    )
    solve = _namespace(
        solve_ref="solve://mixed/export-test",
        status=StationaryWeymouthSolverStatus.CONVERGED,
        final_evaluation=final_evaluation,
        convergence=convergence,
        numerical_bounds=numerical_bounds,
        initial_vector=_namespace(values=(4.0, 1.0, 1.0, 1.0)),
        final_vector=_namespace(values=(4.0, 1.0, 1.0, 1.0)),
        scipy_success=True,
        scipy_status=1,
        scipy_message="synthetic test",
        scipy_version="test-version",
        nfev=1,
        njev=1,
        cost=0.0,
        optimality=0.0,
        active_mask=(0, 0, 0, 0),
        configuration_ref="configuration://mixed/test",
        configuration_source_ref="source://solver/configuration",
        missing_operational_envelope_compressor_ids=("C1",),
    )
    result = _namespace(
        solve=solve,
        scale_artifact_ref="artifact://scale/mixed/v1",
        scale_policy_ref="scale-policy://mixed/v1",
        scale_approval_ref="approval://scale/mixed/v1",
        initial_guess_artifact_ref="artifact://initial/mixed/v1",
        initial_guess_policy_ref="initial-policy://mixed/v1",
        initial_guess_approval_ref="approval://initial/mixed/v1",
    )
    return cast(StationaryActiveCompressorGovernedSolveResult, result)


def test_mixed_solver_export_is_canonical_traceable_and_json_safe() -> None:
    artifact = export_stationary_active_compressor_solve_result_json(
        _governed_result(),
        composition_source_ref="composition://gas/test",
        property_method_ref="property-method://gas/test",
    )

    assert artifact.media_type == "application/json"
    assert artifact.filename == "gas-results.json"
    assert artifact.sha256 == hashlib.sha256(artifact.content).hexdigest()

    document = json.loads(artifact.content)
    assert document["export_version"] == MIXED_STATIONARY_GAS_EXPORT_VERSION
    assert document["model_version"] == MIXED_STATIONARY_GAS_RESULT_MODEL_VERSION
    assert document["results"]["status"] == "converged"
    assert document["assumptions"]["certification_claim"] is False
    assert document["results"]["candidate"]["compressor_inputs"][0]["speed_rpm"] == 1000.0
    assert document["diagnostics"]["convergence"]["approval_ref"] == (
        "approval://criterion/mixed/v1"
    )
    assert document["diagnostics"]["physical_residuals"]["pipe_residuals"][0][
        "resistance_coefficient_pa2_per_kg_s2"
    ] == 5_000_000_000_000.0
    assert document["diagnostics"]["numerical_bounds"]["null_bound_semantics"] == "unbounded"
    assert document["diagnostics"]["numerical_bounds"]["lower_values"] == [0.0, None, 0.5, None]
    assert document["diagnostics"]["numerical_bounds"]["upper_values"] == [None, None, 2.0, None]
    assert document["diagnostics"]["governance"]["scale_approval_ref"] == (
        "approval://scale/mixed/v1"
    )
    assert document["diagnostics"]["missing_operational_envelope_compressor_ids"] == ["C1"]


def test_mixed_solver_export_requires_property_and_composition_provenance() -> None:
    with pytest.raises(ValueError, match="composition.*méthode de propriétés"):
        export_stationary_active_compressor_solve_result_json(
            _governed_result(),
            composition_source_ref="",
            property_method_ref="property-method://gas/test",
        )
