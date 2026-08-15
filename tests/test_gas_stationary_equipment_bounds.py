from __future__ import annotations

import math

import pytest

from hydro_gas.compressor_limits import (
    CompressorFlowLimitPoint,
    CompressorOperatingEnvelope,
    compressor_envelope_flow_limits_at_speed,
)
from hydro_gas.compressor_map import (
    CompressorMap,
    CompressorMapPoint,
    CompressorSpeedLine,
    compressor_map_flow_domain_at_speed,
    interpolate_compressor_map,
)
from hydro_gas.network_balance import GasBoundaryMassFlow, SteadyGasNetwork, SteadyGasNode
from hydro_gas.stationary_equipment_balance import SteadyGasCompressorEdge
from hydro_gas.stationary_equipment_bounds import (
    build_stationary_active_compressor_numerical_bounds,
)
from hydro_gas.stationary_equipment_numerics import StationaryActiveCompressorNumericalScale
from hydro_gas.stationary_equipment_problem import (
    StationaryActiveCompressorProblem,
    StationaryCompressorSpeedControl,
    build_stationary_active_compressor_unknown_layout,
)
from hydro_gas.stationary_equipment_residual import StationaryCompressorMapBinding
from hydro_gas.stationary_problem import GasPressureSlack


def _map() -> CompressorMap:
    return CompressorMap(
        source_ref="supplier://synthetic-domain-map",
        version="test-v1",
        speed_lines=(
            CompressorSpeedLine(
                speed_rpm=1000.0,
                points=(
                    CompressorMapPoint(1.0, 1.4, 0.8),
                    CompressorMapPoint(3.0, 1.3, 0.82),
                ),
            ),
            CompressorSpeedLine(
                speed_rpm=2000.0,
                points=(
                    CompressorMapPoint(2.0, 1.8, 0.78),
                    CompressorMapPoint(4.0, 1.6, 0.8),
                ),
            ),
        ),
    )


def _envelope() -> CompressorOperatingEnvelope:
    return CompressorOperatingEnvelope(
        source_ref="supplier://synthetic-envelope",
        version="test-v1",
        points=(
            CompressorFlowLimitPoint(1000.0, 1.5, 2.5),
            CompressorFlowLimitPoint(2000.0, 2.5, 3.5),
        ),
    )


def test_map_flow_domain_uses_exact_line_or_intersection_without_extrapolation() -> None:
    exact = compressor_map_flow_domain_at_speed(_map(), speed_rpm=1000.0)
    assert exact.minimum_mass_flow_kg_s == 1.0
    assert exact.maximum_mass_flow_kg_s == 3.0

    between = compressor_map_flow_domain_at_speed(_map(), speed_rpm=1500.0)
    assert between.minimum_mass_flow_kg_s == 2.0
    assert between.maximum_mass_flow_kg_s == 3.0

    point = interpolate_compressor_map(_map(), speed_rpm=1000.0, mass_flow_kg_s=1.5)
    assert point.mass_flow_kg_s == 1.5

    with pytest.raises(ValueError, match="hors du domaine"):
        interpolate_compressor_map(_map(), speed_rpm=1500.0, mass_flow_kg_s=1.5)


def test_envelope_limits_are_interpolated_without_hidden_margin() -> None:
    limits = compressor_envelope_flow_limits_at_speed(_envelope(), speed_rpm=1500.0)
    assert limits.minimum_mass_flow_kg_s == 2.0
    assert limits.maximum_mass_flow_kg_s == 3.0


def test_mixed_bounds_use_map_envelope_intersection_at_fixed_speed() -> None:
    problem = StationaryActiveCompressorProblem(
        problem_ref="problem://mixed/bounds-test",
        network=SteadyGasNetwork(
            nodes=(
                SteadyGasNode("A", "model://node/A"),
                SteadyGasNode("B", "model://node/B"),
            ),
            pipes=(),
        ),
        compressor_edges=(
            SteadyGasCompressorEdge("C1", "A", "B", "model://compressor/C1"),
        ),
        pressure_slacks=(GasPressureSlack("A", 2_000_000.0, "boundary://pressure/A"),),
        compressor_speed_controls=(
            StationaryCompressorSpeedControl("C1", 1000.0, "control://speed/C1"),
        ),
        map_bindings=(
            StationaryCompressorMapBinding(
                compressor_id="C1",
                compressor_map=_map(),
                source_ref="binding://map/C1",
                envelope=_envelope(),
            ),
        ),
        specified_boundary_flows=(
            GasBoundaryMassFlow("DEMAND-B", "B", -1.0, "boundary://demand/B"),
        ),
    )
    layout = build_stationary_active_compressor_unknown_layout(problem)
    scale = StationaryActiveCompressorNumericalScale(
        pressure_squared_scale_pa2=1.0e12,
        mass_flow_scale_kg_s=0.5,
        mass_residual_scale_kg_s=1.0,
        pipe_residual_scale_pa2=1.0e12,
        compressor_residual_scale_pa=1.0e6,
        source_ref="scale://synthetic/bounds-test",
    )

    bounds = build_stationary_active_compressor_numerical_bounds(
        problem,
        layout,
        scale,
        source_ref="bounds://mixed/test",
    )

    assert layout.unknown_count == 3
    assert bounds.lower_values == (0.0, 3.0, -math.inf)
    assert bounds.upper_values == (math.inf, 5.0, math.inf)
    physical = bounds.compressor_flow_bounds[0]
    assert physical.minimum_mass_flow_kg_s == 1.5
    assert physical.maximum_mass_flow_kg_s == 2.5
    assert physical.envelope_source_ref == "supplier://synthetic-envelope"
