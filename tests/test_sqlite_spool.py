from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from hydro_api.industrial.buffer_checkpoint import ConnectorCheckpoint
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


def test_checkpoint_persists_across_reopen_and_cannot_regress(tmp_path: Path) -> None:
    path = tmp_path / "gateway-spool.db"
    checkpoint = ConnectorCheckpoint(
        connector_ref="connector://opcua/lab",
        checkpoint_version="v1",
        last_local_sequence=2,
        last_idempotency_key="k2",
    )
    with SQLiteIndustrialSpool(path) as spool:
        _append(spool, "k1", b"one")
        _append(spool, "k2", b"two")
        spool.save_checkpoint(checkpoint)
        assert spool.load_checkpoint(
            connector_ref="connector://opcua/lab",
            checkpoint_version="v1",
        ) == checkpoint

    with SQLiteIndustrialSpool(path) as reopened:
        assert reopened.load_checkpoint(
            connector_ref="connector://opcua/lab",
            checkpoint_version="v1",
        ) == checkpoint
        with pytest.raises(ValueError, match="ne peut pas régresser"):
            reopened.save_checkpoint(
                ConnectorCheckpoint(
                    connector_ref="connector://opcua/lab",
                    checkpoint_version="v1",
                    last_local_sequence=1,
                    last_idempotency_key="k1",
                )
            )


def test_checkpoint_same_sequence_cannot_change_idempotency_identity(tmp_path: Path) -> None:
    with SQLiteIndustrialSpool(tmp_path / "spool.db") as spool:
        spool.save_checkpoint(ConnectorCheckpoint("connector://hist/lab", "v1", 4, "k4"))
        with pytest.raises(ValueError, match="même séquence"):
            spool.save_checkpoint(
                ConnectorCheckpoint("connector://hist/lab", "v1", 4, "other-key")
            )


def test_atomic_acknowledge_persists_checkpoint_and_compacts_prefix(tmp_path: Path) -> None:
    path = tmp_path / "gateway-spool.db"
    with SQLiteIndustrialSpool(path) as spool:
        _append(spool, "k1", b"one")
        _append(spool, "k2", b"two")
        _append(spool, "k3", b"three")
        checkpoint = ConnectorCheckpoint("connector://opcua/lab", "v1", 2, "k2")

        deleted = spool.acknowledge_through(checkpoint)

        assert deleted == 2
        assert spool.load_checkpoint(
            connector_ref="connector://opcua/lab",
            checkpoint_version="v1",
        ) == checkpoint
        assert tuple(record.local_sequence for record in spool.list_after(0)) == (3,)
        assert spool.acknowledge_through(checkpoint) == 0

    with SQLiteIndustrialSpool(path) as reopened:
        assert reopened.load_checkpoint(
            connector_ref="connector://opcua/lab",
            checkpoint_version="v1",
        ) == checkpoint
        assert tuple(record.local_sequence for record in reopened.list_after(0)) == (3,)


def test_atomic_acknowledge_rejects_wrong_final_idempotency_key(tmp_path: Path) -> None:
    with SQLiteIndustrialSpool(tmp_path / "spool.db") as spool:
        _append(spool, "k1", b"one")
        _append(spool, "k2", b"two")
        with pytest.raises(ValueError, match="ne correspond pas"):
            spool.acknowledge_through(
                ConnectorCheckpoint("connector://opcua/lab", "v1", 2, "wrong-key")
            )
        assert spool.load_checkpoint(
            connector_ref="connector://opcua/lab",
            checkpoint_version="v1",
        ) is None
        assert tuple(record.local_sequence for record in spool.list_after(0)) == (1, 2)


def test_missing_checkpoint_remains_explicitly_absent(tmp_path: Path) -> None:
    with SQLiteIndustrialSpool(tmp_path / "spool.db") as spool:
        assert (
            spool.load_checkpoint(
                connector_ref="connector://opcua/lab",
                checkpoint_version="v1",
            )
            is None
        )


def test_compaction_deletes_only_acknowledged_prefix(tmp_path: Path) -> None:
    with SQLiteIndustrialSpool(tmp_path / "spool.db") as spool:
        _append(spool, "k1", b"one")
        _append(spool, "k2", b"two")
        _append(spool, "k3", b"three")
        deleted = spool.compact_through(2)

        assert deleted == 2
        remaining = spool.list_after(0)
        assert tuple(record.local_sequence for record in remaining) == (3,)
