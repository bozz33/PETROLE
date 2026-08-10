"""Analytics déterministes de Phase 3 sur les séries SI versionnées.

Ce module reste strictement en lecture seule : il ne corrige, n'impute et ne
supprime aucun échantillon. Les agrégats décrivent une projection déjà créée
par le pipeline V1 et ne constituent pas un moteur de prévision.
"""

from __future__ import annotations

import math
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hydro_api.errors import ResourceConflictError
from hydro_api.models import SampleNormalized
from hydro_api.schemas.time_series import SampleQuality
from hydro_api.services.time_series import DEFAULT_ANALYSIS_QUALITIES, get_measurement_tag


def _normalize_boundary(timestamp: datetime | None) -> datetime | None:
    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        raise ResourceConflictError("Les bornes temporelles doivent inclure un fuseau horaire.")
    return timestamp.astimezone(UTC)


def _population_statistics(values: list[float]) -> tuple[float | None, float | None, float | None, float | None]:
    if not values:
        return None, None, None, None
    minimum = min(values)
    maximum = max(values)
    mean = math.fsum(values) / len(values)
    variance = math.fsum((value - mean) ** 2 for value in values) / len(values)
    return minimum, maximum, mean, math.sqrt(variance)


def _linear_trend(records: list[tuple[datetime, float]]) -> dict[str, Any]:
    if len(records) < 2:
        timestamp = records[0][0] if records else None
        return {
            "sample_count": len(records),
            "slope_si_per_second": None,
            "intercept_si": records[0][1] if records else None,
            "r_squared": None,
            "start_timestamp": timestamp,
            "end_timestamp": timestamp,
        }

    ordered = sorted(records, key=lambda item: item[0])
    origin = ordered[0][0]
    xs = [(timestamp - origin).total_seconds() for timestamp, _ in ordered]
    ys = [value for _, value in ordered]
    x_mean = math.fsum(xs) / len(xs)
    y_mean = math.fsum(ys) / len(ys)
    denominator = math.fsum((value - x_mean) ** 2 for value in xs)
    if math.isclose(denominator, 0.0, abs_tol=1e-15):
        return {
            "sample_count": len(ordered),
            "slope_si_per_second": None,
            "intercept_si": y_mean,
            "r_squared": None,
            "start_timestamp": ordered[0][0],
            "end_timestamp": ordered[-1][0],
        }

    slope = math.fsum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True)) / denominator
    intercept = y_mean - slope * x_mean
    predictions = [intercept + slope * x for x in xs]
    residual_sum_squares = math.fsum((y - prediction) ** 2 for y, prediction in zip(ys, predictions, strict=True))
    total_sum_squares = math.fsum((y - y_mean) ** 2 for y in ys)
    r_squared = (
        1.0
        if math.isclose(total_sum_squares, 0.0, abs_tol=1e-15)
        and math.isclose(residual_sum_squares, 0.0, abs_tol=1e-15)
        else None
        if math.isclose(total_sum_squares, 0.0, abs_tol=1e-15)
        else max(0.0, min(1.0, 1.0 - residual_sum_squares / total_sum_squares))
    )
    return {
        "sample_count": len(ordered),
        "slope_si_per_second": slope,
        "intercept_si": intercept,
        "r_squared": r_squared,
        "start_timestamp": ordered[0][0],
        "end_timestamp": ordered[-1][0],
    }


def analyze_time_series(
    session: Session,
    *,
    tag_id: uuid.UUID,
    processing_version: str,
    start_timestamp: datetime | None,
    end_timestamp: datetime | None,
    qualities: list[SampleQuality] | None,
    bucket_seconds: int,
    expected_interval_seconds: float | None,
) -> dict[str, Any]:
    """Agrège une série versionnée en buckets UTC et calcule une tendance descriptive."""

    if bucket_seconds <= 0:
        raise ResourceConflictError("La durée d'un bucket doit être strictement positive.")
    if expected_interval_seconds is not None and expected_interval_seconds <= 0:
        raise ResourceConflictError("L'intervalle attendu doit être strictement positif.")

    normalized_start = _normalize_boundary(start_timestamp)
    normalized_end = _normalize_boundary(end_timestamp)
    if normalized_start is not None and normalized_end is not None and normalized_start > normalized_end:
        raise ResourceConflictError("La borne de début doit précéder la borne de fin.")

    tag = get_measurement_tag(session, tag_id)
    filters = [
        SampleNormalized.tag_id == tag_id,
        SampleNormalized.processing_version == processing_version,
    ]
    if normalized_start is not None:
        filters.append(SampleNormalized.timestamp >= normalized_start)
    if normalized_end is not None:
        filters.append(SampleNormalized.timestamp <= normalized_end)

    candidate_records = [
        (timestamp.astimezone(UTC), float(value), str(quality))
        for timestamp, value, quality in session.execute(
            select(
                SampleNormalized.timestamp,
                SampleNormalized.value_si,
                SampleNormalized.quality,
            ).where(*filters)
        )
    ]
    included_qualities = list(dict.fromkeys(qualities or DEFAULT_ANALYSIS_QUALITIES))
    visible_records = [
        (timestamp, value)
        for timestamp, value, quality in candidate_records
        if quality in included_qualities
    ]
    visible_records.sort(key=lambda item: item[0])

    buckets: dict[int, list[tuple[datetime, float]]] = defaultdict(list)
    for timestamp, value in visible_records:
        bucket_index = math.floor(timestamp.timestamp() / bucket_seconds)
        buckets[bucket_index].append((timestamp, value))

    bucket_payloads: list[dict[str, Any]] = []
    expected_sample_count = (
        max(1, int(round(bucket_seconds / expected_interval_seconds)))
        if expected_interval_seconds is not None
        else None
    )
    for bucket_index in sorted(buckets):
        rows = buckets[bucket_index]
        values = [value for _, value in rows]
        minimum, maximum, mean, stddev = _population_statistics(values)
        bucket_start = datetime.fromtimestamp(bucket_index * bucket_seconds, tz=UTC)
        bucket_end = bucket_start + timedelta(seconds=bucket_seconds)
        completeness_ratio = None
        if expected_sample_count is not None:
            unique_timestamp_count = len({timestamp for timestamp, _ in rows})
            completeness_ratio = min(unique_timestamp_count / expected_sample_count, 1.0)
        bucket_payloads.append(
            {
                "start_timestamp": bucket_start,
                "end_timestamp": bucket_end,
                "sample_count": len(rows),
                "minimum_value_si": minimum,
                "maximum_value_si": maximum,
                "mean_value_si": mean,
                "stddev_value_si": stddev,
                "expected_sample_count": expected_sample_count,
                "completeness_ratio": completeness_ratio,
            }
        )

    return {
        "tag_id": tag.id,
        "processing_version": processing_version,
        "si_unit": tag.si_unit,
        "included_qualities": included_qualities,
        "requested_start_timestamp": normalized_start,
        "requested_end_timestamp": normalized_end,
        "source_start_timestamp": visible_records[0][0] if visible_records else None,
        "source_end_timestamp": visible_records[-1][0] if visible_records else None,
        "candidate_sample_count": len(candidate_records),
        "included_sample_count": len(visible_records),
        "excluded_sample_count": len(candidate_records) - len(visible_records),
        "bucket_seconds": bucket_seconds,
        "expected_interval_seconds": expected_interval_seconds,
        "buckets": bucket_payloads,
        "trend": _linear_trend(visible_records),
    }


__all__ = ["analyze_time_series"]
