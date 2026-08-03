"""Services transactionnels du noyau projet et versionnement."""

from __future__ import annotations

import re
import uuid
from copy import deepcopy
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hydro_api.database.base import utc_now
from hydro_api.errors import ResourceConflictError, ResourceNotFoundError
from hydro_api.models import (
    AuditEvent,
    BackgroundJob,
    CalculationRun,
    GeneratedReport,
    ModelVersion,
    Organization,
    OrganizationMembership,
    Project,
    ScenarioRecord,
    Site,
    StoredFile,
)
from hydro_api.schemas import (
    CalculationCreate,
    ModelVersionCreate,
    ModelVersionUpdate,
    OrganizationCreate,
    OrganizationUpdate,
    ProjectCreate,
    ProjectUpdate,
    ReportApproval,
    ReportCreate,
    ScenarioCreate,
    ScenarioUpdate,
)
from hydro_api.storage import ObjectStorage
from hydro_domain import Provenance, canonical_input_from_dict
from hydro_reporting import HydraulicReportData, build_hydraulic_calculation_pdf
from hydro_shared.codes import ErrorCode
from hydro_shared.errors import InvalidInputError
from hydro_shared.hashing import sha256_of, sha256_of_bytes
from hydro_shared.observability import correlation_id_var
from hydro_shared.versioning import INPUT_SCHEMA_VERSION
from hydroliquid import get_engine


def _flush(session: Session, conflict_message: str) -> None:
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ResourceConflictError(conflict_message) from error


def _audit(
    session: Session,
    *,
    organization_id: uuid.UUID,
    action: str,
    object_type: str,
    object_id: uuid.UUID,
    actor_id: uuid.UUID | None = None,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditEvent(
            organization_id=organization_id,
            actor_id=actor_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            details=details or {},
            created_at=utc_now(),
        )
    )


def get_organization(session: Session, organization_id: uuid.UUID) -> Organization:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise ResourceNotFoundError("Organisation", organization_id)
    return organization


def create_organization(
    session: Session,
    data: OrganizationCreate,
    *,
    actor_id: uuid.UUID | None = None,
) -> Organization:
    organization = Organization(**data.model_dump())
    session.add(organization)
    _flush(session, f"Le slug d'organisation « {data.slug} » existe déjà.")
    if actor_id is not None:
        session.add(
            OrganizationMembership(
                organization_id=organization.id,
                user_id=actor_id,
                role="admin",
            )
        )
    _audit(
        session,
        organization_id=organization.id,
        action="organization.created",
        object_type="organization",
        object_id=organization.id,
    )
    _flush(session, "Impossible d'enregistrer l'événement d'audit.")
    return organization


def list_organizations(
    session: Session,
    *,
    limit: int,
    offset: int,
    allowed_organization_ids: tuple[uuid.UUID, ...] | None = None,
) -> tuple[list[Organization], int]:
    query = select(Organization)
    count_query = select(func.count()).select_from(Organization)
    if allowed_organization_ids is not None:
        if not allowed_organization_ids:
            return [], 0
        query = query.where(Organization.id.in_(allowed_organization_ids))
        count_query = count_query.where(Organization.id.in_(allowed_organization_ids))
    total = session.scalar(count_query) or 0
    items = list(
        session.scalars(
            query.order_by(Organization.created_at, Organization.id).limit(limit).offset(offset)
        )
    )
    return items, total


def update_organization(
    session: Session,
    organization_id: uuid.UUID,
    data: OrganizationUpdate,
) -> Organization:
    organization = get_organization(session, organization_id)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in changes.items():
        setattr(organization, field, value)
    _audit(
        session,
        organization_id=organization.id,
        action="organization.updated",
        object_type="organization",
        object_id=organization.id,
        details={"fields": sorted(changes)},
    )
    _flush(session, "La mise à jour de l'organisation entre en conflit avec une donnée existante.")
    return organization


def get_project(session: Session, project_id: uuid.UUID) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise ResourceNotFoundError("Projet", project_id)
    return project


