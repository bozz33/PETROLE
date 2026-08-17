"""Adapter P6-H du solveur stationnaire mixte vers le contrat de benchmark gaz.

Aucune conversion, tolérance ou décision de conformité n'est introduite ici.
Chaque liaison déclare explicitement la grandeur, l'entité, l'unité et la valeur
de référence ; l'adapter extrait seulement la valeur PETROLE déjà calculée.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from hydro_gas.external_benchmark import GasBenchmarkObservation
from hydro_gas.stationary_equipment_solver import StationaryActiveCompressorGovernedSolveResult
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus


class StationaryEquipmentBenchmarkQuantity(StrEnum):
    """Grandeurs mixtes exposables au benchmark sans conversion implicite."""

    BOUNDARY_SIGNED_MASS_FLOW = "boundary_signed_mass_flow"
    COMPRESSOR_MASS_FLOW = "compressor_mass_flow"
    COMPRESSOR_PRESSURE_RATIO = "compressor_pressure_ratio"
    NODE_ABSOLUTE_PRESSURE = "node_absolute_pressure"
    PIPE_SIGNED_MASS_FLOW = "pipe_signed_mass_flow"


_EXPECTED_UNITS: dict[StationaryEquipmentBenchmarkQuantity, str] = {
    StationaryEquipmentBenchmarkQuantity.BOUNDARY_SIGNED_MASS_FLOW: "kg/s",
    StationaryEquipmentBenchmarkQuantity.COMPRESSOR_MASS_FLOW: "kg/s",
    StationaryEquipmentBenchmarkQuantity.COMPRESSOR_PRESSURE_RATIO: "1",
    StationaryEquipmentBenchmarkQuantity.NODE_ABSOLUTE_PRESSURE: "Pa",
    StationaryEquipmentBenchmarkQuantity.PIPE_SIGNED_MASS_FLOW: "kg/s",
}


@dataclass(frozen=True, slots=True)
class StationaryEquipmentBenchmarkBinding:
    """Liaison explicite entre une sortie mixte et une référence externe."""

    observation_id: str
    quantity: StationaryEquipmentBenchmarkQuantity
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
            raise ValueError("La valeur de référence du benchmark mixte doit être finie.")
        expected_unit = _EXPECTED_UNITS[self.quantity]
        if self.unit != expected_unit:
            raise ValueError(
                f"L'unité {self.unit!r} ne correspond pas à l'unité PETROLE {expected_unit!r}; "
                "aucune conversion implicite n'est autorisée."
            )


@dataclass(frozen=True, slots=True)
class StationaryEquipmentBenchmarkObservationBundle:
    """Observations mixtes accompagnées du statut exact du solveur source."""

    solve_ref: str
    solver_status: StationaryWeymouthSolverStatus
    petrole_source_ref: str
    observations: tuple[GasBenchmarkObservation, ...]


def build_stationary_equipment_benchmark_observations(
    governed_result: StationaryActiveCompressorGovernedSolveResult,
    bindings: tuple[StationaryEquipmentBenchmarkBinding, ...],
    *,
    petrole_source_ref: str,
) -> StationaryEquipmentBenchmarkObservationBundle:
    """Extrait les sorties mixtes sans conversion, agrégation ou seuil implicite."""

    normalized_source_ref = petrole_source_ref.strip()
    if not normalized_source_ref:
        raise ValueError("La provenance PETROLE des observations mixtes est obligatoire.")
    if not bindings:
        raise ValueError("Au moins une liaison de benchmark mixte est obligatoire.")

    observation_ids = tuple(binding.observation_id for binding in bindings)
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("Les identifiants d'observation de benchmark mixte doivent être uniques.")

    solve = governed_result.solve
    physical = solve.final_evaluation.physical_evaluation
    candidate = physical.candidate
    node_pressures = {item.node_id: item.pressure_pa for item in candidate.node_pressures}
    pipe_flows = {item.pipe_id: item.mass_flow_kg_s for item in candidate.pipe_flows}
    compressor_flows = {
        item.compressor_id: item.mass_flow_kg_s for item in candidate.compressor_inputs
    }
    compressor_ratios = {
        item.compressor_id: item.operating_point.pressure_ratio
        for item in physical.equipment_residuals.compressor_constraints
    }
    boundary_flows = {item.boundary_id: item.mass_flow_kg_s for item in candidate.boundary_flows}

    observations: list[GasBenchmarkObservation] = []
    for binding in bindings:
        if binding.quantity is StationaryEquipmentBenchmarkQuantity.NODE_ABSOLUTE_PRESSURE:
            values = node_pressures
            location_ref = f"node://{binding.entity_id}"
        elif binding.quantity is StationaryEquipmentBenchmarkQuantity.PIPE_SIGNED_MASS_FLOW:
            values = pipe_flows
            location_ref = f"pipe://{binding.entity_id}"
        elif binding.quantity is StationaryEquipmentBenchmarkQuantity.COMPRESSOR_MASS_FLOW:
            values = compressor_flows
            location_ref = f"compressor://{binding.entity_id}"
        elif binding.quantity is StationaryEquipmentBenchmarkQuantity.COMPRESSOR_PRESSURE_RATIO:
            values = compressor_ratios
            location_ref = f"compressor://{binding.entity_id}"
        elif binding.quantity is StationaryEquipmentBenchmarkQuantity.BOUNDARY_SIGNED_MASS_FLOW:
            values = boundary_flows
            location_ref = f"boundary://{binding.entity_id}"
        else:  # pragma: no cover - défense pour futures extensions d'enum
            raise ValueError(f"Grandeur de benchmark mixte non supportée : {binding.quantity!r}.")

        if binding.entity_id not in values:
            raise ValueError(
                f"L'entité {binding.entity_id!r} n'existe pas pour la grandeur "
                f"{binding.quantity.value!r} dans le résultat mixte."
            )
        observations.append(
            GasBenchmarkObservation(
                observation_id=binding.observation_id,
                quantity_ref=f"quantity://gas/{binding.quantity.value}",
                location_ref=location_ref,
                unit=binding.unit,
                petrole_value=values[binding.entity_id],
                reference_value=binding.reference_value,
                petrole_source_ref=normalized_source_ref,
                reference_source_ref=binding.reference_source_ref,
            )
        )

    return StationaryEquipmentBenchmarkObservationBundle(
        solve_ref=solve.solve_ref,
        solver_status=solve.status,
        petrole_source_ref=normalized_source_ref,
        observations=tuple(observations),
    )


__all__ = [
    "StationaryEquipmentBenchmarkBinding",
    "StationaryEquipmentBenchmarkObservationBundle",
    "StationaryEquipmentBenchmarkQuantity",
    "build_stationary_equipment_benchmark_observations",
]
