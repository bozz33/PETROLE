"""Tests du rapport V1 RPT-07 qualité des données."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO

import pytest
from pypdf import PdfReader

from hydro_reporting import DataQualityReportData, build_data_quality_report_pdf


def _data() -> DataQualityReportData:
    return DataQualityReportData(
        tag_id="11111111-1111-1111-1111-111111111111",
        tag_name="Pression refoulement",
        external_name="PT-401",
        processing_version="pilot-v1-a3",
        generated_at=datetime(2026, 8, 10, 6, 0, tzinfo=UTC),
        start_timestamp=datetime(2026, 8, 9, 10, 0, tzinfo=UTC),
        end_timestamp=datetime(2026, 8, 9, 11, 0, tzinfo=UTC),
        si_unit="Pa",
        candidate_sample_count=60,
        included_sample_count=58,
        excluded_sample_count=2,
        quality_counts={"good": 57, "uncertain": 1, "bad": 2},
        minimum_value_si=900_000.0,
        maximum_value_si=1_200_000.0,
        mean_value_si=1_050_000.0,
        stddev_value_si=42_000.0,
        duplicate_timestamp_count=1,
        out_of_order_count=0,
        gap_count=2,
        observed_interval_seconds=60.0,
        reference_interval_seconds=60.0,
        outlier_method="iqr",
        outlier_threshold=1.5,
        outlier_count=1,
        issues=({"code": "DQ-008", "message": "2 mesures bad exclues des statistiques"},),
        included_qualities=("good", "uncertain"),
        metadata={"Site": "SITE-A"},
    )


def test_rpt07_pdf_is_deterministic_and_contains_quality_diagnostics() -> None:
    first = build_data_quality_report_pdf(_data())
    second = build_data_quality_report_pdf(_data())
    assert first == second
    assert first.startswith(b"%PDF")

    reader = PdfReader(BytesIO(first))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "RPT-07" in text
    assert "Qualité des données" in text
    assert "PT-401" in text
    assert "pilot-v1-a3" in text
    assert "DQ-008" in text
    assert "Aberrants signalés" in text


def test_rpt07_refuses_inconsistent_counts() -> None:
    payload = _data().__dict__ if hasattr(_data(), "__dict__") else None
    assert payload is None  # dataclass slots: aucune mutation accidentelle possible
    with pytest.raises(ValueError, match="reconstituer"):
        DataQualityReportData(
            tag_id="tag",
            tag_name="Tag",
            external_name="PT-X",
            processing_version="v1",
            generated_at=datetime.now(UTC),
            start_timestamp=None,
            end_timestamp=None,
            si_unit="Pa",
            candidate_sample_count=10,
            included_sample_count=9,
            excluded_sample_count=2,
            quality_counts={},
            minimum_value_si=None,
            maximum_value_si=None,
            mean_value_si=None,
            stddev_value_si=None,
            duplicate_timestamp_count=0,
            out_of_order_count=0,
            gap_count=0,
            observed_interval_seconds=None,
            reference_interval_seconds=None,
            outlier_method="none",
            outlier_threshold=None,
            outlier_count=0,
        )