def create_project(session: Session, data: ProjectCreate) -> Project:
    get_organization(session, data.organization_id)
    if data.site_id is not None:
        site = session.get(Site, data.site_id)
        if site is None:
            raise ResourceNotFoundError("Site", data.site_id)
        if site.organization_id != data.organization_id:
            raise ResourceConflictError(
                "Le site et le projet doivent appartenir à la même organisation."
            )
    project = Project(**data.model_dump())
    if project.country_code is not None:
        project.country_code = project.country_code.upper()
    session.add(project)
    _flush(
        session,
        f"Le code projet « {data.code} » existe déjà dans cette organisation.",
    )
    _audit(
        session,
        organization_id=project.organization_id,
        action="project.created",
        object_type="project",
        object_id=project.id,
    )
    _flush(session, "Impossible d'enregistrer l'événement d'audit.")
    return project


def list_projects(
    session: Session,
    *,
    organization_id: uuid.UUID | None,
    limit: int,
    offset: int,
    allowed_organization_ids: tuple[uuid.UUID, ...] | None = None,
) -> tuple[list[Project], int]:
    query = select(Project)
    count_query = select(func.count()).select_from(Project)
    if organization_id is not None:
        query = query.where(Project.organization_id == organization_id)
        count_query = count_query.where(Project.organization_id == organization_id)
    if allowed_organization_ids is not None:
        if not allowed_organization_ids:
            return [], 0
        query = query.where(Project.organization_id.in_(allowed_organization_ids))
        count_query = count_query.where(Project.organization_id.in_(allowed_organization_ids))
    total = session.scalar(count_query) or 0
    items = list(
        session.scalars(query.order_by(Project.created_at, Project.id).limit(limit).offset(offset))
    )
    return items, total


def update_project(
    session: Session,
    project_id: uuid.UUID,
    data: ProjectUpdate,
) -> Project:
    project = get_project(session, project_id)
    changes = data.model_dump(exclude_unset=True)
    if "site_id" in changes and changes["site_id"] is not None:
        site = session.get(Site, changes["site_id"])
        if site is None:
            raise ResourceNotFoundError("Site", changes["site_id"])
        if site.organization_id != project.organization_id:
            raise ResourceConflictError(
                "Le site et le projet doivent appartenir à la même organisation."
            )
    for field, value in changes.items():
        if field in {"name", "status"} and value is None:
            continue
        if field == "country_code" and value is not None:
            value = value.upper()
        setattr(project, field, value)
    _audit(
        session,
        organization_id=project.organization_id,
        action="project.updated",
        object_type="project",
        object_id=project.id,
        details={"fields": sorted(changes)},
    )
    _flush(session, "La mise à jour du projet entre en conflit avec une donnée existante.")
    return project


def get_model_version(session: Session, model_id: uuid.UUID) -> ModelVersion:
    model = session.get(ModelVersion, model_id)
    if model is None:
        raise ResourceNotFoundError("Version de modèle", model_id)
    return model


def create_model_version(
    session: Session,
    project_id: uuid.UUID,
    data: ModelVersionCreate,
) -> ModelVersion:
    project = session.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if project is None:
        raise ResourceNotFoundError("Projet", project_id)
    if data.parent_id is not None:
        parent = get_model_version(session, data.parent_id)
        if parent.project_id != project_id:
            raise ResourceConflictError("La version parente appartient à un autre projet.")
    latest = session.scalar(
        select(func.max(ModelVersion.version_number)).where(ModelVersion.project_id == project_id)
    )
    model = ModelVersion(
        project_id=project_id,
        parent_id=data.parent_id,
        version_number=(latest or 0) + 1,
        name=data.name,
        content_hash=sha256_of(data.payload),
        payload=data.payload,
    )
    session.add(model)
    _flush(session, "Une version portant ce numéro existe déjà pour le projet.")
    _audit(
        session,
        organization_id=project.organization_id,
        action="model_version.created",
        object_type="model_version",
        object_id=model.id,
        details={"version_number": model.version_number},
    )
    _flush(session, "Impossible d'enregistrer l'événement d'audit.")
    return model


def list_model_versions(
    session: Session,
    project_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[ModelVersion], int]:
    get_project(session, project_id)
    condition = ModelVersion.project_id == project_id
    total = session.scalar(select(func.count()).select_from(ModelVersion).where(condition)) or 0
    items = list(
        session.scalars(
            select(ModelVersion)
            .where(condition)
            .order_by(ModelVersion.version_number)
            .limit(limit)
            .offset(offset)
        )
    )
    return items, total


