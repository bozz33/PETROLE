from __future__ import annotations

import pytest

from hydro_gas import (
    CompressorStationConfiguration,
    CompressorUnitConfiguration,
    CompressorUnitRole,
    StationCoolerConfiguration,
    StationValveConfiguration,
    StationValveRole,
)


def _unit(unit_id: str, role: CompressorUnitRole) -> CompressorUnitConfiguration:
    return CompressorUnitConfiguration(
        unit_id=unit_id,
        role=role,
        performance_map_ref=f"vendor://{unit_id}/map/rev-C",
        operating_envelope_ref=f"vendor://{unit_id}/envelope/rev-C",
        source_ref=f"vendor://{unit_id}/datasheet/rev-C",
    )


def test_station_configuration_preserves_main_standby_and_auxiliary_inventory() -> None:
    station = CompressorStationConfiguration(
        station_id="CS-01",
        source_ref="project://station/CS-01/rev-4",
        units=(
            _unit("C-101A", CompressorUnitRole.MAIN),
            _unit("C-101B", CompressorUnitRole.STANDBY),
        ),
        coolers=(StationCoolerConfiguration("AC-101", "vendor://AC-101/datasheet"),),
        valves=(
            StationValveConfiguration(
                "XV-101",
                StationValveRole.ISOLATION,
                "project://station/CS-01/XV-101",
            ),
            StationValveConfiguration(
                "FV-101",
                StationValveRole.RECYCLE,
                "project://station/CS-01/FV-101",
            ),
        ),
        bypass_path_ref="project://station/CS-01/bypass-path",
    )

    assert station.main_unit_ids == ("C-101A",)
    assert station.standby_unit_ids == ("C-101B",)
    assert station.bypass_path_ref == "project://station/CS-01/bypass-path"


def test_station_requires_at_least_one_main_unit() -> None:
    with pytest.raises(ValueError, match="unité principale"):
        CompressorStationConfiguration(
            station_id="CS-01",
            source_ref="project://station/CS-01",
            units=(_unit("C-101B", CompressorUnitRole.STANDBY),),
        )


def test_station_rejects_duplicate_equipment_identifier_across_component_types() -> None:
    with pytest.raises(ValueError, match="uniques"):
        CompressorStationConfiguration(
            station_id="CS-01",
            source_ref="project://station/CS-01",
            units=(_unit("C-101A", CompressorUnitRole.MAIN),),
            coolers=(StationCoolerConfiguration("C-101A", "vendor://cooler/datasheet"),),
        )
