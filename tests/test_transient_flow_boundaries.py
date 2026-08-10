from __future__ import annotations

import pytest

from hydro_transients import (
    MocPipeGrid,
    fixed_flow_left_boundary,
    fixed_flow_right_boundary,
)


def _grid() -> MocPipeGrid:
    return MocPipeGrid(
        diameter_m=0.5,
        wave_speed_m_s=1_000.0,
        cell_length_m=100.0,
        time_step_s=0.1,
        friction_factor=0.0,
    )


def test_fixed_flow_boundaries_preserve_uniform_state() -> None:
    left_head, left_flow = fixed_flow_left_boundary(
        boundary_flow_m3_s=0.2,
        interior_head_m=120.0,
        interior_flow_m3_s=0.2,
        grid=_grid(),
    )
    right_head, right_flow = fixed_flow_right_boundary(
        boundary_flow_m3_s=0.2,
        interior_head_m=120.0,
        interior_flow_m3_s=0.2,
        grid=_grid(),
    )

    assert left_head == pytest.approx(120.0)
    assert right_head == pytest.approx(120.0)
    assert left_flow == pytest.approx(0.2)
    assert right_flow == pytest.approx(0.2)


def test_downstream_flow_reduction_creates_positive_head_rise() -> None:
    head, flow = fixed_flow_right_boundary(
        boundary_flow_m3_s=0.1,
        interior_head_m=120.0,
        interior_flow_m3_s=0.2,
        grid=_grid(),
    )
    assert flow == pytest.approx(0.1)
    assert head > 120.0


def test_boundary_rejects_non_finite_flow() -> None:
    with pytest.raises(ValueError, match="finis"):
        fixed_flow_left_boundary(
            boundary_flow_m3_s=float("nan"),
            interior_head_m=120.0,
            interior_flow_m3_s=0.2,
            grid=_grid(),
        )
