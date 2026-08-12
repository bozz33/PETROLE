from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hydro_api.industrial.historian import (
    HistorianBatch,
    HistorianQuality,
    HistorianQueryWindow,
    HistorianRecord,
    analytics_usable,
)


def _record(
    *,
    minute: int,
    quality: HistorianQuality = HistorianQuality.GOOD,
    sequence: int | None = None,
) -> HistorianRecord:
    return HistorianRecord(
        external_tag="PT-101",
        source_timestamp=datetime(2026, 8, 10, 8, minute, tzinfo=UTC),
        value=2_000_000.0 + minute,
        source_unit="Pa",
        quality=quality,
        source_ref="historian://lab/PT-101",
        sequence_number=sequence,
    )


def test_batch_preserves_bad_uncertain_duplicates_and_source_order_diagnostics() -> None:
    window = HistorianQueryWindow(
        start=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
        end=datetime(2026, 8, 10, 9, 0, tzinfo=UTC),
    )
    records = (
        _record(minute=2, quality=HistorianQuality.GOOD, sequence=1),
        _record(minute=2, quality=HistorianQuality.GOOD, sequence=1),
        _record(minute=1, quality=HistorianQuality.UNCERTAIN, sequence=2),
        _record(minute=3, quality=HistorianQuality.BAD, sequence=3),
    )
    batch = HistorianBatch(window=window, records=records, connector_ref="connector://hist/lab")

    assert batch.duplicate_count == 1
    assert batch.source_order_violation_count == 1
    assert batch.bad_count == 1
    assert batch.uncertain_count == 1
    assert analytics_usable(records[-1]) is False
    assert analytics_usable(records[2]) is True


def test_historian_batch_rejects_point_outside_half_open_window() -> None:
    start = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    window = HistorianQueryWindow(start=start, end=start + timedelta(minutes=10))
    record = HistorianRecord(
        external_tag="FT-101",
        source_timestamp=start + timedelta(minutes=10),
        value=0.25,
        source_unit="m^3/s",
        quality=HistorianQuality.GOOD,
        source_ref="historian://lab/FT-101",
    )
    with pytest.raises(ValueError, match="hors de la fenêtre"):
        HistorianBatch(window=window, records=(record,), connector_ref="connector://hist/lab")


def test_historian_requires_timezone_and_finite_numeric_value() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        HistorianRecord(
            external_tag="PT-101",
            source_timestamp=datetime(2026, 8, 10, 8, 0),
            value=1.0,
            source_unit="Pa",
            quality=HistorianQuality.GOOD,
            source_ref="historian://lab/PT-101",
        )

    with pytest.raises(ValueError, match="finie"):
        HistorianRecord(
            external_tag="PT-101",
            source_timestamp=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            value=float("nan"),
            source_unit="Pa",
            quality=HistorianQuality.GOOD,
            source_ref="historian://lab/PT-101",
        )
