from __future__ import annotations

import pytest

from hydro_gas.compressor_limits import CompressorFlowLimitPoint, CompressorOperatingEnvelope
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
from hydro_gas.stationary_equipment_solver import (
    ACTIVE_COMPRESSOR_P2_NUMERICAL_REPRESENTATION_REF,
    ACTIVE_COMPRESSOR_PROBLEM_FAMILY_REF,
    ScipyActiveCompressorLeastSquaresTrfConfiguration,
    solve_stationary_active_compressor_with_approved_inputs,
)
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
from hydro_gas.stationary_solver import SCIPY_LEAST_SQUARES_TRF_METHOD_REF
from hydro_gas.stationary_solver_governance import (
    StationarySolverPolicyState,
    StationarySolverQualificationContext,
    StationaryWeymouthSolverStatus,
)
from hydro_gas.weymouth_network_residual import GasNodePressure
from hydro_gas.weymouth_si import WeymouthSiPipeParameters


def _problem(*, with_envelope: bool = True) -> StationaryActiveCompressorProblem:
    compressor_map = CompressorMap(
        source_ref="supplier://synthetic-solver-map",
        version="test-v1",
        speed_lines=(
            CompressorSpeedLine(
                speed_rpm=1000.0,
                points=(
                    CompressorMapPoint(0.5, 1.5, 0.8),
                    CompressorMapPoint(2.0, 1.5, 0.8),
                ),
            ),
        ),
    )
    envelope = (
        CompressorOperatingEnvelope(
            source_ref="supplier://synthetic-solver-envelope",
            version="test-v1",
            points=(CompressorFlowLimitPoint(1000.0, 0.5, 2.0),),
        )
        if with_envelope
        else None
    )
    return StationaryActiveCompressorProblem(
        problem_ref="problem://mixed/solver-test",
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
            StationaryCompressorMapBinding(
                compressor_id="C1",
                compressor_map=compressor_map,
                source_ref="binding://map/C1",
                envelope=envelope,
            ),
        ),
        specified_boundary_flows=(
            GasBoundaryMassFlow("DEMAND-C", "C", -1.0, "boundary://demand/C"),
        ),
    )


def _state(*, compressor_flow_kg_s: float = 1.0) -> StationaryActiveCompressorUnknownState:
    return StationaryActiveCompressorUnknownState(
        state_ref="state://mixed/solver-test",
        unknown_node_pressures=(
            GasNodePressure("B", 2_000_000.0, "state://pressure/B"),
            GasNodePressure("C", 3_000_000.0, "state://pressure/C"),
        ),
        pipe_flows=(GasPipeMassFlow("P1", 1.0, "state://pipe/P1"),),
        compressor_flows=(
            GasCompressorMassFlow("C1", compressor_flow_kg_s, "state://compressor/C1"),
        ),
        slack_external_flows=(
            GasBoundaryMassFlow("SLACK-A", "A", 1.0, "state://slack/A"),
        ),
    )


def _context() -> StationarySolverQualificationContext:
    return StationarySolverQualificationContext(
        protocol_ref="protocol://mixed/solver-test/v1",
        problem_family_ref=ACTIVE_COMPRESSOR_PROBLEM_FAMILY_REF,
        numerical_representation_ref=ACTIVE_COMPRESSOR_P2_NUMERICAL_REPRESENTATION_REF,
        solver_method_ref=SCIPY_LEAST_SQUARES_TRF_METHOD_REF,
        scale_policy_ref="scale-policy://mixed/solver-test/v1",
        initial_guess_policy_ref="initial-policy://mixed/solver-test/v1",
    )


def _configuration() -> ScipyActiveCompressorLeastSquaresTrfConfiguration:
    context = _context()
    return ScipyActiveCompressorLeastSquaresTrfConfiguration(
        configuration_ref="configuration://mixed/solver-test",
        source_ref="source://scipy/test-configuration",
        solver_method_ref=context.solver_method_ref,
        numerical_representation_ref=context.numerical_representation_ref,
        scale_policy_ref=context.scale_policy_ref,
        initial_guess_policy_ref=context.initial_guess_policy_ref,
        ftol=1.0e-8,
        xtol=1.0e-8,
        gtol=1.0e-8,
        x_scale=1.0,
        diff_step=1.0e-6,
        max_nfev=100,
        jacobian_scheme="2-point",
        trust_region_solver="exact",
    )


def _approved_scale():
    artifact = PreRegisteredStationaryEquipmentScaleArtifact(
        artifact_ref="artifact://scale/mixed/solver-test",
        policy_ref=_context().scale_policy_ref,
        policy_version="1",
        source_ref="source://synthetic/solver-scale",
        registration_ref="registration://scale/mixed/solver-test",
        pressure_squared_scale_pa2=1.0e12,
        mass_flow_scale_kg_s=1.0,
        mass_residual_scale_kg_s=1.0,
        pipe_residual_scale_pa2=1.0e12,
        compressor_residual_scale_pa=1.0e6,
        state=StationarySolverPolicyState.APPROVED,
        approval_ref="approval://scale/mixed/solver-test",
    )
    return materialize_approved_stationary_equipment_scale(artifact)


