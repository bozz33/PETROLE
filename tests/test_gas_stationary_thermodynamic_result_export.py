from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from typing import cast

import pytest

from hydro_gas.stationary_compressor_thermodynamic_limits import (
    StationaryActiveCompressorThermodynamicLimitAssessment,
)
from hydro_gas.stationary_compressor_thermodynamics import (
    StationaryActiveCompressorThermodynamicAssessment,
)
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus
from hydro_gas.stationary_station_thermodynamics import (
    StationaryCompressorStationThermodynamicSummary,
)
from hydro_gas.stationary_thermodynamic_result_export import (
    STATIONARY_COMPRESSOR_THERMODYNAMIC_EXPORT_VERSION,
    STATIONARY_COMPRESSOR_THERMODYNAMIC_RESULT_MODEL_VERSION,
    export_stationary_compressor_thermodynamic_result_json,
)


def _assessment(
    *,
    status: StationaryWeymouthSolverStatus = StationaryWeymouthSolverStatus.CONVERGED,
) -> StationaryActiveCompressorThermodynamicAssessment:
    property_state = SimpleNamespace(
        fluid_name="Methane",
        coolprop_version="8.0.0",
        inlet_pressure_pa=100_000.0,
        inlet_temperature_k=300.0,
        inlet_enthalpy_j_kg=900_000.0,
        inlet_entropy_j_kg_k=6_000.0,
        outlet_pressure_pa=200_000.0,
        isentropic_outlet_temperature_k=340.0,
        isentropic_outlet_enthalpy_j_kg=1_000_000.0,
        actual_outlet_temperature_k=350.0,
        actual_outlet_enthalpy_j_kg=1_025_000.0,
        isentropic_efficiency=0.8,
        fluid_source_ref="fluid://coolprop/Methane",
        state_source_ref="state://compressor/C1/thermal",
        efficiency_source_ref="supplier://map/C1#map-version/v1",
        property_method_ref="property-method://coolprop/PropsSI/v1",
    )
    energy_balance = SimpleNamespace(
        enthalpy_rise_j_kg=125_000.0,
        kinetic_energy_change_j_kg=0.0,
        potential_energy_change_j_kg=0.0,
        total_specific_energy_rise_j_kg=125_000.0,
        heat_transfer_to_gas_w=0.0,
        shaft_power_input_w=187_500.0,
        state_source_ref="state://compressor/C1/thermal",
        equation_ref="equation://steady-flow-energy/v1",
    )
    compressor = SimpleNamespace(
        compressor_id="C1",
        solver_status=status,
        mass_flow_kg_s=1.5,
        inlet_node_id="A",
        outlet_node_id="B",
        property_state=property_state,
        energy_balance=energy_balance,
    )
    return cast(
        StationaryActiveCompressorThermodynamicAssessment,
        SimpleNamespace(
            solve_ref="solve://mixed/thermo-export/v1",
            solver_status=status,
            compressors=(compressor,),
        ),
    )


def _station_summary(
    *,
    status: StationaryWeymouthSolverStatus = StationaryWeymouthSolverStatus.CONVERGED,
    solve_ref: str = "solve://mixed/thermo-export/v1",
    qualification_claim: bool = False,
) -> StationaryCompressorStationThermodynamicSummary:
    return cast(
        StationaryCompressorStationThermodynamicSummary,
        SimpleNamespace(
            station_ref="station://gas/CS-01",
            solve_ref=solve_ref,
            solver_status=status,
            compressor_count=1,
            compressor_ids=("C1",),
            total_shaft_power_input_w=187_500.0,
            total_heat_transfer_to_gas_w=0.0,
            minimum_inlet_temperature_k=300.0,
            maximum_actual_outlet_temperature_k=350.0,
            non_positive_shaft_power_compressor_ids=(),
            fluid_names=("Methane",),
            property_method_refs=("property-method://coolprop/PropsSI/v1",),
            source_ref="assessment://station/CS-01/thermal/v1",
            qualification_claim=qualification_claim,
            certification_claim=False,
        ),
    )


