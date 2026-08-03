"""Services transactionnels des opérations de stockage et d'aide à la décision."""

from __future__ import annotations

import uuid
from copy import deepcopy
from dataclasses import asdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hydro_api.database.base import utc_now
from hydro_api.errors import ResourceConflictError, ResourceNotFoundError
from hydro_api.models import (
    AuditEvent,
    CalculationRun,
    OptimizationRun,
    Organization,
    Project,
    ScenarioComparison,
    ScenarioRecord,
    Site,
    TankRecord,
    TransferRun,
)
from hydro_api.schemas.operations import (
    ComparisonCreate,
    OptimizationCreate,
    TankCreate,
    TankUpdate,
    TransferBalanceCreate,
    TransferCreate,
)
from hydro_api.services import core
from hydro_domain import canonical_input_from_dict
from hydro_domain.enums import EquipmentStatus, ObjectiveKind, TankType
from hydro_domain.tanks import StrappingTable, Tank, TankLevels
from hydro_optimization import (
    CandidateEvaluation,
    ExhaustivePumpOptimizer,
    OptimizationConstraints,
    OptimizationRequest,
)
from hydro_shared.errors import InvalidInputError
from hydro_shared.hashing import sha256_of
from hydro_tanks import (
    TankTransferEngine,
    TransferBalanceInput,
    TransferRequest,
    VolumeMeasurement,
    compute_transfer_balance,
    constant_operating_point,
)
from hydroliquid import get_engine


def _flush(session: Session, message: str) -> None:
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ResourceConflictError(message) from error


def _audit(
    session: Session,
    *,
    organization_id: uuid.UUID,
    action: str,
    object_type: str,
    object_id: uuid.UUID,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditEvent(
            organization_id=organization_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            details=details or {},
            created_at=utc_now(),
        )
    )


def _tank_domain(record: TankRecord) -> Tank:
    """Reconstruit le modèle physique depuis la fiche persistante."""

    points = [
        (float(point["height_m"]), float(point["volume_m3"])) for point in record.strapping_payload
    ]
    return Tank(
        id=str(record.id),
        name=record.name,
        strapping=StrappingTable.from_pairs(points),
        levels=TankLevels(**record.levels_payload),
        tank_type=TankType(record.tank_type),
        elevation_m=record.elevation_m,
        current_level_m=record.current_level_m,
        fluid_id=record.fluid_id,
        compatible_fluid_ids=tuple(record.compatible_fluid_ids),
        status=EquipmentStatus(record.status),
        dead_volume_m3=record.dead_volume_m3,
    )


