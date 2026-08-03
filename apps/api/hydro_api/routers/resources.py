"""Routes REST pour organisations, projets, versions et scénarios."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy.orm import Session

from hydro_api.database.session import get_session
from hydro_api.schemas import (
    ApprovalResponse,
    CalculationCreate,
    CalculationRead,
    CalculationResultRead,
    CalculationSummaryRead,
    ModelVersionCreate,
    ModelVersionRead,
    ModelVersionUpdate,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
    Page,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    ReportApproval,
    ReportCreate,
    ReportRead,
    ScenarioCreate,
    ScenarioRead,
    ScenarioUpdate,
)
from hydro_api.services import core
from hydro_api.storage import ObjectStorageDependency

router = APIRouter()
DatabaseSession = Annotated[Session, Depends(get_session, scope="function")]
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=100,
        description="Clé stable permettant de rejouer la requête sans créer de doublon.",
    ),
]


@router.post(
    "/organizations",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une organisation",
)
def create_organization(
    data: OrganizationCreate,
    request: Request,
    session: DatabaseSession,
):
    access = request.state.access_context
    return core.create_organization(session, data, actor_id=access.user_id)


@router.get(
    "/organizations",
    response_model=Page[OrganizationRead],
    summary="Lister les organisations",
)
def list_organizations(
    request: Request,
    session: DatabaseSession,
    limit: Limit = 50,
    offset: Offset = 0,
):
    access = request.state.access_context
    allowed_ids = None if access.local_bypass else access.organization_ids
    items, total = core.list_organizations(
        session,
        limit=limit,
        offset=offset,
        allowed_organization_ids=allowed_ids,
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/organizations/{organization_id}",
    response_model=OrganizationRead,
    summary="Lire une organisation",
)
def read_organization(organization_id: uuid.UUID, session: DatabaseSession):
    return core.get_organization(session, organization_id)


@router.patch(
    "/organizations/{organization_id}",
    response_model=OrganizationRead,
    summary="Modifier une organisation",
)
def update_organization(
    organization_id: uuid.UUID,
    data: OrganizationUpdate,
    session: DatabaseSession,
):
    return core.update_organization(session, organization_id, data)


@router.post(
    "/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un projet",
)
def create_project(data: ProjectCreate, session: DatabaseSession):
    return core.create_project(session, data)


@router.get(
    "/projects",
    response_model=Page[ProjectRead],
    summary="Lister les projets",
)
def list_projects(
    request: Request,
    session: DatabaseSession,
    organization_id: uuid.UUID | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    access = request.state.access_context
    allowed_ids = None if access.local_bypass else access.organization_ids
    items, total = core.list_projects(
        session,
        organization_id=organization_id,
        limit=limit,
        offset=offset,
        allowed_organization_ids=allowed_ids,
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/projects/{project_id}",
    response_model=ProjectRead,
    summary="Lire un projet",
)
def read_project(project_id: uuid.UUID, session: DatabaseSession):
    return core.get_project(session, project_id)


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectRead,
    summary="Modifier un projet",
)
def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    session: DatabaseSession,
):
    return core.update_project(session, project_id, data)


@router.post(
    "/projects/{project_id}/models",
    response_model=ModelVersionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une version du modèle",
)
def create_model_version(
    project_id: uuid.UUID,
    data: ModelVersionCreate,
    session: DatabaseSession,
):
    return core.create_model_version(session, project_id, data)


@router.get(
    "/projects/{project_id}/models",
    response_model=Page[ModelVersionRead],
    summary="Lister les versions d'un projet",
)
def list_model_versions(
    project_id: uuid.UUID,
    session: DatabaseSession,
    limit: Limit = 50,
    offset: Offset = 0,
):
    items, total = core.list_model_versions(
        session,
        project_id,
        limit=limit,
        offset=offset,
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/models/{model_id}",
    response_model=ModelVersionRead,
    summary="Lire une version du modèle",
)
def read_model_version(model_id: uuid.UUID, session: DatabaseSession):
    return core.get_model_version(session, model_id)


@router.patch(
    "/models/{model_id}",
    response_model=ModelVersionRead,
    summary="Modifier une version du modèle en brouillon",
)
def update_model_version(
    model_id: uuid.UUID,
    data: ModelVersionUpdate,
    request: Request,
    session: DatabaseSession,
):
    access = request.state.access_context
    return core.update_model_version(session, model_id, data, actor_id=access.user_id)


@router.post(
    "/models/{model_id}/approve",
    response_model=ApprovalResponse,
    summary="Approuver une version du modèle",
)
def approve_model_version(model_id: uuid.UUID, session: DatabaseSession):
    model = core.approve_model_version(session, model_id)
    if model.approved_at is None:
        raise RuntimeError("Une version approuvée doit porter une date d'approbation.")
    return ApprovalResponse(
        id=model.id,
        status=model.status,
        approved_at=model.approved_at,
    )


@router.post(
    "/models/{model_id}/archive",
    response_model=ModelVersionRead,
    summary="Archiver une version du modèle",
)
def archive_model_version(
    model_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
):
    access = request.state.access_context
    return core.archive_model_version(session, model_id, actor_id=access.user_id)


@router.post(
    "/models/{model_id}/scenarios",
    response_model=ScenarioRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un scénario",
)
def create_scenario(
    model_id: uuid.UUID,
    data: ScenarioCreate,
    session: DatabaseSession,
):
    return core.create_scenario(session, model_id, data)


@router.get(
    "/models/{model_id}/scenarios",
    response_model=Page[ScenarioRead],
    summary="Lister les scénarios d'une version",
)
def list_scenarios(
    model_id: uuid.UUID,
    session: DatabaseSession,
    limit: Limit = 50,
    offset: Offset = 0,
):
    items, total = core.list_scenarios(
        session,
        model_id,
        limit=limit,
        offset=offset,
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/scenarios/{scenario_id}",
    response_model=ScenarioRead,
    summary="Lire un scénario",
)
def read_scenario(scenario_id: uuid.UUID, session: DatabaseSession):
    return core.get_scenario(session, scenario_id)


@router.patch(
    "/scenarios/{scenario_id}",
    response_model=ScenarioRead,
    summary="Modifier un scénario",
)
def update_scenario(
    scenario_id: uuid.UUID,
    data: ScenarioUpdate,
    session: DatabaseSession,
):
    return core.update_scenario(session, scenario_id, data)


@router.post(
    "/scenarios/{scenario_id}/calculations",
    response_model=CalculationRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Lancer un calcul hydraulique",
)
def create_calculation(
    scenario_id: uuid.UUID,
    data: CalculationCreate,
    request: Request,
    session: DatabaseSession,
    idempotency_key: IdempotencyKey,
):
    if request.app.state.settings.background_jobs_enabled:
        return core.queue_calculation(
            session,
            scenario_id,
            data,
            idempotency_key=idempotency_key,
        )
    return core.create_calculation(
        session,
        scenario_id,
        data,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/calculations/{calculation_id}",
    response_model=CalculationRead,
    summary="Lire l'état d'un calcul",
)
def read_calculation(calculation_id: uuid.UUID, session: DatabaseSession):
    return core.get_calculation(session, calculation_id)


@router.post(
    "/calculations/{calculation_id}/cancel",
    response_model=CalculationRead,
    summary="Annuler un calcul en attente ou en cours",
)
def cancel_calculation(
    calculation_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
):
    access = request.state.access_context
    return core.cancel_calculation(session, calculation_id, actor_id=access.user_id)


@router.post(
    "/calculations/{calculation_id}/rerun",
    response_model=CalculationRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Relancer exactement l'entrée archivée d'un calcul",
)
def rerun_calculation(
    calculation_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    idempotency_key: IdempotencyKey,
):
    access = request.state.access_context
    return core.rerun_calculation(
        session,
        calculation_id,
        idempotency_key=idempotency_key,
        synchronous=not request.app.state.settings.background_jobs_enabled,
        actor_id=access.user_id,
    )


@router.get(
    "/calculations/{calculation_id}/summary",
    response_model=CalculationSummaryRead,
    summary="Lire la synthèse d'un calcul",
)
def read_calculation_summary(calculation_id: uuid.UUID, session: DatabaseSession):
    calculation = core.get_calculation(session, calculation_id)
    return CalculationSummaryRead(
        calculation_id=calculation.id,
        status=calculation.status,
        summary=core.calculation_summary(calculation),
    )


@router.get(
    "/calculations/{calculation_id}/results",
    response_model=CalculationResultRead,
    summary="Lire le résultat complet d'un calcul",
)
def read_calculation_results(calculation_id: uuid.UUID, session: DatabaseSession):
    calculation = core.get_calculation(session, calculation_id)
    return CalculationResultRead(
        calculation_id=calculation.id,
        status=calculation.status,
        result=calculation.result_payload,
        diagnostics=calculation.diagnostics,
    )


@router.post(
    "/calculations/{calculation_id}/reports",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Générer une note de calcul",
)
def create_report(
    calculation_id: uuid.UUID,
    data: ReportCreate,
    session: DatabaseSession,
    storage: ObjectStorageDependency,
    idempotency_key: IdempotencyKey,
):
    return core.create_report(
        session,
        calculation_id,
        data,
        idempotency_key=idempotency_key,
        storage=storage,
    )


@router.get(
    "/reports/{report_id}",
    response_model=ReportRead,
    summary="Lire les métadonnées d'un rapport",
)
def read_report(report_id: uuid.UUID, session: DatabaseSession):
    return core.get_report(session, report_id)


@router.get(
    "/reports/{report_id}/download",
    summary="Télécharger un rapport",
    response_class=Response,
)
def download_report(
    report_id: uuid.UUID,
    session: DatabaseSession,
    storage: ObjectStorageDependency,
):
    report = core.get_report(session, report_id)
    stored_file = core.get_report_file(session, report)
    content = storage.get_bytes(stored_file.object_key)
    return Response(
        content=content,
        media_type=stored_file.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{stored_file.filename}"',
            "ETag": f'"{stored_file.content_hash}"',
            "Content-Length": str(stored_file.size_bytes),
        },
    )


@router.post(
    "/reports/{report_id}/approve",
    response_model=ReportRead,
    summary="Approuver ou rejeter un rapport",
)
def approve_report(
    report_id: uuid.UUID,
    data: ReportApproval,
    session: DatabaseSession,
):
    return core.approve_report(session, report_id, data)
