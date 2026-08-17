from __future__ import annotations

import pytest

from hydro_gas import (
    GasBoundaryMassFlow,
    GasPipeMassFlow,
    SteadyGasNetwork,
    SteadyGasNode,
    SteadyGasPipe,
    assess_stationary_mass_balance,
)


def _network() -> SteadyGasNetwork:
    return SteadyGasNetwork(
        nodes=(
            SteadyGasNode(node_id="N-IN", source_ref="model://nodes/in"),
            SteadyGasNode(node_id="N-OUT", source_ref="model://nodes/out"),
        ),
        pipes=(
            SteadyGasPipe(
                pipe_id="P-001",
                from_node_id="N-IN",
                to_node_id="N-OUT",
                source_ref="model://pipes/P-001",
            ),
        ),
    )


def test_stationary_mass_balance_closes_for_injection_and_withdrawal() -> None:
    result = assess_stationary_mass_balance(
        _network(),
        pipe_flows=(
            GasPipeMassFlow(
                pipe_id="P-001",
                mass_flow_kg_s=5.0,
                source_ref="calc://steady/P-001",
            ),
        ),
        boundary_flows=(
            GasBoundaryMassFlow(
                boundary_id="B-IN",
                node_id="N-IN",
                mass_flow_kg_s=5.0,
                source_ref="input://station/injection",
            ),
            GasBoundaryMassFlow(
                boundary_id="B-OUT",
                node_id="N-OUT",
                mass_flow_kg_s=-5.0,
                source_ref="input://station/withdrawal",
            ),
        ),
    )

    assert result.global_residual_kg_s == pytest.approx(0.0)
    assert result.max_abs_node_residual_kg_s == pytest.approx(0.0)
    assert tuple(balance.residual_kg_s for balance in result.node_balances) == pytest.approx(
        (0.0, 0.0)
    )
    assert result.pipe_flow_source_refs == ("calc://steady/P-001",)
    assert result.boundary_source_refs == (
        "input://station/injection",
        "input://station/withdrawal",
    )


def test_stationary_mass_balance_handles_reverse_flow_without_reorienting_topology() -> None:
    result = assess_stationary_mass_balance(
        _network(),
        pipe_flows=(
            GasPipeMassFlow(
                pipe_id="P-001",
                mass_flow_kg_s=-3.0,
                source_ref="measurement://flow/P-001",
            ),
        ),
        boundary_flows=(
            GasBoundaryMassFlow(
                boundary_id="B-WITHDRAW-IN",
                node_id="N-IN",
                mass_flow_kg_s=-3.0,
                source_ref="input://withdrawal/in",
            ),
            GasBoundaryMassFlow(
                boundary_id="B-INJECT-OUT",
                node_id="N-OUT",
                mass_flow_kg_s=3.0,
                source_ref="input://injection/out",
            ),
        ),
    )

    inlet, outlet = result.node_balances
    assert inlet.incoming_mass_flow_kg_s == pytest.approx(3.0)
    assert inlet.outgoing_mass_flow_kg_s == pytest.approx(0.0)
    assert outlet.incoming_mass_flow_kg_s == pytest.approx(0.0)
    assert outlet.outgoing_mass_flow_kg_s == pytest.approx(3.0)
    assert result.max_abs_node_residual_kg_s == pytest.approx(0.0)


def test_stationary_mass_balance_rejects_incomplete_pipe_flow_set() -> None:
    with pytest.raises(ValueError, match="exactement"):
        assess_stationary_mass_balance(_network(), pipe_flows=())


def test_network_rejects_pipe_referencing_unknown_node() -> None:
    with pytest.raises(ValueError, match="deux noeuds"):
        SteadyGasNetwork(
            nodes=(SteadyGasNode(node_id="N-1", source_ref="model://nodes/1"),),
            pipes=(
                SteadyGasPipe(
                    pipe_id="P-1",
                    from_node_id="N-1",
                    to_node_id="N-UNKNOWN",
                    source_ref="model://pipes/1",
                ),
            ),
        )


def test_stationary_mass_balance_rejects_unknown_boundary_node() -> None:
    with pytest.raises(ValueError, match="frontière gaz"):
        assess_stationary_mass_balance(
            _network(),
            pipe_flows=(
                GasPipeMassFlow(
                    pipe_id="P-001",
                    mass_flow_kg_s=1.0,
                    source_ref="calc://steady/P-001",
                ),
            ),
            boundary_flows=(
                GasBoundaryMassFlow(
                    boundary_id="B-UNKNOWN",
                    node_id="N-UNKNOWN",
                    mass_flow_kg_s=1.0,
                    source_ref="input://unknown",
                ),
            ),
        )
