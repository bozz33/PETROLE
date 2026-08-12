from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hydro_api.industrial.opcua_data_value import OpcUaDataValue
from hydro_api.industrial.opcua_lab_simulator import (
    OpcUaReadOnlyLabSimulator,
    SimulatedMonitoredItem,
)
from hydro_api.industrial.opcua_policy import OpcUaOperation
from hydro_api.industrial.opcua_sequence import OpcUaSequenceTracker


def _item(value: float = 42.0) -> SimulatedMonitoredItem:
    timestamp = datetime(2026, 8, 12, 6, 0, tzinfo=UTC)
    return SimulatedMonitoredItem(
        tag_ref="tag://PT-101",
        namespace_uri="urn:petrole:test",
        node_id="s=PT-101",
        data_value=OpcUaDataValue(
            value=value,
            status_code=0,
            source_timestamp=timestamp,
            server_timestamp=timestamp,
        ),
    )


def test_simulator_supports_gap_detection_and_republish_recovery() -> None:
    simulator = OpcUaReadOnlyLabSimulator(
        subscription_id="SUB-001",
        source_ref="simulator://ot-1",
        republish_cache_size=10,
        next_sequence=100,
    )
    first = simulator.publish((_item(1.0),), publish_timestamp=datetime.now(UTC))
    missing = simulator.publish((_item(2.0),), publish_timestamp=datetime.now(UTC))
    third = simulator.publish((_item(3.0),), publish_timestamp=datetime.now(UTC))

    tracker = OpcUaSequenceTracker(maximum_republish_gap=10)
    assert tracker.observe(first.sequence_number).accepted is True
    observation = tracker.observe(third.sequence_number)

    assert observation.republish_required is True
    assert observation.missing_sequences == (missing.sequence_number,)
    recovered = simulator.republish(missing.sequence_number)
    assert recovered == missing
    assert recovered.monitored_items[0].data_value.value == pytest.approx(2.0)


def test_subscription_acknowledgement_removes_only_transport_message() -> None:
    simulator = OpcUaReadOnlyLabSimulator(
        subscription_id="SUB-ACK",
        source_ref="simulator://ot-1/ack",
    )
    message = simulator.publish((_item(),), publish_timestamp=datetime.now(UTC))

    assert simulator.acknowledge(message.sequence_number) is True
    assert simulator.available_republish_sequences() == ()
    assert simulator.acknowledge(message.sequence_number) is False
    with pytest.raises(KeyError, match="n'est plus disponible"):
        simulator.republish(message.sequence_number)


def test_simulator_evicts_old_republish_messages_deterministically() -> None:
    simulator = OpcUaReadOnlyLabSimulator(
        subscription_id="SUB-001",
        source_ref="simulator://ot-1",
        republish_cache_size=2,
    )
    first = simulator.publish((_item(1.0),), publish_timestamp=datetime.now(UTC))
    second = simulator.publish((_item(2.0),), publish_timestamp=datetime.now(UTC))
    third = simulator.publish((_item(3.0),), publish_timestamp=datetime.now(UTC))

    assert simulator.available_republish_sequences() == (
        second.sequence_number,
        third.sequence_number,
    )
    with pytest.raises(KeyError, match="n'est plus disponible"):
        simulator.republish(first.sequence_number)


def test_simulator_handles_sequence_rollover() -> None:
    simulator = OpcUaReadOnlyLabSimulator(
        subscription_id="SUB-ROLLOVER",
        source_ref="simulator://ot-1/rollover",
        next_sequence=0xFFFFFFFF,
    )

    last = simulator.publish((_item(),), publish_timestamp=datetime.now(UTC))
    first = simulator.publish((_item(),), publish_timestamp=datetime.now(UTC))

    assert last.sequence_number == 0xFFFFFFFF
    assert first.sequence_number == 1
    assert simulator.next_sequence == 2


def test_simulator_refuses_write_and_call_operations() -> None:
    simulator = OpcUaReadOnlyLabSimulator(
        subscription_id="SUB-001",
        source_ref="simulator://ot-1",
    )

    with pytest.raises(PermissionError, match="read-only"):
        simulator.authorize_client_operation(OpcUaOperation.WRITE)
    with pytest.raises(PermissionError, match="read-only"):
        simulator.authorize_client_operation(OpcUaOperation.CALL)


def test_simulator_preserves_status_code_and_double_timestamps() -> None:
    simulator = OpcUaReadOnlyLabSimulator(
        subscription_id="SUB-001",
        source_ref="simulator://ot-1",
    )
    source_timestamp = datetime(2026, 8, 12, 5, 59, tzinfo=UTC)
    server_timestamp = datetime(2026, 8, 12, 6, 0, tzinfo=UTC)
    item = SimulatedMonitoredItem(
        tag_ref="tag://FT-001",
        namespace_uri="urn:petrole:test",
        node_id="s=FT-001",
        data_value=OpcUaDataValue(
            value=12.5,
            status_code=0x40000000,
            source_timestamp=source_timestamp,
            server_timestamp=server_timestamp,
        ),
    )

    message = simulator.publish((item,), publish_timestamp=datetime.now(UTC))
    retained = message.monitored_items[0].data_value

    assert retained.status_code == 0x40000000
    assert retained.source_timestamp == source_timestamp
    assert retained.server_timestamp == server_timestamp


def test_simulator_rejects_naive_publish_timestamp() -> None:
    simulator = OpcUaReadOnlyLabSimulator(
        subscription_id="SUB-001",
        source_ref="simulator://ot-1",
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        simulator.publish((_item(),), publish_timestamp=datetime(2026, 8, 12, 6, 0))


def test_zero_republish_cache_keeps_no_history() -> None:
    simulator = OpcUaReadOnlyLabSimulator(
        subscription_id="SUB-NO-CACHE",
        source_ref="simulator://ot-1/no-cache",
        republish_cache_size=0,
    )
    message = simulator.publish((_item(),), publish_timestamp=datetime.now(UTC))

    assert simulator.available_republish_sequences() == ()
    with pytest.raises(KeyError):
        simulator.republish(message.sequence_number)
