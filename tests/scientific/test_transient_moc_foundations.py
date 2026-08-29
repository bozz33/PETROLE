"""Tests analytiques des premières briques MOC de Phase 4."""

from __future__ import annotations

import pytest

from hydro_transients import (
    MocPipeGrid,
    fixed_head_left_boundary,
    fixed_head_right_boundary,
    interior_characteristic_step,
)


def _grid(*, friction_factor: float = 0.0) -> MocPipeGrid:
    return MocPipeGrid(
        diameter_m=0.5,
        wave_speed_m_s=1_000.0,
        cell_length_m=100.0,
        time_step_s=0.1,
        friction_factor=friction_factor,
    )


def test_uniform_frictionless_state_is_invariant_at_interior_node() -> None:
    head, flow = interior_characteristic_step(
        left_head_m=120.0,
        left_flow_m3_s=0.2,
        right_head_m=120.0,
        right_flow_m3_s=0.2,
        grid=_grid(),
    )
    assert head == pytest.approx(120.0)
    assert flow == pytest.approx(0.2)


def test_fixed_head_boundaries_preserve_uniform_frictionless_state() -> None:
    grid = _grid()
    left = fixed_head_left_boundary(
        boundary_head_m=120.0,
        interior_head_m=120.0,
        interior_flow_m3_s=0.2,
        grid=grid,
    )
    right = fixed_head_right_boundary(
        boundary_head_m=120.0,
        interior_head_m=120.0,
        interior_flow_m3_s=0.2,
        grid=grid,
    )
    assert left == pytest.approx((120.0, 0.2))
    assert right == pytest.approx((120.0, 0.2))


def test_reference_grid_refuses_cfl_different_from_one() -> None:
    with pytest.raises(ValueError, match="CFL"):
        MocPipeGrid(
            diameter_m=0.5,
            wave_speed_m_s=1_000.0,
            cell_length_m=100.0,
            time_step_s=0.08,
        )


def test_quasi_steady_friction_coefficient_is_explicit() -> None:
    grid = _grid(friction_factor=0.02)
    assert grid.quasi_steady_friction_coefficient > 0
