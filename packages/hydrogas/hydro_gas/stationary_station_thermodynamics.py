"""Agrégation stationnaire P6-D des résultats thermodynamiques compresseurs.

Cette couche n'introduit aucune hypothèse de topologie hydraulique entre les
machines. Elle additionne uniquement des puissances et transferts thermiques
déjà calculés unité par unité, et publie des extrema de température factuels.
Elle ne somme donc jamais les débits compresseurs, qui pourraient représenter
le même gaz dans des machines en série.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.stationary_compressor_thermodynamics import (
    StationaryActiveCompressorThermodynamicAssessment,
)
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus


@dataclass(frozen=True, slots=True)
class StationaryCompressorStationThermodynamicSummary:
    """Synthèse factuelle d'une station, sans critère d'acceptation implicite."""

    station_ref: str
    solve_ref: str
    solver_status: StationaryWeymouthSolverStatus
    compressor_count: int
    compressor_ids: tuple[str, ...]
    total_shaft_power_input_w: float
    total_heat_transfer_to_gas_w: float
    minimum_inlet_temperature_k: float
    maximum_actual_outlet_temperature_k: float
    non_positive_shaft_power_compressor_ids: tuple[str, ...]
    fluid_names: tuple[str, ...]
    property_method_refs: tuple[str, ...]
    source_ref: str
    qualification_claim: bool = False
    certification_claim: bool = False


def _unique_in_order(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def aggregate_stationary_compressor_thermodynamics(
    assessment: StationaryActiveCompressorThermodynamicAssessment,
    *,
    station_ref: str,
    source_ref: str,
) -> StationaryCompressorStationThermodynamicSummary:
    """Agrège les résultats unitaires sans inventer de capacité ou de limite station."""

    normalized_station_ref = station_ref.strip()
    normalized_source_ref = source_ref.strip()
    if not normalized_station_ref or not normalized_source_ref:
        raise ValueError("La station et la provenance de la synthèse sont obligatoires.")
    if not assessment.solve_ref.strip():
        raise ValueError("La synthèse station doit référencer le solveur source.")
    if not assessment.compressors:
        raise ValueError("La synthèse station exige au moins un compresseur thermodynamique.")

    compressor_ids = tuple(item.compressor_id for item in assessment.compressors)
    if any(not compressor_id.strip() for compressor_id in compressor_ids):
        raise ValueError("Tous les compresseurs de la synthèse doivent être identifiés.")
    if len(compressor_ids) != len(set(compressor_ids)):
        raise ValueError("Les identifiants compresseurs de la synthèse station doivent être uniques.")

    for item in assessment.compressors:
        if item.solver_status is not assessment.solver_status:
            raise ValueError(
                "Chaque résultat thermodynamique doit conserver le statut du solveur station."
            )
        numeric_values = (
            item.energy_balance.shaft_power_input_w,
            item.energy_balance.heat_transfer_to_gas_w,
            item.property_state.inlet_temperature_k,
            item.property_state.actual_outlet_temperature_k,
        )
        if any(not math.isfinite(value) for value in numeric_values):
            raise ValueError("Les grandeurs thermodynamiques agrégées doivent être finies.")
        if (
            item.property_state.inlet_temperature_k <= 0.0
            or item.property_state.actual_outlet_temperature_k <= 0.0
        ):
            raise ValueError("Les températures thermodynamiques agrégées doivent être positives.")

    total_shaft_power = math.fsum(
        item.energy_balance.shaft_power_input_w for item in assessment.compressors
    )
    total_heat_transfer = math.fsum(
        item.energy_balance.heat_transfer_to_gas_w for item in assessment.compressors
    )
    minimum_inlet_temperature = min(
        item.property_state.inlet_temperature_k for item in assessment.compressors
    )
    maximum_actual_outlet_temperature = max(
        item.property_state.actual_outlet_temperature_k for item in assessment.compressors
    )
    non_positive_power_ids = tuple(
        item.compressor_id
        for item in assessment.compressors
        if item.energy_balance.shaft_power_input_w <= 0.0
    )
    fluid_names = _unique_in_order(
        tuple(item.property_state.fluid_name for item in assessment.compressors)
    )
    property_method_refs = _unique_in_order(
        tuple(item.property_state.property_method_ref for item in assessment.compressors)
    )

    return StationaryCompressorStationThermodynamicSummary(
        station_ref=normalized_station_ref,
        solve_ref=assessment.solve_ref,
        solver_status=assessment.solver_status,
        compressor_count=len(assessment.compressors),
        compressor_ids=compressor_ids,
        total_shaft_power_input_w=total_shaft_power,
        total_heat_transfer_to_gas_w=total_heat_transfer,
        minimum_inlet_temperature_k=minimum_inlet_temperature,
        maximum_actual_outlet_temperature_k=maximum_actual_outlet_temperature,
        non_positive_shaft_power_compressor_ids=non_positive_power_ids,
        fluid_names=fluid_names,
        property_method_refs=property_method_refs,
        source_ref=normalized_source_ref,
    )


__all__ = [
    "StationaryCompressorStationThermodynamicSummary",
    "aggregate_stationary_compressor_thermodynamics",
]