def _approved_initial(problem: StationaryActiveCompressorProblem, *, flow: float = 1.0):
    layout = build_stationary_active_compressor_unknown_layout(problem)
    artifact = PreRegisteredStationaryEquipmentInitialGuessArtifact(
        artifact_ref="artifact://initial/mixed/solver-test",
        policy_ref=_context().initial_guess_policy_ref,
        policy_version="1",
        problem_ref=problem.problem_ref,
        layout_sha256=stationary_active_compressor_layout_sha256(layout),
        source_ref="source://synthetic/solver-initial",
        registration_ref="registration://initial/mixed/solver-test",
        unknown_state=_state(compressor_flow_kg_s=flow),
        state=StationarySolverPolicyState.APPROVED,
        approval_ref="approval://initial/mixed/solver-test",
    )
    return materialize_approved_stationary_equipment_initial_guess(
        problem=problem,
        layout=layout,
        artifact=artifact,
    )


def _approved_criterion():
    context = _context()
    criterion = PreRegisteredStationaryEquipmentConvergenceCriterion(
        criterion_id="mixed-solver-synthetic",
        criterion_version="1",
        protocol_ref=context.protocol_ref,
        problem_family_ref=context.problem_family_ref,
        numerical_representation_ref=context.numerical_representation_ref,
        solver_method_ref=context.solver_method_ref,
        scale_policy_ref=context.scale_policy_ref,
        initial_guess_policy_ref=context.initial_guess_policy_ref,
        source_ref="source://synthetic/solver-criterion",
        registration_ref="registration://criterion/mixed/solver-test",
        maximum_scaled_residual_inf_norm=1.0e-8,
        maximum_mass_residual_kg_s=1.0e-8,
        maximum_pipe_residual_pa2=1.0,
        maximum_compressor_residual_pa=1.0e-6,
        state=StationarySolverPolicyState.APPROVED,
        approval_ref="approval://criterion/mixed/solver-test",
    )
    return materialize_approved_stationary_equipment_convergence_criterion(
        context=context,
        criterion=criterion,
    )


def _pipe_parameters() -> tuple[WeymouthSiPipeParameters, ...]:
    return (
        WeymouthSiPipeParameters(
            pipe_id="P1",
            length_m=1000.0,
            diameter_m=0.5,
            friction_factor=0.0,
            sound_speed_m_s=350.0,
            equation_ref="equation://weymouth/test",
            parameter_source_ref="parameters://pipe/P1/test",
        ),
    )


def test_governed_mixed_solver_converges_on_exact_synthetic_state() -> None:
    problem = _problem()
    layout = build_stationary_active_compressor_unknown_layout(problem)

    result = solve_stationary_active_compressor_with_approved_inputs(
        problem,
        layout,
        _pipe_parameters(),
        context=_context(),
        convergence_criterion=_approved_criterion(),
        configuration=_configuration(),
        scale_artifact=_approved_scale(),
        initial_guess_artifact=_approved_initial(problem),
        solve_ref="solve://mixed/synthetic",
    )

    assert result.solve.status is StationaryWeymouthSolverStatus.CONVERGED
    assert result.solve.convergence.all_approved_criteria_passed is True
    assert result.solve.final_evaluation.residual_vector.values == pytest.approx((0.0,) * 5)
    assert result.solve.missing_operational_envelope_compressor_ids == ()
    assert result.solve.numerical_bounds.compressor_flow_bounds[0].minimum_mass_flow_kg_s == 0.5
    assert result.scale_approval_ref == "approval://scale/mixed/solver-test"
    assert result.initial_guess_approval_ref == "approval://initial/mixed/solver-test"


def test_governed_mixed_solver_refuses_approved_initial_guess_outside_map_domain() -> None:
    problem = _problem()
    layout = build_stationary_active_compressor_unknown_layout(problem)

    with pytest.raises(ValueError, match="hors des bornes"):
        solve_stationary_active_compressor_with_approved_inputs(
            problem,
            layout,
            _pipe_parameters(),
            context=_context(),
            convergence_criterion=_approved_criterion(),
            configuration=_configuration(),
            scale_artifact=_approved_scale(),
            initial_guess_artifact=_approved_initial(problem, flow=3.0),
            solve_ref="solve://mixed/out-of-domain",
        )


def test_governed_mixed_solver_reports_missing_optional_operational_envelope() -> None:
    problem = _problem(with_envelope=False)
    layout = build_stationary_active_compressor_unknown_layout(problem)

    result = solve_stationary_active_compressor_with_approved_inputs(
        problem,
        layout,
        _pipe_parameters(),
        context=_context(),
        convergence_criterion=_approved_criterion(),
        configuration=_configuration(),
        scale_artifact=_approved_scale(),
        initial_guess_artifact=_approved_initial(problem),
        solve_ref="solve://mixed/no-envelope",
    )

    assert result.solve.status is StationaryWeymouthSolverStatus.CONVERGED
    assert result.solve.missing_operational_envelope_compressor_ids == ("C1",)
