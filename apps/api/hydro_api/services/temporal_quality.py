"""Diagnostics temporels et de mesure prévus par D15.

Les seuils de latence, stagnation et saut sont fournis explicitement par le
protocole métier. Le module ne corrige, ne réordonne et ne supprime aucun point.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from typing import Literal

SampleQuality = Literal["good", "uncertain", "bad", "substituted", "estimated"]
_ALLOWED_QUALITIES: frozenset[str] = frozenset(
    {"good", "uncertain", "bad", "substituted", "estimated"}
)


@dataclass(frozen=True, slots=True)
class TemporalQualitySample:
    """Point SI avec timestamps source/ingestion et qualité conservée."""

    source_timestamp: datetime
    ingest_timestamp: datetime
    value_si: float
    quality: SampleQuality

    def __post_init__(self) -> None:
        if self.source_timestamp.tzinfo is None or self.ingest_timestamp.tzinfo is None:
            raise ValueError("Les timestamps source et ingestion doivent être timezone-aware.")
        if not math.isfinite(self.value_si):
            raise ValueError("La valeur SI doit être finie.")
        if self.quality not in _ALLOWED_QUALITIES:
            raise ValueError("La qualité n'appartient pas au contrat PETROLE.")

    @property
    def source_timestamp_utc(self) -> datetime:
        return self.source_timestamp.astimezone(UTC)

    @property
    def ingest_timestamp_utc(self) -> datetime:
        return self.ingest_timestamp.astimezone(UTC)

    @property
    def latency_s(self) -> float:
        return (self.ingest_timestamp_utc - self.source_timestamp_utc).total_seconds()


@dataclass(frozen=True, slots=True)
class TemporalQualityPolicy:
    """Tolérances approuvées pour une campagne/site, sans valeurs par défaut."""

    maximum_latency_s: float | None
    stagnation_delta_tolerance_si: float | None
    stagnation_min_duration_s: float | None
    maximum_jump_si: float | None
    policy_ref: str

    def __post_init__(self) -> None:
        if not self.policy_ref.strip():
            raise ValueError("La référence de politique temporelle est obligatoire.")
        nonnegative = (
            self.maximum_latency_s,
            self.stagnation_delta_tolerance_si,
            self.stagnation_min_duration_s,
            self.maximum_jump_si,
        )
        if any(
            value is not None and (not math.isfinite(value) or value < 0) for value in nonnegative
        ):
            raise ValueError("Les seuils temporels doivent être finis et positifs ou nuls.")
        stagnation_fields = (
            self.stagnation_delta_tolerance_si,
            self.stagnation_min_duration_s,
        )
        if (stagnation_fields[0] is None) != (stagnation_fields[1] is None):
            raise ValueError("Tolérance et durée de stagnation doivent être fournies ensemble.")


@dataclass(frozen=True, slots=True)
class TemporalQualityAssessment:
    sample_count: int
    source_order_violation_count: int
    negative_latency_count: int
    mean_latency_s: float
    maximum_latency_s: float
    latency_violation_count: int | None
    quality_counts: dict[str, int]
    quality_fractions: dict[str, float]
    jump_count: int | None
    longest_stagnation_duration_s: float | None
    stagnation_detected: bool | None
    policy_ref: str


def _longest_stagnation_duration(
    ordered: tuple[TemporalQualitySample, ...],
    tolerance_si: float,
) -> float:
    """Mesure la plus longue suite où chaque variation consécutive reste <= tolérance."""

    if len(ordered) < 2:
        return 0.0
    longest = 0.0
    run_start = ordered[0].source_timestamp_utc
    previous = ordered[0]
    for current in ordered[1:]:
        if abs(current.value_si - previous.value_si) <= tolerance_si:
            duration = (current.source_timestamp_utc - run_start).total_seconds()
            longest = max(longest, duration)
        else:
            run_start = current.source_timestamp_utc
        previous = current
    return longest


def assess_temporal_quality(
    samples: tuple[TemporalQualitySample, ...],
    policy: TemporalQualityPolicy,
) -> TemporalQualityAssessment:
    """Calcule les indicateurs D15 sans modifier l'ordre source fourni."""

    if not samples:
        raise ValueError("L'évaluation temporelle exige au moins un échantillon.")

    order_violations = 0
    previous_source: datetime | None = None
    for sample in samples:
        current_source = sample.source_timestamp_utc
        if previous_source is not None and current_source < previous_source:
            order_violations += 1
        previous_source = current_source

    latencies = [sample.latency_s for sample in samples]
    negative_latency_count = sum(latency < 0 for latency in latencies)
    mean_latency = math.fsum(latencies) / len(latencies)
    maximum_latency = max(latencies)
    latency_violations = (
        sum(latency > policy.maximum_latency_s for latency in latencies)
        if policy.maximum_latency_s is not None
        else None
    )

    quality_counts = {quality: 0 for quality in sorted(_ALLOWED_QUALITIES)}
    for sample in samples:
        quality_counts[sample.quality] += 1
    quality_fractions = {quality: count / len(samples) for quality, count in quality_counts.items()}

    ordered = tuple(sorted(samples, key=lambda sample: sample.source_timestamp_utc))
    jump_count = None
    if policy.maximum_jump_si is not None:
        jump_count = sum(
            abs(current.value_si - previous.value_si) > policy.maximum_jump_si
            for previous, current in pairwise(ordered)
        )

    longest_stagnation: float | None = None
    stagnation_detected: bool | None = None
    if (
        policy.stagnation_delta_tolerance_si is not None
        and policy.stagnation_min_duration_s is not None
    ):
        longest_stagnation = _longest_stagnation_duration(
            ordered,
            policy.stagnation_delta_tolerance_si,
        )
        stagnation_detected = longest_stagnation >= policy.stagnation_min_duration_s

    return TemporalQualityAssessment(
        sample_count=len(samples),
        source_order_violation_count=order_violations,
        negative_latency_count=negative_latency_count,
        mean_latency_s=mean_latency,
        maximum_latency_s=maximum_latency,
        latency_violation_count=latency_violations,
        quality_counts=quality_counts,
        quality_fractions=quality_fractions,
        jump_count=jump_count,
        longest_stagnation_duration_s=longest_stagnation,
        stagnation_detected=stagnation_detected,
        policy_ref=policy.policy_ref,
    )


__all__ = [
    "TemporalQualityAssessment",
    "TemporalQualityPolicy",
    "TemporalQualitySample",
    "assess_temporal_quality",
]
