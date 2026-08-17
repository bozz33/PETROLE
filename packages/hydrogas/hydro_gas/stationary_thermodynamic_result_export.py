"""Export canonique P6-G du post-traitement thermodynamique compresseur.

Cette couche ne recalcule aucune propriété, puissance, température ou limite.
Elle assemble les résultats thermodynamiques déjà calculés, la synthèse station
et l'évaluation des limites APPROVED dans l'enveloppe JSON canonique P6-G.
"""

from __future__ import annotations

from typing import Any

from hydro_gas.result_export import GasResultExportArtifact, export_gas_results_json
from hydro_gas.stationary_compressor_thermodynamic_limits import (
    StationaryActiveCompressorThermodynamicLimitAssessment,
)
from hydro_gas.stationary_compressor_thermodynamics import (
    StationaryActiveCompressorThermodynamicAssessment,
)
from hydro_gas.stationary_station_thermodynamics import (
    StationaryCompressorStationThermodynamicSummary,
)

STATIONARY_COMPRESSOR_THERMODYNAMIC_EXPORT_VERSION = (
    "phase6-gas/stationary-compressor-thermodynamics/2"
)
STATIONARY_COMPRESSOR_THERMODYNAMIC_RESULT_MODEL_VERSION = (
    "phase6/stationary-compressor-thermodynamics/2"
)