def update_model_version(
    session: Session,
    model_id: uuid.UUID,
    data: ModelVersionUpdate,
    *,
    actor_id: uuid.UUID | None = None,
) -> ModelVersion:
    """Modifie les métadonnées d'un brouillon et recalcule son empreinte complète."""

    model = get_model_version(session, model_id)
    if model.status != "draft":
        raise ResourceConflictError(
            "Une version approuvée ou archivée est immuable ; créez un clone."
        )
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in changes.items():
        setattr(model, field, value)
    from hydro_api.services.network import refresh_model_hash

    refresh_model_hash(session, model)
    project = get_project(session, model.project_id)
    _audit(
        session,
        organization_id=project.organization_id,
        action="model_version.updated",
        object_type="model_version",
        object_id=model.id,
        actor_id=actor_id,
        details={"fields": sorted(changes)},
    )
    _flush(session, "Impossible de modifier la version du modèle.")
    return model


def approve_model_version(session: Session, model_id: uuid.UUID) -> ModelVersion:
    model = session.scalar(
        select(ModelVersion).where(ModelVersion.id == model_id).with_for_update()
    )
    if model is None:
        raise ResourceNotFoundError("Version de modèle", model_id)
    if model.status == "approved":
        return model
    if model.status != "draft":
        raise ResourceConflictError(
            "Seule une version de modèle au statut brouillon peut être approuvée."
        )
    from hydro_api.models import NetworkNode
    from hydro_api.services.network import validate_network

    normalized_node_count = session.scalar(
        select(func.count()).select_from(NetworkNode).where(NetworkNode.model_version_id == model.id)
    ) or 0
    if normalized_node_count:
        validation = validate_network(session, model.id)
        if not validation.valid:
            details = "; ".join(f"{issue.code}: {issue.message}" for issue in validation.errors)
            raise ResourceConflictError(
                "Le réseau normalisé doit être valide avant approbation. " + details
            )
    existing = session.scalar(
        select(ModelVersion.id).where(
            ModelVersion.project_id == model.project_id,
            ModelVersion.status == "approved",
            ModelVersion.id != model.id,
        )
    )
    if existing is not None:
        raise ResourceConflictError(
            "Une autre version du projet est déjà approuvée. Archivez-la avant l'approbation."
        )
    project = get_project(session, model.project_id)
    model.status = "approved"
    model.approved_at = utc_now()
    _audit(
        session,
        organization_id=project.organization_id,
        action="model_version.approved",
        object_type="model_version",
        object_id=model.id,
        details={"content_hash": model.content_hash},
    )
    _flush(session, "Impossible d'approuver la version du modèle.")
    return model


def archive_model_version(
    session: Session,
    model_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None = None,
) -> ModelVersion:
    """Archive une version sans altérer son contenu ni son approbation passée."""

    model = session.scalar(
        select(ModelVersion).where(ModelVersion.id == model_id).with_for_update()
    )
    if model is None:
        raise ResourceNotFoundError("Version de modèle", model_id)
    if model.status == "archived":
        return model
    project = get_project(session, model.project_id)
    previous_status = model.status
    model.status = "archived"
    _audit(
        session,
        organization_id=project.organization_id,
        action="model_version.archived",
        object_type="model_version",
        object_id=model.id,
        actor_id=actor_id,
        details={"previous_status": previous_status},
    )
    _flush(session, "Impossible d'archiver la version du modèle.")
    return model


def get_scenario(session: Session, scenario_id: uuid.UUID) -> ScenarioRecord:
    item = session.get(ScenarioRecord, scenario_id)
    if item is None:
        raise ResourceNotFoundError("Scénario", scenario_id)
    return item


def create_scenario(
    session: Session,
    model_id: uuid.UUID,
    data: ScenarioCreate,
) -> ScenarioRecord:
    model = get_model_version(session, model_id)
    if data.parent_id is not None:
        parent = get_scenario(session, data.parent_id)
        if parent.model_version_id != model_id:
            raise ResourceConflictError(
                "Le scénario parent appartient à une autre version de modèle."
            )
    item = ScenarioRecord(
        model_version_id=model_id,
        parent_id=data.parent_id,
        name=data.name,
        description=data.description,
        payload=data.payload,
    )
    session.add(item)
    _flush(
        session,
        f"Un scénario nommé « {data.name} » existe déjà dans cette version.",
    )
    project = get_project(session, model.project_id)
    _audit(
        session,
        organization_id=project.organization_id,
        action="scenario.created",
        object_type="scenario",
        object_id=item.id,
    )
    _flush(session, "Impossible d'enregistrer l'événement d'audit.")
    return item


