from __future__ import annotations

import pytest

import hydro_gas.network_balance as network_balance
import hydro_gas.weymouth_network_residual as weymouth_network_residual
import hydro_gas.weymouth_si as weymouth_si


_EQUATION_REF = "reference://weymouth/validated-formulation"
_PARAMETER_SOURCE = "reference://parameters/case-simple"


def _network() -> network_balance.SteadyGasNetwork:
    return network_balance.SteadyGasNetwork(
        nodes=(
            network_balance.SteadyGasNode("A", "model://node/A"),
            network_balance.SteadyGasNode("B", "model://node/B"),
        ),
        pipes=(network_balance.SteadyGasPipe("P1", "A", "B", "model://pipe/P1"),),
    )


def _parameters(pipe_id: str = "P1") -> weymouth_si.WeymouthSiPipeParameters:
    return weymouth_si.WeymouthSiPipeParameters(
        pipe_id=pipe_id,
        length_m=1_000.0,
        diameter_m=0.5,
        friction_factor=0.01,
        sound_speed_m_s=350.0,
        equation_ref=_EQUATION_REF,
        parameter_source_ref=_PARAMETER_SOURCE,
    )


def _candidate(
    *, flow_kg_s: float = 5.0
) -> weymouth_network_residual.WeymouthNetworkCandidateState:
    return weymouth_network_residual.WeymouthNetworkCandidateState(
        candidate_ref="candidate://simple-network/state-001",
        node_pressures=(
            weymouth_network_residual.GasNodePressure("A", 5_000_000.0, "candidate://pressure/A"),
            weymouth_network_residual.GasNodePressure("B", 4_900_000.0, "candidate://pressure/B"),
        ),
        pipe_flows=(network_balance.GasPipeMassFlow("P1", flow_kg_s, "candidate://flow/P1"),),
        boundary_flows=(
            network_balance.GasBoundaryMassFlow("IN", "A", flow_kg_s, "candidate://boundary/IN"),
            network_balance.GasBoundaryMassFlow("OUT", "B", -flow_kg_s, "candidate://boundary/OUT"),
        ),
    )


def test_network_residual_assembly_preserves_separate_physical_residuals() -> None:
    parameters = _parameters()
    candidate = _candidate()

    result = weymouth_network_residual.assemble_weymouth_network_residuals(
        _network(),
        candidate,
        (parameters,),
    )

    assert result.candidate_ref == candidate.candidate_ref
    assert tuple(item.residual_kg_s for item in result.mass_balance.node_balances) == (0.0, 0.0)
    assert result.mass_balance.global_residual_kg_s == 0.0

    residual = result.pipe_residuals[0]
    expected_pressure_term = 4_900_000.0**2 - 5_000_000.0**2
    expected_friction_term = parameters.resistance_coefficient_pa2_per_kg_s2 * 5.0 * 5.0
    assert residual.pressure_squared_difference_pa2 == expected_pressure_term
    assert residual.friction_term_pa2 == expected_friction_term
    assert residual.residual_pa2 == expected_pressure_term + expected_friction_term
    assert not hasattr(residual, "passed")


def test_network_residual_assembly_preserves_provenance() -> None:
    result = weymouth_network_residual.assemble_weymouth_network_residuals(
        _network(),
        _candidate(),
        (_parameters(),),
    )

    assert result.node_pressure_source_refs == (
        "candidate://pressure/A",
        "candidate://pressure/B",
    )
    assert result.pipe_flow_source_refs == ("candidate://flow/P1",)
    assert result.boundary_source_refs == (
        "candidate://boundary/IN",
        "candidate://boundary/OUT",
    )
    assert result.pipe_residuals[0].observation_source_ref == "candidate://simple-network/state-001"


def test_network_residual_assembly_keeps_reverse_flow_sign() -> None:
    network = _network()
    parameters = _parameters()
    candidate = weymouth_network_residual.WeymouthNetworkCandidateState(
        candidate_ref="candidate://reverse/state-001",
        node_pressures=(
            weymouth_network_residual.GasNodePressure(
                "A", 4_900_000.0, "candidate://reverse/pressure/A"
            ),
            weymouth_network_residual.GasNodePressure(
                "B", 5_000_000.0, "candidate://reverse/pressure/B"
            ),
        ),
        pipe_flows=(network_balance.GasPipeMassFlow("P1", -5.0, "candidate://reverse/flow/P1"),),
        boundary_flows=(
            network_balance.GasBoundaryMassFlow(
                "OUT-A", "A", -5.0, "candidate://reverse/boundary/OUT-A"
            ),
            network_balance.GasBoundaryMassFlow(
                "IN-B", "B", 5.0, "candidate://reverse/boundary/IN-B"
            ),
        ),
    )

    result = weymouth_network_residual.assemble_weymouth_network_residuals(
        network, candidate, (parameters,)
    )

    assert tuple(item.residual_kg_s for item in result.mass_balance.node_balances) == (0.0, 0.0)
    assert result.pipe_residuals[0].friction_term_pa2 < 0.0


def test_candidate_requires_unique_pressures_and_flows() -> None:
    pressure = weymouth_network_residual.GasNodePressure("A", 5_000_000.0, "candidate://pressure/A")
    with pytest.raises(ValueError, match="pression candidate"):
        weymouth_network_residual.WeymouthNetworkCandidateState(
            candidate_ref="candidate://duplicate-pressure",
            node_pressures=(pressure, pressure),
            pipe_flows=(network_balance.GasPipeMassFlow("P1", 1.0, "candidate://flow/P1"),),
        )

    flow = network_balance.GasPipeMassFlow("P1", 1.0, "candidate://flow/P1")
    with pytest.raises(ValueError, match="débit candidat"):
        weymouth_network_residual.WeymouthNetworkCandidateState(
            candidate_ref="candidate://duplicate-flow",
            node_pressures=(pressure,),
            pipe_flows=(flow, flow),
        )


def test_network_residual_assembly_requires_exact_node_pressure_coverage() -> None:
    candidate = weymouth_network_residual.WeymouthNetworkCandidateState(
        candidate_ref="candidate://missing-pressure",
        node_pressures=(
            weymouth_network_residual.GasNodePressure("A", 5_000_000.0, "candidate://pressure/A"),
        ),
        pipe_flows=(network_balance.GasPipeMassFlow("P1", 1.0, "candidate://flow/P1"),),
    )

    with pytest.raises(ValueError, match=r"pressions candidates.*exactement"):
        weymouth_network_residual.assemble_weymouth_network_residuals(
            _network(), candidate, (_parameters(),)
        )


def test_network_residual_assembly_requires_exact_unique_parameter_coverage() -> None:
    network = _network()
    candidate = _candidate()
    parameters = _parameters()

    with pytest.raises(ValueError, match="Un seul jeu de paramètres"):
        weymouth_network_residual.assemble_weymouth_network_residuals(
            network, candidate, (parameters, parameters)
        )

    with pytest.raises(ValueError, match=r"paramètres Weymouth.*exactement"):
        weymouth_network_residual.assemble_weymouth_network_residuals(
            network, candidate, (_parameters("OTHER"),)
        )


def test_node_pressure_rejects_invalid_values_or_missing_provenance() -> None:
    with pytest.raises(ValueError, match="provenance"):
        weymouth_network_residual.GasNodePressure("A", 1.0, "")

    with pytest.raises(ValueError, match="pression absolue"):
        weymouth_network_residual.GasNodePressure("A", -1.0, "candidate://pressure/A")