def _limit_assessment(
    *,
    status: StationaryWeymouthSolverStatus = StationaryWeymouthSolverStatus.CONVERGED,
    solve_ref: str = "solve://mixed/thermo-export/v1",
) -> StationaryActiveCompressorThermodynamicLimitAssessment:
    evaluable = status is StationaryWeymouthSolverStatus.CONVERGED
    item = SimpleNamespace(
        compressor_id="C1",
        solver_status=status,
        limit_set_id="limits-C1",
        limit_set_version="1",
        observed_shaft_power_input_w=187_500.0,
        maximum_shaft_power_input_w=200_000.0,
        shaft_power_margin_w=12_500.0 if evaluable else None,
        shaft_power_within_limit=True if evaluable else None,
        observed_actual_outlet_temperature_k=350.0,
        maximum_actual_outlet_temperature_k=360.0,
        outlet_temperature_margin_k=10.0 if evaluable else None,
        outlet_temperature_within_limit=True if evaluable else None,
        all_approved_limits_passed=True if evaluable else None,
        evaluation_reason=None if evaluable else "source_solver_status:non_converged",
        non_positive_shaft_power_observed=False,
        source_ref="supplier://limits/C1/v1",
        registration_ref="registration://limits/C1/v1",
        approval_ref="approval://limits/C1/v1",
        qualification_claim=False,
        certification_claim=False,
    )
    return cast(
        StationaryActiveCompressorThermodynamicLimitAssessment,
        SimpleNamespace(
            solve_ref=solve_ref,
            solver_status=status,
            compressors=(item,),
            all_limits_evaluable=evaluable,
            all_approved_limits_passed=True if evaluable else None,
            qualification_claim=False,
            certification_claim=False,
        ),
    )


def test_thermodynamic_export_is_canonical_traceable_and_non_certifying() -> None:
    artifact = export_stationary_compressor_thermodynamic_result_json(
        _assessment(),
        _station_summary(),
        _limit_assessment(),
        composition_source_ref="composition://gas/test",
        property_method_ref="property-method://gas/thermo-protocol/v1",
    )

    assert artifact.sha256 == hashlib.sha256(artifact.content).hexdigest()
    document = json.loads(artifact.content)
    assert document["export_version"] == STATIONARY_COMPRESSOR_THERMODYNAMIC_EXPORT_VERSION
    assert document["model_version"] == STATIONARY_COMPRESSOR_THERMODYNAMIC_RESULT_MODEL_VERSION
    assert document["results"]["status"] == "converged"
    assert document["results"]["station"]["total_shaft_power_input_w"] == 187_500.0
    assert (
        document["results"]["compressors"][0]["property_state"]["actual_outlet_temperature_k"]
        == 350.0
    )
    limits = document["diagnostics"]["thermodynamic_limits"]
    assert limits["all_limits_evaluable"] is True
    assert limits["all_approved_limits_passed"] is True
    assert limits["compressors"][0]["approval_ref"] == "approval://limits/C1/v1"
    assert document["assumptions"]["qualification_claim"] is False
    assert document["assumptions"]["certification_claim"] is False
    assert len(document["source_refs"]) == len(set(document["source_refs"]))


def test_thermodynamic_export_preserves_non_converged_status_and_unevaluable_limits() -> None:
    status = StationaryWeymouthSolverStatus.NON_CONVERGED
    artifact = export_stationary_compressor_thermodynamic_result_json(
        _assessment(status=status),
        _station_summary(status=status),
        _limit_assessment(status=status),
        composition_source_ref="composition://gas/test",
        property_method_ref="property-method://gas/thermo-protocol/v1",
    )

    document = json.loads(artifact.content)
    assert document["results"]["status"] == "non_converged"
    limits = document["diagnostics"]["thermodynamic_limits"]
    assert limits["all_limits_evaluable"] is False
    assert limits["all_approved_limits_passed"] is None
    assert limits["compressors"][0]["shaft_power_within_limit"] is None


def test_thermodynamic_export_rejects_mismatched_sources_and_claims() -> None:
    with pytest.raises(ValueError, match="même calcul"):
        export_stationary_compressor_thermodynamic_result_json(
            _assessment(),
            _station_summary(solve_ref="solve://other"),
            _limit_assessment(),
            composition_source_ref="composition://gas/test",
            property_method_ref="property-method://gas/thermo-protocol/v1",
        )

    with pytest.raises(ValueError, match="qualification/certification"):
        export_stationary_compressor_thermodynamic_result_json(
            _assessment(),
            _station_summary(qualification_claim=True),
            _limit_assessment(),
            composition_source_ref="composition://gas/test",
            property_method_ref="property-method://gas/thermo-protocol/v1",
        )
