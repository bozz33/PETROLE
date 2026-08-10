from __future__ import annotations

import pytest

from hydro_transients import (
    BoundaryKind,
    BoundarySchedulePoint,
    BoundaryValueSchedule,
    MocPipeGrid,
    ScheduleInterpolation,
    ScheduledBoundary,
    simulate_scheduled_boundary_pipe,
)


def _grid() -> MocPipeGrid:
    return MocPipeGrid(
        diameter_m=0.5,
        wave_speed_m_s=1_000.0,
        cell_length_m=100.0,
        time_step_s=0.1,
        friction_factor=0.0,
    )


def test_linear_schedule_interpolates_only_inside_explicit_time_domain() -> None:
    schedule = BoundaryValueSchedule(
        points=(BoundarySchedulePoint(0.0, 100.0), BoundarySchedulePoint(10.0, 200.0)),
        interpolation=ScheduleInterpolation.LINEAR,
        source_ref="scenario://boundary/linear",
    )

    assert schedule.value_at(5.0) == pytest.approx(150.0)
    with pytest.raises(ValueError, match="ne couvre pas"):
        schedule.value_at(10.1)


def test_step_schedule_switches_at_declared_point() -> None:
    schedule = BoundaryValueSchedule(
        points=(
            BoundarySchedulePoint(0.0, 0.2),
            BoundarySchedulePoint(0.1, 0.1),
            BoundarySchedulePoint(0.2, 0.1),
        ),
        interpolation=ScheduleInterpolation.STEP,
        source_ref="scenario://boundary/step",
    )

    assert schedule.value_at(0.05) == pytest.approx(0.2)
    assert schedule.value_at(0.1) == pytest.approx(0.1)


def test_scheduled_downstream_flow_reduction_produces_head_response() -> None:
    left = ScheduledBoundary(
        kind=BoundaryKind.HEAD,
        schedule=BoundaryValueSchedule(
            points=(BoundarySchedulePoint(0.0, 120.0), BoundarySchedulePoint(0.2, 120.0)),
            interpolation=ScheduleInterpolation.STEP,
            source_ref="scenario://left-reservoir",
        ),
    )
    right = ScheduledBoundary(
        kind=BoundaryKind.FLOW,
        schedule=BoundaryValueSchedule(
            points=(
                BoundarySchedulePoint(0.0, 0.2),
                BoundarySchedulePoint(0.1, 0.1),
                BoundarySchedulePoint(0.2, 0.1),
            ),
            interpolation=ScheduleInterpolation.STEP,
            source_ref="scenario://right-flow",
        ),
    )
    snapshots = simulate_scheduled_boundary_pipe(
        initial_heads_m=(120.0, 120.0, 120.0),
        initial_flows_m3_s=(0.2, 0.2, 0.2),
        left_boundary=left,
        right_boundary=right,
        grid=_grid(),
        time_steps=2,
    )

    assert len(snapshots) == 3
    assert snapshots[1].flows_m3_s[-1] == pytest.approx(0.1)
    assert snapshots[1].heads_m[-1] > 120.0


def test_simulation_refuses_boundary_schedule_shorter_than_horizon() -> None:
    short = ScheduledBoundary(
        kind=BoundaryKind.HEAD,
        schedule=BoundaryValueSchedule(
            points=(BoundarySchedulePoint(0.0, 120.0), BoundarySchedulePoint(0.1, 120.0)),
            interpolation=ScheduleInterpolation.STEP,
            source_ref="scenario://short",
        ),
    )
    with pytest.raises(ValueError, match="ne couvre pas toute"):
        simulate_scheduled_boundary_pipe(
            initial_heads_m=(120.0, 120.0, 120.0),
            initial_flows_m3_s=(0.2, 0.2, 0.2),
            left_boundary=short,
            right_boundary=short,
            grid=_grid(),
            time_steps=2,
        )
