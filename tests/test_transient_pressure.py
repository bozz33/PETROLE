from __future__ import annotations

import pytest

from hydro_transients import mean_velocity_full_pipe, pressure_from_total_head


def test_mean_velocity_uses_full_circular_pipe_relation() -> None:
    velocity = mean_velocity_full_pipe(flow_m3_s=0.2, diameter_m=0.5)
    assert velocity == pytest.approx(1.0185916357881302)


def test_pressure_reconstruction_inverts_total_head_definition() -> None:
    velocity = mean_velocity_full_pipe(flow_m3_s=0.2, diameter_m=0.5)
    result = pressure_from_total_head(
        total_head_m=150.0,
        elevation_m=50.0,
        density_kg_m3=850.0,
        velocity_m_s=velocity,
        kinetic_correction_alpha=1.0,
    )

    expected_kinetic = velocity**2 / (2 * 9.80665)
    expected_pressure = 850.0 * 9.80665 * (150.0 - 50.0 - expected_kinetic)
    assert result.kinetic_head_m == pytest.approx(expected_kinetic)
    assert result.pressure_pa == pytest.approx(expected_pressure)
    assert result.nonphysical_negative_absolute is False


def test_negative_absolute_candidate_is_exposed_not_clamped() -> None:
    result = pressure_from_total_head(
        total_head_m=10.0,
        elevation_m=20.0,
        density_kg_m3=850.0,
        velocity_m_s=0.0,
        kinetic_correction_alpha=1.0,
    )

    assert result.pressure_pa < 0
    assert result.nonphysical_negative_absolute is True


def test_pressure_reconstruction_requires_explicit_positive_density_and_alpha() -> None:
    with pytest.raises(ValueError, match="densité"):
        pressure_from_total_head(
            total_head_m=100.0,
            elevation_m=0.0,
            density_kg_m3=0.0,
            velocity_m_s=1.0,
            kinetic_correction_alpha=1.0,
        )
    with pytest.raises(ValueError, match="alpha"):
        pressure_from_total_head(
            total_head_m=100.0,
            elevation_m=0.0,
            density_kg_m3=850.0,
            velocity_m_s=1.0,
            kinetic_correction_alpha=0.0,
        )
