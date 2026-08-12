"""Simulateur déterministe OPC UA read-only pour le POC OT-1.

Ce module simule uniquement les comportements dont PETROLE a besoin pour tester
son pipeline analytique hors ligne : NotificationMessage ordonnés, rollover des
numéros de séquence, cache de Republish borné et DataValue avec qualité et
double horodatage. Il ne prétend pas implémenter le protocole réseau IEC 62541
et ne remplace pas le futur gateway open62541 prévu par D14.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from hydro_api.industrial.opcua_data_value import OpcUaDataValue
from hydro_api.industrial.opcua_policy import OpcUaOperation, assert_read_only_operation
from hydro_api.industrial.opcua_sequence import next_sequence_number


@dataclass(frozen=True, slots=True)
class SimulatedMonitoredItem:
    """Valeur d'un nœud surveillé conservant son identité OPC UA stable."""

    tag_ref: str
    namespace_uri: str
    node_id: str
    data_value: OpcUaDataValue

    def __post_init__(self) -> None:
        values = (self.tag_ref, self.namespace_uri, self.node_id)
        if any(not value.strip() for value in values):
            raise ValueError("Tag, namespace URI et NodeId simulés sont obligatoires.")


@dataclass(frozen=True, slots=True)
class SimulatedNotificationMessage:
    """NotificationMessage de laboratoire, sans encodage wire OPC UA."""

    subscription_id: str
    sequence_number: int
    publish_timestamp: datetime
    monitored_items: tuple[SimulatedMonitoredItem, ...]
    source_ref: str

    def __post_init__(self) -> None:
        if not self.subscription_id.strip() or not self.source_ref.strip():
            raise ValueError("Subscription et provenance du message simulé sont obligatoires.")
        next_sequence_number(self.sequence_number)
        if self.publish_timestamp.tzinfo is None:
            raise ValueError("Le timestamp Publish simulé doit être timezone-aware.")
        if not self.monitored_items:
            raise ValueError("Un message de données simulé doit contenir au moins un item surveillé.")

    @property
    def publish_timestamp_utc(self) -> datetime:
        return self.publish_timestamp.astimezone(UTC)


@dataclass(slots=True)
class OpcUaReadOnlyLabSimulator:
    """Producteur hors ligne de notifications et cache Republish borné.

    Le simulateur ne contient aucun Write/Call. ``authorize_client_operation``
    réutilise la politique centrale pour garantir que les scénarios de test ne
    puissent pas étendre silencieusement le périmètre au contrôle procédé.
    """

    subscription_id: str
    source_ref: str
    republish_cache_size: int = 256
    next_sequence: int = 1
    _republish_cache: dict[int, SimulatedNotificationMessage] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _cache_order: list[int] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.subscription_id.strip() or not self.source_ref.strip():
            raise ValueError("Subscription et provenance du simulateur sont obligatoires.")
        if self.republish_cache_size < 0:
            raise ValueError("La taille du cache Republish doit être positive ou nulle.")
        next_sequence_number(self.next_sequence)

    def authorize_client_operation(self, operation: OpcUaOperation) -> None:
        """Applique exactement l'allow-list read-only commune au futur adapter."""

        assert_read_only_operation(operation)

    def publish(
        self,
        monitored_items: tuple[SimulatedMonitoredItem, ...],
        *,
        publish_timestamp: datetime,
    ) -> SimulatedNotificationMessage:
        """Crée le prochain message et le conserve dans le cache Republish."""

        self.authorize_client_operation(OpcUaOperation.SUBSCRIBE)
        message = SimulatedNotificationMessage(
            subscription_id=self.subscription_id,
            sequence_number=self.next_sequence,
            publish_timestamp=publish_timestamp,
            monitored_items=monitored_items,
            source_ref=self.source_ref,
        )
        self.next_sequence = next_sequence_number(self.next_sequence)
        self._cache_message(message)
        return message

    def republish(self, sequence_number: int) -> SimulatedNotificationMessage:
        """Retourne exactement le message encore disponible pour Republish."""

        self.authorize_client_operation(OpcUaOperation.SUBSCRIBE)
        next_sequence_number(sequence_number)
        try:
            return self._republish_cache[sequence_number]
        except KeyError as exc:
            raise KeyError(
                f"La séquence {sequence_number} n'est plus disponible dans le cache Republish simulé."
            ) from exc

    def available_republish_sequences(self) -> tuple[int, ...]:
        """Expose l'ordre du cache pour les assertions de qualification OT-1."""

        return tuple(self._cache_order)

    def _cache_message(self, message: SimulatedNotificationMessage) -> None:
        if self.republish_cache_size == 0:
            return
        self._republish_cache[message.sequence_number] = message
        self._cache_order.append(message.sequence_number)
        while len(self._cache_order) > self.republish_cache_size:
            expired_sequence = self._cache_order.pop(0)
            self._republish_cache.pop(expired_sequence, None)


__all__ = [
    "OpcUaReadOnlyLabSimulator",
    "SimulatedMonitoredItem",
    "SimulatedNotificationMessage",
]
