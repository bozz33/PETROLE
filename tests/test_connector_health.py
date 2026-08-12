from __future__ import annotations

import pytest

from hydro_api.industrial.connector_health import (
    ConnectorHealthEvidence,
    ConnectorHealthObjectives,
    assess_connector_health,
)


def _objectives() -> ConnectorHealthObjectives:
    return ConnectorHealthObjectives(
        maximum_source_age_s=5.0,
        maximum_gap_count=2,
        maximum_bad_quality_fraction=0.05,
        maximum_reconnect_count=1,
    )


def test_connector_health_passes_when_site_objectives_are_met() -> None:
    assessment = assess_connector_health(
        _objectives(),
        ConnectorHealthEvidence(
            source_age_s=1.2,
            gap_count=0,
            sample_count=100,
            bad_quality_count=2,
            reconnect_count=0,
        ),
    )
    assert assessment.healthy is True
    assert assessment.bad_quality_fraction == pytest.approx(0.02)
    assert assessment.violations == ()


def test_connector_health_exposes_each_failed_objective() -> None:
    assessment = assess_connector_health(
        _objectives(),
        ConnectorHealthEvidence(
            source_age_s=8.0,
            gap_count=3,
            sample_count=20,
            bad_quality_count=2,
            reconnect_count=4,
        ),
    )
    assert assessment.healthy is False
    assert assessment.violations == (
        "source_age_above_objective",
        "sequence_gaps_above_objective",
        "bad_quality_fraction_above_objective",
        "reconnect_count_above_objective",
    )


def test_connector_health_rejects_impossible_bad_count() -> None:
    with pytest.raises(ValueError, match="ne peut pas dépasser"):
        ConnectorHealthEvidence(
            source_age_s=0.0,
            gap_count=0,
            sample_count=2,
            bad_quality_count=3,
            reconnect_count=0,
        )
