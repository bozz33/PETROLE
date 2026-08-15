from __future__ import annotations

import pytest

from hydro_gas.compressor_map import CompressorMap, CompressorMapPoint, CompressorSpeedLine
from hydro_gas.network_balance import (
    GasBoundaryMassFlow,
    GasPipeMassFlow,
    SteadyGasNetwork,
    SteadyGasNode,
    SteadyGasPipe,
)
from hydro_gas.stationary_equipment_balance import GasCompressorMassFlow, SteadyGasCompressorEdge
from hydro_gas.stationary_equipment_candidate import StationaryActiveCompressorUnknownState
from hydro_gas.stationary_equipment_problem import (
    StationaryActiveCompressorProblem,
    StationaryCompressorSpeedControl,
    build_stationary_active_compressor_unknown_layout,
)
from hydro_gas.stationary_equipment_residual import StationaryCompressorMapBinding
from hydro_gas.stationary_equipment_solver_governance import (
    PreRegisteredStationaryEquipmentConvergenceCriterion,
    materialize_approved_stationary_equipment_convergence_criterion,
)
from hydro_gas.stationary_equipment_solver_inputs import (
    PreRegisteredStationaryEquipmentInitialGuessArtifact,
    PreRegisteredStationaryEquipmentScaleArtifact,
    materialize_approved_stationary_equipment_initial_guess,
    materialize_approved_stationary_equipment_scale,
    stationary_active_compressor_layout_sha256,
)
from hydro_gas.stationary_problem import GasPressureSlack
from hydro_gas.stationary_solver_governance import (
    StationarySolverPolicyState,
    StationarySolverQualificationContext,
)
from hydro_gas.weymouth_network_residual import GasNodePressure


def _problem() -> StationaryActiveCompressorProblem:
    compressor_map = CompressorMap(
        source_ref="supplier://synthetic-governance-test",
        version="test-v1",
        speed_lines=(
            CompressorSpeedLine(
                speed_rpm=1000.0,
                points=(
                    CompressorMapPoint(1.0, 1.5, 0.8),
                    CompressorMapPoint(2.0, 1.5, 0.8),
                ),
            ),
        ),
    )
    return StationaryActiveCompressorProblem(
        problem_ref="problem://mixed/governance-test",
        network=SteadyGasNetwork(
            nodes=tuple(
                SteadyGasNode(node_id, f"model://node/{node_id}")
                for node_id in ("A", "B", "C")
            ),
            pipes=(SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),),
        ),
        compressor_edges=(
            SteadyGasCompressorEdge("C1", "B", "C", "model://compressor/C1"),
        ),
        pressure_slacks=(GasPressureSlack("A", 2_000_000.0, "boundary://pressure/A"),),
        compressor_speed_controls=(
            StationaryCompressorSpeedControl("C1", 1000.0, "control://speed/C1"),
        ),
        map_bindings=(
            StationaryCompressorMapBinding("C1", compressor_map, "binding://map/C1"),
        ),
        specified_boundary_flows=(
            GasBoundaryMassFlow("DEMAND-C", "C", -1.0, "boundary://demand/C"),
        ),
    )


def _state() -> StationaryActiveCompressorUnknownState:
    return StationaryActiveCompressorUnknownState(
        state_ref="state://mixed/governance-test",
        unknown_node_pressures=(
            GasNodePressure("B", 2_000_000.0, "state://pressure/B"),
            GasNodePressure("C", 3_000_000.0, "state://pressure/C"),
        ),
        pipe_flows=(GasPipeMassFlow("P1", 1.0, "state://pipe/P1"),),
        compressor_flows=(
            GasCompressorMassFlow("C1", 1.0, "state://compressor/C1"),
        ),
        slack_external_flows=(
            GasBoundaryMassFlow("SLACK-A", "A", 1.0, "state://slack/A"),
        ),
    )


def _context() -> StationarySolverQualificationContext:
    return StationarySolverQualificationContext(
        protocol_ref="protocol://mixed/test/v1",
        problem_family_ref="problem-family://gas/mixed-compressor/v1",
        numerical_representation_ref="numerics://gas/mixed/psqr-scaled/v1",
        solver_method_ref="solver-method://synthetic/not-executed",
        scale_policy_ref="scale-policy://mixed/test/v1",
        initial_guess_policy_ref="initial-policy://mixed/test/v1",
    )


