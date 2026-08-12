from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hydro_api.industrial.buffer_checkpoint import (
    BufferedIndustrialRecord,
    ConnectorCheckpoint,
    advance_checkpoint,
    plan_buffer_drain,
)


def _record(sequence: int, key: str, digest_char: str = "a") -> BufferedIndustrialRecord:
    return BufferedIndustrialRecord(
        local_sequence=sequence,
        idempotency_key=key,
        payload_sha256=digest_char * 64,
        source_timestamp=datetime(2026, 8, 10, 22, sequence % 60, tzinfo=UTC),
        source_ref="opcua://lab/subscription-1",
    )


def test_buffer_drain_preserves_contiguous_order_after_checkpoint() -> None:
    checkpoint = ConnectorCheckpoint("connector://opcua/lab", "v1", 1, "k1")
    plan = plan_buffer_drain(
        (_record(3, "k3"), _record(1, "k1"), _record(2, "k2")),
        checkpoint,
    )

    assert tuple(record.local_sequence for record in plan.pending) == (2, 3)
    advanced = advance_checkpoint(checkpoint, plan.pending)
    assert advanced.last_local_sequence == 3
    assert advanced.last_idempotency_key == "k3"


def test_identical_idempotent_duplicate_is_counted_not_replayed() -> None:
    checkpoint = ConnectorCheckpoint("connector://opcua/lab", "v1", 0)
    plan = plan_buffer_drain(
        (_record(1, "k1"), _record(1, "k1")),
        checkpoint,
    )

    assert plan.duplicate_count == 1
    assert len(plan.pending) == 1


def test_same_idempotency_key_with_different_payload_is_rejected() -> None:
    checkpoint = ConnectorCheckpoint("connector://opcua/lab", "v1", 0)
    with pytest.raises(ValueError, match="deux payloads"):
        plan_buffer_drain(
            (_record(1, "k1", "a"), _record(2, "k1", "b")),
            checkpoint,
        )


def test_gap_after_checkpoint_is_not_silently_skipped() -> None:
    checkpoint = ConnectorCheckpoint("connector://opcua/lab", "v1", 1, "k1")
    with pytest.raises(ValueError, match="Trou de buffer"):
        plan_buffer_drain((_record(3, "k3"),), checkpoint)


def test_checkpoint_cannot_acknowledge_non_contiguous_suffix() -> None:
    checkpoint = ConnectorCheckpoint("connector://opcua/lab", "v1", 1, "k1")
    with pytest.raises(ValueError, match="préfixe contigu"):
        advance_checkpoint(checkpoint, (_record(3, "k3"),))
