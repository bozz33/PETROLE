from __future__ import annotations

import pytest

from hydro_api.industrial.opcua_publish_recovery import plan_publish_recovery
from hydro_api.industrial.opcua_sequence import SequenceObservation


def test_durable_notification_is_acknowledged_and_gap_is_republished() -> None:
    observation = SequenceObservation(
        accepted=True,
        duplicate=False,
        out_of_order=False,
        missing_sequences=(101, 102),
        republish_required=True,
    )

    plan = plan_publish_recovery(
        subscription_id=7,
        received_sequence_number=103,
        observation=observation,
        notification_durable=True,
        source_ref="connector://opcua/site-a",
    )

    assert tuple(item.sequence_number for item in plan.acknowledgements) == (103,)
    assert tuple(item.sequence_number for item in plan.republish_requests) == (101, 102)
    assert all(item.subscription_id == 7 for item in plan.republish_requests)


def test_non_durable_notification_is_never_acknowledged() -> None:
    observation = SequenceObservation(
        accepted=True,
        duplicate=False,
        out_of_order=False,
        missing_sequences=(41,),
        republish_required=True,
    )

    plan = plan_publish_recovery(
        subscription_id=9,
        received_sequence_number=42,
        observation=observation,
        notification_durable=False,
        source_ref="connector://opcua/site-a",
    )

    assert plan.acknowledgements == ()
    assert tuple(item.sequence_number for item in plan.republish_requests) == (41,)


def test_durable_duplicate_can_be_reacknowledged_without_process_action() -> None:
    observation = SequenceObservation(
        accepted=False,
        duplicate=True,
        out_of_order=False,
        missing_sequences=(),
        republish_required=False,
    )

    plan = plan_publish_recovery(
        subscription_id=3,
        received_sequence_number=88,
        observation=observation,
        notification_durable=True,
        source_ref="connector://opcua/site-a",
    )

    assert tuple(item.sequence_number for item in plan.acknowledgements) == (88,)
    assert plan.republish_requests == ()


def test_recovery_plan_rejects_invalid_subscription_id() -> None:
    observation = SequenceObservation(True, False, False, (), False)

    with pytest.raises(ValueError, match="SubscriptionId"):
        plan_publish_recovery(
            subscription_id=0,
            received_sequence_number=1,
            observation=observation,
            notification_durable=True,
            source_ref="connector://opcua/site-a",
        )


def test_recovery_plan_rejects_zero_sequence() -> None:
    observation = SequenceObservation(True, False, False, (), False)

    with pytest.raises(ValueError, match="séquence OPC UA"):
        plan_publish_recovery(
            subscription_id=1,
            received_sequence_number=0,
            observation=observation,
            notification_durable=True,
            source_ref="connector://opcua/site-a",
        )