def tank_payload(record: TankRecord) -> dict[str, Any]:
    tank = _tank_domain(record)
    return {
        "id": record.id,
        "organization_id": record.organization_id,
        "site_id": record.site_id,
        "name": record.name,
        "code": record.code,
        "tank_type": record.tank_type,
        "elevation_m": record.elevation_m,
        "current_level_m": record.current_level_m,
        "current_volume_m3": tank.current_volume_m3,
        "nominal_capacity_m3": tank.nominal_capacity_m3,
        "available_capacity_m3": tank.available_capacity_m3,
        "pumpable_volume_m3": tank.pumpable_volume_m3,
        "fluid_id": record.fluid_id,
        "compatible_fluid_ids": record.compatible_fluid_ids,
        "status": record.status,
        "dead_volume_m3": record.dead_volume_m3,
        "levels": record.levels_payload,
        "strapping": record.strapping_payload,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def get_tank(session: Session, tank_id: uuid.UUID) -> TankRecord:
    record = session.get(TankRecord, tank_id)
    if record is None:
        raise ResourceNotFoundError("Réservoir", tank_id)
    return record


def create_tank(session: Session, data: TankCreate) -> TankRecord:
    if session.get(Organization, data.organization_id) is None:
        raise ResourceNotFoundError("Organisation", data.organization_id)
    if data.site_id is not None:
        site = session.get(Site, data.site_id)
        if site is None:
            raise ResourceNotFoundError("Site", data.site_id)
        if site.organization_id != data.organization_id:
            raise ResourceConflictError(
                "Le site et le réservoir doivent appartenir à la même organisation."
            )

    levels_payload = data.levels.model_dump()
    strapping_payload = [point.model_dump() for point in data.strapping]
    record = TankRecord(
        organization_id=data.organization_id,
        site_id=data.site_id,
        name=data.name.strip(),
        code=data.code,
        tank_type=data.tank_type,
        elevation_m=data.elevation_m,
        current_level_m=data.current_level_m,
        fluid_id=data.fluid_id,
        compatible_fluid_ids=data.compatible_fluid_ids,
        status=data.status,
        dead_volume_m3=data.dead_volume_m3,
        levels_payload=levels_payload,
        strapping_payload=strapping_payload,
    )
    _tank_domain(record)
    session.add(record)
    _flush(
        session,
        f"Le code réservoir « {data.code} » existe déjà dans cette organisation.",
    )
    _audit(
        session,
        organization_id=record.organization_id,
        action="tank.created",
        object_type="tank",
        object_id=record.id,
        details={"code": record.code},
    )
    _flush(session, "Impossible d'enregistrer l'audit du réservoir.")
    return record


def list_tanks(
    session: Session,
    *,
    organization_id: uuid.UUID,
    site_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[TankRecord], int]:
    condition = TankRecord.organization_id == organization_id
    query = select(TankRecord).where(condition)
    count_query = select(func.count()).select_from(TankRecord).where(condition)
    if site_id is not None:
        query = query.where(TankRecord.site_id == site_id)
        count_query = count_query.where(TankRecord.site_id == site_id)
    total = int(session.scalar(count_query) or 0)
    items = list(
        session.scalars(query.order_by(TankRecord.name, TankRecord.id).limit(limit).offset(offset))
    )
    return items, total


def update_tank(
    session: Session,
    tank_id: uuid.UUID,
    data: TankUpdate,
) -> TankRecord:
    record = get_tank(session, tank_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("compatible_fluid_ids") is not None:
        changes["compatible_fluid_ids"] = sorted(
            {value.strip() for value in changes["compatible_fluid_ids"] if value.strip()}
        )
    for field, value in changes.items():
        setattr(record, field, value)
    _tank_domain(record)
    _audit(
        session,
        organization_id=record.organization_id,
        action="tank.updated",
        object_type="tank",
        object_id=record.id,
        details={"fields": sorted(changes)},
    )
    _flush(session, "La mise à jour du réservoir entre en conflit avec une donnée existante.")
    return record


def _transfer_result_payload(result) -> dict[str, Any]:
    return {
        "stop_reason": result.stop_reason.value,
        "target_reached": result.target_reached,
        "preflight_feasible": result.preflight_feasible,
        "duration_s": result.duration_s,
        "withdrawn_volume_m3": result.withdrawn_volume_m3,
        "received_volume_m3": result.received_volume_m3,
        "losses_m3": result.losses_m3,
        "balance_residual_m3": result.balance_residual_m3,
        "energy_j": result.energy_j,
        "source_final_level_m": result.source_final.current_level_m,
        "destination_final_level_m": result.destination_final.current_level_m,
        "messages": list(result.messages),
        "warning_codes": list(result.warning_codes),
        "violation_codes": list(result.violation_codes),
        "samples": [asdict(sample) for sample in result.samples],
    }


def simulate_transfer(
    session: Session,
    organization_id: uuid.UUID,
    data: TransferCreate,
    *,
    idempotency_key: str,
) -> TransferRun:
    input_payload = data.model_dump(mode="json")
    input_hash = sha256_of(input_payload)
    existing = session.scalar(
        select(TransferRun).where(
            TransferRun.organization_id == organization_id,
            TransferRun.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.input_hash != input_hash:
            raise ResourceConflictError(
                "La clé d'idempotence du transfert correspond à d'autres paramètres."
            )
        return existing

    source_record = get_tank(session, data.source_tank_id)
    destination_record = get_tank(session, data.destination_tank_id)
    if (
        source_record.organization_id != organization_id
        or destination_record.organization_id != organization_id
    ):
        raise ResourceConflictError(
            "Les deux réservoirs doivent appartenir à l'organisation du transfert."
        )
    request = TransferRequest(
        source=_tank_domain(source_record),
        destination=_tank_domain(destination_record),
        fluid_id=data.fluid_id,
        requested_flow_m3_s=data.requested_flow_m3_s,
        target_volume_m3=data.target_volume_m3,
        target_destination_level_m=data.target_destination_level_m,
        target_duration_s=data.target_duration_s,
        time_step_s=data.time_step_s,
        maximum_duration_s=data.maximum_duration_s,
        maximum_flow_m3_s=data.maximum_flow_m3_s,
        loss_fraction=data.loss_fraction,
    )
    resolver = constant_operating_point(
        data.requested_flow_m3_s,
        discharge_pressure_pa=data.discharge_pressure_pa,
        absorbed_power_w=data.absorbed_power_w,
    )
    created_at = utc_now()
    started_at = utc_now()
    result = TankTransferEngine().simulate(request, resolver)
    record = TransferRun(
        organization_id=organization_id,
        source_tank_id=source_record.id,
        destination_tank_id=destination_record.id,
        idempotency_key=idempotency_key,
        status=result.stop_reason.value,
        input_hash=input_hash,
        input_payload=input_payload,
        result_payload=_transfer_result_payload(result),
        created_at=created_at,
        started_at=started_at,
        finished_at=utc_now(),
    )
    session.add(record)
    _flush(session, "Une simulation de transfert identique existe déjà.")
    _audit(
        session,
        organization_id=organization_id,
        action="transfer.simulated",
        object_type="transfer",
        object_id=record.id,
        details={"status": record.status, "input_hash": input_hash},
    )
    _flush(session, "Impossible d'enregistrer l'audit du transfert.")
    return record


def get_transfer(session: Session, transfer_id: uuid.UUID) -> TransferRun:
    record = session.get(TransferRun, transfer_id)
    if record is None:
        raise ResourceNotFoundError("Transfert", transfer_id)
    return record


def list_transfers(
    session: Session,
    organization_id: uuid.UUID,
    *,
    tank_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[TransferRun], int]:
    """Liste les simulations d'une organisation, avec filtre facultatif par bac."""

    conditions = [TransferRun.organization_id == organization_id]
    if tank_id is not None:
        conditions.append(
            (TransferRun.source_tank_id == tank_id)
            | (TransferRun.destination_tank_id == tank_id)
        )
    total = session.scalar(select(func.count()).select_from(TransferRun).where(*conditions)) or 0
    items = list(
        session.scalars(
            select(TransferRun)
            .where(*conditions)
            .order_by(TransferRun.created_at.desc(), TransferRun.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return items, int(total)


def compute_balance(
    session: Session,
    transfer_id: uuid.UUID,
    data: TransferBalanceCreate,
) -> dict[str, Any]:
    record = get_transfer(session, transfer_id)

    def measurement(value) -> VolumeMeasurement:
        return VolumeMeasurement(**value.model_dump())

    result = compute_transfer_balance(
        TransferBalanceInput(
            source_opening=measurement(data.source_opening),
            source_closing=measurement(data.source_closing),
            destination_opening=measurement(data.destination_opening),
            destination_closing=measurement(data.destination_closing),
            metered_volume=measurement(data.metered_volume),
            accounted_losses=measurement(data.accounted_losses),
            coverage_factor=data.coverage_factor,
            absolute_tolerance_m3=data.absolute_tolerance_m3,
            relative_tolerance=data.relative_tolerance,
        )
    )
    payload = result.as_dict()
    record.balance_payload = payload
    _audit(
        session,
        organization_id=record.organization_id,
        action="transfer.balance_computed",
        object_type="transfer",
        object_id=record.id,
        details={"within_tolerance": result.within_tolerance},
    )
    session.flush()
    return payload


def _calculation_metrics(calculation: CalculationRun) -> dict[str, Any]:
    result = calculation.result_payload or {}
    violations = result.get("violations") or []
    warnings = result.get("warnings") or []
    return {
        "calculation_id": str(calculation.id),
        "scenario_id": str(calculation.scenario_id),
        "status": calculation.status,
        "flow_m3_s": result.get("flow_m3_s"),
        "minimum_pressure_pa": result.get("min_pressure_pa"),
        "maximum_pressure_pa": result.get("max_pressure_pa"),
        "total_head_loss_m": result.get("total_head_loss_m"),
        "total_power_w": result.get("total_power_w"),
        "feasible": bool(result.get("feasible", False)),
        "approvable": bool(result.get("approvable", False)),
        "violation_count": len(violations),
        "warning_count": len(warnings),
        "input_hash": calculation.input_hash,
    }


def create_comparison(
    session: Session,
    project_id: uuid.UUID,
    data: ComparisonCreate,
    *,
    idempotency_key: str,
) -> ScenarioComparison:
    project = session.get(Project, project_id)
    if project is None:
        raise ResourceNotFoundError("Projet", project_id)
    requested_ids = [str(identifier) for identifier in data.calculation_ids]
    existing = session.scalar(
        select(ScenarioComparison).where(
            ScenarioComparison.project_id == project_id,
            ScenarioComparison.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.calculation_ids != requested_ids:
            raise ResourceConflictError(
                "La clé d'idempotence de comparaison correspond à d'autres calculs."
            )
        return existing

    calculations = [session.get(CalculationRun, identifier) for identifier in data.calculation_ids]
    missing = [
        str(identifier)
        for identifier, calculation in zip(
            data.calculation_ids,
            calculations,
            strict=True,
        )
        if calculation is None
    ]
    if missing:
        raise ResourceNotFoundError("Calcul", missing[0])

    concrete = [calculation for calculation in calculations if calculation is not None]
    for calculation in concrete:
        calculation_project_id = calculation.scenario.model_version.project_id
        if calculation_project_id != project_id:
            raise ResourceConflictError(
                "Tous les calculs comparés doivent appartenir au projet demandé."
            )

    metrics = [_calculation_metrics(calculation) for calculation in concrete]
    ranked = sorted(
        metrics,
        key=lambda item: (
            not item["approvable"],
            item["total_power_w"] is None,
            item["total_power_w"] if item["total_power_w"] is not None else float("inf"),
            item["calculation_id"],
        ),
    )
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
    reference = metrics[0]
    deltas = {
        item["calculation_id"]: {
            key: (
                item[key] - reference[key]
                if isinstance(item.get(key), (int, float))
                and not isinstance(item.get(key), bool)
                and isinstance(reference.get(key), (int, float))
                and not isinstance(reference.get(key), bool)
                else None
            )
            for key in (
                "flow_m3_s",
                "minimum_pressure_pa",
                "maximum_pressure_pa",
                "total_head_loss_m",
                "total_power_w",
            )
        }
        for item in metrics
    }
    result_payload = {
        "reference_calculation_id": str(concrete[0].id),
        "ranked": ranked,
        "deltas_from_reference": deltas,
        "recommended_calculation_id": ranked[0]["calculation_id"],
    }
    content_hash = sha256_of(result_payload)
    comparison = ScenarioComparison(
        organization_id=project.organization_id,
        project_id=project_id,
        idempotency_key=idempotency_key,
        calculation_ids=requested_ids,
        content_hash=content_hash,
        result_payload=result_payload,
        created_at=utc_now(),
    )
    session.add(comparison)
    _flush(session, "Une comparaison identique existe déjà.")
    _audit(
        session,
        organization_id=project.organization_id,
        action="comparison.created",
        object_type="comparison",
        object_id=comparison.id,
        details={"content_hash": content_hash},
    )
    _flush(session, "Impossible d'enregistrer l'audit de comparaison.")
    return comparison


def get_comparison(
    session: Session,
    comparison_id: uuid.UUID,
) -> ScenarioComparison:
    comparison = session.get(ScenarioComparison, comparison_id)
    if comparison is None:
        raise ResourceNotFoundError("Comparaison", comparison_id)
    return comparison


def list_comparisons(
    session: Session,
    project_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[ScenarioComparison], int]:
    """Liste les comparaisons persistées d'un projet."""

    if session.get(Project, project_id) is None:
        raise ResourceNotFoundError("Projet", project_id)
    condition = ScenarioComparison.project_id == project_id
    total = session.scalar(
        select(func.count()).select_from(ScenarioComparison).where(condition)
    ) or 0
    items = list(
        session.scalars(
            select(ScenarioComparison)
            .where(condition)
            .order_by(ScenarioComparison.created_at.desc(), ScenarioComparison.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return items, int(total)


def _evaluation_payload(evaluation: CandidateEvaluation) -> dict[str, Any]:
    return {
        "flow_m3_s": evaluation.flow_m3_s,
        "energy_kwh": evaluation.energy_kwh,
        "cost": evaluation.cost,
        "minimum_pressure_pa": evaluation.minimum_pressure_pa,
        "maximum_pressure_pa": evaluation.maximum_pressure_pa,
        "starts_count": evaluation.starts_count,
        "availability_penalty": evaluation.availability_penalty,
        "converged": evaluation.converged,
        "violation_codes": list(evaluation.violation_codes),
        "rejection_reasons": list(evaluation.rejection_reasons),
        "metadata": evaluation.metadata,
    }


def _configuration_payload(configuration) -> dict[str, Any]:
    return {
        "id": configuration.id,
        "active_pump_ids": list(configuration.active_pump_ids),
        "speed_ratios": dict(configuration.speed_ratios),
        "active_pump_count": configuration.active_pump_count,
    }


def _optimization_result_payload(result) -> dict[str, Any]:
    return {
        "status": result.status.value,
        "solver_name": result.solver_name,
        "generated_count": result.generated_count,
        "evaluated_count": result.evaluated_count,
        "complete": result.complete,
        "optimality_gap": result.optimality_gap,
        "best": (
            {
                "rank": result.best.rank,
                "objective_value": result.best.objective_value,
                "configuration": _configuration_payload(result.best.configuration),
                "evaluation": _evaluation_payload(result.best.evaluation),
            }
            if result.best
            else None
        ),
        "ranked": [
            {
                "rank": item.rank,
                "objective_value": item.objective_value,
                "configuration": _configuration_payload(item.configuration),
                "evaluation": _evaluation_payload(item.evaluation),
            }
            for item in result.ranked
        ],
        "rejected": [
            {
                "configuration": _configuration_payload(item.configuration),
                "reasons": list(item.reasons),
                "evaluation": (_evaluation_payload(item.evaluation) if item.evaluation else None),
            }
            for item in result.rejected
        ],
    }


def run_optimization(
    session: Session,
    scenario_id: uuid.UUID,
    data: OptimizationCreate,
    *,
    idempotency_key: str,
) -> OptimizationRun:
    input_payload = data.model_dump(mode="json")
    input_hash = sha256_of(input_payload)
    existing = session.scalar(
        select(OptimizationRun).where(
            OptimizationRun.scenario_id == scenario_id,
            OptimizationRun.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.input_hash != input_hash:
            raise ResourceConflictError(
                "La clé d'idempotence d'optimisation correspond à d'autres paramètres."
            )
        return existing

    scenario = session.get(ScenarioRecord, scenario_id)
    if scenario is None:
        raise ResourceNotFoundError("Scénario", scenario_id)
    model = scenario.model_version
    project = model.project
    engine = get_engine("long_distance_liquid")
    base_payload = core.canonical_payload_for_calculation(
        session,
        model,
        scenario,
        engine_name=engine.name,
        engine_version=f"{engine.name}-{engine.version}",
        organization_id=project.organization_id,
    )
    base_input = canonical_input_from_dict(base_payload)
    available_pump_ids = sorted(
        pump.id for station in base_input.pipeline.stations for pump in station.pumps
    )
    selected_pump_ids = sorted(data.pump_ids or available_pump_ids)
    if not selected_pump_ids:
        raise InvalidInputError(
            "Le modèle ne contient aucune pompe à optimiser.",
            scenario_id=str(scenario_id),
        )
    unknown = set(selected_pump_ids) - set(available_pump_ids)
    if unknown:
        raise InvalidInputError(
            "L'espace d'optimisation contient des pompes absentes du modèle.",
            pump_ids=sorted(unknown),
        )

    constraints = OptimizationConstraints(
        minimum_flow_m3_s=data.constraints.minimum_flow_m3_s,
        maximum_flow_m3_s=data.constraints.maximum_flow_m3_s,
        minimum_pressure_pa=data.constraints.minimum_pressure_pa,
        maximum_pressure_pa=data.constraints.maximum_pressure_pa,
        maximum_active_pumps=data.constraints.maximum_active_pumps,
        required_pump_ids=frozenset(data.constraints.required_pump_ids),
        forbidden_pump_ids=frozenset(data.constraints.forbidden_pump_ids),
        allow_violations=data.constraints.allow_violations,
    )
    request = OptimizationRequest(
        pump_ids=tuple(selected_pump_ids),
        speed_options=tuple(sorted(set(data.speed_options))),
        objective=ObjectiveKind(data.objective),
        constraints=constraints,
        maximum_configurations=data.maximum_configurations,
        maximum_evaluations=data.maximum_evaluations,
    )

    def evaluate(configuration) -> CandidateEvaluation:
        candidate_payload = deepcopy(base_payload)
        scenario_payload = candidate_payload["scenario"]
        existing_overrides = {
            item["pump_id"]: item
            for item in scenario_payload.get("pump_overrides", [])
            if isinstance(item, dict) and item.get("pump_id")
        }
        active = set(configuration.active_pump_ids)
        speeds = dict(configuration.speed_ratios)
        for pump_id in selected_pump_ids:
            existing_overrides[pump_id] = {
                "pump_id": pump_id,
                "status": None,
                "running": pump_id in active,
                "speed_ratio": speeds.get(pump_id),
            }
        scenario_payload["pump_overrides"] = [
            existing_overrides[pump_id] for pump_id in sorted(existing_overrides)
        ]
        candidate = canonical_input_from_dict(candidate_payload)
        if not engine.supports(candidate):
            raise InvalidInputError("Le moteur principal ne couvre pas cette configuration.")
        result = engine.simulate(candidate)
        absorbed_power = (
            result.energy.total_absorbed_power_w
            if result.energy and result.energy.total_absorbed_power_w is not None
            else 0.0
        )
        energy_kwh = absorbed_power * data.reference_duration_s / 3_600_000.0
        cost = (
            energy_kwh * data.energy_price_per_kwh
            if data.energy_price_per_kwh is not None
            else None
        )
        return CandidateEvaluation(
            flow_m3_s=result.flow_m3_s,
            energy_kwh=energy_kwh,
            cost=cost,
            minimum_pressure_pa=result.min_pressure_pa,
            maximum_pressure_pa=result.max_pressure_pa,
            starts_count=configuration.active_pump_count,
            converged=result.diagnostics.converged,
            violation_codes=tuple(str(item.code) for item in result.violations),
            rejection_reasons=(
                () if result.is_feasible else ("Le résultat hydraulique n'est pas réalisable.",)
            ),
            metadata={
                "simulation_status": result.status.value,
                "input_hash": candidate.fingerprint,
            },
        )

    created_at = utc_now()
    started_at = utc_now()
    result = ExhaustivePumpOptimizer().optimize(request, evaluate)
    result_payload = _optimization_result_payload(result)
    record = OptimizationRun(
        organization_id=project.organization_id,
        scenario_id=scenario_id,
        idempotency_key=idempotency_key,
        status=result.status.value,
        input_hash=input_hash,
        input_payload=input_payload,
        result_payload=result_payload,
        engine_version=f"{engine.name}-{engine.version}",
        created_at=created_at,
        started_at=started_at,
        finished_at=utc_now(),
    )
    session.add(record)
    _flush(session, "Une optimisation identique existe déjà.")
    _audit(
        session,
        organization_id=project.organization_id,
        action="optimization.completed",
        object_type="optimization",
        object_id=record.id,
        details={"status": record.status, "input_hash": input_hash},
    )
    _flush(session, "Impossible d'enregistrer l'audit de l'optimisation.")
    return record


def get_optimization(
    session: Session,
    optimization_id: uuid.UUID,
) -> OptimizationRun:
    record = session.get(OptimizationRun, optimization_id)
    if record is None:
        raise ResourceNotFoundError("Optimisation", optimization_id)
    return record


def list_optimizations(
    session: Session,
    scenario_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[OptimizationRun], int]:
    """Liste les recherches de configuration d'un scénario."""

    if session.get(ScenarioRecord, scenario_id) is None:
        raise ResourceNotFoundError("Scénario", scenario_id)
    condition = OptimizationRun.scenario_id == scenario_id
    total = session.scalar(
        select(func.count()).select_from(OptimizationRun).where(condition)
    ) or 0
    items = list(
        session.scalars(
            select(OptimizationRun)
            .where(condition)
            .order_by(OptimizationRun.created_at.desc(), OptimizationRun.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return items, int(total)


__all__ = [
    "compute_balance",
    "create_comparison",
    "create_tank",
    "get_comparison",
    "get_optimization",
    "get_tank",
    "get_transfer",
    "list_tanks",
    "run_optimization",
    "simulate_transfer",
    "tank_payload",
    "update_tank",
]