def list_scenarios(
    session: Session,
    model_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[ScenarioRecord], int]:
    get_model_version(session, model_id)
    condition = ScenarioRecord.model_version_id == model_id
    total = session.scalar(select(func.count()).select_from(ScenarioRecord).where(condition)) or 0
    items = list(
        session.scalars(
            select(ScenarioRecord)
            .where(condition)
            .order_by(ScenarioRecord.created_at, ScenarioRecord.id)
            .limit(limit)
            .offset(offset)
        )
    )
    return items, total


def update_scenario(
    session: Session,
    scenario_id: uuid.UUID,
    data: ScenarioUpdate,
) -> ScenarioRecord:
    item = get_scenario(session, scenario_id)
    model = get_model_version(session, item.model_version_id)
    if model.status != "draft":
        raise ResourceConflictError(
            "Un scénario lié à une version approuvée ou archivée est immuable. Clonez la version."
        )
    changes = data.model_dump(exclude_unset=True)

    for field, value in changes.items():
        if field == "name" and value is None:
            continue
        setattr(item, field, value)
    project = get_project(session, model.project_id)
    _audit(
        session,
        organization_id=project.organization_id,
        action="scenario.updated",
        object_type="scenario",
        object_id=item.id,
        details={"fields": sorted(changes)},
    )
    _flush(session, "La mise à jour du scénario entre en conflit avec une donnée existante.")
    return item


def get_calculation(session: Session, calculation_id: uuid.UUID) -> CalculationRun:
    """Lit une exécution sans modifier son contenu immuable."""

    calculation = session.get(CalculationRun, calculation_id)
    if calculation is None:
        raise ResourceNotFoundError("Calcul", calculation_id)
    return calculation


def canonical_payload_for_calculation(
    session: Session,
    model: ModelVersion,
    scenario: ScenarioRecord,
    *,
    engine_name: str,
    engine_version: str,
    organization_id: uuid.UUID,
) -> dict[str, Any]:
    """Assemble les sections modèle et scénario avant désérialisation stricte."""

    model_payload = deepcopy(model.payload)
    if not isinstance(model_payload, dict):
        raise InvalidInputError(
            "Le contenu de la version de modèle doit être un objet JSON.",
            model_version_id=str(model.id),
        )
    scenario_payload = deepcopy(scenario.payload)
    if not isinstance(scenario_payload, dict):
        raise InvalidInputError(
            "Le contenu du scénario doit être un objet JSON.",
            scenario_id=str(scenario.id),
        )

    scenario_payload["id"] = str(scenario.id)
    scenario_payload["name"] = scenario.name
    if scenario.description is not None:
        scenario_payload["description"] = scenario.description

    from hydro_api.models import NetworkNode

    normalized_node_count = session.scalar(
        select(func.count()).select_from(NetworkNode).where(NetworkNode.model_version_id == model.id)
    ) or 0
    fluid: Any
    network: Any
    equipment: Any
    if normalized_node_count:
        from hydro_api.services.network import canonical_sections_from_normalized

        fluid, network, equipment = canonical_sections_from_normalized(session, model)
    else:
        network = model_payload.get("network")
        fluid = model_payload.get("fluid")
        equipment = model_payload.get("equipment", {"pump_models": []})
    source_manifest = model_payload.get("manifest")
    if source_manifest is None:
        source_manifest = {}
    if not isinstance(source_manifest, dict):
        raise InvalidInputError(
            "La section « manifest » de la version de modèle doit être un objet JSON.",
            model_version_id=str(model.id),
        )

    network_id = network.get("id", "") if isinstance(network, dict) else ""
    fluid_id = fluid.get("id", "") if isinstance(fluid, dict) else ""
    return {
        "manifest": {
            "schema_version": source_manifest.get(
                "schema_version",
                INPUT_SCHEMA_VERSION,
            ),
            "engine": engine_name,
            "engine_version": engine_version,
            "pipeline_id": network_id,
            "fluid_id": fluid_id,
            "scenario_id": str(scenario.id),
        },
        "units": model_payload.get("units", {}),
        "fluid": fluid,
        "network": network,
        "equipment": equipment,
        "scenario": scenario_payload,
        "rules": model_payload.get("rules", {"rule_set_ids": []}),
        "provenance": Provenance.now(
            project_id=str(model.project_id),
            model_version_id=str(model.id),
            organization_id=str(organization_id),
            client_reference=str(scenario.id),
        ).as_dict(),
    }


