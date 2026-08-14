from __future__ import annotations

import pytest

import hydro_gas


def _network() -> hydro_gas.SteadyGasNetwork:
    return hydro_gas.SteadyGasNetwork(
        nodes=tuple(
            hydro_gas.SteadyGasNode(node_id, f"model://node/{node_id}")
            for node_id in ("A", "B", "C")
        ),
        pipes=(hydro_gas.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),),
    )


def test_mixed_balance_keeps_pipe_and_compressor_contributions_separate() -> None:
    result = hydro_gas.assess_stationary_equipment_mass_balance(
        _network(),
        pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 3.0, "state://pipe/P1"),),
        compressor_edges=(
            hydro_gas.SteadyGasCompressorEdge("C1", "B", "C", "model://compressor/C1"),
        ),
        compressor_flows=(
            hydro_gas.GasCompressorMassFlow("C1", 3.0, "state://compressor/C1"),
        ),
        boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("SUPPLY-A", "A", 3.0, "boundary://supply/A"),
            hydro_gas.GasBoundaryMassFlow("DEMAND-C", "C", -3.0, "boundary://demand/C"),
        ),
    )

    by_node = {item.node_id: item for item in result.node_balances}
    assert by_node["A"].outgoing_pipe_mass_flow_kg_s == 3.0
    assert by_node["A"].outgoing_compressor_mass_flow_kg_s == 0.0
    assert by_node["B"].incoming_pipe_mass_flow_kg_s == 3.0
    assert by_node["B"].outgoing_compressor_mass_flow_kg_s == 3.0
    assert by_node["C"].incoming_compressor_mass_flow_kg_s == 3.0
    assert tuple(item.residual_kg_s for item in result.node_balances) == (0.0, 0.0, 0.0)
    assert result.global_residual_kg_s == 0.0
    assert result.max_abs_node_residual_kg_s == 0.0
    assert result.pipe_flow_source_refs == ("state://pipe/P1",)
    assert result.compressor_flow_source_refs == ("state://compressor/C1",)


def test_internal_pipe_and_compressor_transport_cancel_from_global_residual() -> None:
    result = hydro_gas.assess_stationary_equipment_mass_balance(
        _network(),
        pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 2.0, "state://pipe/P1"),),
        compressor_edges=(
            hydro_gas.SteadyGasCompressorEdge("C1", "B", "C", "model://compressor/C1"),
        ),
        compressor_flows=(
            hydro_gas.GasCompressorMassFlow("C1", 2.0, "state://compressor/C1"),
        ),
        boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("SUPPLY-A", "A", 2.5, "boundary://supply/A"),
            hydro_gas.GasBoundaryMassFlow("DEMAND-C", "C", -2.0, "boundary://demand/C"),
        ),
    )

    assert result.global_residual_kg_s == pytest.approx(0.5)
    assert sum(item.external_mass_flow_kg_s for item in result.node_balances) == pytest.approx(0.5)


def test_reverse_pipe_flow_remains_signed_while_compressor_flow_stays_directional() -> None:
    result = hydro_gas.assess_stationary_equipment_mass_balance(
        _network(),
        pipe_flows=(hydro_gas.GasPipeMassFlow("P1", -2.0, "state://pipe/P1-reverse"),),
        compressor_edges=(
            hydro_gas.SteadyGasCompressorEdge("C1", "A", "C", "model://compressor/C1"),
        ),
        compressor_flows=(
            hydro_gas.GasCompressorMassFlow("C1", 1.0, "state://compressor/C1"),
        ),
        boundary_flows=(
            hydro_gas.GasBoundaryMassFlow("SUPPLY-B", "B", 2.0, "boundary://supply/B"),
            hydro_gas.GasBoundaryMassFlow("SUPPLY-A", "A", 1.0, "boundary://supply/A"),
            hydro_gas.GasBoundaryMassFlow("DEMAND-C", "C", -1.0, "boundary://demand/C"),
            hydro_gas.GasBoundaryMassFlow("DEMAND-A", "A", -2.0, "boundary://demand/A"),
        ),
    )

    by_node = {item.node_id: item for item in result.node_balances}
    assert by_node["A"].incoming_pipe_mass_flow_kg_s == 2.0
    assert by_node["B"].outgoing_pipe_mass_flow_kg_s == 2.0
    assert by_node["A"].outgoing_compressor_mass_flow_kg_s == 1.0
    assert by_node["C"].incoming_compressor_mass_flow_kg_s == 1.0
    assert result.max_abs_node_residual_kg_s == 0.0


def test_compressor_flow_coverage_must_match_edges_exactly() -> None:
    edge = hydro_gas.SteadyGasCompressorEdge("C1", "B", "C", "model://compressor/C1")

    with pytest.raises(ValueError, match="couvrir exactement"):
        hydro_gas.assess_stationary_equipment_mass_balance(
            _network(),
            pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 3.0, "state://pipe/P1"),),
            compressor_edges=(edge,),
            compressor_flows=(),
        )

    with pytest.raises(ValueError, match="Un seul débit massique.*compresseur"):
        hydro_gas.assess_stationary_equipment_mass_balance(
            _network(),
            pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 3.0, "state://pipe/P1"),),
            compressor_edges=(edge,),
            compressor_flows=(
                hydro_gas.GasCompressorMassFlow("C1", 3.0, "state://compressor/C1/a"),
                hydro_gas.GasCompressorMassFlow("C1", 3.0, "state://compressor/C1/b"),
            ),
        )


def test_compressor_edges_must_reference_network_nodes_and_unique_ids() -> None:
    with pytest.raises(ValueError, match="deux noeuds présents"):
        hydro_gas.assess_stationary_equipment_mass_balance(
            _network(),
            pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 0.0, "state://pipe/P1"),),
            compressor_edges=(
                hydro_gas.SteadyGasCompressorEdge(
                    "C1", "B", "UNKNOWN", "model://compressor/C1"
                ),
            ),
            compressor_flows=(
                hydro_gas.GasCompressorMassFlow("C1", 0.0, "state://compressor/C1"),
            ),
        )

    with pytest.raises(ValueError, match="identifiants de compresseurs.*uniques"):
        hydro_gas.assess_stationary_equipment_mass_balance(
            _network(),
            pipe_flows=(hydro_gas.GasPipeMassFlow("P1", 0.0, "state://pipe/P1"),),
            compressor_edges=(
                hydro_gas.SteadyGasCompressorEdge("C1", "A", "C", "model://compressor/C1/a"),
                hydro_gas.SteadyGasCompressorEdge("C1", "B", "C", "model://compressor/C1/b"),
            ),
            compressor_flows=(
                hydro_gas.GasCompressorMassFlow("C1", 0.0, "state://compressor/C1"),
            ),
        )


def test_compressor_flow_is_nonnegative_in_documented_active_direction() -> None:
    with pytest.raises(ValueError, match="positif ou nul"):
        hydro_gas.GasCompressorMassFlow(
            compressor_id="C1",
            mass_flow_kg_s=-1.0,
            source_ref="state://compressor/C1/reverse",
        )
