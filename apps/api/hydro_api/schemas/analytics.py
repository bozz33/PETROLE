"""Contrats API de la Phase 3 — analytics temporels explicables."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from hydro_api.schemas.time_series import SampleQuality


class AnalyticsBucket(BaseModel):
    """Agrégat déterministe d'un bucket UTC sans modifier les échantillons source."""

    start_timestamp: datetime
    end_timestamp: datetime
    sample_count: int = Field(ge=0)
    minimum_value_si: float | None
    maximum_value_si: float | None
    mean_value_si: float | None
    stddev_value_si: float | None
    expected_sample_count: int | None = Field(default=None, ge=1)
    completeness_ratio: float | None = Field(default=None, ge=0.0, le=1.0)


class LinearTrend(BaseModel):
    """Régression linéaire descriptive, pas une prévision."""

    sample_count: int = Field(ge=0)
    slope_si_per_second: float | None
    intercept_si: float | None
    r_squared: float | None = Field(default=None, ge=0.0, le=1.0)
    start_timestamp: datetime | None
    end_timestamp: datetime | None


class TimeSeriesAnalyticsRead(BaseModel):
    """Vue d'analytics Phase 3 sur une projection SI versionnée."""

    tag_id: uuid.UUID
    processing_version: str
    si_unit: str
    included_qualities: list[SampleQuality]
    requested_start_timestamp: datetime | None
    requested_end_timestamp: datetime | None
    source_start_timestamp: datetime | None
    source_end_timestamp: datetime | None
    candidate_sample_count: int = Field(ge=0)
    included_sample_count: int = Field(ge=0)
    excluded_sample_count: int = Field(ge=0)
    bucket_seconds: int = Field(ge=1)
    expected_interval_seconds: float | None = Field(default=None, gt=0)
    buckets: list[AnalyticsBucket]
    trend: LinearTrend


__all__ = ["AnalyticsBucket", "LinearTrend", "TimeSeriesAnalyticsRead"]