def _compressor_payload(
    assessment: StationaryActiveCompressorThermodynamicAssessment,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in assessment.compressors:
        state = item.property_state
        energy = item.energy_balance
        rows.append(
            {
                "compressor_id": item.compressor_id,
                "solver_status": item.solver_status.value,
                "mass_flow_kg_s": item.mass_flow_kg_s,
                "inlet_node_id": item.inlet_node_id,
                "outlet_node_id": item.outlet_node_id,
                "property_state": {
                    "fluid_name": state.fluid_name,
                    "coolprop_version": state.coolprop_version,
                    "coolprop_gitrevision": state.coolprop_gitrevision,
                    "coolprop_backend": state.coolprop_backend,
                    "composition_source_ref": state.composition_source_ref,
                    "component_mapping_source_ref": state.component_mapping_source_ref,
                    "composition_component_names": list(state.composition_component_names),
                    "coolprop_component_names": list(state.coolprop_component_names),
                    "mole_fractions": list(state.mole_fractions),
                    "inlet_pressure_pa": state.inlet_pressure_pa,
                    "inlet_temperature_k": state.inlet_temperature_k,
                    "inlet_enthalpy_j_kg": state.inlet_enthalpy_j_kg,
                    "inlet_entropy_j_kg_k": state.inlet_entropy_j_kg_k,
                    "outlet_pressure_pa": state.outlet_pressure_pa,
                    "isentropic_outlet_temperature_k": state.isentropic_outlet_temperature_k,
                    "isentropic_outlet_enthalpy_j_kg": state.isentropic_outlet_enthalpy_j_kg,
                    "actual_outlet_temperature_k": state.actual_outlet_temperature_k,
                    "actual_outlet_enthalpy_j_kg": state.actual_outlet_enthalpy_j_kg,
                    "isentropic_efficiency": state.isentropic_efficiency,
                    "fluid_source_ref": state.fluid_source_ref,
                    "state_source_ref": state.state_source_ref,
                    "efficiency_source_ref": state.efficiency_source_ref,
                    "property_method_ref": state.property_method_ref,
                },
                "energy_balance": {
                    "enthalpy_rise_j_kg": energy.enthalpy_rise_j_kg,
                    "kinetic_energy_change_j_kg": energy.kinetic_energy_change_j_kg,
                    "potential_energy_change_j_kg": energy.potential_energy_change_j_kg,
                    "total_specific_energy_rise_j_kg": energy.total_specific_energy_rise_j_kg,
                    "heat_transfer_to_gas_w": energy.heat_transfer_to_gas_w,
                    "shaft_power_input_w": energy.shaft_power_input_w,
                    "state_source_ref": energy.state_source_ref,
                    "equation_ref": energy.equation_ref,
                },
            }
        )
    return rows


def _station_payload(summary: StationaryCompressorStationThermodynamicSummary) -> dict[str, Any]:
    return {
        "station_ref": summary.station_ref,
        "solver_status": summary.solver_status.value,
        "compressor_count": summary.compressor_count,
        "compressor_ids": list(summary.compressor_ids),
        "total_shaft_power_input_w": summary.total_shaft_power_input_w,
        "total_heat_transfer_to_gas_w": summary.total_heat_transfer_to_gas_w,
        "minimum_inlet_temperature_k": summary.minimum_inlet_temperature_k,
        "maximum_actual_outlet_temperature_k": summary.maximum_actual_outlet_temperature_k,
        "non_positive_shaft_power_compressor_ids": list(
            summary.non_positive_shaft_power_compressor_ids
        ),
        "fluid_names": list(summary.fluid_names),
        "property_method_refs": list(summary.property_method_refs),
        "source_ref": summary.source_ref,
        "qualification_claim": summary.qualification_claim,
        "certification_claim": summary.certification_claim,
    }


def _limits_payload(
    assessment: StationaryActiveCompressorThermodynamicLimitAssessment,
) -> dict[str, Any]:
    return {
        "solver_status": assessment.solver_status.value,
        "all_limits_evaluable": assessment.all_limits_evaluable,
        "all_approved_limits_passed": assessment.all_approved_limits_passed,
        "qualification_claim": assessment.qualification_claim,
        "certification_claim": assessment.certification_claim,
        "compressors": [
            {
                "compressor_id": item.compressor_id,
                "solver_status": item.solver_status.value,
                "limit_set_id": item.limit_set_id,
                "limit_set_version": item.limit_set_version,
                "observed_shaft_power_input_w": item.observed_shaft_power_input_w,
                "maximum_shaft_power_input_w": item.maximum_shaft_power_input_w,
                "shaft_power_margin_w": item.shaft_power_margin_w,
                "shaft_power_within_limit": item.shaft_power_within_limit,
                "observed_actual_outlet_temperature_k": (item.observed_actual_outlet_temperature_k),
                "maximum_actual_outlet_temperature_k": (item.maximum_actual_outlet_temperature_k),
                "outlet_temperature_margin_k": item.outlet_temperature_margin_k,
                "outlet_temperature_within_limit": item.outlet_temperature_within_limit,
                "all_approved_limits_passed": item.all_approved_limits_passed,
                "evaluation_reason": item.evaluation_reason,
                "non_positive_shaft_power_observed": item.non_positive_shaft_power_observed,
                "source_ref": item.source_ref,
                "registration_ref": item.registration_ref,
                "approval_ref": item.approval_ref,
                "qualification_claim": item.qualification_claim,
                "certification_claim": item.certification_claim,
            }
            for item in assessment.compressors
        ],
    }


def _embedded_composition_refs(
    assessment: StationaryActiveCompressorThermodynamicAssessment,
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            ref
            for item in assessment.compressors
            if (ref := item.property_state.composition_source_ref) is not None and ref.strip()
        )
    )


def _unique_source_refs(
    assessment: StationaryActiveCompressorThermodynamicAssessment,
    limits: StationaryActiveCompressorThermodynamicLimitAssessment,
    *,
    composition_source_ref: str,
    property_method_ref: str,
    station_source_ref: str,
) -> list[str]:
    refs = [composition_source_ref, property_method_ref, station_source_ref]
    for compressor_result in assessment.compressors:
        state = compressor_result.property_state
        refs.extend(
            (
                state.fluid_source_ref,
                state.composition_source_ref or "",
                state.component_mapping_source_ref or "",
                state.state_source_ref,
                state.efficiency_source_ref,
                state.property_method_ref,
                compressor_result.energy_balance.state_source_ref,
                compressor_result.energy_balance.equation_ref,
            )
        )
    for limit_result in limits.compressors:
        refs.extend(
            (limit_result.source_ref, limit_result.registration_ref, limit_result.approval_ref)
        )
    return list(dict.fromkeys(ref.strip() for ref in refs if ref.strip()))


