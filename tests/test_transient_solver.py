from __future__ import annotations

import pytest

from hydro_transients import MocPipeGrid, simulate_fixed_head_pipe


def _grid() -> MocPipeGrid:
    return MocPipeGrid(
        diameter_m=0.5,
        wave_speed_m_s=1_000.0,
        cell_length_m=100.0,
        time_step_s=0.1,
        friction_factor=0.0,
    )


def test_uniform_frictionless_pipe_remains_invariant() -> None:
    snapshots = simulate_fixed_head_pipe(
        initial_heads_m=(120.0, 120.0, 120.0, 120.0, 120.0),
        initial_flows_m3_s=(0.2, 0.2, 0.2, 0.2, 0.2),
        left_boundary_head_m=120.0,
        right_boundary_head_m=120.0,
        grid=_grid(),
        time_steps=4,
    )
    assert len(snapshots) == 5
    for index, snapshot in enumerate(snapshots):
        assert snapshot.time_s == pytest.approx(index * 0.1)
        assert snapshot.heads_m == pytest.approx((120.0,) * 5)
        assert snapshot.flows_m3_s == pytest.approx((0.2,) * 5)


def test_downstream_head_change_propagates_one_cell_per_cfl_step() -> None:
    snapshots = simulate_fixed_head_pipe(
        initial_heads_m=(120.0, 120.0, 120.0, 120.0, 120.0),
        initial_flows_m3_s=(0.0, 0.0, 0.0, 0.0, 0.0),
        left_boundary_head_m=120.0,
        right_boundary_head_m=119.0,
        grid=_grid(),
        time_steps=2,
    )
    first = snapshots[1]
    second = snapshots[2]
    assert first.heads_m[-1] == pytest.approx(119.0)
    assert first.heads_m[-2] == pytest.approx(120.0)
    assert second.heads_m[-2] < 120.0
    assert second.heads_m[1] == pytest.approx(120.0)


def test_solver_rejects_inconsistent_initial_state() -> None:
    with pytest.raises(ValueError, match="même taille"):
        simulate_fixed_head_pipe(
            initial_heads_m=(120.0, 120.0, 120.0),
            initial_flows_m3_s=(0.0, 0.0),
            left_boundary_head_m=120.0,
            right_boundary_head_m=120.0,
            grid=_grid(),
            time_steps=1,
        )
