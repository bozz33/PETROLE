"""Partition reproductible des événements labellisés pour P7-I.

Le module ne crée aucun label et ne sélectionne aucun événement. Il exige que
chaque événement disponible soit affecté à calibration, validation, test ou à
une exclusion explicitement justifiée. Le jeu de test indépendant est
obligatoire avant toute campagne de performance.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from hydro_leak.event_matching import LeakEventLabel


@dataclass(frozen=True, slots=True)
class ExcludedLeakEvent:
    """Exclusion explicite d'un événement, jamais silencieuse."""

    event_id: str
    reason_ref: str
    evidence_ref: str

    def __post_init__(self) -> None:
        if any(not value.strip() for value in (self.event_id, self.reason_ref, self.evidence_ref)):
            raise ValueError("Événement exclu, motif et preuve sont obligatoires.")


@dataclass(frozen=True, slots=True)
class LeakValidationDatasetPartition:
    """Partition P7-I figée avec provenance et empreinte canonique."""

    dataset_ref: str
    protocol_ref: str
    label_definition_ref: str
    calibration_event_ids: tuple[str, ...]
    validation_event_ids: tuple[str, ...]
    test_event_ids: tuple[str, ...]
    excluded_events: tuple[ExcludedLeakEvent, ...]
    event_count: int
    partition_sha256: str


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def freeze_leak_validation_dataset(
    *,
    dataset_ref: str,
    protocol_ref: str,
    label_definition_ref: str,
    events: tuple[LeakEventLabel, ...],
    calibration_event_ids: tuple[str, ...] = (),
    validation_event_ids: tuple[str, ...] = (),
    test_event_ids: tuple[str, ...],
    excluded_events: tuple[ExcludedLeakEvent, ...] = (),
) -> LeakValidationDatasetPartition:
    """Fige une partition exhaustive sans chevauchement ni sélection silencieuse."""

    if any(not value.strip() for value in (dataset_ref, protocol_ref, label_definition_ref)):
        raise ValueError("Dataset, protocole et définition des labels sont obligatoires.")
    if not events:
        raise ValueError("Le dataset de validation doit contenir au moins un événement labellisé.")
    if not test_event_ids:
        raise ValueError("Un jeu de test indépendant non vide est obligatoire.")

    ordered_events = tuple(sorted(events, key=lambda item: (item.started_at_utc, item.event_id)))
    event_ids = tuple(event.event_id for event in ordered_events)
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Chaque événement labellisé du dataset doit avoir un identifiant unique.")

    groups = {
        "calibration": tuple(calibration_event_ids),
        "validation": tuple(validation_event_ids),
        "test": tuple(test_event_ids),
        "excluded": tuple(item.event_id for item in excluded_events),
    }
    for group_name, ids in groups.items():
        if any(not event_id.strip() for event_id in ids):
            raise ValueError(f"Le groupe {group_name} contient un identifiant d'événement vide.")
        if len(ids) != len(set(ids)):
            raise ValueError(f"Le groupe {group_name} contient un événement dupliqué.")

    assigned: dict[str, str] = {}
    for group_name, ids in groups.items():
        for event_id in ids:
            previous = assigned.get(event_id)
            if previous is not None:
                raise ValueError(
                    f"L'événement {event_id} est affecté à plusieurs groupes : {previous}, {group_name}."
                )
            assigned[event_id] = group_name

    known = set(event_ids)
    unknown = tuple(sorted(set(assigned) - known))
    if unknown:
        raise ValueError(f"La partition référence des événements absents du dataset : {unknown}.")
    unassigned = tuple(sorted(known - set(assigned)))
    if unassigned:
        raise ValueError(f"Des événements labellisés ne sont pas affectés explicitement : {unassigned}.")

    excluded_by_id = {item.event_id: item for item in excluded_events}
    event_payload = [
        {
            "event_id": event.event_id,
            "started_at": event.started_at_utc.isoformat().replace("+00:00", "Z"),
            "label_source_ref": event.source_ref,
            "partition": assigned[event.event_id],
            "exclusion_reason_ref": excluded_by_id[event.event_id].reason_ref
            if event.event_id in excluded_by_id
            else None,
            "exclusion_evidence_ref": excluded_by_id[event.event_id].evidence_ref
            if event.event_id in excluded_by_id
            else None,
        }
        for event in ordered_events
    ]
    payload = {
        "dataset_ref": dataset_ref,
        "protocol_ref": protocol_ref,
        "label_definition_ref": label_definition_ref,
        "events": event_payload,
    }

    return LeakValidationDatasetPartition(
        dataset_ref=dataset_ref,
        protocol_ref=protocol_ref,
        label_definition_ref=label_definition_ref,
        calibration_event_ids=tuple(sorted(calibration_event_ids)),
        validation_event_ids=tuple(sorted(validation_event_ids)),
        test_event_ids=tuple(sorted(test_event_ids)),
        excluded_events=tuple(sorted(excluded_events, key=lambda item: item.event_id)),
        event_count=len(ordered_events),
        partition_sha256=_canonical_sha256(payload),
    )


__all__ = [
    "ExcludedLeakEvent",
    "LeakValidationDatasetPartition",
    "freeze_leak_validation_dataset",
]
