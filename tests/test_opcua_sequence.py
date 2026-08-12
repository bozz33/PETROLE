from __future__ import annotations

import pytest

from hydro_api.industrial.opcua_sequence import (
    OpcUaSequenceTracker,
    missing_sequence_numbers,
    next_sequence_number,
)


def test_sequence_number_rolls_over_to_one() -> None:
    assert next_sequence_number(0xFFFFFFFF) == 1
    assert next_sequence_number(41) == 42


def test_tracker_detects_gap_for_republish() -> None:
    tracker = OpcUaSequenceTracker(maximum_republish_gap=10)
    first = tracker.observe(100)
    gap = tracker.observe(104)

    assert first.accepted is True
    assert gap.accepted is True
    assert gap.republish_required is True
    assert gap.missing_sequences == (101, 102, 103)
    assert tracker.last_sequence_number == 104


def test_tracker_handles_rollover_gap() -> None:
    tracker = OpcUaSequenceTracker(last_sequence_number=0xFFFFFFFE)
    observation = tracker.observe(2)
    assert observation.missing_sequences == (0xFFFFFFFF, 1)
    assert observation.republish_required is True


def test_tracker_rejects_duplicate_and_old_message() -> None:
    tracker = OpcUaSequenceTracker(last_sequence_number=100)
    duplicate = tracker.observe(100)
    old = tracker.observe(99)

    assert duplicate.accepted is False
    assert duplicate.duplicate is True
    assert old.accepted is False
    assert old.out_of_order is True
    assert tracker.last_sequence_number == 100


def test_gap_larger_than_policy_requires_resynchronization() -> None:
    with pytest.raises(ValueError, match="dépasse la limite"):
        missing_sequence_numbers(10, 20, maximum_listed=3)


def test_zero_sequence_is_rejected() -> None:
    with pytest.raises(ValueError, match="appartenir"):
        next_sequence_number(0)
