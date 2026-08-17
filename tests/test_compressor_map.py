from __future__ import annotations

import pytest

from hydro_gas import (
    CompressorMap,
    CompressorMapPoint,
    CompressorSpeedLine,
    interpolate_compressor_map,
)


def _map() -> CompressorMap:
    return CompressorMap(
        source_ref="supplier://compressor/demo-map",
        version="2026-08-test",
        speed_lines=(
            CompressorSpeedLine(
                speed_rpm=8_000.0,
                points=(
                    CompressorMapPoint(10.0, 1.50, 0.70),
                    CompressorMapPoint(20.0, 1.40, 0.76),
                ),
            ),
            CompressorSpeedLine(
                speed_rpm=10_000.0,
                points=(
                    CompressorMapPoint(10.0, 1.80, 0.72),
                    CompressorMapPoint(20.0, 1.65, 0.80),
                ),
            ),
        ),
    )


def test_map_interpolates_inside_supplied_domain() -> None:
    point = interpolate_compressor_map(_map(), speed_rpm=9_000.0, mass_flow_kg_s=15.0)
    assert point.pressure_ratio == pytest.approx(1.5875)
    assert point.isentropic_efficiency == pytest.approx(0.745)
    assert point.source_ref == "supplier://compressor/demo-map"
    assert point.map_version == "2026-08-test"


def test_map_rejects_speed_and_flow_extrapolation() -> None:
    with pytest.raises(ValueError, match="vitesse demandée"):
        interpolate_compressor_map(_map(), speed_rpm=11_000.0, mass_flow_kg_s=15.0)
    with pytest.raises(ValueError, match="débit demandé"):
        interpolate_compressor_map(_map(), speed_rpm=9_000.0, mass_flow_kg_s=25.0)


def test_speed_line_requires_strictly_increasing_flow() -> None:
    with pytest.raises(ValueError, match="strictement croissants"):
        CompressorSpeedLine(
            speed_rpm=8_000.0,
            points=(
                CompressorMapPoint(20.0, 1.4, 0.75),
                CompressorMapPoint(10.0, 1.5, 0.70),
            ),
        )
