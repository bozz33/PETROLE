"""Noyau déterministe de buffer/checkpoint pour connecteurs read-only.

D15 exige de résister aux coupures sans perdre l'ordre et de dédupliquer par
séquence/checkpoint/idempotence. Ce module définit le contrat append-only ; la
persistance disque/DB est un adaptateur séparé afin de ne pas confondre logique
d'ordre et technologie de stockage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class BufferedIndustrialRecord:
    """Enregistrement brut ordonné localement avant ingestion applicative."""

    local_sequence: int
    idempotency_key: str
    payload_sha256: str
    source_timestamp: datetime
    source_ref: str

    def __post_init__(self) -> None:
        if self.local_sequence < 1:
            raise ValueError("La séquence locale du buffer doit être strictement positive.")
        if not self.idempotency_key.strip():
            raise ValueError("La clé d'idempotence du buffer est obligatoire.")
        if not _SHA256_PATTERN.fullmatch(self.payload_sha256):
            raise ValueError("Le payload du buffer doit être identifié par un SHA-256 complet.")
        if self.source_timestamp.tzinfo is None:
            raise ValueError("Le SourceTimestamp du buffer doit être timezone-aware.")
        if not self.source_ref.strip():
            raise ValueError("La provenance du point bufferisé est obligatoire.")

    @property
    def source_timestamp_utc(self) -> datetime:
        return self.source_timestamp.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class ConnectorCheckpoint:
    """Dernier enregistrement durablement confirmé par le consommateur."""

    connector_ref: str
    checkpoint_version: str
    last_local_sequence: int
    last_idempotency_key: str | None = None

    def __post_init__(self) -> None:
        if not self.connector_ref.strip() or not self.checkpoint_version.strip():
            raise ValueError("Le connecteur et la version de checkpoint sont obligatoires.")
        if self.last_local_sequence < 0:
            raise ValueError("La séquence checkpoint doit être positive ou nulle.")
        if self.last_idempotency_key is not None and not self.last_idempotency_key.strip():
            raise ValueError("La dernière clé d'idempotence ne peut pas être vide.")


@dataclass(frozen=True, slots=True)
class BufferDrainPlan:
    """Plan ordonné à remettre au consommateur après un checkpoint."""

    checkpoint: ConnectorCheckpoint
    pending: tuple[BufferedIndustrialRecord, ...]
    duplicate_count: int


def plan_buffer_drain(
    records: tuple[BufferedIndustrialRecord, ...],
    checkpoint: ConnectorCheckpoint,
) -> BufferDrainPlan:
    """Déduplique et sélectionne le suffixe strictement postérieur au checkpoint.

    Les enregistrements doivent former une séquence locale contiguë après
    déduplication. Un trou provoque un refus explicite afin qu'un adaptateur de
    stockage restaure/réconcilie les données plutôt que de masquer une perte.
    """

    ordered = sorted(records, key=lambda record: record.local_sequence)
    unique_by_key: dict[str, BufferedIndustrialRecord] = {}
    duplicate_count = 0
    for record in ordered:
        existing = unique_by_key.get(record.idempotency_key)
        if existing is None:
            unique_by_key[record.idempotency_key] = record
            continue
        if existing.payload_sha256 != record.payload_sha256:
            raise ValueError("Une clé d'idempotence du buffer référence deux payloads différents.")
        duplicate_count += 1

    unique = sorted(unique_by_key.values(), key=lambda record: record.local_sequence)
    sequences = [record.local_sequence for record in unique]
    if len(sequences) != len(set(sequences)):
        raise ValueError("Deux enregistrements distincts partagent la même séquence locale.")

    pending = tuple(
        record for record in unique if record.local_sequence > checkpoint.last_local_sequence
    )
    expected = checkpoint.last_local_sequence + 1
    for record in pending:
        if record.local_sequence != expected:
            raise ValueError(
                f"Trou de buffer détecté : séquence locale {expected} attendue, "
                f"{record.local_sequence} reçue."
            )
        expected += 1
    return BufferDrainPlan(
        checkpoint=checkpoint,
        pending=pending,
        duplicate_count=duplicate_count,
    )


def advance_checkpoint(
    checkpoint: ConnectorCheckpoint,
    processed: tuple[BufferedIndustrialRecord, ...],
) -> ConnectorCheckpoint:
    """Avance le checkpoint seulement sur un préfixe contigu du plan traité."""

    if not processed:
        return checkpoint
    expected = checkpoint.last_local_sequence + 1
    seen_keys: set[str] = set()
    for record in processed:
        if record.local_sequence != expected:
            raise ValueError("Le checkpoint ne peut avancer que sur un préfixe contigu et ordonné.")
        if record.idempotency_key in seen_keys:
            raise ValueError("Un même enregistrement ne peut être acquitté deux fois dans un lot.")
        seen_keys.add(record.idempotency_key)
        expected += 1
    last = processed[-1]
    return ConnectorCheckpoint(
        connector_ref=checkpoint.connector_ref,
        checkpoint_version=checkpoint.checkpoint_version,
        last_local_sequence=last.local_sequence,
        last_idempotency_key=last.idempotency_key,
    )


__all__ = [
    "BufferDrainPlan",
    "BufferedIndustrialRecord",
    "ConnectorCheckpoint",
    "advance_checkpoint",
    "plan_buffer_drain",
]
