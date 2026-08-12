from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from hydro_api.industrial.opcua_data_value import (
    OpcUaDataValue,
    OpcUaStatusSeverity,
    normalize_data_value,
    status_severity,
)


def test_status_code_severity_decoding_matches_opcua_bits() -> None:
    assert status_severity(0x00000000) is OpcUaStatusSeverity.GOOD
    assert status_severity(0x40000000) is OpcUaStatusSeverity.UNCERTAIN
    assert status_severity(0x80000000) is OpcUaStatusSeverity.BAD
    assert status_severity(0xC0000000) is OpcUaStatusSeverity.BAD


def test_bad_value_is_never_exposed_as_usable_measurement() -> None:
    normalized = normalize_data_value(
        OpcUaDataValue(
            value=42.0,
            status_code=0x80000000,
            source_timestamp=datetime(2026, 8, 10, 7, 0, tzinfo=UTC),
            server_timestamp=datetime(2026, 8, 10, 7, 0, 1, tzinfo=UTC),
        )
    )
    assert normalized.quality is OpcUaStatusSeverity.BAD
    assert normalized.usable is False
    assert normalized.value is None
    assert normalized.status_code == 0x80000000


def test_uncertain_value_is_preserved_but_explicitly_flagged() -> None:
    offset = timezone(timedelta(hours=2))
    normalized = normalize_data_value(
        OpcUaDataValue(
            value=12.5,
            status_code=0x40000000,
            source_timestamp=datetime(2026, 8, 10, 9, 0, tzinfo=offset),
            server_timestamp=datetime(2026, 8, 10, 9, 0, 1, tzinfo=offset),
        )
    )
    assert normalized.quality is OpcUaStatusSeverity.UNCERTAIN
    assert normalized.usable is True
    assert normalized.value == 12.5
    assert normalized.source_timestamp == datetime(2026, 8, 10, 7, 0, tzinfo=UTC)
    assert normalized.server_timestamp == datetime(2026, 8, 10, 7, 0, 1, tzinfo=UTC)


def test_naive_timestamps_and_invalid_status_codes_are_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        OpcUaDataValue(
            value=1.0,
            status_code=0,
            source_timestamp=datetime(2026, 8, 10, 7, 0),
            server_timestamp=None,
        )
    with pytest.raises(ValueError, match="32 bits"):
        status_severity(0x1_0000_0000)
