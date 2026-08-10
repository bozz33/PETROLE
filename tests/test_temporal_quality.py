from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hydro_api.services.temporal_quality import (
    SampleQuality,
    TemporalQualityPolicy,
    TemporalQualitySample,
    assess_temporal_quality,
)

_BASE = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)


def _sample(
    minute: int,
    value: float,
    *,
    latency_s: float = 2.0,
    quality: SampleQuality = "good",
) -> TemporalQualitySample:
    source = _BASE + timedelta(minutes=minute)
    return TemporalQualitySample(
        source_timestamp=source,
        ingest_timestamp=source + timedelta(seconds=latency_s),
        value_si=value,
        quality=quality,
    )


def test_temporal_quality_reports_latency_quality_stagnation_and_jumps() -> None:
    policy = TemporalQualityPolicy(
        maximum_latency_s=5.0,
        stagnation_delta_tolerance_si=0.1,
        stagnation_min_duration_s=120.0,
        maximum_jump_si=5.0,
        policy_ref="policy://site-A/PT-101/v2",
    )
    result = assess_temporal_quality(
        (
            _sample(0, 100.0),
            _sample(1, 100.05, quality="uncertain"),
            _sample(2, 100.08),
            _sample(3, 120.0, latency_s=8.0, quality="bad"),
        ),
        policy,
    )

    assert result.sample_count == 4
    assert result.mean_latency_s == pytest.approx(3.5)
    assert result.maximum_latency_s == pytest.approx(8.0)
    assert result.latency_violation_count == 1
    assert result.quality_counts["good"] == 2
    assert result.quality_counts["uncertain"] == 1
    assert result.quality_counts["bad"] == 1
    assert result.jump_count == 1
    assert result.longest_stagnation_duration_s == pytest.approx(120.0)
    assert result.stagnation_detected is True


def test_temporal_quality_counts_source_order_and_negative_latency_without_reordering_input() -> (
    None
):
    first = _sample(2, 100.0)
    second = _sample(1, 101.0, latency_s=-1.0)
    result = assess_temporal_quality(
        (first, second),
        TemporalQualityPolicy(
            maximum_latency_s=None,
            stagnation_delta_tolerance_si=None,
            stagnation_min_duration_s=None,
            maximum_jump_si=None,
            policy_ref="policy://diagnostic-only/v1",
        ),
    )

    assert result.source_order_violation_count == 1
    assert result.negative_latency_count == 1
    assert result.latency_violation_count is None
    assert result.jump_count is None
    assert result.stagnation_detected is None


def test_stagnation_configuration_must_be_complete() -> None:
    with pytest.raises(ValueError, match="fournies ensemble"):
        TemporalQualityPolicy(
            maximum_latency_s=None,
            stagnation_delta_tolerance_si=0.1,
            stagnation_min_duration_s=None,
            maximum_jump_si=None,
            policy_ref="policy://invalid",
        )
