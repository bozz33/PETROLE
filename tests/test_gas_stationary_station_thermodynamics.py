from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from hydro_gas.stationary_compressor_thermodynamics import (
    StationaryActiveCompressorThermodynamicAssessment,
)
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus
from hydro_gas.stationary_station_thermodynamics import (
    aggregate_stationary_compressor_thermodynamics,
)


def _item(
    compressor_id: str,
    *,
    status: StationaryWeymouthSolverStatus,
    shaft_power_w: float,
    heat_transfer_w: float,
    inlet_temperature_k: float,
    outlet_temperature_k: float,
    fluid_name: str = "Methane",
    property_method_ref: str = "property-method://coolprop/PropsSI/v1",
) -> SimpleNamespace:
    return SimpleNamespace(
        compressor_id=compressor_id,
        solver_status=status,
        energy_balance=SimpleNamespace(
            shaft_power_input_w=shaft_power_w,
            heat_transfer_to_gas_w=heat_transfer_w,
        ),
        property_state=SimpleNamespace(
            inlet_temperature_k=inlet_temperature_k,
            actual_outlet_temperature_k=outlet_temperature_k,
            fluid_name=fluid_name,
            property_method_ref=property_method_ref,
        ),
    )


def _assessment(
    *,
    status: StationaryWeymouthSolverStatus = StationaryWeymouthSolverStatus.CONVERGED,
) -> StationaryActiveCompressorThermodynamicAssessment:
    value = SimpleNamespace(
        solve_ref="solve://mixed/station-thermal/v1",
        solver_status=status,
        compressors=(
            _item(
                "C1",
                status=status,
                shaft_power_w=100_000.0,
                heat_transfer_w=2_000.0,
                inlet_temperature_k=295.0,
                outlet_temperature_k=335.0,
            ),
            _item(
                "C2",
                status=status,
                shaft_power_w=150_000.0,
                heat_transfer_w=-500.0,
                inlet_temperature_k=300.0,
                outlet_temperature_k=345.0,
                property_method_ref="property-method://coolprop/PropsSI/v2",
            ),
        ),
    )
    return cast(StationaryActiveCompressorThermodynamicAssessment, value)


def test_station_thermodynamics_aggregates_only_additive_energy_and_temperature_extrema() -> None:
    summary = aggregate_stationary_compressor_thermodynamics(
        _assessment(),
        station_ref="station://gas/CS-01",
        source_ref="assessment://station/CS-01/thermal/v1",
    )

    assert summary.solve_ref == "solve://mixed/station-thermal/v1"
    assert summary.solver_status is StationaryWeymouthSolverStatus.CONVERGED
    assert summary.compressor_count == 2
    assert summary.compressor_ids == ("C1", "C2")
    assert summary.total_shaft_power_input_w == 250_000.0
    assert summary.total_heat_transfer_to_gas_w == 1_500.0
    assert summary.minimum_inlet_temperature_k == 295.0
    assert summary.maximum_actual_outlet_temperature_k == 345.0
    assert summary.fluid_names == ("Methane",)
    assert summary.property_method_refs == (
        "property-method://coolprop/PropsSI/v1",
        "property-method://coolprop/PropsSI/v2",
    )
    assert summary.non_positive_shaft_power_compressor_ids == ()
    assert summary.qualification_claim is False
    assert summary.certification_claim is False
    assert not hasattr(summary, "total_mass_flow_kg_s")


def test_station_thermodynamics_preserves_non_converged_status_and_flags_non_positive_power() -> None:
    status = StationaryWeymouthSolverStatus.NON_CONVERGED
    value = SimpleNamespace(
        solve_ref="solve://mixed/station-thermal/non-converged",
        solver_status=status,
        compressors=(
            _item(
                "C1",
                status=status,
                shaft_power_w=-5.0,
                heat_transfer_w=10.0,
                inlet_temperature_k=295.0,
                outlet_temperature_k=305.0,
            ),
        ),
    )
    assessment = cast(StationaryActiveCompressorThermodynamicAssessment, value)

    summary = aggregate_stationary_compressor_thermodynamics(
        assessment,
        station_ref="station://gas/CS-01",
        source_ref="assessment://station/CS-01/non-converged",
    )

    assert summary.solver_status is StationaryWeymouthSolverStatus.NON_CONVERGED
    assert summary.total_shaft_power_input_w == -5.0
    assert summary.non_positive_shaft_power_compressor_ids == ("C1",)
    assert summary.qualification_claim is False


def test_station_thermodynamics_rejects_duplicate_ids_status_mismatch_and_empty_assessment() -> None:
    status = StationaryWeymouthSolverStatus.CONVERGED
    duplicate_item = _item(
        "C1",
        status=status,
        shaft_power_w=1.0,
        heat_transfer_w=0.0,
        inlet_temperature_k=300.0,
        outlet_temperature_k=310.0,
    )
    duplicate = cast(
        StationaryActiveCompressorThermodynamicAssessment,
        SimpleNamespace(
            solve_ref="solve://duplicate",
            solver_status=status,
            compressors=(duplicate_item, duplicate_item),
        ),
    )
    with pytest.raises(ValueError, match="identifiants compresseurs.*uniques"):
        aggregate_stationary_compressor_thermodynamics(
            duplicate,
            station_ref="station://gas/CS-01",
            source_ref="assessment://duplicate",
        )

    mismatch = cast(
        StationaryActiveCompressorThermodynamicAssessment,
        SimpleNamespace(
            solve_ref="solve://mismatch",
            solver_status=status,
            compressors=(
                _item(
                    "C1",
                    status=StationaryWeymouthSolverStatus.NON_CONVERGED,
                    shaft_power_w=1.0,
                    heat_transfer_w=0.0,
                    inlet_temperature_k=300.0,
                    outlet_temperature_k=310.0,
                ),
            ),
        ),
    )
    with pytest.raises(ValueError, match="conserver le statut"):
        aggregate_stationary_compressor_thermodynamics(
            mismatch,
            station_ref="station://gas/CS-01",
            source_ref="assessment://mismatch",
        )

    empty = cast(
        StationaryActiveCompressorThermodynamicAssessment,
        SimpleNamespace(
            solve_ref="solve://empty",
            solver_status=status,
            compressors=(),
        ),
    )
    with pytest.raises(ValueError, match="au moins un compresseur"):
        aggregate_stationary_compressor_thermodynamics(
            empty,
            station_ref="station://gas/CS-01",
            source_ref="assessment://empty",
        )
