"""Adaptateur P6-G pour les résultats du solveur gaz mixte gouverné.

Le module ne recalcule aucune grandeur scientifique. Il projette uniquement le
résultat déjà produit par le solveur conduites + compresseurs vers l'enveloppe
JSON canonique P6-G, afin de conserver les valeurs, diagnostics, bornes et
preuves d'approbation utilisées pendant l'exécution.
"""

from __future__ import annotations

import math
from typing import Any

from hydro_gas.result_export import GasResultExportArtifact, export_gas_results_json
from hydro_gas.stationary_equipment_solver import StationaryActiveCompressorGovernedSolveResult

MIXED_STATIONARY_GAS_RESULT_MODEL_VERSION = "phase6/stationary-active-compressor-solver/1"
MIXED_STATIONARY_GAS_EXPORT_VERSION = "phase6-gas/stationary-active-compressor/1"


def _candidate_payload(result: StationaryActiveCompressorGovernedSolveResult) -> dict[str, Any]:
    candidate = result.solve.final_evaluation.physical_evaluation.candidate
    return {
        "node_pressures": [
            {
                "node_id": item.node_id,
                "pressure_pa": item.pressure_pa,
                "source_ref": item.source_ref,
            }
            for item in candidate.node_pressures
        ],
        "pipe_flows": [
            {
                "pipe_id": item.pipe_id,
                "mass_flow_kg_s": item.mass_flow_kg_s,
                "source_ref": item.source_ref,
            }
            for item in candidate.pipe_flows
        ],
        "compressor_inputs": [
            {
                "compressor_id": item.compressor_id,
                "mass_flow_kg_s": item.mass_flow_kg_s,
                "speed_rpm": item.speed_rpm,
                "source_ref": item.source_ref,
            }
            for item in candidate.compressor_inputs
        ],
        "boundary_flows": [
            {
                "boundary_id": item.boundary_id,
                "node_id": item.node_id,
                "mass_flow_kg_s": item.mass_flow_kg_s,
                "source_ref": item.source_ref,
            }
            for item in candidate.boundary_flows
        ],
    }


def _residual_payload(result: StationaryActiveCompressorGovernedSolveResult) -> dict[str, Any]:
    physical = result.solve.final_evaluation.physical_evaluation
    mass_balance = physical.equipment_residuals.mass_balance
    return {
        "mass_balance": {
            "global_residual_kg_s": mass_balance.global_residual_kg_s,
            "max_abs_node_residual_kg_s": mass_balance.max_abs_node_residual_kg_s,
            "nodes": [
                {
                    "node_id": item.node_id,
                    "incoming_pipe_mass_flow_kg_s": item.incoming_pipe_mass_flow_kg_s,
                    "outgoing_pipe_mass_flow_kg_s": item.outgoing_pipe_mass_flow_kg_s,
                    "incoming_compressor_mass_flow_kg_s": item.incoming_compressor_mass_flow_kg_s,
                    "outgoing_compressor_mass_flow_kg_s": item.outgoing_compressor_mass_flow_kg_s,
                    "external_mass_flow_kg_s": item.external_mass_flow_kg_s,
                    "residual_kg_s": item.residual_kg_s,
                }
                for item in mass_balance.node_balances
            ],
        },
        "pipe_residuals": [
            {
                "pipe_id": item.pipe_id,
                "residual_pa2": item.residual_pa2,
                "pressure_squared_difference_pa2": item.pressure_squared_difference_pa2,
                "friction_term_pa2": item.friction_term_pa2,
                "resistance_coefficient_pa2_per_kg_s2": (
                    item.resistance_coefficient_pa2_per_kg_s2
                ),
                "observation_source_ref": item.observation_source_ref,
                "parameter_source_ref": item.parameter_source_ref,
                "equation_ref": item.equation_ref,
            }
            for item in physical.pipe_residuals
        ],
        "compressor_constraints": [
            {
                "compressor_id": item.compressor_id,
                "state_source_ref": item.state_source_ref,
                "expected_outlet_pressure_pa": item.expected_outlet_pressure_pa,
                "pressure_ratio_residual_pa": item.pressure_ratio_residual_pa,
                "operating_point": {
                    "speed_rpm": item.operating_point.speed_rpm,
                    "mass_flow_kg_s": item.operating_point.mass_flow_kg_s,
                    "pressure_ratio": item.operating_point.pressure_ratio,
                    "isentropic_efficiency": item.operating_point.isentropic_efficiency,
                    "source_ref": item.operating_point.source_ref,
                    "map_version": item.operating_point.map_version,
                },
                "envelope": (
                    None
                    if item.envelope_assessment is None
                    else {
                        "minimum_mass_flow_kg_s": item.envelope_assessment.minimum_mass_flow_kg_s,
                        "maximum_mass_flow_kg_s": item.envelope_assessment.maximum_mass_flow_kg_s,
                        "minimum_flow_margin_kg_s": item.envelope_assessment.minimum_flow_margin_kg_s,
                        "maximum_flow_margin_kg_s": item.envelope_assessment.maximum_flow_margin_kg_s,
                        "inside_envelope": item.envelope_assessment.inside_envelope,
                        "source_ref": item.envelope_assessment.source_ref,
                        "envelope_version": item.envelope_assessment.envelope_version,
                    }
                ),
            }
            for item in physical.equipment_residuals.compressor_constraints
        ],
    }


