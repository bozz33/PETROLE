"""Suivi read-only des séquences OPC UA Publish/Republish.

Référence : OPC UA 10000-4 v1.05.07, modèle Subscription et services
Publish/Republish. Les NotificationMessages utilisent des numéros de séquence
32 bits non nuls ; un trou doit rester visible afin que le connecteur puisse
planifier un Republish si le serveur conserve encore le message.
"""

from __future__ import annotations

from dataclasses import dataclass

_MAX_SEQUENCE = 0xFFFFFFFF


def next_sequence_number(sequence_number: int) -> int:
    """Retourne le prochain numéro OPC UA, avec rollover de 0xFFFFFFFF vers 1."""

    if sequence_number < 1 or sequence_number > _MAX_SEQUENCE:
        raise ValueError("Un numéro de séquence OPC UA doit appartenir à [1, 2^32-1].")
    return 1 if sequence_number == _MAX_SEQUENCE else sequence_number + 1


def _forward_distance(start: int, end: int) -> int:
    """Nombre d'incréments OPC UA nécessaires pour aller de start à end."""

    if start < 1 or start > _MAX_SEQUENCE or end < 1 or end > _MAX_SEQUENCE:
        raise ValueError("Les numéros de séquence OPC UA doivent être non nuls sur 32 bits.")
    if end >= start:
        return end - start
    return (_MAX_SEQUENCE - start) + end


def missing_sequence_numbers(
    previous: int,
    current: int,
    *,
    maximum_listed: int = 1_024,
) -> tuple[int, ...]:
    """Liste les séquences manquantes entre deux messages dans l'ordre OPC UA.

    Une protection empêche d'allouer une liste gigantesque après une reprise
    incohérente. Dans ce cas, l'appelant reçoit une erreur et doit déclencher
    une resynchronisation plutôt que supposer les messages récupérables.
    """

    if maximum_listed < 0:
        raise ValueError("maximum_listed doit être positif ou nul.")
    distance = _forward_distance(previous, current)
    missing_count = max(distance - 1, 0)
    if missing_count > maximum_listed:
        raise ValueError("Le trou de séquence dépasse la limite de Republish planifiable.")
    missing: list[int] = []
    candidate = next_sequence_number(previous)
    for _ in range(missing_count):
        missing.append(candidate)
        candidate = next_sequence_number(candidate)
    return tuple(missing)


@dataclass(frozen=True, slots=True)
class SequenceObservation:
    """Verdict de réception d'un NotificationMessage."""

    accepted: bool
    duplicate: bool
    out_of_order: bool
    missing_sequences: tuple[int, ...]
    republish_required: bool


@dataclass(slots=True)
class OpcUaSequenceTracker:
    """État minimal par Subscription, sans acquittement ni écriture serveur."""

    last_sequence_number: int | None = None
    maximum_republish_gap: int = 1_024

    def __post_init__(self) -> None:
        if self.last_sequence_number is not None:
            next_sequence_number(self.last_sequence_number)
        if self.maximum_republish_gap < 0:
            raise ValueError("maximum_republish_gap doit être positif ou nul.")

    def observe(self, sequence_number: int) -> SequenceObservation:
        """Observe un message et expose doublons/trous sans les masquer."""

        next_sequence_number(sequence_number)
        previous = self.last_sequence_number
        if previous is None:
            self.last_sequence_number = sequence_number
            return SequenceObservation(True, False, False, (), False)
        if sequence_number == previous:
            return SequenceObservation(False, True, False, (), False)

        expected = next_sequence_number(previous)
        if sequence_number == expected:
            self.last_sequence_number = sequence_number
            return SequenceObservation(True, False, False, (), False)

        distance = _forward_distance(previous, sequence_number)
        # Un saut très important est traité comme un message ancien/rejoué plutôt
        # que comme des milliards de pertes à réclamer. La moitié de l'espace
        # séquentiel donne un ordre non ambigu autour du rollover.
        if distance > _MAX_SEQUENCE // 2:
            return SequenceObservation(False, False, True, (), False)

        missing = missing_sequence_numbers(
            previous,
            sequence_number,
            maximum_listed=self.maximum_republish_gap,
        )
        self.last_sequence_number = sequence_number
        return SequenceObservation(True, False, False, missing, bool(missing))


__all__ = [
    "OpcUaSequenceTracker",
    "SequenceObservation",
    "missing_sequence_numbers",
    "next_sequence_number",
]
