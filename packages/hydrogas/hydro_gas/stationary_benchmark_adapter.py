"""Adapter P6-H entre un résultat stationnaire PETROLE et les observations externes.

Aucune conversion d'unité n'est effectuée. Chaque observation déclare la
quantité, l'entité, l'unité et la valeur de référence attendues. L'adapter
extrait seulement la valeur PETROLE correspondante et conserve le statut du
solveur qui l'a produite.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from hydro_gas.external_benchmark import GasBenchmarkObservation
from hydro_gas.stationary_solver import StationaryWeymouthSolveResult
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus


class StationaryGasBenchmarkQuantity(StrEnum):
    """Grandeurs stationnaires actuellement exposables au benchmark P6-H."""

    NODE_ABSOLUTE_PRESSURE = "node_absolute_pressure"
    PIPE_SIGNED_MASS_FLOW = "pipe_signed_mass_flow"


_EXPECTED_UNITS: dict[StationaryGasBenchmarkQuantity, str] = {
    StationaryGasBenchmarkQuantity.NODE_ABSOLUTE_PRESSURE: "Pa",
    StationaryGasBenchmarkQuantity.PIPE_SIGNED_MASS_FLOW: "kg/s",
}


@dataclass(frozen=True, slots=True)
class StationaryGasBenchmarkBinding:
    """Liaison explicite entre une sortie PETROLE et une valeur de référence."""

    observation_id: str
    quantity: StationaryGasBenchmarkQuantity
    entity_id: str
    unit: str
    reference_value: float
    reference_source_ref: str

    def __post_init__(self) -> None:
        required = (
            self.observation_id,
            self.entity_id,
            self.unit,
            self.reference_source_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError(
                "Observation, entité, unité et provenance de référence sont obligatoires."
            )
        if not math.isfinite(self.reference_value):
            raise ValueError("La valeur de référence doit être finie.")
        expected_unit = _EXPECTED_UNITS[self.quantity]
        if self.unit != expected_unit:
            raise ValueError(
                f"L'unité {self.unit!r} ne correspond pas à l'unité PETROLE {expected_unit!r}; "
                "aucune conversion implicite n'est autorisée."
            )


@dataclass(frozen=True, slots=True)
class StationaryGasBenchmarkObservationBundle:
    """Observations extraites avec le statut exact du solveur source."""

    solve_ref: str
    solver_status: StationaryWeymouthSolverStatus
    petrole_source_ref: str
    observations: tuple[GasBenchmarkObservation, ...]


def build_stationary_weymouth_benchmark_observations(
    solve_result: StationaryWeymouthSolveResult,
    bindings: tuple[StationaryGasBenchmarkBinding, ...],
    *,
    petrole_source_ref: str,
) -> StationaryGasBenchmarkObservationBundle:
    """Construit les observations sans conversion, agrégation ou seuil implicite."""

    normalized_source_ref = petrole_source_ref.strip()
    if not normalized_source_ref:
        raise ValueError("La provenance PETROLE des observations est obligatoire.")
    if not bindings:
        raise ValueError("Au moins une liaison de benchmark est obligatoire.")

    observation_ids = tuple(binding.observation_id for binding in bindings)
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("Les identifiants d'observation de benchmark doivent être uniques.")

    node_pressures = {
        item.node_id: item.pressure_pa
        for item in solve_result.final_evaluation.physical_evaluation.candidate.node_pressures
    }
    pipe_flows = {
        item.pipe_id: item.mass_flow_kg_s
        for item in solve_result.final_evaluation.decoded_state.pipe_flows
    }

    observations: list[GasBenchmarkObservation] = []
    for binding in bindings:
        if binding.quantity is StationaryGasBenchmarkQuantity.NODE_ABSOLUTE_PRESSURE:
            if binding.entity_id not in node_pressures:
                raise ValueError(
                    f"Le nœud {binding.entity_id!r} n'existe pas dans le résultat stationnaire."
                )
            petrole_value = node_pressures[binding.entity_id]
            location_ref = f"node://{binding.entity_id}"
        elif binding.quantity is StationaryGasBenchmarkQuantity.PIPE_SIGNED_MASS_FLOW:
            if binding.entity_id not in pipe_flows:
                raise ValueError(
                    f"La conduite {binding.entity_id!r} n'existe pas dans le résultat stationnaire."
                )
            petrole_value = pipe_flows[binding.entity_id]
            location_ref = f"pipe://{binding.entity_id}"
        else:  # pragma: no cover - protection défensive pour futures extensions d'enum
            raise ValueError(f"Grandeur de benchmark non supportée : {binding.quantity!r}.")

        observations.append(
            GasBenchmarkObservation(
                observation_id=binding.observation_id,
                quantity_ref=f"quantity://gas/{binding.quantity.value}",
                location_ref=location_ref,
                unit=binding.unit,
                petrole_value=petrole_value,
                reference_value=binding.reference_value,
                petrole_source_ref=normalized_source_ref,
                reference_source_ref=binding.reference_source_ref,
            )
        )

    return StationaryGasBenchmarkObservationBundle(
        solve_ref=solve_result.solve_ref,
        solver_status=solve_result.status,
        petrole_source_ref=normalized_source_ref,
        observations=tuple(observations),
    )


__all__ = [
    "StationaryGasBenchmarkBinding",
    "StationaryGasBenchmarkObservationBundle",
    "StationaryGasBenchmarkQuantity",
    "build_stationary_weymouth_benchmark_observations",
]
