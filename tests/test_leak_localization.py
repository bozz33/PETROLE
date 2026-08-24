from __future__ import annotations

import pytest

from hydro_leak import LeakLocationEstimate


def test_leak_location_requires_estimate_inside_explicit_uncertainty_interval() -> None:
    estimate = LeakLocationEstimate(
        pipeline_ref="pipeline://line-A",
        pipeline_length_m=100_000.0,
        estimated_chainage_m=42_500.0,
        lower_chainage_m=41_000.0,
        upper_chainage_m=44_000.0,
        method_ref="method://localization/research-v1",
        model_version="twin-v17",
        evidence_ref="evidence://leak-campaign/run-42",
    )

    assert estimate.uncertainty_width_m == pytest.approx(3_000.0)
    assert estimate.lower_margin_m == pytest.approx(1_500.0)
    assert estimate.upper_margin_m == pytest.approx(1_500.0)


def test_leak_location_rejects_interval_outside_pipeline() -> None:
    with pytest.raises(ValueError, match="dans la conduite"):
        LeakLocationEstimate(
            pipeline_ref="pipeline://line-A",
            pipeline_length_m=100_000.0,
            estimated_chainage_m=99_000.0,
            lower_chainage_m=98_000.0,
            upper_chainage_m=101_000.0,
            method_ref="method://localization/research-v1",
            model_version="twin-v17",
            evidence_ref="evidence://leak-campaign/run-42",
        )


def test_leak_location_rejects_estimate_outside_its_interval() -> None:
    with pytest.raises(ValueError, match="appartenir"):
        LeakLocationEstimate(
            pipeline_ref="pipeline://line-A",
            pipeline_length_m=100_000.0,
            estimated_chainage_m=50_000.0,
            lower_chainage_m=40_000.0,
            upper_chainage_m=45_000.0,
            method_ref="method://localization/research-v1",
            model_version="twin-v17",
            evidence_ref="evidence://leak-campaign/run-42",
        )
