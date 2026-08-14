from __future__ import annotations

from dataclasses import replace

import pytest

import hydro_gas

_SCALE_POLICY_REF = "scale-policy://synthetic-test-only/benchmark-adapter/v1"
_INITIAL_GUESS_POLICY_REF = "initial-guess://synthetic-test-only/benchmark-adapter/v1"


def _solve() -> hydro_gas.StationaryWeymouthSolveResult:
    problem = hydro_gas.StationaryWeymouthProblem(
        problem_ref="problem://gas/benchmark-adapter/simple/v1",
        network=hydro_gas.SteadyGasNetwork(
            nodes=(
                hydro_gas.SteadyGasNode("A", "model://node/A"),
                hydro_gas.SteadyGasNode("B", "model://node/B"),
            ),
            pipes=(hydro_gas.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),),
        ),
        pressure_slacks=(hydro_gas.GasPressureSlack("A", 5_000_000.0, "boundary://pressure/A"),),
        specified_boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("DEMAND-B", "B", -3.0, "boundary://demand/B"),
        ),
    )
    layout = hydro_gas.build_stationary_weymouth_unknown_layout(problem)
    state = hydro_gas.StationaryWeymouthUnknownState(
        state_ref="state://gas/benchmark-adapter/initial",
        unknown_node_pressures=(
            hydro_gas.GasNodePressure("B", 4_800_000.0, "initial://pressure/B"),
        ),
        pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 2.0, "initial://flow/P1"),),
        slack_external_flows=(
            hydro_gas.GasBoundaryMassFlow("SLACK-A", "A", 2.0, "initial://slack/A"),
        ),
    )
    scale = hydro_gas.StationaryWeymouthNumericalScale(
        pressure_squared_scale_pa2=25_000_000_000_000.0,
        mass_flow_scale_kg_s=10.0,
        mass_residual_scale_kg_s=10.0,
        pipe_residual_scale_pa2=1_000_000_000_000.0,
        source_ref="scale://synthetic-test-only/benchmark-adapter/v1",
    )
    initial_vector = hydro_gas.encode_stationary_weymouth_unknown_state(layout, state, scale)
    context = hydro_gas.StationarySolverQualificationContext(
        protocol_ref="protocol://gas/benchmark-adapter/synthetic-test-only/v1",
        problem_family_ref="problem-family://gas/weymouth/pressure-slack/v1",
        numerical_representation_ref=hydro_gas.WEYMOUTH_P2_NUMERICAL_REPRESENTATION_REF,
        solver_method_ref=hydro_gas.SCIPY_LEAST_SQUARES_TRF_METHOD_REF,
        scale_policy_ref=_SCALE_POLICY_REF,
        initial_guess_policy_ref=_INITIAL_GUESS_POLICY_REF,
    )
    preregistered = hydro_gas.PreRegisteredStationaryConvergenceCriterion(
        criterion_id="criterion://gas/benchmark-adapter/synthetic-test-only/v1",
        criterion_version="1",
        protocol_ref=context.protocol_ref,
        problem_family_ref=context.problem_family_ref,
        numerical_representation_ref=context.numerical_representation_ref,
        solver_method_ref=context.solver_method_ref,
        scale_policy_ref=context.scale_policy_ref,
        initial_guess_policy_ref=context.initial_guess_policy_ref,
        source_ref="source://synthetic-test-only/benchmark-adapter/convergence",
        registration_ref="registration://synthetic-test-only/benchmark-adapter/pre-run",
        maximum_scaled_residual_inf_norm=1e-8,
        state=hydro_gas.StationarySolverPolicyState.APPROVED,
        approval_ref="approval://synthetic-test-only/benchmark-adapter/convergence",
        maximum_mass_residual_kg_s=1e-7,
        maximum_pipe_residual_pa2=1_000.0,
    )
    criterion = hydro_gas.materialize_approved_stationary_convergence_criterion(
        context=context,
        criterion=preregistered,
    )
    configuration = hydro_gas.ScipyLeastSquaresTrfConfiguration(
        configuration_ref="config://synthetic-test-only/benchmark-adapter/trf/v1",
        source_ref="source://synthetic-test-only/benchmark-adapter/trf",
        solver_method_ref=context.solver_method_ref,
        numerical_representation_ref=context.numerical_representation_ref,
        scale_policy_ref=context.scale_policy_ref,
        initial_guess_policy_ref=context.initial_guess_policy_ref,
        ftol=1e-12,
        xtol=1e-12,
        gtol=1e-12,
        x_scale=1.0,
        diff_step=1e-6,
        max_nfev=100,
        jacobian_scheme="2-point",
        trust_region_solver="exact",
    )
    parameters = (
        hydro_gas.WeymouthSiPipeParameters(
            pipe_id="P1",
            length_m=1_000.0,
            diameter_m=0.5,
            friction_factor=0.01,
            sound_speed_m_s=350.0,
            equation_ref="reference://weymouth/validated-formulation",
            parameter_source_ref="reference://parameters/benchmark-adapter",
        ),
    )
    return hydro_gas.solve_stationary_weymouth_least_squares_trf(
        problem,
        layout,
        state,
        initial_vector,
        scale,
        parameters,
        context=context,
        convergence_criterion=criterion,
        configuration=configuration,
        solve_ref="solve://gas/benchmark-adapter/synthetic-test-only/001",
    )