def _json_bound(value: float) -> float | None:
    """Encode ``None`` pour une borne numérique structurellement non bornée."""

    return value if math.isfinite(value) else None


def _bounds_payload(result: StationaryActiveCompressorGovernedSolveResult) -> dict[str, Any]:
    bounds = result.solve.numerical_bounds
    return {
        "source_ref": bounds.source_ref,
        "lower_values": [_json_bound(value) for value in bounds.lower_values],
        "upper_values": [_json_bound(value) for value in bounds.upper_values],
        "null_bound_semantics": "unbounded",
        "compressor_flow_bounds": [
            {
                "compressor_id": item.compressor_id,
                "speed_rpm": item.speed_rpm,
                "minimum_mass_flow_kg_s": item.minimum_mass_flow_kg_s,
                "maximum_mass_flow_kg_s": item.maximum_mass_flow_kg_s,
                "map_source_ref": item.map_source_ref,
                "map_version": item.map_version,
                "envelope_source_ref": item.envelope_source_ref,
                "envelope_version": item.envelope_version,
            }
            for item in bounds.compressor_flow_bounds
        ],
    }


def export_stationary_active_compressor_solve_result_json(
    result: StationaryActiveCompressorGovernedSolveResult,
    *,
    composition_source_ref: str,
    property_method_ref: str,
) -> GasResultExportArtifact:
    """Sérialise un résultat mixte gouverné sans recalcul scientifique."""

    normalized_composition_ref = composition_source_ref.strip()
    normalized_property_ref = property_method_ref.strip()
    if not normalized_composition_ref or not normalized_property_ref:
        raise ValueError("La composition et la méthode de propriétés doivent être référencées.")

    solve = result.solve
    convergence = solve.convergence
    payload: dict[str, Any] = {
        "calculation_ref": solve.solve_ref,
        "model_version": MIXED_STATIONARY_GAS_RESULT_MODEL_VERSION,
        "composition_source_ref": normalized_composition_ref,
        "property_method_ref": normalized_property_ref,
        "assumptions": {
            "stationary": True,
            "active_compressor_speed_fixed": True,
            "certification_claim": False,
        },
        "results": {
            "status": solve.status.value,
            "candidate": _candidate_payload(result),
            "initial_vector": list(solve.initial_vector.values),
            "final_vector": list(solve.final_vector.values),
        },
        "diagnostics": {
            "convergence": {
                "criterion_id": convergence.criterion_id,
                "criterion_version": convergence.criterion_version,
                "approval_ref": convergence.approval_ref,
                "scaled_residual_inf_norm": convergence.scaled_residual_inf_norm,
                "maximum_mass_residual_kg_s": convergence.maximum_mass_residual_kg_s,
                "maximum_pipe_residual_pa2": convergence.maximum_pipe_residual_pa2,
                "maximum_compressor_residual_pa": convergence.maximum_compressor_residual_pa,
                "scaled_residual_passed": convergence.scaled_residual_passed,
                "mass_residual_passed": convergence.mass_residual_passed,
                "pipe_residual_passed": convergence.pipe_residual_passed,
                "compressor_residual_passed": convergence.compressor_residual_passed,
                "all_approved_criteria_passed": convergence.all_approved_criteria_passed,
            },
            "physical_residuals": _residual_payload(result),
            "numerical_bounds": _bounds_payload(result),
            "scipy": {
                "success": solve.scipy_success,
                "status": solve.scipy_status,
                "message": solve.scipy_message,
                "version": solve.scipy_version,
                "nfev": solve.nfev,
                "njev": solve.njev,
                "cost": solve.cost,
                "optimality": solve.optimality,
                "active_mask": list(solve.active_mask),
                "configuration_ref": solve.configuration_ref,
                "configuration_source_ref": solve.configuration_source_ref,
            },
            "missing_operational_envelope_compressor_ids": list(
                solve.missing_operational_envelope_compressor_ids
            ),
            "governance": {
                "scale_artifact_ref": result.scale_artifact_ref,
                "scale_policy_ref": result.scale_policy_ref,
                "scale_approval_ref": result.scale_approval_ref,
                "initial_guess_artifact_ref": result.initial_guess_artifact_ref,
                "initial_guess_policy_ref": result.initial_guess_policy_ref,
                "initial_guess_approval_ref": result.initial_guess_approval_ref,
            },
        },
        "source_refs": [
            normalized_composition_ref,
            normalized_property_ref,
            solve.configuration_source_ref,
            result.scale_approval_ref,
            result.initial_guess_approval_ref,
            convergence.approval_ref,
        ],
    }
    return export_gas_results_json(
        payload,
        export_version=MIXED_STATIONARY_GAS_EXPORT_VERSION,
    )


__all__ = [
    "MIXED_STATIONARY_GAS_EXPORT_VERSION",
    "MIXED_STATIONARY_GAS_RESULT_MODEL_VERSION",
    "export_stationary_active_compressor_solve_result_json",
]