def queue_calculation(
    session: Session,
    scenario_id: uuid.UUID,
    data: CalculationCreate,
    *,
    idempotency_key: str,
) -> CalculationRun:
    """Valide l'entrée, crée l'exécution en attente et persiste sa tâche."""

    existing = session.scalar(
        select(CalculationRun).where(
            CalculationRun.scenario_id == scenario_id,
            CalculationRun.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.engine != data.engine:
            raise ResourceConflictError(
                "La clé d'idempotence a déjà été utilisée avec un autre moteur."
            )
        return existing

    scenario = get_scenario(session, scenario_id)
    model = get_model_version(session, scenario.model_version_id)
    project = get_project(session, model.project_id)
    try:
        engine = get_engine(data.engine)
    except KeyError as error:
        raise InvalidInputError(
            str(error),
            code=ErrorCode.ENGINE_UNSUPPORTED_CASE,
            engine=data.engine,
        ) from error

    engine_version = f"{engine.name}-{engine.version}"
    canonical_payload = canonical_payload_for_calculation(
        session,
        model,
        scenario,
        engine_name=engine.name,
        engine_version=engine_version,
        organization_id=project.organization_id,
    )
    canonical_input = canonical_input_from_dict(canonical_payload)
    from hydro_api.services.governance import validate_rule_sets_for_calculation

    validate_rule_sets_for_calculation(
        session,
        project.organization_id,
        canonical_input.rule_set_ids,
    )
    if not engine.supports(canonical_input):
        raise InvalidInputError(
            "Le moteur choisi ne couvre pas la topologie ou les équipements de ce modèle.",
            code=ErrorCode.ENGINE_UNSUPPORTED_CASE,
            engine=engine.name,
        )

    calculation = CalculationRun(
        scenario_id=scenario.id,
        idempotency_key=idempotency_key,
        engine=engine.name,
        engine_version=engine_version,
        status="SIM_QUEUED",
        input_hash=canonical_input.fingerprint,
        input_payload=canonical_input.as_dict(),
        created_at=utc_now(),
    )
    session.add(calculation)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        duplicate = session.scalar(
            select(CalculationRun).where(
                CalculationRun.scenario_id == scenario_id,
                CalculationRun.idempotency_key == idempotency_key,
            )
        )
        if duplicate is not None:
            if duplicate.engine != data.engine:
                raise ResourceConflictError(
                    "La clé d'idempotence a déjà été utilisée avec un autre moteur."
                ) from error
            return duplicate
        raise ResourceConflictError(
            "Le calcul entre en conflit avec une exécution existante."
        ) from error

    job = BackgroundJob(
        kind="calculation",
        resource_id=calculation.id,
        status="queued",
        payload={
            "calculation_id": str(calculation.id),
            "correlation_id": correlation_id_var.get(),
        },
        attempts=0,
        maximum_attempts=3,
        available_at=utc_now(),
    )
    session.add(job)
    _audit(
        session,
        organization_id=project.organization_id,
        action="calculation.queued",
        object_type="calculation",
        object_id=calculation.id,
        details={
            "engine": calculation.engine,
            "input_hash": calculation.input_hash,
        },
    )
    _flush(session, "Impossible d'enregistrer la tâche du calcul.")
    return calculation


def execute_calculation(
    session: Session,
    calculation_id: uuid.UUID,
) -> CalculationRun:
    """Exécute une tâche préparée et fige son résultat scientifique."""

    calculation = get_calculation(session, calculation_id)
    if calculation.finished_at is not None:
        return calculation
    try:
        engine = get_engine(calculation.engine)
    except KeyError as error:
        raise InvalidInputError(
            str(error),
            code=ErrorCode.ENGINE_UNSUPPORTED_CASE,
            engine=calculation.engine,
        ) from error
    canonical_input = canonical_input_from_dict(calculation.input_payload)
    if not engine.supports(canonical_input):
        raise InvalidInputError(
            "Le moteur choisi ne couvre plus ce paquet canonique.",
            code=ErrorCode.ENGINE_UNSUPPORTED_CASE,
            engine=engine.name,
        )

    calculation.status = "SIM_RUNNING"
    calculation.started_at = calculation.started_at or utc_now()
    result = engine.simulate(canonical_input)
    session.expire(calculation)
    locked_calculation = session.scalar(
        select(CalculationRun).where(CalculationRun.id == calculation_id).with_for_update()
    )
    if locked_calculation is None:
        raise ResourceNotFoundError("Calcul", calculation_id)
    calculation = locked_calculation
    if calculation.status == "SIM_CANCELLED":
        return calculation
    result_payload = result.as_dict()
    result_payload["explanation"] = engine.explain(result).as_dict()
    from hydro_api.services.governance import evaluate_calculation_rules

    evaluations = evaluate_calculation_rules(session, calculation, result_payload)
    result_payload["rule_evaluations"] = [
        {
            "id": str(item.id),
            "rule_set_id": str(item.rule_set_id),
            "rule_id": str(item.rule_id),
            "status": item.status,
            "measured_value": item.measured_value,
            "limit_value": item.limit_value,
            "margin": item.margin,
            "unit": item.unit,
            "message": item.message,
        }
        for item in evaluations
    ]
    calculation.engine_version = result.engine_version
    calculation.status = result.status.value
    calculation.result_payload = result_payload
    calculation.diagnostics = result.diagnostics.as_dict()
    calculation.finished_at = utc_now()

    organization_id = calculation.scenario.model_version.project.organization_id
    _audit(
        session,
        organization_id=organization_id,
        action="calculation.completed",
        object_type="calculation",
        object_id=calculation.id,
        details={
            "engine": calculation.engine,
            "input_hash": calculation.input_hash,
            "status": calculation.status,
        },
    )
    _flush(session, "Impossible d'enregistrer le résultat du calcul.")
    return calculation


def cancel_calculation(
    session: Session,
    calculation_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None = None,
) -> CalculationRun:
    """Annule une exécution en attente ou en cours et neutralise sa tâche."""

    calculation = session.scalar(
        select(CalculationRun).where(CalculationRun.id == calculation_id).with_for_update()
    )
    if calculation is None:
        raise ResourceNotFoundError("Calcul", calculation_id)
    if calculation.status == "SIM_CANCELLED":
        return calculation
    if calculation.status not in {"SIM_QUEUED", "SIM_RUNNING"}:
        raise ResourceConflictError("Un calcul terminé ne peut plus être annulé.")
    job = session.scalar(
        select(BackgroundJob)
        .where(
            BackgroundJob.kind == "calculation",
            BackgroundJob.resource_id == calculation.id,
        )
        .with_for_update()
    )
    if job is not None and job.status in {"queued", "running"}:
        job.status = "cancelled"
        job.locked_at = None
        job.finished_at = utc_now()
    calculation.status = "SIM_CANCELLED"
    calculation.finished_at = utc_now()
    calculation.diagnostics = {"reason": "Annulation demandée par un utilisateur autorisé."}
    organization_id = calculation.scenario.model_version.project.organization_id
    _audit(
        session,
        organization_id=organization_id,
        action="calculation.cancelled",
        object_type="calculation",
        object_id=calculation.id,
        actor_id=actor_id,
        details={"job_id": str(job.id) if job is not None else None},
    )
    _flush(session, "Impossible d'annuler le calcul.")
    return calculation


def rerun_calculation(
    session: Session,
    calculation_id: uuid.UUID,
    *,
    idempotency_key: str,
    synchronous: bool,
    actor_id: uuid.UUID | None = None,
) -> CalculationRun:
    """Crée une nouvelle exécution à partir de l'entrée canonique archivée."""

    source = get_calculation(session, calculation_id)
    if source.status in {"SIM_QUEUED", "SIM_RUNNING"}:
        raise ResourceConflictError("Attendez la fin ou annulez le calcul avant de le relancer.")
    existing = session.scalar(
        select(CalculationRun).where(
            CalculationRun.scenario_id == source.scenario_id,
            CalculationRun.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.engine != source.engine or existing.input_hash != source.input_hash:
            raise ResourceConflictError(
                "La clé d'idempotence désigne une autre exécution de ce scénario."
            )
        return existing

    replay = CalculationRun(
        scenario_id=source.scenario_id,
        idempotency_key=idempotency_key,
        engine=source.engine,
        engine_version=source.engine_version,
        status="SIM_QUEUED",
        input_hash=source.input_hash,
        input_payload=deepcopy(source.input_payload),
        created_at=utc_now(),
    )
    session.add(replay)
    session.flush()
    job = BackgroundJob(
        kind="calculation",
        resource_id=replay.id,
        status="queued",
        payload={
            "calculation_id": str(replay.id),
            "source_calculation_id": str(source.id),
            "correlation_id": correlation_id_var.get(),
        },
        attempts=0,
        maximum_attempts=3,
        available_at=utc_now(),
    )
    session.add(job)
    organization_id = source.scenario.model_version.project.organization_id
    _audit(
        session,
        organization_id=organization_id,
        action="calculation.rerun_queued",
        object_type="calculation",
        object_id=replay.id,
        actor_id=actor_id,
        details={
            "source_calculation_id": str(source.id),
            "input_hash": replay.input_hash,
        },
    )
    _flush(session, "Impossible de mettre la relance du calcul en file.")
    if synchronous:
        execute_calculation(session, replay.id)
        job.status = "completed"
        job.finished_at = utc_now()
        session.flush()
    return replay


def create_calculation(
    session: Session,
    scenario_id: uuid.UUID,
    data: CalculationCreate,
    *,
    idempotency_key: str,
) -> CalculationRun:
    """Exécute immédiatement un calcul pour les tests et le développement local."""

    calculation = queue_calculation(
        session,
        scenario_id,
        data,
        idempotency_key=idempotency_key,
    )
    if calculation.status == "SIM_QUEUED":
        execute_calculation(session, calculation.id)
        job = session.scalar(
            select(BackgroundJob).where(
                BackgroundJob.kind == "calculation",
                BackgroundJob.resource_id == calculation.id,
            )
        )
        if job is not None:
            job.status = "completed"
            job.finished_at = utc_now()
            session.flush()
    return calculation


def calculation_summary(calculation: CalculationRun) -> dict[str, Any]:
    """Extrait la synthèse persistée sans profil ni tableaux détaillés."""

    if calculation.result_payload is None:
        return {
            "status": calculation.status,
            "input_hash": calculation.input_hash,
        }
    detailed_keys = {
        "assumptions",
        "diagnostics",
        "energy",
        "environment",
        "explanation",
        "gravity_zones",
        "profile",
        "segments",
        "stations",
    }
    return {
        key: value for key, value in calculation.result_payload.items() if key not in detailed_keys
    }


def get_report(session: Session, report_id: uuid.UUID) -> GeneratedReport:
    """Lit les métadonnées d'un rapport archivé."""

    report = session.get(GeneratedReport, report_id)
    if report is None:
        raise ResourceNotFoundError("Rapport", report_id)
    return report


def get_report_file(session: Session, report: GeneratedReport) -> StoredFile:
    """Résout le fichier privé associé au rapport."""

    stored_file = session.get(StoredFile, report.file_id)
    if stored_file is None:
        raise ResourceNotFoundError("Fichier du rapport", report.file_id)
    return stored_file


def _report_parameters_match(report: GeneratedReport, data: ReportCreate) -> bool:
    return (
        report.report_type == data.report_type
        and report.template_version == data.template_version
        and report.format == data.format
        and report.locale == data.locale
    )


def create_report(
    session: Session,
    calculation_id: uuid.UUID,
    data: ReportCreate,
    *,
    idempotency_key: str,
    storage: ObjectStorage,
) -> GeneratedReport:
    """Génère, archive et trace une note de calcul RPT-02."""

    existing = session.scalar(
        select(GeneratedReport).where(
            GeneratedReport.source_type == "calculation",
            GeneratedReport.source_id == calculation_id,
            GeneratedReport.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if not _report_parameters_match(existing, data):
            raise ResourceConflictError(
                "La clé d'idempotence du rapport a déjà été utilisée avec d'autres paramètres."
            )
        return existing

    calculation = get_calculation(session, calculation_id)
    if calculation.result_payload is None:
        raise ResourceConflictError(
            "Le calcul ne possède pas encore de résultat exploitable pour produire un rapport."
        )
    scenario = get_scenario(session, calculation.scenario_id)
    model = get_model_version(session, scenario.model_version_id)
    project = get_project(session, model.project_id)

    generated_at = utc_now()
    report_id = uuid.uuid4()
    file_id = uuid.uuid4()
    report_data = HydraulicReportData(
        report_id=str(report_id),
        calculation_id=str(calculation.id),
        project_name=project.name,
        project_code=project.code,
        model_name=model.name,
        model_version=model.version_number,
        scenario_name=scenario.name,
        generated_at=generated_at,
        input_payload=calculation.input_payload,
        result_payload=calculation.result_payload,
        template_version=data.template_version,
        locale=data.locale,
    )
    content = build_hydraulic_calculation_pdf(report_data)
    content_hash = sha256_of_bytes(content)
    safe_code = re.sub(r"[^A-Za-z0-9._-]+", "-", project.code).strip("-") or "projet"
    filename = f"note-calcul-{safe_code}-{str(calculation.id)[:8]}.pdf"
    object_key = f"organizations/{project.organization_id}/reports/{report_id}/{filename}"
    storage.put_bytes(object_key, content, "application/pdf")

    stored_file = StoredFile(
        id=file_id,
        organization_id=project.organization_id,
        bucket=storage.bucket,
        object_key=object_key,
        filename=filename,
        media_type="application/pdf",
        size_bytes=len(content),
        content_hash=content_hash,
        created_at=generated_at,
    )
    report = GeneratedReport(
        id=report_id,
        organization_id=project.organization_id,
        calculation_id=calculation.id,
        source_type="calculation",
        source_id=calculation.id,
        file_id=file_id,
        idempotency_key=idempotency_key,
        report_type=data.report_type,
        template_version=data.template_version,
        format=data.format,
        locale=data.locale,
        status="generated",
        content_hash=content_hash,
        created_at=generated_at,
    )
    session.add_all([stored_file, report])
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        storage.delete(object_key)
        duplicate = session.scalar(
            select(GeneratedReport).where(
                GeneratedReport.source_type == "calculation",
                GeneratedReport.source_id == calculation_id,
                GeneratedReport.idempotency_key == idempotency_key,
            )
        )
        if duplicate is not None and _report_parameters_match(duplicate, data):
            return duplicate
        raise ResourceConflictError(
            "Le rapport entre en conflit avec une génération existante."
        ) from error

    _audit(
        session,
        organization_id=project.organization_id,
        action="report.generated",
        object_type="report",
        object_id=report.id,
        details={
            "calculation_id": str(calculation.id),
            "content_hash": content_hash,
            "template_version": data.template_version,
        },
    )
    _flush(session, "Impossible d'enregistrer l'événement d'audit du rapport.")
    return report


def approve_report(
    session: Session,
    report_id: uuid.UUID,
    data: ReportApproval,
) -> GeneratedReport:
    """Enregistre une décision humaine définitive sur un rapport."""

    report = session.scalar(
        select(GeneratedReport).where(GeneratedReport.id == report_id).with_for_update()
    )
    if report is None:
        raise ResourceNotFoundError("Rapport", report_id)
    if report.status != "generated":
        if report.status == data.decision and report.approval_comment == data.comment:
            return report
        raise ResourceConflictError(
            "Une décision a déjà été enregistrée pour ce rapport et ne peut pas être remplacée."
        )

    report.status = data.decision
    report.approved_at = utc_now()
    report.approval_comment = data.comment
    _audit(
        session,
        organization_id=report.organization_id,
        action=f"report.{data.decision}",
        object_type="report",
        object_id=report.id,
        details={"comment_present": bool(data.comment)},
    )
    _flush(session, "Impossible d'enregistrer la décision portée sur le rapport.")
    return report
