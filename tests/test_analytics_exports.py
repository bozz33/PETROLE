from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from hydro_api.services.analytics_exports import (
    export_analytics_buckets_csv,
    export_analytics_json,
)


def _payload() -> dict[str, object]:
    return {
        "tag_id": "11111111-1111-1111-1111-111111111111",
        "processing_version": "pilot-v1-a2",
        "si_unit": "Pa",
        "included_qualities": ["good", "uncertain"],
        "requested_start_timestamp": datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
        "requested_end_timestamp": datetime(2026, 8, 10, 9, 0, tzinfo=UTC),
        "source_start_timestamp": datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
        "source_end_timestamp": datetime(2026, 8, 10, 8, 59, tzinfo=UTC),
        "candidate_sample_count": 60,
        "included_sample_count": 58,
        "excluded_sample_count": 2,
        "bucket_seconds": 3600,
        "expected_interval_seconds": 60.0,
        "buckets": [
            {
                "start_timestamp": datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
                "end_timestamp": datetime(2026, 8, 10, 9, 0, tzinfo=UTC),
                "sample_count": 58,
                "minimum_value_si": 1_900_000.0,
                "maximum_value_si": 2_100_000.0,
                "mean_value_si": 2_000_000.0,
                "stddev_value_si": 50_000.0,
                "expected_sample_count": 60,
                "completeness_ratio": 58 / 60,
            }
        ],
        "trend": {
            "sample_count": 58,
            "slope_si_per_second": 1.0,
            "intercept_si": 1_900_000.0,
            "r_squared": 0.9,
            "start_timestamp": datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            "end_timestamp": datetime(2026, 8, 10, 8, 59, tzinfo=UTC),
        },
    }


def test_json_export_is_deterministic_and_hashed() -> None:
    first = export_analytics_json(_payload())
    second = export_analytics_json(_payload())

    assert first.content == second.content
    assert first.sha256 == hashlib.sha256(first.content).hexdigest()
    assert b'"export_version":"phase3-analytics/1.0"' in first.content
    assert b'"processing_version":"pilot-v1-a2"' in first.content


def test_csv_export_contains_exact_bucket_columns_and_hash() -> None:
    artifact = export_analytics_buckets_csv(_payload())
    decoded = artifact.content.decode("utf-8-sig")

    assert decoded.startswith("start_timestamp;end_timestamp;sample_count;")
    assert "2026-08-10T08:00:00+00:00" in decoded
    assert "2000000.0" in decoded
    assert artifact.sha256 == hashlib.sha256(artifact.content).hexdigest()
