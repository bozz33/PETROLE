from __future__ import annotations

import pytest

from hydro_transients import ProductBatch, build_batch_sequence
from hydro_transients.batch_positions import (
    InterfaceSpatialStatus,
    PipelineVolumeProfile,
    PipelineVolumeSegment,
    locate_batch_interfaces,
)


def _batch(batch_id: str, volume_m3: float) -> ProductBatch:
    return ProductBatch(
        batch_id=batch_id,
        product_ref=f"product://{batch_id}",
        volume_m3=volume_m3,
        source_ref=f"schedule://{batch_id}",
    )


def _profile() -> PipelineVolumeProfile:
    return PipelineVolumeProfile(
        segments=(
            PipelineVolumeSegment(
                segment_id="S1",
                length_m=100.0,
                internal_area_m2=1.0,
                source_ref="geometry://S1",
            ),
            PipelineVolumeSegment(
                segment_id="S2",
                length_m=50.0,
                internal_area_m2=2.0,
                source_ref="geometry://S2",
            ),
        )
    )


def test_profile_exposes_geometric_capacity() -> None:
    profile = _profile()

    assert profile.total_length_m == pytest.approx(150.0)
    assert profile.total_internal_volume_m3 == pytest.approx(200.0)


def test_interfaces_are_located_from_explicit_displaced_volume() -> None:
    sequence = build_batch_sequence(
        (_batch("B1", 50.0), _batch("B2", 50.0), _batch("B3", 50.0))
    )

    positions = locate_batch_interfaces(
        sequence,
        _profile(),
        cumulative_displaced_volume_m3=225.0,
    )

    first, second = positions
    assert first.status is InterfaceSpatialStatus.IN_PIPELINE
    assert first.travelled_volume_m3 == pytest.approx(175.0)
    assert first.x_m == pytest.approx(137.5)
    assert first.segment_id == "S2"

    assert second.status is InterfaceSpatialStatus.IN_PIPELINE
    assert second.travelled_volume_m3 == pytest.approx(125.0)
    assert second.x_m == pytest.approx(112.5)
    assert second.segment_id == "S2"


def test_interface_can_be_pending_or_exited_without_hidden_wrapping() -> None:
    sequence = build_batch_sequence(
        (_batch("B1", 100.0), _batch("B2", 100.0), _batch("B3", 100.0))
    )

    pending = locate_batch_interfaces(
        sequence,
        _profile(),
        cumulative_displaced_volume_m3=50.0,
    )
    assert tuple(position.status for position in pending) == (
        InterfaceSpatialStatus.PENDING,
        InterfaceSpatialStatus.PENDING,
    )
    assert all(position.x_m is None for position in pending)

    exited = locate_batch_interfaces(
        sequence,
        _profile(),
        cumulative_displaced_volume_m3=350.0,
    )
    assert exited[0].status is InterfaceSpatialStatus.EXITED
    assert exited[0].x_m is None
    assert exited[1].status is InterfaceSpatialStatus.IN_PIPELINE
    assert exited[1].x_m == pytest.approx(125.0)


def test_interface_at_inlet_and_outlet_remains_explicit() -> None:
    sequence = build_batch_sequence((_batch("B1", 100.0), _batch("B2", 100.0)))
    profile = _profile()

    inlet = locate_batch_interfaces(
        sequence,
        profile,
        cumulative_displaced_volume_m3=100.0,
    )[0]
    outlet = locate_batch_interfaces(
        sequence,
        profile,
        cumulative_displaced_volume_m3=300.0,
    )[0]

    assert inlet.status is InterfaceSpatialStatus.IN_PIPELINE
    assert inlet.x_m == pytest.approx(0.0)
    assert inlet.segment_id == "S1"
    assert outlet.status is InterfaceSpatialStatus.IN_PIPELINE
    assert outlet.x_m == pytest.approx(profile.total_length_m)
    assert outlet.segment_id == "S2"


def test_profile_rejects_invalid_geometry_and_duplicate_segments() -> None:
    segment = PipelineVolumeSegment(
        segment_id="S1",
        length_m=10.0,
        internal_area_m2=1.0,
        source_ref="geometry://S1",
    )
    with pytest.raises(ValueError, match="uniques"):
        PipelineVolumeProfile(segments=(segment, segment))

    with pytest.raises(ValueError, match="strictement positive"):
        PipelineVolumeSegment(
            segment_id="BAD",
            length_m=0.0,
            internal_area_m2=1.0,
            source_ref="geometry://bad",
        )


def test_spatial_projection_rejects_negative_displacement() -> None:
    sequence = build_batch_sequence((_batch("B1", 10.0), _batch("B2", 10.0)))

    with pytest.raises(ValueError, match="positif ou nul"):
        locate_batch_interfaces(
            sequence,
            _profile(),
            cumulative_displaced_volume_m3=-1.0,
        )
