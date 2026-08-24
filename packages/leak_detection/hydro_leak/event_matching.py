"""Association déterministe entre événements de fuite labellisés et alertes.

La fenêtre de détection est fournie par le protocole de campagne. Le module
n'invente aucun seuil, exige des fenêtres non ambiguës et associe au plus une
alerte à chaque événement et réciproquement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import pairwise


@dataclass(frozen=True, slots=True)
class LeakEventLabel:
    """Début d'un événement de vérité terrain avec provenance obligatoire."""

    event_id: str
    started_at: datetime
    source_ref: str

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.source_ref.strip():
            raise ValueError("Identifiant et provenance de l'événement sont obligatoires.")
        if self.started_at.tzinfo is None:
            raise ValueError("L'événement labellisé doit être timezone-aware.")

    @property
    def started_at_utc(self) -> datetime:
        return self.started_at.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class LeakAlertObservation:
    """Alerte analytique observée, sans sémantique de commande."""

    alert_id: str
    raised_at: datetime
    source_ref: str

    def __post_init__(self) -> None:
        if not self.alert_id.strip() or not self.source_ref.strip():
            raise ValueError("Identifiant et provenance de l'alerte sont obligatoires.")
        if self.raised_at.tzinfo is None:
            raise ValueError("L'alerte analytique doit être timezone-aware.")

    @property
    def raised_at_utc(self) -> datetime:
        return self.raised_at.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class EventMatchingPolicy:
    """Règle de campagne définie avant évaluation des alertes."""

    maximum_detection_delay_s: float
    protocol_ref: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.maximum_detection_delay_s) or self.maximum_detection_delay_s < 0:
            raise ValueError("Le délai maximal de matching doit être fini et positif ou nul.")
        if not self.protocol_ref.strip():
            raise ValueError("La référence du protocole de matching est obligatoire.")


@dataclass(frozen=True, slots=True)
class MatchedLeakEvent:
    event_id: str
    alert_id: str
    detection_delay_s: float


@dataclass(frozen=True, slots=True)
class EventMatchingResult:
    """Associations et éléments non associés, sans verdict de performance."""

    matches: tuple[MatchedLeakEvent, ...]
    unmatched_event_ids: tuple[str, ...]
    unmatched_alert_ids: tuple[str, ...]
    protocol_ref: str


def _validate_unambiguous_event_windows(
    events: tuple[LeakEventLabel, ...],
    policy: EventMatchingPolicy,
) -> tuple[LeakEventLabel, ...]:
    ordered = tuple(sorted(events, key=lambda event: event.started_at_utc))
    event_ids = [event.event_id for event in ordered]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Chaque événement labellisé doit avoir un identifiant unique.")
    window = timedelta(seconds=policy.maximum_detection_delay_s)
    for previous, current in pairwise(ordered):
        if current.started_at_utc <= previous.started_at_utc + window:
            raise ValueError(
                "Les fenêtres de matching de deux événements se chevauchent ; "
                "le protocole doit lever l'ambiguïté avant l'évaluation."
            )
    return ordered


def match_alerts_to_events(
    *,
    events: tuple[LeakEventLabel, ...],
    alerts: tuple[LeakAlertObservation, ...],
    policy: EventMatchingPolicy,
) -> EventMatchingResult:
    """Associe la première alerte non utilisée située dans la fenêtre de l'événement."""

    ordered_events = _validate_unambiguous_event_windows(events, policy)
    alert_ids = [alert.alert_id for alert in alerts]
    if len(alert_ids) != len(set(alert_ids)):
        raise ValueError("Chaque alerte doit avoir un identifiant unique.")
    ordered_alerts = tuple(sorted(alerts, key=lambda alert: alert.raised_at_utc))
    used_alert_ids: set[str] = set()
    matches: list[MatchedLeakEvent] = []
    unmatched_events: list[str] = []
    maximum_delay = timedelta(seconds=policy.maximum_detection_delay_s)

    for event in ordered_events:
        window_end = event.started_at_utc + maximum_delay
        candidate = next(
            (
                alert
                for alert in ordered_alerts
                if alert.alert_id not in used_alert_ids
                and event.started_at_utc <= alert.raised_at_utc <= window_end
            ),
            None,
        )
        if candidate is None:
            unmatched_events.append(event.event_id)
            continue
        used_alert_ids.add(candidate.alert_id)
        delay = (candidate.raised_at_utc - event.started_at_utc).total_seconds()
        matches.append(
            MatchedLeakEvent(
                event_id=event.event_id,
                alert_id=candidate.alert_id,
                detection_delay_s=delay,
            )
        )

    unmatched_alerts = tuple(
        alert.alert_id for alert in ordered_alerts if alert.alert_id not in used_alert_ids
    )
    return EventMatchingResult(
        matches=tuple(matches),
        unmatched_event_ids=tuple(unmatched_events),
        unmatched_alert_ids=unmatched_alerts,
        protocol_ref=policy.protocol_ref,
    )


__all__ = [
    "EventMatchingPolicy",
    "EventMatchingResult",
    "LeakAlertObservation",
    "LeakEventLabel",
    "MatchedLeakEvent",
    "match_alerts_to_events",
]
