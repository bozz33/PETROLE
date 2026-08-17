from __future__ import annotations

import pytest

from hydro_gas import (
    CompressorFlowLimitPoint,
    CompressorOperatingEnvelope,
    assess_compressor_envelope,
)


def _envelope() -> CompressorOperatingEnvelope:
    return CompressorOperatingEnvelope(
        source_ref="vendor://compressor-C01/envelope",
        version="rev-C",
        points=(
            CompressorFlowLimitPoint(
                speed_rpm=8_000.0,
                minimum_mass_flow_kg_s=10.0,
                maximum_mass_flow_kg_s=30.0,
            ),
            CompressorFlowLimitPoint(
                speed_rpm=10_000.0,
                minimum_mass_flow_kg_s=12.0,
                maximum_mass_flow_kg_s=36.0,
            ),
        ),
    )


def test_compressor_envelope_interpolates_supplier_limits_without_hidden_margin() -> None:
    assessment = assess_compressor_envelope(
        _envelope(),
        speed_rpm=9_000.0,
        mass_flow_kg_s=20.0,
    )
    assert assessment.minimum_mass_flow_kg_s == pytest.approx(11.0)
    assert assessment.maximum_mass_flow_kg_s == pytest.approx(33.0)
    assert assessment.minimum_flow_margin_kg_s == pytest.approx(9.0)
    assert assessment.maximum_flow_margin_kg_s == pytest.approx(13.0)
    assert assessment.inside_envelope is True
    assert assessment.source_ref == "vendor://compressor-C01/envelope"


def test_compressor_envelope_reports_outside_domain_without_control_action() -> None:
    assessment = assess_compressor_envelope(
        _envelope(),
        speed_rpm=9_000.0,
        mass_flow_kg_s=9.0,
    )
    assert assessment.inside_envelope is False
    assert assessment.minimum_flow_margin_kg_s == pytest.approx(-2.0)


def test_compressor_envelope_refuses_speed_extrapolation() -> None:
    with pytest.raises(ValueError, match="hors du domaine"):
        assess_compressor_envelope(
            _envelope(),
            speed_rpm=11_000.0,
            mass_flow_kg_s=20.0,
        )