def test_mixed_scale_requires_approval_before_materialization() -> None:
    draft = PreRegisteredStationaryEquipmentScaleArtifact(
        artifact_ref="artifact://scale/mixed/test",
        policy_ref="scale-policy://mixed/test/v1",
        policy_version="1",
        source_ref="source://synthetic/scale",
        registration_ref="registration://scale/mixed/test",
        pressure_squared_scale_pa2=1.0e12,
        mass_flow_scale_kg_s=1.0,
        mass_residual_scale_kg_s=1.0,
        pipe_residual_scale_pa2=1.0e12,
        compressor_residual_scale_pa=1.0e6,
    )
    with pytest.raises(PermissionError, match="n'est pas APPROVED"):
        materialize_approved_stationary_equipment_scale(draft)

    approved = PreRegisteredStationaryEquipmentScaleArtifact(
        artifact_ref=draft.artifact_ref,
        policy_ref=draft.policy_ref,
        policy_version=draft.policy_version,
        source_ref=draft.source_ref,
        registration_ref=draft.registration_ref,
        pressure_squared_scale_pa2=draft.pressure_squared_scale_pa2,
        mass_flow_scale_kg_s=draft.mass_flow_scale_kg_s,
        mass_residual_scale_kg_s=draft.mass_residual_scale_kg_s,
        pipe_residual_scale_pa2=draft.pipe_residual_scale_pa2,
        compressor_residual_scale_pa=draft.compressor_residual_scale_pa,
        state=StationarySolverPolicyState.APPROVED,
        approval_ref="approval://scale/mixed/test",
    )
    materialized = materialize_approved_stationary_equipment_scale(approved)
    assert materialized.compressor_residual_scale_pa == 1.0e6
    assert materialized.to_numerical_scale().compressor_residual_scale_pa == 1.0e6


def test_mixed_initial_guess_is_bound_to_exact_layout_hash() -> None:
    problem = _problem()
    layout = build_stationary_active_compressor_unknown_layout(problem)
    layout_sha256 = stationary_active_compressor_layout_sha256(layout)
    assert layout_sha256.startswith("sha256:")
    assert len(layout_sha256) == 71

    artifact = PreRegisteredStationaryEquipmentInitialGuessArtifact(
        artifact_ref="artifact://initial/mixed/test",
        policy_ref="initial-policy://mixed/test/v1",
        policy_version="1",
        problem_ref=problem.problem_ref,
        layout_sha256=layout_sha256,
        source_ref="source://synthetic/initial",
        registration_ref="registration://initial/mixed/test",
        unknown_state=_state(),
        state=StationarySolverPolicyState.APPROVED,
        approval_ref="approval://initial/mixed/test",
    )
    approved = materialize_approved_stationary_equipment_initial_guess(
        problem=problem,
        layout=layout,
        artifact=artifact,
    )
    assert approved.layout_sha256 == layout_sha256
    assert approved.unknown_state.compressor_flows[0].mass_flow_kg_s == 1.0


def test_mixed_convergence_criterion_preserves_explicit_compressor_limit() -> None:
    context = _context()
    criterion = PreRegisteredStationaryEquipmentConvergenceCriterion(
        criterion_id="mixed-synthetic-test",
        criterion_version="1",
        protocol_ref=context.protocol_ref,
        problem_family_ref=context.problem_family_ref,
        numerical_representation_ref=context.numerical_representation_ref,
        solver_method_ref=context.solver_method_ref,
        scale_policy_ref=context.scale_policy_ref,
        initial_guess_policy_ref=context.initial_guess_policy_ref,
        source_ref="source://synthetic/convergence",
        registration_ref="registration://convergence/mixed/test",
        maximum_scaled_residual_inf_norm=0.01,
        maximum_mass_residual_kg_s=0.02,
        maximum_pipe_residual_pa2=3.0,
        maximum_compressor_residual_pa=4.0,
        state=StationarySolverPolicyState.APPROVED,
        approval_ref="approval://convergence/mixed/test",
    )
    approved = materialize_approved_stationary_equipment_convergence_criterion(
        context=context,
        criterion=criterion,
    )
    assert approved.maximum_scaled_residual_inf_norm == 0.01
    assert approved.maximum_compressor_residual_pa == 4.0


def test_mixed_convergence_draft_and_context_mismatch_are_blocked() -> None:
    context = _context()
    draft = PreRegisteredStationaryEquipmentConvergenceCriterion(
        criterion_id="mixed-draft",
        criterion_version="1",
        protocol_ref=context.protocol_ref,
        problem_family_ref=context.problem_family_ref,
        numerical_representation_ref=context.numerical_representation_ref,
        solver_method_ref=context.solver_method_ref,
        scale_policy_ref=context.scale_policy_ref,
        initial_guess_policy_ref=context.initial_guess_policy_ref,
        source_ref="source://synthetic/convergence",
        registration_ref="registration://convergence/mixed/draft",
        maximum_scaled_residual_inf_norm=0.01,
    )
    with pytest.raises(PermissionError, match="n'est pas APPROVED"):
        materialize_approved_stationary_equipment_convergence_criterion(
            context=context,
            criterion=draft,
        )

    approved_wrong_context = PreRegisteredStationaryEquipmentConvergenceCriterion(
        criterion_id="mixed-wrong-context",
        criterion_version="1",
        protocol_ref=context.protocol_ref,
        problem_family_ref=context.problem_family_ref,
        numerical_representation_ref=context.numerical_representation_ref,
        solver_method_ref="solver-method://other",
        scale_policy_ref=context.scale_policy_ref,
        initial_guess_policy_ref=context.initial_guess_policy_ref,
        source_ref="source://synthetic/convergence",
        registration_ref="registration://convergence/mixed/wrong",
        maximum_scaled_residual_inf_norm=0.01,
        state=StationarySolverPolicyState.APPROVED,
        approval_ref="approval://convergence/mixed/wrong",
    )
    with pytest.raises(ValueError, match="contexte solveur"):
        materialize_approved_stationary_equipment_convergence_criterion(
            context=context,
            criterion=approved_wrong_context,
        )
