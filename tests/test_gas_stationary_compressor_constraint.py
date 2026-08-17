from __future__ import annotations

import pytest

import hydro_gas


def _map() -> hydro_gas.CompressorMap:
    return hydro_gas.CompressorMap(
        source_ref="supplier://compressor/map/rev-A",
        version="rev-A",
        speed_lines=(
            hydro_gas.CompressorSpeedLine(
                speed_rpm=10_000.0,
                points=(
                    hydro_gas.CompressorMapPoint(2.0, 1.5, 0.78),
                    hydro_gas.CompressorMapPoint(4.0, 1.3, 0.82),
                ),
            ),
        ),
    )


def _envelope() -> hydro_gas.CompressorOperatingEnvelope:
    return hydro_gas.CompressorOperatingEnvelope(
        source_ref="supplier://compressor/envelope/rev-A",
        version="rev-A",
        points=(
            hydro_gas.CompressorFlowLimitPoint(
                speed_rpm=10_000.0,
                minimum_mass_flow_kg_s=1.5,
                maximum_mass_flow_kg_s=4.5,
            ),
        ),
    )


def test_compressor_constraint_uses_supplier_pressure_ratio_without_hidden_tolerance() -> None:
    state = hydro_gas.StationaryCompressorState(
        compressor_id="C1",
        inlet_pressure_pa=5_000_000.0,
        outlet_pressure_pa=6_900_000.0,
        mass_flow_kg_s=3.0,
        speed_rpm=10_000.0,
        source_ref="state://compressor/C1/001",
    )

    assessment = hydro_gas.evaluate_stationary_compressor_map_constraint(
        _map(),
        state,
        envelope=_envelope(),
    )

    assert assessment.operating_point.pressure_ratio == pytest.approx(1.4)
    assert assessment.operating_point.isentropic_efficiency == pytest.approx(0.80)
    assert assessment.expected_outlet_pressure_pa == pytest.approx(7_000_000.0)
    assert assessment.pressure_ratio_residual_pa == pytest.approx(-100_000.0)
    assert assessment.envelope_assessment is not None
    assert assessment.envelope_assessment.inside_envelope is True
    assert assessment.operating_point.source_ref == "supplier://compressor/map/rev-A"
    assert assessment.state_source_ref == "state://compressor/C1/001"
    assert not hasattr(assessment, "passed")


def test_exact_supplier_ratio_produces_zero_raw_pressure_residual() -> None:
    state = hydro_gas.StationaryCompressorState(
        compressor_id="C1",
        inlet_pressure_pa=5_000_000.0,
        outlet_pressure_pa=7_000_000.0,
        mass_flow_kg_s=3.0,
        speed_rpm=10_000.0,
        source_ref="state://compressor/C1/exact",
    )

    assessment = hydro_gas.evaluate_stationary_compressor_map_constraint(_map(), state)

    assert assessment.pressure_ratio_residual_pa == pytest.approx(0.0)
    assert assessment.envelope_assessment is None


def test_compressor_constraint_refuses_map_extrapolation() -> None:
    outside_map = hydro_gas.StationaryCompressorState(
        compressor_id="C1",
        inlet_pressure_pa=5_000_000.0,
        outlet_pressure_pa=7_000_000.0,
        mass_flow_kg_s=5.0,
        speed_rpm=10_000.0,
        source_ref="state://compressor/C1/outside-map",
    )

    with pytest.raises(ValueError, match="hors du domaine"):
        hydro_gas.evaluate_stationary_compressor_map_constraint(_map(), outside_map)


def test_compressor_state_rejects_reverse_or_zero_flow_in_active_compression_mode() -> None:
    with pytest.raises(ValueError, match="finis et positifs"):
        hydro_gas.StationaryCompressorState(
            compressor_id="C1",
            inlet_pressure_pa=5_000_000.0,
            outlet_pressure_pa=7_000_000.0,
            mass_flow_kg_s=-3.0,
            speed_rpm=10_000.0,
            source_ref="state://compressor/C1/reverse",
        )


def test_envelope_is_assessed_separately_from_pressure_ratio_residual() -> None:
    state = hydro_gas.StationaryCompressorState(
        compressor_id="C1",
        inlet_pressure_pa=5_000_000.0,
        outlet_pressure_pa=7_500_000.0,
        mass_flow_kg_s=2.0,
        speed_rpm=10_000.0,
        source_ref="state://compressor/C1/envelope",
    )

    assessment = hydro_gas.evaluate_stationary_compressor_map_constraint(
        _map(),
        state,
        envelope=_envelope(),
    )

    assert assessment.operating_point.pressure_ratio == pytest.approx(1.5)
    assert assessment.pressure_ratio_residual_pa == pytest.approx(0.0)
    assert assessment.envelope_assessment is not None
    assert assessment.envelope_assessment.minimum_flow_margin_kg_s == pytest.approx(0.5)
    assert assessment.envelope_assessment.maximum_flow_margin_kg_s == pytest.approx(2.5)
