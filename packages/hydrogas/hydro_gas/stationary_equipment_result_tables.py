"""Tables P6-G typées à partir d'un résultat stationnaire mixte déjà calculé.

Cette couche prépare les données pour l'API, l'UI et les rapports sans
recalculer aucune grandeur scientifique. Elle vérifie seulement que les familles
de résultats couvrent les mêmes entités avant de les joindre.
"""

from __future__ import annotations

from dataclasses import dataclass

from hydro_gas.stationary_equipment_solver import StationaryActiveCompressorGovernedSolveResult
from hydro_gas.stationary_solver_governance import StationaryWeymouthSolverStatus


@dataclass(frozen=True, slots=True)
class StationaryGasNodeResultRow:
    node_id: str
    pressure_pa: float
    mass_residual_kg_s: float
    pressure_source_ref: str


@dataclass(frozen=True, slots=True)
class StationaryGasPipeResultRow:
    pipe_id: str
    mass_flow_kg_s: float
    residual_pa2: float
    pressure_squared_difference_pa2: float
    friction_term_pa2: float
    flow_source_ref: str
    equation_ref: str
    parameter_source_ref: str


@dataclass(frozen=True, slots=True)
class StationaryGasCompressorResultRow:
    compressor_id: str
    mass_flow_kg_s: float
    speed_rpm: float
    pressure_ratio: float
    isentropic_efficiency: float
    expected_outlet_pressure_pa: float
    pressure_ratio_residual_pa: float
    map_source_ref: str
    map_version: str
    inside_envelope: bool | None
    minimum_mass_flow_kg_s: float | None
    maximum_mass_flow_kg_s: float | None
    envelope_source_ref: str | None
    envelope_version: str | None
    state_source_ref: str


@dataclass(frozen=True, slots=True)
class StationaryGasBoundaryResultRow:
    boundary_id: str
    node_id: str
    mass_flow_kg_s: float
    source_ref: str


@dataclass(frozen=True, slots=True)
class StationaryActiveCompressorResultTables:
    solve_ref: str
    status: StationaryWeymouthSolverStatus
    nodes: tuple[StationaryGasNodeResultRow, ...]
    pipes: tuple[StationaryGasPipeResultRow, ...]
    compressors: tuple[StationaryGasCompressorResultRow, ...]
    boundaries: tuple[StationaryGasBoundaryResultRow, ...]
    warnings: tuple[str, ...]


def build_stationary_active_compressor_result_tables(
    governed_result: StationaryActiveCompressorGovernedSolveResult,
) -> StationaryActiveCompressorResultTables:
    """Joint les sorties déjà calculées et refuse toute couverture incohérente."""

    solve = governed_result.solve
    physical = solve.final_evaluation.physical_evaluation
    candidate = physical.candidate
    equipment = physical.equipment_residuals

    mass_by_node = {item.node_id: item for item in equipment.mass_balance.node_balances}
    pressure_by_node = {item.node_id: item for item in candidate.node_pressures}
    if set(mass_by_node) != set(pressure_by_node):
        raise ValueError(
            "Les pressions nodales et les résidus massiques doivent couvrir exactement les mêmes noeuds."
        )

    pipe_residual_by_id = {item.pipe_id: item for item in physical.pipe_residuals}
    pipe_flow_by_id = {item.pipe_id: item for item in candidate.pipe_flows}
    if set(pipe_residual_by_id) != set(pipe_flow_by_id):
        raise ValueError(
            "Les débits de conduite et les résidus Weymouth doivent couvrir exactement les mêmes conduites."
        )

    compressor_constraint_by_id = {
        item.compressor_id: item for item in equipment.compressor_constraints
    }
    compressor_input_by_id = {item.compressor_id: item for item in candidate.compressor_inputs}
    if set(compressor_constraint_by_id) != set(compressor_input_by_id):
        raise ValueError(
            "Les états compresseurs et les contraintes de carte doivent couvrir exactement les mêmes compresseurs."
        )

    nodes = tuple(
        StationaryGasNodeResultRow(
            node_id=pressure.node_id,
            pressure_pa=pressure.pressure_pa,
            mass_residual_kg_s=mass_by_node[pressure.node_id].residual_kg_s,
            pressure_source_ref=pressure.source_ref,
        )
        for pressure in candidate.node_pressures
    )
    pipes = tuple(
        StationaryGasPipeResultRow(
            pipe_id=flow.pipe_id,
            mass_flow_kg_s=flow.mass_flow_kg_s,
            residual_pa2=pipe_residual_by_id[flow.pipe_id].residual_pa2,
            pressure_squared_difference_pa2=(
                pipe_residual_by_id[flow.pipe_id].pressure_squared_difference_pa2
            ),
            friction_term_pa2=pipe_residual_by_id[flow.pipe_id].friction_term_pa2,
            flow_source_ref=flow.source_ref,
            equation_ref=pipe_residual_by_id[flow.pipe_id].equation_ref,
            parameter_source_ref=pipe_residual_by_id[flow.pipe_id].parameter_source_ref,
        )
        for flow in candidate.pipe_flows
    )

    compressors: list[StationaryGasCompressorResultRow] = []
    for compressor_input in candidate.compressor_inputs:
        constraint = compressor_constraint_by_id[compressor_input.compressor_id]
        envelope = constraint.envelope_assessment
        compressors.append(
            StationaryGasCompressorResultRow(
                compressor_id=compressor_input.compressor_id,
                mass_flow_kg_s=compressor_input.mass_flow_kg_s,
                speed_rpm=compressor_input.speed_rpm,
                pressure_ratio=constraint.operating_point.pressure_ratio,
                isentropic_efficiency=constraint.operating_point.isentropic_efficiency,
                expected_outlet_pressure_pa=constraint.expected_outlet_pressure_pa,
                pressure_ratio_residual_pa=constraint.pressure_ratio_residual_pa,
                map_source_ref=constraint.operating_point.source_ref,
                map_version=constraint.operating_point.map_version,
                inside_envelope=None if envelope is None else envelope.inside_envelope,
                minimum_mass_flow_kg_s=(
                    None if envelope is None else envelope.minimum_mass_flow_kg_s
                ),
                maximum_mass_flow_kg_s=(
                    None if envelope is None else envelope.maximum_mass_flow_kg_s
                ),
                envelope_source_ref=None if envelope is None else envelope.source_ref,
                envelope_version=None if envelope is None else envelope.envelope_version,
                state_source_ref=constraint.state_source_ref,
            )
        )

    boundaries = tuple(
        StationaryGasBoundaryResultRow(
            boundary_id=item.boundary_id,
            node_id=item.node_id,
            mass_flow_kg_s=item.mass_flow_kg_s,
            source_ref=item.source_ref,
        )
        for item in candidate.boundary_flows
    )
    warnings = tuple(
        f"operational_envelope_missing:{compressor_id}"
        for compressor_id in solve.missing_operational_envelope_compressor_ids
    )
    return StationaryActiveCompressorResultTables(
        solve_ref=solve.solve_ref,
        status=solve.status,
        nodes=nodes,
        pipes=pipes,
        compressors=tuple(compressors),
        boundaries=boundaries,
        warnings=warnings,
    )


__all__ = [
    "StationaryActiveCompressorResultTables",
    "StationaryGasBoundaryResultRow",
    "StationaryGasCompressorResultRow",
    "StationaryGasNodeResultRow",
    "StationaryGasPipeResultRow",
    "build_stationary_active_compressor_result_tables",
]
