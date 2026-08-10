from __future__ import annotations

import pytest

from hydro_transients import MocStateSnapshot, build_transient_envelopes


def test_transient_envelopes_keep_extrema_and_times_without_interpolation() -> None:
    snapshots = (
        MocStateSnapshot(time_s=0.0, heads_m=(100.0, 90.0), flows_m3_s=(0.2, 0.2)),
        MocStateSnapshot(time_s=0.1, heads_m=(105.0, 80.0), flows_m3_s=(0.1, 0.3)),
        MocStateSnapshot(time_s=0.2, heads_m=(98.0, 95.0), flows_m3_s=(0.25, 0.15)),
    )
    result = build_transient_envelopes(snapshots)

    assert result.node_count == 2
    assert result.start_time_s == pytest.approx(0.0)
    assert result.end_time_s == pytest.approx(0.2)
    node0 = result.envelopes[0]
    assert node0.minimum_head_m == pytest.approx(98.0)
    assert node0.minimum_head_time_s == pytest.approx(0.2)
    assert node0.maximum_head_m == pytest.approx(105.0)
    assert node0.maximum_head_time_s == pytest.approx(0.1)
    assert node0.minimum_flow_m3_s == pytest.approx(0.1)
    assert node0.maximum_flow_m3_s == pytest.approx(0.25)


def test_transient_envelopes_reject_inconsistent_node_count() -> None:
    with pytest.raises(ValueError, match="même nombre de nœuds"):
        build_transient_envelopes(
            (
                MocStateSnapshot(time_s=0.0, heads_m=(100.0, 90.0), flows_m3_s=(0.2, 0.2)),
                MocStateSnapshot(time_s=0.1, heads_m=(100.0,), flows_m3_s=(0.2,)),
            )
        )


def test_transient_envelopes_reject_non_monotonic_time() -> None:
    with pytest.raises(ValueError, match="strictement ordonnés"):
        build_transient_envelopes(
            (
                MocStateSnapshot(time_s=0.1, heads_m=(100.0,), flows_m3_s=(0.2,)),
                MocStateSnapshot(time_s=0.1, heads_m=(101.0,), flows_m3_s=(0.3,)),
            )
        )
