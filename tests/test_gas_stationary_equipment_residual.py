from __future__ import annotations

import pytest

import hydro_gas
from hydro_gas.stationary_equipment_residual import (
    StationaryCompressorMapBinding,
    StationaryCompressorOperatingInput,
    assemble_stationary_equipment_residuals,
)


def _network() -> hydro_gas.SteadyGasNetwork:
    return hydro_gas.SteadyGasNetwork(
        nodes=tuple(
            hydro_gas.SteadyGasNode(node_id, f"model://node/{node_id}")
            for node_id in ("A", "B", "C")
        ),
        pipes=(hydro_gas.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),),
    )


def _compressor_map() -> hydro_gas.CompressorMap:
    return hydro_gas.CompressorMap(
        source_ref="vendor://compressor/C1/map",
        version="test-v1",
        speed_lines=(
            hydro_gas.CompressorSpeedLine(
                speed_rpm=10_000.0,
                points=(
                    hydro_gas.CompressorMapPoint(2.0, 1.25, 0.80),
                    hydro_gas.CompressorMapPoint(4.0, 1.25, 0.78),
                ),
            ),
        ),
    )


def _edges() -> tuple[hydro_gas.SteadyGasCompressorEdge, ...]:
    return (hydro_gas.SteadyGasCompressorEdge("C1", "B", "C", "model://compressor/C1"),)


def _inputs() -> tuple[StationaryCompressorOperatingInput, ...]:
    return (
        StationaryCompressorOperatingInput(
            compressor_id="C1",
            mass_flow_kg_s=3.0,
            speed_rpm=10_000.0,
            source_ref="state://compressor/C1",
        ),
    )


def _bindings() -> tuple[StationaryCompressorMapBinding, ...]:
    return (
        StationaryCompressorMapBinding(
            compressor_id="C1",
            compressor_map=_compressor_map(),
            source_ref="binding://compressor/C1/map",
        ),
    )


def _pressures(outlet_pressure_pa: float = 6_000_000.0) -> tuple[hydro_gas.GasNodePressure, ...]:
    return (
        hydro_gas.GasNodePressure("A", 5_000_000.0, "state://pressure/A"),
        hydro_gas.GasNodePressure("B", 4_800_000.0, "state://pressure/B"),
        hydro_gas.GasNodePressure("C", outlet_pressure_pa, "state://pressure/C"),
    )


def test_mixed_assembly_combines_mass_balance_and_vendor_map_residual() -> None:
    result = assemble_stationary_equipment_residuals(
        _network(),
        pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 3.0, "state://pipe/P1"),),
        compressor_edges=_edges(),
        compressor_inputs=_inputs(),
        node_pressures=_pressures(),
        map_bindings=_bindings(),
        boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("SUPPLY-A", "A", 3.0, "boundary://supply/A"),
            hydro_gas.GasBoundaryMassFlow("DEMAND-C", "C", -3.0, "boundary://demand/C"),
        ),
    )

    assert result.mass_balance.max_abs_node_residual_kg_s == 0.0
    assert result.mass_balance.global_residual_kg_s == 0.0
    assert len(result.compressor_constraints) == 1
    constraint = result.compressor_constraints[0]
    assert constraint.compressor_id == "C1"
    assert constraint.operating_point.pressure_ratio == pytest.approx(1.25)
    assert constraint.expected_outlet_pressure_pa == pytest.approx(6_000_000.0)
    assert constraint.pressure_ratio_residual_pa == pytest.approx(0.0)
    assert not hasattr(result, "passed")


def test_mixed_assembly_preserves_nonzero_compressor_residual_without_pass_fail() -> None:
    result = assemble_stationary_equipment_residuals(
        _network(),
        pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 3.0, "state://pipe/P1"),),
        compressor_edges=_edges(),
        compressor_inputs=_inputs(),
        node_pressures=_pressures(outlet_pressure_pa=5_900_000.0),
        map_bindings=_bindings(),
        boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("SUPPLY-A", "A", 3.0, "boundary://supply/A"),
            hydro_gas.GasBoundaryMassFlow("DEMAND-C", "C", -3.0, "boundary://demand/C"),
        ),
    )

    constraint = result.compressor_constraints[0]
    assert constraint.pressure_ratio_residual_pa == pytest.approx(-100_000.0)
    assert not hasattr(constraint, "passed")


def test_mixed_assembly_requires_exact_pressure_input_and_binding_coverage() -> None:
    with pytest.raises(ValueError, match="pressions doivent couvrir exactement"):
        assemble_stationary_equipment_residuals(
            _network(),
            pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 3.0, "state://pipe/P1"),),
            compressor_edges=_edges(),
            compressor_inputs=_inputs(),
            node_pressures=_pressures()[:-1],
            map_bindings=_bindings(),
        )

    with pytest.raises(ValueError, match="bindings de cartes doivent couvrir exactement"):
        assemble_stationary_equipment_residuals(
            _network(),
            pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 3.0, "state://pipe/P1"),),
            compressor_edges=_edges(),
            compressor_inputs=_inputs(),
            node_pressures=_pressures(),
            map_bindings=(),
        )


def test_active_compressor_input_rejects_zero_or_negative_operating_values() -> None:
    with pytest.raises(ValueError, match="finis et positifs"):
        StationaryCompressorOperatingInput(
            compressor_id="C1",
            mass_flow_kg_s=0.0,
            speed_rpm=10_000.0,
            source_ref="state://compressor/C1/off",
        )

    with pytest.raises(ValueError, match="finis et positifs"):
        StationaryCompressorOperatingInput(
            compressor_id="C1",
            mass_flow_kg_s=3.0,
            speed_rpm=-1.0,
            source_ref="state://compressor/C1/invalid-speed",
        )