def test_adapter_extracts_node_pressure_and_signed_pipe_flow_without_conversion() -> None:
    result = _solve()
    final_pressure_b = next(
        item.pressure_pa
        for item in result.final_evaluation.physical_evaluation.candidate.node_pressures
        if item.node_id == "B"
    )
    final_flow_p1 = result.final_evaluation.decoded_state.pipe_flows[0].mass_flow_kg_s
    bindings = (
        hydro_gas.StationaryGasBenchmarkBinding(
            observation_id="obs-pressure-B",
            quantity=hydro_gas.StationaryGasBenchmarkQuantity.NODE_ABSOLUTE_PRESSURE,
            entity_id="B",
            unit="Pa",
            reference_value=final_pressure_b + 10.0,
            reference_source_ref="reference://external/pressure-B",
        ),
        hydro_gas.StationaryGasBenchmarkBinding(
            observation_id="obs-flow-P1",
            quantity=hydro_gas.StationaryGasBenchmarkQuantity.PIPE_SIGNED_MASS_FLOW,
            entity_id="P1",
            unit="kg/s",
            reference_value=final_flow_p1 - 0.1,
            reference_source_ref="reference://external/flow-P1",
        ),
    )

    bundle = hydro_gas.build_stationary_weymouth_benchmark_observations(
        result,
        bindings,
        petrole_source_ref="result://petrole/benchmark-adapter/001",
    )

    pressure_obs, flow_obs = bundle.observations
    assert bundle.solver_status is hydro_gas.StationaryWeymouthSolverStatus.CONVERGED
    assert pressure_obs.unit == "Pa"
    assert pressure_obs.location_ref == "node://B"
    assert pressure_obs.petrole_value == pytest.approx(final_pressure_b)
    assert flow_obs.unit == "kg/s"
    assert flow_obs.location_ref == "pipe://P1"
    assert flow_obs.petrole_value == pytest.approx(final_flow_p1)
    assert flow_obs.quantity_ref.endswith("pipe_signed_mass_flow")


def test_adapter_refuses_unit_conversion_by_construction() -> None:
    with pytest.raises(ValueError, match="aucune conversion implicite"):
        hydro_gas.StationaryGasBenchmarkBinding(
            observation_id="obs-pressure-bar",
            quantity=hydro_gas.StationaryGasBenchmarkQuantity.NODE_ABSOLUTE_PRESSURE,
            entity_id="B",
            unit="bar",
            reference_value=50.0,
            reference_source_ref="reference://external/pressure-B-bar",
        )


def test_adapter_rejects_unknown_entities_and_duplicate_observation_ids() -> None:
    result = _solve()
    unknown_node = hydro_gas.StationaryGasBenchmarkBinding(
        observation_id="obs-unknown-node",
        quantity=hydro_gas.StationaryGasBenchmarkQuantity.NODE_ABSOLUTE_PRESSURE,
        entity_id="UNKNOWN",
        unit="Pa",
        reference_value=1.0,
        reference_source_ref="reference://external/unknown-node",
    )
    with pytest.raises(ValueError, match="nœud.*n'existe pas"):
        hydro_gas.build_stationary_weymouth_benchmark_observations(
            result,
            (unknown_node,),
            petrole_source_ref="result://petrole/benchmark-adapter/unknown",
        )

    first = hydro_gas.StationaryGasBenchmarkBinding(
        observation_id="duplicate",
        quantity=hydro_gas.StationaryGasBenchmarkQuantity.PIPE_SIGNED_MASS_FLOW,
        entity_id="P1",
        unit="kg/s",
        reference_value=3.0,
        reference_source_ref="reference://external/flow-1",
    )
    second = hydro_gas.StationaryGasBenchmarkBinding(
        observation_id="duplicate",
        quantity=hydro_gas.StationaryGasBenchmarkQuantity.NODE_ABSOLUTE_PRESSURE,
        entity_id="B",
        unit="Pa",
        reference_value=4_900_000.0,
        reference_source_ref="reference://external/pressure-2",
    )
    with pytest.raises(ValueError, match="uniques"):
        hydro_gas.build_stationary_weymouth_benchmark_observations(
            result,
            (first, second),
            petrole_source_ref="result://petrole/benchmark-adapter/duplicate",
        )


def test_adapter_preserves_non_converged_source_status_instead_of_hiding_it() -> None:
    converged = _solve()
    non_converged = replace(
        converged,
        status=hydro_gas.StationaryWeymouthSolverStatus.NON_CONVERGED,
    )
    binding = hydro_gas.StationaryGasBenchmarkBinding(
        observation_id="obs-status-preserved",
        quantity=hydro_gas.StationaryGasBenchmarkQuantity.PIPE_SIGNED_MASS_FLOW,
        entity_id="P1",
        unit="kg/s",
        reference_value=3.0,
        reference_source_ref="reference://external/status-preserved",
    )

    bundle = hydro_gas.build_stationary_weymouth_benchmark_observations(
        non_converged,
        (binding,),
        petrole_source_ref="result://petrole/benchmark-adapter/non-converged",
    )

    assert bundle.solver_status is hydro_gas.StationaryWeymouthSolverStatus.NON_CONVERGED
    assert len(bundle.observations) == 1
