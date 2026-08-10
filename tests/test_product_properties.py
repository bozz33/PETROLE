from __future__ import annotations

import pytest

from hydro_transients import (
    ProductPropertyTables,
    TemperaturePropertyPoint,
    TemperaturePropertyTable,
)


def _table(name: str, unit: str, low: float, high: float) -> TemperaturePropertyTable:
    return TemperaturePropertyTable(
        property_name=name,
        unit=unit,
        source_ref=f"lab://product-A/{name}",
        version="lab-2026-08",
        points=(
            TemperaturePropertyPoint(temperature_k=293.15, value=low),
            TemperaturePropertyPoint(temperature_k=313.15, value=high),
        ),
    )


def test_product_properties_interpolate_only_between_lab_points() -> None:
    properties = ProductPropertyTables(
        product_ref="product://A",
        density=_table("density", "kg/m^3", 850.0, 830.0),
        kinematic_viscosity=_table("kinematic_viscosity", "m^2/s", 6.0e-6, 3.0e-6),
        vapor_pressure=_table("vapor_pressure", "Pa", 4_000.0, 7_000.0),
    )
    result = properties.at_temperature(303.15)

    assert result["density_kg_m3"] == pytest.approx(840.0)
    assert result["kinematic_viscosity_m2_s"] == pytest.approx(4.5e-6)
    assert result["vapor_pressure_pa"] == pytest.approx(5_500.0)


def test_property_table_refuses_temperature_extrapolation() -> None:
    table = _table("density", "kg/m^3", 850.0, 830.0)
    with pytest.raises(ValueError, match="hors domaine"):
        table.interpolate(320.0)


def test_product_property_tables_enforce_expected_si_contract() -> None:
    with pytest.raises(ValueError, match="density"):
        ProductPropertyTables(
            product_ref="product://A",
            density=_table("density", "g/cm3", 0.85, 0.83),
            kinematic_viscosity=_table("kinematic_viscosity", "m^2/s", 6.0e-6, 3.0e-6),
            vapor_pressure=_table("vapor_pressure", "Pa", 4_000.0, 7_000.0),
        )
