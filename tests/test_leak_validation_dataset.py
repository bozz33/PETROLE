from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hydro_leak.event_matching import LeakEventLabel
from hydro_leak.validation_dataset import ExcludedLeakEvent, freeze_leak_validation_dataset

START = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)


def _event(index: int) -> LeakEventLabel:
    return LeakEventLabel(
        event_id=f"LEAK-{index:03d}",
        started_at=START + timedelta(hours=index),
        source_ref=f"evidence://controlled-leak/{index}",
    )


def test_partition_is_exhaustive_traceable_and_deterministic() -> None:
    events = tuple(_event(index) for index in range(1, 6))
    excluded = ExcludedLeakEvent(
        event_id="LEAK-005",
        reason_ref="protocol://exclusion/sensor-outage",
        evidence_ref="evidence://sensor-outage/LEAK-005",
    )

    first = freeze_leak_validation_dataset(
        dataset_ref="dataset://leak-campaign/pilot-v1",
        protocol_ref="protocol://leak-campaign/v1",
        label_definition_ref="labels://controlled-leak/v1",
        events=events,
        calibration_event_ids=("LEAK-001",),
        validation_event_ids=("LEAK-002",),
        test_event_ids=("LEAK-003", "LEAK-004"),
        excluded_events=(excluded,),
    )
    second = freeze_leak_validation_dataset(
        dataset_ref="dataset://leak-campaign/pilot-v1",
        protocol_ref="protocol://leak-campaign/v1",
        label_definition_ref="labels://controlled-leak/v1",
        events=tuple(reversed(events)),
        calibration_event_ids=("LEAK-001",),
        validation_event_ids=("LEAK-002",),
        test_event_ids=("LEAK-004", "LEAK-003"),
        excluded_events=(excluded,),
    )

    assert first.event_count == 5
    assert first.test_event_ids == ("LEAK-003", "LEAK-004")
    assert first.partition_sha256 == second.partition_sha256
    assert len(first.partition_sha256) == 64


def test_partition_requires_nonempty_independent_test_set() -> None:
    with pytest.raises(ValueError, match="test indépendant"):
        freeze_leak_validation_dataset(
            dataset_ref="dataset://1",
            protocol_ref="protocol://1",
            label_definition_ref="labels://1",
            events=(_event(1),),
            test_event_ids=(),
            excluded_events=(
                ExcludedLeakEvent(
                    event_id="LEAK-001",
                    reason_ref="reason://1",
                    evidence_ref="evidence://1",
                ),
            ),
        )


def test_partition_rejects_overlap_between_calibration_validation_test_or_exclusion() -> None:
    with pytest.raises(ValueError, match="plusieurs groupes"):
        freeze_leak_validation_dataset(
            dataset_ref="dataset://1",
            protocol_ref="protocol://1",
            label_definition_ref="labels://1",
            events=(_event(1), _event(2)),
            calibration_event_ids=("LEAK-001",),
            validation_event_ids=("LEAK-001",),
            test_event_ids=("LEAK-002",),
        )


def test_partition_rejects_unknown_and_silently_unassigned_events() -> None:
    events = (_event(1), _event(2))
    with pytest.raises(ValueError, match="absents du dataset"):
        freeze_leak_validation_dataset(
            dataset_ref="dataset://1",
            protocol_ref="protocol://1",
            label_definition_ref="labels://1",
            events=events,
            test_event_ids=("LEAK-001", "LEAK-999"),
        )

    with pytest.raises(ValueError, match="ne sont pas affectés explicitement"):
        freeze_leak_validation_dataset(
            dataset_ref="dataset://1",
            protocol_ref="protocol://1",
            label_definition_ref="labels://1",
            events=events,
            test_event_ids=("LEAK-001",),
        )


def test_exclusion_requires_reason_and_evidence() -> None:
    with pytest.raises(ValueError, match="motif et preuve"):
        ExcludedLeakEvent(
            event_id="LEAK-001",
            reason_ref="",
            evidence_ref="evidence://1",
        )


def test_partition_rejects_duplicate_labels_and_duplicate_group_membership() -> None:
    duplicate = _event(1)
    with pytest.raises(ValueError, match="identifiant unique"):
        freeze_leak_validation_dataset(
            dataset_ref="dataset://1",
            protocol_ref="protocol://1",
            label_definition_ref="labels://1",
            events=(duplicate, duplicate),
            test_event_ids=("LEAK-001",),
        )

    with pytest.raises(ValueError, match="dupliqué"):
        freeze_leak_validation_dataset(
            dataset_ref="dataset://1",
            protocol_ref="protocol://1",
            label_definition_ref="labels://1",
            events=(_event(1), _event(2)),
            test_event_ids=("LEAK-001", "LEAK-001"),
            excluded_events=(
                ExcludedLeakEvent(
                    event_id="LEAK-002",
                    reason_ref="reason://2",
                    evidence_ref="evidence://2",
                ),
            ),
        )


def test_partition_requires_dataset_protocol_and_label_definition() -> None:
    with pytest.raises(ValueError, match="Dataset, protocole"):
        freeze_leak_validation_dataset(
            dataset_ref="",
            protocol_ref="protocol://1",
            label_definition_ref="labels://1",
            events=(_event(1),),
            test_event_ids=("LEAK-001",),
        )
