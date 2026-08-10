from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hydro_leak import (
    EventMatchingPolicy,
    LeakAlertObservation,
    LeakEventLabel,
    match_alerts_to_events,
)


def _event(event_id: str, minute: int) -> LeakEventLabel:
    return LeakEventLabel(
        event_id=event_id,
        started_at=datetime(2026, 8, 10, 8, minute, tzinfo=UTC),
        source_ref=f"field-test://events/{event_id}",
    )


def _alert(alert_id: str, minute: int, second: int = 0) -> LeakAlertObservation:
    return LeakAlertObservation(
        alert_id=alert_id,
        raised_at=datetime(2026, 8, 10, 8, minute, second, tzinfo=UTC),
        source_ref=f"detector://run-001/{alert_id}",
    )


def test_matching_uses_first_unmatched_alert_inside_predefined_window() -> None:
    policy = EventMatchingPolicy(
        maximum_detection_delay_s=120.0,
        protocol_ref="protocol://leak-campaign/v1",
    )
    result = match_alerts_to_events(
        events=(_event("E1", 0), _event("E2", 10)),
        alerts=(_alert("A0", 0, 30), _alert("A1", 1), _alert("A2", 12), _alert("FP", 20)),
        policy=policy,
    )

    assert tuple(match.event_id for match in result.matches) == ("E1", "E2")
    assert tuple(match.alert_id for match in result.matches) == ("A0", "A2")
    assert result.matches[0].detection_delay_s == pytest.approx(30.0)
    assert result.matches[1].detection_delay_s == pytest.approx(120.0)
    assert result.unmatched_event_ids == ()
    assert result.unmatched_alert_ids == ("A1", "FP")


def test_matching_reports_event_without_alert() -> None:
    result = match_alerts_to_events(
        events=(_event("E1", 0),),
        alerts=(),
        policy=EventMatchingPolicy(60.0, "protocol://leak-campaign/v1"),
    )
    assert result.matches == ()
    assert result.unmatched_event_ids == ("E1",)


def test_overlapping_event_windows_are_rejected_as_ambiguous() -> None:
    first = _event("E1", 0)
    second = LeakEventLabel(
        event_id="E2",
        started_at=first.started_at + timedelta(seconds=30),
        source_ref="field-test://events/E2",
    )
    with pytest.raises(ValueError, match="se chevauchent"):
        match_alerts_to_events(
            events=(first, second),
            alerts=(),
            policy=EventMatchingPolicy(60.0, "protocol://leak-campaign/v1"),
        )


def test_alert_before_event_is_not_matched() -> None:
    event = _event("E1", 1)
    result = match_alerts_to_events(
        events=(event,),
        alerts=(_alert("A0", 0, 59),),
        policy=EventMatchingPolicy(60.0, "protocol://leak-campaign/v1"),
    )
    assert result.unmatched_event_ids == ("E1",)
    assert result.unmatched_alert_ids == ("A0",)
