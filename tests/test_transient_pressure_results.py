from __future__ import annotations

import pytest

from hydro_transients.moc import MocStateSnapshot
from hydro_transients.pressure_results import (
    TransientNodePressureInput,
    build_transient_pressure_envelopes,
    build_transient_pressure_snapshots,
)


def _properties(
    density_kg_m3: float,
) -> tuple[TransientNodePressureInput, TransientNodePressureInput]:
    return (
        TransientNodePressureInput(
            elevation_m=0.0,
            diameter_m=1.0,
            density_kg_m3=density_kg_m3,
            kinetic_correction_alpha=1.0,
        ),
        TransientNodePressureInput(
            elevation_m=10.0,
            diameter_m=1.0,
            density_kg_m3=density_kg_m3,
            kinetic_correction_alpha=1.0,
        ),
    )


def test_pressure_snapshots_use_explicit_time_varying_density() -> None:
    snapshots = (
        MocStateSnapshot(time_s=0.0, heads_m=(100.0, 90.0), flows_m3_s=(0.0, 0.0)),
        MocStateSnapshot(time_s=1.0, heads_m=(100.0, 90.0), flows_m3_s=(0.0, 0.0)),
    )
    pressure_snapshots = build_transient_pressure_snapshots(
        snapshots,
        (_properties(1_000.0), _properties(800.0)),
    )

    assert pressure_snapshots[0].pressures_pa == pytest.approx(
        (980_665.0, 784_532.0)
    )
    assert pressure_snapshots[1].pressures_pa == pytest.approx(
        (784_532.0, 627_625.6)
    )
    assert pressure_snapshots[0].negative_absolute_flags == (False, False)


def test_pressure_envelopes_publish_extremes_times_and_negative_count() -> None:
    snapshots = (
        MocStateSnapshot(time_s=0.0, heads_m=(10.0,), flows_m3_s=(0.0,)),
        MocStateSnapshot(time_s=1.0, heads_m=(-1.0,), flows_m3_s=(0.0,)),
        MocStateSnapshot(time_s=2.0, heads_m=(20.0,), flows_m3_s=(0.0,)),
    )
    properties = tuple(
        (
            TransientNodePressureInput(
                elevation_m=0.0,
                diameter_m=0.5,
                density_kg_m3=1_000.0,
                kinetic_correction_alpha=1.0,
            ),
        )
        for _ in snapshots
    )
    pressure_snapshots = build_transient_pressure_snapshots(snapshots, properties)

    envelope_set = build_transient_pressure_envelopes(pressure_snapshots)

    envelope = envelope_set.envelopes[0]
    assert envelope.minimum_pressure_pa == pytest.approx(-9_806.65)
    assert envelope.minimum_pressure_time_s == pytest.approx(1.0)
    assert envelope.maximum_pressure_pa == pytest.approx(196_133.0)
    assert envelope.maximum_pressure_time_s == pytest.approx(2.0)
    assert envelope.negative_absolute_count == 1


def test_pressure_reconstruction_requires_properties_for_every_time_and_node() -> None:
    snapshots = (
        MocStateSnapshot(time_s=0.0, heads_m=(10.0, 9.0), flows_m3_s=(0.0, 0.0)),
    )
    with pytest.raises(ValueError, match="exactement tous les nœuds"):
        build_transient_pressure_snapshots(
            snapshots,
            (
                (
                    TransientNodePressureInput(
                        elevation_m=0.0,
                        diameter_m=1.0,
                        density_kg_m3=1_000.0,
                        kinetic_correction_alpha=1.0,
                    ),
                ),
            ),
        )


def test_pressure_reconstruction_rejects_non_monotonic_times() -> None:
    snapshots = (
        MocStateSnapshot(time_s=1.0, heads_m=(10.0,), flows_m3_s=(0.0,)),
        MocStateSnapshot(time_s=1.0, heads_m=(11.0,), flows_m3_s=(0.0,)),
    )
    properties = tuple(
        (
            TransientNodePressureInput(
                elevation_m=0.0,
                diameter_m=1.0,
                density_kg_m3=1_000.0,
                kinetic_correction_alpha=1.0,
            ),
        )
        for _ in snapshots
    )
    with pytest.raises(ValueError, match="strictement ordonnés"):
        build_transient_pressure_snapshots(snapshots, properties)
