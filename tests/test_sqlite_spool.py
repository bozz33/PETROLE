from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from hydro_api.industrial.sqlite_spool import SQLiteIndustrialSpool


def _append(spool: SQLiteIndustrialSpool, key: str, payload: bytes) -> int:
    record = spool.append(
        idempotency_key=key,
        payload=payload,
        source_timestamp=datetime(2026, 8, 10, 22, 0, tzinfo=UTC),
        source_ref="opcua://lab/subscription-1",
    )
    return record.local_sequence


def test_sqlite_spool_persists_order_and_raw_payload_across_reopen(tmp_path: Path) -> None:
    path = tmp_path / "gateway-spool.db"
    with SQLiteIndustrialSpool(path) as spool:
        first = _append(spool, "k1", b'{"value":1}')
        second = _append(spool, "k2", b'{"value":2}')
        assert spool.journal_mode == "wal"
        assert spool.synchronous_level == 2
        assert (first, second) == (1, 2)

    with SQLiteIndustrialSpool(path) as reopened:
        records = reopened.list_after(0)
        assert tuple(record.local_sequence for record in records) == (1, 2)
        assert records[0].payload == b'{"value":1}'
        assert records[1].payload == b'{"value":2}'
        assert records[0].to_buffered_record().payload_sha256 == records[0].payload_sha256


def test_spool_returns_identical_replay_without_creating_new_sequence(tmp_path: Path) -> None:
    with SQLiteIndustrialSpool(tmp_path / "spool.db") as spool:
        first = spool.append(
            idempotency_key="same-key",
            payload=b"raw-payload",
            source_timestamp=datetime(2026, 8, 10, 22, 0, tzinfo=UTC),
            source_ref="historian://lab/PT-101",
        )
        replay = spool.append(
            idempotency_key="same-key",
            payload=b"raw-payload",
            source_timestamp=datetime(2026, 8, 10, 22, 5, tzinfo=UTC),
            source_ref="historian://lab/PT-101",
        )

        assert replay.local_sequence == first.local_sequence
        assert len(spool.list_after(0)) == 1


def test_spool_rejects_changed_payload_for_existing_idempotency_key(tmp_path: Path) -> None:
    with SQLiteIndustrialSpool(tmp_path / "spool.db") as spool:
        _append(spool, "same-key", b"payload-A")
        with pytest.raises(ValueError, match="payload différent"):
            _append(spool, "same-key", b"payload-B")


def test_compaction_deletes_only_acknowledged_prefix(tmp_path: Path) -> None:
    with SQLiteIndustrialSpool(tmp_path / "spool.db") as spool:
        _append(spool, "k1", b"one")
        _append(spool, "k2", b"two")
        _append(spool, "k3", b"three")
        deleted = spool.compact_through(2)

        assert deleted == 2
        remaining = spool.list_after(0)
        assert tuple(record.local_sequence for record in remaining) == (3,)
