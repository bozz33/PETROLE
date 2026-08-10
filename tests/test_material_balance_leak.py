from __future__ import annotations

import pytest

from hydro_leak import MaterialBalanceWindow, compute_material_balance


def test_material_balance_reports_residual_without_alarm_threshold() -> None:
    result = compute_material_balance(
        MaterialBalanceWindow(
            inlet_mass_kg=10_000.0,
            outlet_mass_kg=9_700.0,
            inventory_change_kg=250.0,
            inlet_standard_uncertainty_kg=20.0,
            outlet_standard_uncertainty_kg=30.0,
            inventory_standard_uncertainty_kg=10.0,
        )
    )
    assert result.residual_kg == pytest.approx(50.0)
    assert result.combined_standard_uncertainty_kg == pytest.approx(37.4165738677)
    assert result.normalized_residual == pytest.approx(1.3363062096)


def test_material_balance_with_zero_uncertainty_has_no_normalized_verdict() -> None:
    result = compute_material_balance(
        MaterialBalanceWindow(
            inlet_mass_kg=1_000.0,
            outlet_mass_kg=995.0,
            inventory_change_kg=5.0,
        )
    )
    assert result.residual_kg == pytest.approx(0.0)
    assert result.normalized_residual is None


def test_material_balance_rejects_negative_uncertainty() -> None:
    with pytest.raises(ValueError, match="incertitudes-types"):
        MaterialBalanceWindow(
            inlet_mass_kg=1.0,
            outlet_mass_kg=1.0,
            inventory_change_kg=0.0,
            inlet_standard_uncertainty_kg=-1.0,
        )
