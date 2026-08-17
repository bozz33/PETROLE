"""Assemblage P6-B des résidus d'un état candidat de réseau Weymouth-SI.

Cette brique prépare le futur solveur non linéaire sans en choisir un. Elle
assemble séparément la conservation de masse aux nœuds et l'équation
constitutive Weymouth de chaque conduite à partir de pressions et débits déjà
fournis. Les familles de résidus gardent leurs unités physiques respectives ;
aucune mise à l'échelle, tolérance ou décision PASS/FAIL n'est implicite.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.network_balance import (
    GasBoundaryMassFlow,
    GasNetworkMassBalanceResult,
    GasPipeMassFlow,
    SteadyGasNetwork,
    assess_stationary_mass_balance,
)
from hydro_gas.weymouth_si import (
    WeymouthSiObservation,
    WeymouthSiPipeParameters,
    WeymouthSiResidual,
    evaluate_weymouth_si_residual,
)


@dataclass(frozen=True, slots=True)
class GasNodePressure:
    """Pression absolue candidate d'un nœud avec provenance explicite."""

    node_id: str
    pressure_pa: float
    source_ref: str

    def __post_init__(self) -> None:
        if not self.node_id.strip() or not self.source_ref.strip():
            raise ValueError("Le nœud de pression et sa provenance sont obligatoires.")
        if not math.isfinite(self.pressure_pa) or self.pressure_pa < 0.0:
            raise ValueError("La pression absolue candidate doit être finie et positive ou nulle.")


@dataclass(frozen=True, slots=True)
class WeymouthNetworkCandidateState:
    """État candidat complet à évaluer, sans sémantique de convergence."""

    candidate_ref: str
    node_pressures: tuple[GasNodePressure, ...]
    pipe_flows: tuple[GasPipeMassFlow, ...]
    boundary_flows: tuple[GasBoundaryMassFlow, ...] = ()

    def __post_init__(self) -> None:
        if not self.candidate_ref.strip():
            raise ValueError("La provenance de l'état candidat est obligatoire.")

        node_ids = tuple(item.node_id for item in self.node_pressures)
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Une seule pression candidate peut être fournie par nœud.")

        pipe_ids = tuple(item.pipe_id for item in self.pipe_flows)
        if len(pipe_ids) != len(set(pipe_ids)):
            raise ValueError("Un seul débit candidat peut être fourni par conduite.")


@dataclass(frozen=True, slots=True)
class WeymouthNetworkResidualAssembly:
    """Résidus physiques bruts d'un état candidat, sans agrégation adimensionnelle."""

    candidate_ref: str
    mass_balance: GasNetworkMassBalanceResult
    pipe_residuals: tuple[WeymouthSiResidual, ...]
    node_pressure_source_refs: tuple[str, ...]
    pipe_flow_source_refs: tuple[str, ...]
    boundary_source_refs: tuple[str, ...]


def evaluate_weymouth_pipe_residuals(
    network: SteadyGasNetwork,
    candidate: WeymouthNetworkCandidateState,
    pipe_parameters: tuple[WeymouthSiPipeParameters, ...],
) -> tuple[WeymouthSiResidual, ...]:
    """Évalue uniquement les lois de conduite Weymouth d'un état candidat.

    Cette variante est utilisée quand la conservation de masse est assemblée
    par une couche plus riche, par exemple un réseau contenant aussi des
    compresseurs. Elle ne calcule donc aucun bilan nodal et ne décide jamais de
    la convergence du réseau.
    """

    expected_node_ids = {node.node_id for node in network.nodes}
    supplied_node_ids = {item.node_id for item in candidate.node_pressures}
    if supplied_node_ids != expected_node_ids:
        raise ValueError("Les pressions candidates doivent couvrir exactement les nœuds du réseau.")

    expected_pipe_ids = {pipe.pipe_id for pipe in network.pipes}
    supplied_pipe_ids = tuple(item.pipe_id for item in candidate.pipe_flows)
    if len(supplied_pipe_ids) != len(set(supplied_pipe_ids)):
        raise ValueError("Un seul débit candidat est autorisé par conduite.")
    if set(supplied_pipe_ids) != expected_pipe_ids:
        raise ValueError("Les débits candidats doivent couvrir exactement les conduites du réseau.")

    parameter_ids = tuple(item.pipe_id for item in pipe_parameters)
    if len(parameter_ids) != len(set(parameter_ids)):
        raise ValueError("Un seul jeu de paramètres Weymouth est autorisé par conduite.")
    if set(parameter_ids) != expected_pipe_ids:
        raise ValueError(
            "Les paramètres Weymouth doivent couvrir exactement les conduites du réseau."
        )

    pressures_by_node = {item.node_id: item for item in candidate.node_pressures}
    flows_by_pipe = {item.pipe_id: item for item in candidate.pipe_flows}
    parameters_by_pipe = {item.pipe_id: item for item in pipe_parameters}

    residuals: list[WeymouthSiResidual] = []
    for pipe in network.pipes:
        from_pressure = pressures_by_node[pipe.from_node_id]
        to_pressure = pressures_by_node[pipe.to_node_id]
        flow = flows_by_pipe[pipe.pipe_id]
        parameters = parameters_by_pipe[pipe.pipe_id]
        observation = WeymouthSiObservation(
            pipe_id=pipe.pipe_id,
            from_pressure_pa=from_pressure.pressure_pa,
            to_pressure_pa=to_pressure.pressure_pa,
            mass_flow_kg_s=flow.mass_flow_kg_s,
            source_ref=candidate.candidate_ref,
        )
        residuals.append(evaluate_weymouth_si_residual(parameters, observation))
    return tuple(residuals)


def assemble_weymouth_network_residuals(
    network: SteadyGasNetwork,
    candidate: WeymouthNetworkCandidateState,
    pipe_parameters: tuple[WeymouthSiPipeParameters, ...],
) -> WeymouthNetworkResidualAssembly:
    """Évalue les équations de masse et Weymouth sur un état candidat complet.

    Les pressions doivent couvrir exactement les nœuds du réseau, les débits et
    paramètres exactement les conduites. La fonction ne choisit aucune variable
    inconnue, ne modifie pas l'état fourni et ne conclut jamais à une convergence.
    """

    pipe_residuals = evaluate_weymouth_pipe_residuals(
        network,
        candidate,
        pipe_parameters,
    )
    mass_balance = assess_stationary_mass_balance(
        network,
        candidate.pipe_flows,
        candidate.boundary_flows,
    )

    return WeymouthNetworkResidualAssembly(
        candidate_ref=candidate.candidate_ref,
        mass_balance=mass_balance,
        pipe_residuals=pipe_residuals,
        node_pressure_source_refs=tuple(item.source_ref for item in candidate.node_pressures),
        pipe_flow_source_refs=tuple(item.source_ref for item in candidate.pipe_flows),
        boundary_source_refs=tuple(item.source_ref for item in candidate.boundary_flows),
    )


__all__ = [
    "GasNodePressure",
    "WeymouthNetworkCandidateState",
    "WeymouthNetworkResidualAssembly",
    "assemble_weymouth_network_residuals",
    "evaluate_weymouth_pipe_residuals",
]