def export_stationary_compressor_thermodynamic_result_json(
    assessment: StationaryActiveCompressorThermodynamicAssessment,
    station_summary: StationaryCompressorStationThermodynamicSummary,
    limit_assessment: StationaryActiveCompressorThermodynamicLimitAssessment,
    *,
    composition_source_ref: str,
    property_method_ref: str,
) -> GasResultExportArtifact:
    """Sérialise les résultats thermo et leurs limites sans recalcul scientifique."""

    normalized_composition_ref = composition_source_ref.strip()
    normalized_property_ref = property_method_ref.strip()
    if not normalized_composition_ref or not normalized_property_ref:
        raise ValueError("La composition et la méthode de propriétés doivent être référencées.")
    if not assessment.solve_ref.strip():
        raise ValueError("Le résultat thermodynamique doit référencer son calcul source.")
    if (
        station_summary.solve_ref != assessment.solve_ref
        or limit_assessment.solve_ref != assessment.solve_ref
    ):
        raise ValueError(
            "La thermo, la synthèse station et les limites doivent viser le même calcul."
        )
    if (
        station_summary.solver_status is not assessment.solver_status
        or limit_assessment.solver_status is not assessment.solver_status
    ):
        raise ValueError(
            "La thermo, la station et les limites doivent conserver le même statut solveur."
        )

    compressor_ids = tuple(item.compressor_id for item in assessment.compressors)
    limit_ids = tuple(item.compressor_id for item in limit_assessment.compressors)
    if station_summary.compressor_ids != compressor_ids or limit_ids != compressor_ids:
        raise ValueError(
            "La station et les limites doivent couvrir exactement les mêmes compresseurs."
        )
    if (
        station_summary.qualification_claim
        or station_summary.certification_claim
        or limit_assessment.qualification_claim
        or limit_assessment.certification_claim
        or any(
            item.qualification_claim or item.certification_claim
            for item in limit_assessment.compressors
        )
    ):
        raise ValueError(
            "L'export P6-G ne peut pas propager une prétention de qualification/certification."
        )

    embedded_composition_refs = _embedded_composition_refs(assessment)
    if len(embedded_composition_refs) > 1:
        raise ValueError(
            "Un export thermo P6-G ne peut pas masquer plusieurs compositions gaz sous une seule provenance globale."
        )
    if embedded_composition_refs and embedded_composition_refs[0] != normalized_composition_ref:
        raise ValueError(
            "La provenance de composition de l'export doit correspondre au mélange réellement évalué."
        )

    payload: dict[str, Any] = {
        "calculation_ref": assessment.solve_ref,
        "model_version": STATIONARY_COMPRESSOR_THERMODYNAMIC_RESULT_MODEL_VERSION,
        "composition_source_ref": normalized_composition_ref,
        "property_method_ref": normalized_property_ref,
        "assumptions": {
            "stationary": True,
            "thermodynamic_post_processing": True,
            "explicit_mixture_composition": bool(embedded_composition_refs),
            "vendor_limits_required": True,
            "qualification_claim": False,
            "certification_claim": False,
        },
        "results": {
            "status": assessment.solver_status.value,
            "station": _station_payload(station_summary),
            "compressors": _compressor_payload(assessment),
        },
        "diagnostics": {
            "thermodynamic_limits": _limits_payload(limit_assessment),
        },
        "source_refs": _unique_source_refs(
            assessment,
            limit_assessment,
            composition_source_ref=normalized_composition_ref,
            property_method_ref=normalized_property_ref,
            station_source_ref=station_summary.source_ref,
        ),
    }
    return export_gas_results_json(
        payload,
        export_version=STATIONARY_COMPRESSOR_THERMODYNAMIC_EXPORT_VERSION,
    )


__all__ = [
    "STATIONARY_COMPRESSOR_THERMODYNAMIC_EXPORT_VERSION",
    "STATIONARY_COMPRESSOR_THERMODYNAMIC_RESULT_MODEL_VERSION",
    "export_stationary_compressor_thermodynamic_result_json",
]
