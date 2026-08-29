"""Conditions aux limites temporelles pour le noyau MOC liquide.

Le module applique des valeurs de charge ou de débit explicitement programmées.
Il ne transforme pas un programme arbitraire en modèle de vanne/pompe : les
lois physiques des équipements restent des sous-modèles séparés à valider.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise

from hydro_transients.moc import (
    MocPipeGrid,
    MocStateSnapshot,
    fixed_flow_left_boundary,
    fixed_flow_right_boundary,
    fixed_head_left_boundary,
    fixed_head_right_boundary,
    interior_characteristic_step,
)


class BoundaryKind(StrEnum):
    HEAD = "head"
    FLOW = "flow"


class ScheduleInterpolation(StrEnum):
    STEP = "step"
    LINEAR = "linear"


@dataclass(frozen=True, slots=True)
class BoundarySchedulePoint:
    time_s: float
    value: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.time_s) or self.time_s < 0:
            raise ValueError("Le temps de programme doit être fini et positif ou nul.")
        if not math.isfinite(self.value):
            raise ValueError("La valeur de condition aux limites doit être finie.")


@dataclass(frozen=True, slots=True)
class BoundaryValueSchedule:
    """Programme borné d'une valeur de condition aux limites."""

    points: tuple[BoundarySchedulePoint, ...]
    interpolation: ScheduleInterpolation
    source_ref: str

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("La provenance du programme de frontière est obligatoire.")
        if not self.points:
            raise ValueError("Un programme de frontière doit contenir au moins un point.")
        times = [point.time_s for point in self.points]
        if times != sorted(times) or len(times) != len(set(times)):
            raise ValueError("Les temps du programme doivent être strictement croissants.")
        if not math.isclose(self.points[0].time_s, 0.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("Le programme de frontière doit commencer à t=0.")

    @property
    def maximum_time_s(self) -> float:
        return self.points[-1].time_s

    def value_at(self, time_s: float) -> float:
        """Évalue dans le domaine temporel sans extrapolation après le dernier point."""

        if not math.isfinite(time_s) or time_s < 0:
            raise ValueError("Le temps d'évaluation doit être fini et positif ou nul.")
        if time_s > self.maximum_time_s:
            raise ValueError("Le programme de frontière ne couvre pas le temps demandé.")
        if len(self.points) == 1:
            return self.points[0].value
        for left, right in pairwise(self.points):
            if math.isclose(time_s, left.time_s, rel_tol=0.0, abs_tol=1e-12):
                return left.value
            if left.time_s <= time_s <= right.time_s:
                if self.interpolation is ScheduleInterpolation.STEP:
                    if math.isclose(time_s, right.time_s, rel_tol=0.0, abs_tol=1e-12):
                        return right.value
                    return left.value
                fraction = (time_s - left.time_s) / (right.time_s - left.time_s)
                return left.value + fraction * (right.value - left.value)
        return self.points[-1].value


@dataclass(frozen=True, slots=True)
class ScheduledBoundary:
    kind: BoundaryKind
    schedule: BoundaryValueSchedule


def _apply_left_boundary(
    boundary: ScheduledBoundary,
    *,
    time_s: float,
    interior_head_m: float,
    interior_flow_m3_s: float,
    grid: MocPipeGrid,
) -> tuple[float, float]:
    value = boundary.schedule.value_at(time_s)
    if boundary.kind is BoundaryKind.HEAD:
        return fixed_head_left_boundary(
            boundary_head_m=value,
            interior_head_m=interior_head_m,
            interior_flow_m3_s=interior_flow_m3_s,
            grid=grid,
        )
    return fixed_flow_left_boundary(
        boundary_flow_m3_s=value,
        interior_head_m=interior_head_m,
        interior_flow_m3_s=interior_flow_m3_s,
        grid=grid,
    )


def _apply_right_boundary(
    boundary: ScheduledBoundary,
    *,
    time_s: float,
    interior_head_m: float,
    interior_flow_m3_s: float,
    grid: MocPipeGrid,
) -> tuple[float, float]:
    value = boundary.schedule.value_at(time_s)
    if boundary.kind is BoundaryKind.HEAD:
        return fixed_head_right_boundary(
            boundary_head_m=value,
            interior_head_m=interior_head_m,
            interior_flow_m3_s=interior_flow_m3_s,
            grid=grid,
        )
    return fixed_flow_right_boundary(
        boundary_flow_m3_s=value,
        interior_head_m=interior_head_m,
        interior_flow_m3_s=interior_flow_m3_s,
        grid=grid,
    )


def simulate_scheduled_boundary_pipe(
    *,
    initial_heads_m: tuple[float, ...],
    initial_flows_m3_s: tuple[float, ...],
    left_boundary: ScheduledBoundary,
    right_boundary: ScheduledBoundary,
    grid: MocPipeGrid,
    time_steps: int,
) -> tuple[MocStateSnapshot, ...]:
    """Propage le MOC avec frontières charge/débit programmées à chaque pas."""

    if len(initial_heads_m) != len(initial_flows_m3_s):
        raise ValueError("Les vecteurs initiaux de charge et débit doivent avoir la même taille.")
    if len(initial_heads_m) < 3:
        raise ValueError("Le solveur MOC exige au moins trois nœuds.")
    if time_steps < 0:
        raise ValueError("Le nombre de pas doit être positif ou nul.")
    end_time = time_steps * grid.time_step_s
    if left_boundary.schedule.maximum_time_s < end_time:
        raise ValueError("Le programme amont ne couvre pas toute la simulation.")
    if right_boundary.schedule.maximum_time_s < end_time:
        raise ValueError("Le programme aval ne couvre pas toute la simulation.")
    if any(not math.isfinite(value) for value in (*initial_heads_m, *initial_flows_m3_s)):
        raise ValueError("Les charges et débits initiaux doivent être finis.")

    previous_heads = list(initial_heads_m)
    previous_flows = list(initial_flows_m3_s)
    snapshots = [MocStateSnapshot(0.0, tuple(previous_heads), tuple(previous_flows))]
    node_count = len(previous_heads)

    for step_index in range(1, time_steps + 1):
        time_s = step_index * grid.time_step_s
        next_heads = [0.0] * node_count
        next_flows = [0.0] * node_count
        next_heads[0], next_flows[0] = _apply_left_boundary(
            left_boundary,
            time_s=time_s,
            interior_head_m=previous_heads[1],
            interior_flow_m3_s=previous_flows[1],
            grid=grid,
        )
        for node_index in range(1, node_count - 1):
            next_heads[node_index], next_flows[node_index] = interior_characteristic_step(
                left_head_m=previous_heads[node_index - 1],
                left_flow_m3_s=previous_flows[node_index - 1],
                right_head_m=previous_heads[node_index + 1],
                right_flow_m3_s=previous_flows[node_index + 1],
                grid=grid,
            )
        next_heads[-1], next_flows[-1] = _apply_right_boundary(
            right_boundary,
            time_s=time_s,
            interior_head_m=previous_heads[-2],
            interior_flow_m3_s=previous_flows[-2],
            grid=grid,
        )
        snapshots.append(
            MocStateSnapshot(
                time_s=time_s,
                heads_m=tuple(next_heads),
                flows_m3_s=tuple(next_flows),
            )
        )
        previous_heads = next_heads
        previous_flows = next_flows
    return tuple(snapshots)


__all__ = [
    "BoundaryKind",
    "BoundarySchedulePoint",
    "BoundaryValueSchedule",
    "ScheduleInterpolation",
    "ScheduledBoundary",
    "simulate_scheduled_boundary_pipe",
]
