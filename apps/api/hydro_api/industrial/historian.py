"""Contrat générique d'adaptation historian en lecture seule.

Cette couche ne dépend d'aucun SDK fournisseur. Elle normalise uniquement les
métadonnées minimales nécessaires pour alimenter le pipeline de séries PETROLE
sans perdre l'horodatage source, la qualité ni la provenance du système amont.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class HistorianQuality(StrEnum):
    """Qualité générique conservée avant mapping fournisseur éventuel."""

    GOOD = "good"
    UNCERTAIN = "uncertain"
    BAD = "bad"


@dataclass(frozen=True, slots=True)
class HistorianQueryWindow:
    """Fenêtre UTC bornée d'une lecture historique read-only."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Les bornes historian doivent être timezone-aware.")
        if self.end <= self.start:
            raise ValueError("La fin de fenêtre historian doit être postérieure au début.")

    @property
    def start_utc(self) -> datetime:
        return self.start.astimezone(UTC)

    @property
    def end_utc(self) -> datetime:
        return self.end.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class HistorianRecord:
    """Point numérique provenant d'un historian ou d'un export équivalent."""

    external_tag: str
    source_timestamp: datetime
    value: float
    source_unit: str
    quality: HistorianQuality
    source_ref: str
    server_timestamp: datetime | None = None
    sequence_number: int | None = None

    def __post_init__(self) -> None:
        if not self.external_tag.strip():
            raise ValueError("Le tag externe historian est obligatoire.")
        if self.source_timestamp.tzinfo is None:
            raise ValueError("Le SourceTimestamp historian doit être timezone-aware.")
        if self.server_timestamp is not None and self.server_timestamp.tzinfo is None:
            raise ValueError("Le ServerTimestamp historian doit être timezone-aware.")
        if not math.isfinite(self.value):
            raise ValueError("La valeur historian doit être numérique et finie.")
        if not self.source_unit.strip():
            raise ValueError("L'unité source historian est obligatoire.")
        if not self.source_ref.strip():
            raise ValueError("La provenance historian est obligatoire.")
        if self.sequence_number is not None and self.sequence_number < 0:
            raise ValueError("La séquence historian doit être positive ou nulle.")

    @property
    def source_timestamp_utc(self) -> datetime:
        return self.source_timestamp.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class HistorianBatch:
    """Lot de lecture conservant doublons et ordre source pour diagnostic."""

    window: HistorianQueryWindow
    records: tuple[HistorianRecord, ...]
    connector_ref: str

    def __post_init__(self) -> None:
        if not self.connector_ref.strip():
            raise ValueError("La référence du connecteur historian est obligatoire.")
        for record in self.records:
            timestamp = record.source_timestamp_utc
            if timestamp < self.window.start_utc or timestamp >= self.window.end_utc:
                raise ValueError("Un point historian est hors de la fenêtre demandée.")

    @property
    def bad_count(self) -> int:
        return sum(record.quality is HistorianQuality.BAD for record in self.records)

    @property
    def uncertain_count(self) -> int:
        return sum(record.quality is HistorianQuality.UNCERTAIN for record in self.records)

    @property
    def duplicate_count(self) -> int:
        seen: set[tuple[str, datetime, int | None]] = set()
        duplicates = 0
        for record in self.records:
            key = (record.external_tag, record.source_timestamp_utc, record.sequence_number)
            if key in seen:
                duplicates += 1
            else:
                seen.add(key)
        return duplicates

    @property
    def source_order_violation_count(self) -> int:
        violations = 0
        previous_by_tag: dict[str, datetime] = {}
        for record in self.records:
            timestamp = record.source_timestamp_utc
            previous = previous_by_tag.get(record.external_tag)
            if previous is not None and timestamp < previous:
                violations += 1
            previous_by_tag[record.external_tag] = timestamp
        return violations


def analytics_usable(record: HistorianRecord) -> bool:
    """Une valeur BAD reste archivable mais n'est pas utilisable analytiquement."""

    return record.quality is not HistorianQuality.BAD


__all__ = [
    "HistorianBatch",
    "HistorianQuality",
    "HistorianQueryWindow",
    "HistorianRecord",
    "analytics_usable",
]
