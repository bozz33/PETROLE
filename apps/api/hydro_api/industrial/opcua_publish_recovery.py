"""Planification read-only des acknowledgements Publish et requêtes Republish.

Le futur adapter réseau ne doit acquitter un NotificationMessage qu'après sa
persistance durable côté PETROLE. Un trou de séquence devient une demande
Republish explicite ; ce module ne fabrique jamais de valeur pour combler un
message manquant et n'effectue aucun appel réseau.
"""

from __future__ import annotations

from dataclasses import dataclass

from hydro_api.industrial.opcua_policy import OpcUaOperation, assert_read_only_operation
from hydro_api.industrial.opcua_sequence import SequenceObservation, next_sequence_number

_MAX_INTEGER_ID = 0xFFFFFFFF


def _validate_subscription_id(subscription_id: int) -> None:
    if subscription_id < 1 or subscription_id > _MAX_INTEGER_ID:
        raise ValueError("Le SubscriptionId OPC UA doit appartenir à [1, 2^32-1].")


@dataclass(frozen=True, slots=True)
class OpcUaSubscriptionAcknowledgement:
    """Acknowledgement de transport d'un NotificationMessage persisté."""

    subscription_id: int
    sequence_number: int
    source_ref: str

    def __post_init__(self) -> None:
        _validate_subscription_id(self.subscription_id)
        next_sequence_number(self.sequence_number)
        if not self.source_ref.strip():
            raise ValueError("La provenance de l'acknowledgement OPC UA est obligatoire.")


@dataclass(frozen=True, slots=True)
class OpcUaRepublishRequest:
    """Demande read-only d'un NotificationMessage absent du flux reçu."""

    subscription_id: int
    sequence_number: int
    source_ref: str

    def __post_init__(self) -> None:
        _validate_subscription_id(self.subscription_id)
        next_sequence_number(self.sequence_number)
        if not self.source_ref.strip():
            raise ValueError("La provenance de la demande Republish est obligatoire.")


@dataclass(frozen=True, slots=True)
class OpcUaPublishRecoveryPlan:
    """Actions de transport à transmettre plus tard au gateway OPC UA réel."""

    acknowledgements: tuple[OpcUaSubscriptionAcknowledgement, ...]
    republish_requests: tuple[OpcUaRepublishRequest, ...]
    notification_durable: bool
    source_ref: str


def plan_publish_recovery(
    *,
    subscription_id: int,
    received_sequence_number: int,
    observation: SequenceObservation,
    notification_durable: bool,
    source_ref: str,
) -> OpcUaPublishRecoveryPlan:
    """Construit les actions sans appel réseau ni effet sur le procédé.

    L'acknowledgement du message reçu est proposé seulement si la couche de
    persistance confirme sa durabilité. Les trous signalés par le tracker sont
    toujours transformés en demandes Republish explicites.
    """

    _validate_subscription_id(subscription_id)
    next_sequence_number(received_sequence_number)
    if not source_ref.strip():
        raise ValueError("La provenance du plan de reprise OPC UA est obligatoire.")

    assert_read_only_operation(OpcUaOperation.REPUBLISH)
    assert_read_only_operation(OpcUaOperation.SUBSCRIPTION_ACKNOWLEDGE)

    acknowledgements: tuple[OpcUaSubscriptionAcknowledgement, ...] = ()
    if notification_durable:
        acknowledgements = (
            OpcUaSubscriptionAcknowledgement(
                subscription_id=subscription_id,
                sequence_number=received_sequence_number,
                source_ref=source_ref,
            ),
        )

    republish_requests = tuple(
        OpcUaRepublishRequest(
            subscription_id=subscription_id,
            sequence_number=sequence_number,
            source_ref=source_ref,
        )
        for sequence_number in observation.missing_sequences
    )
    return OpcUaPublishRecoveryPlan(
        acknowledgements=acknowledgements,
        republish_requests=republish_requests,
        notification_durable=notification_durable,
        source_ref=source_ref,
    )


__all__ = [
    "OpcUaPublishRecoveryPlan",
    "OpcUaRepublishRequest",
    "OpcUaSubscriptionAcknowledgement",
    "plan_publish_recovery",
]
