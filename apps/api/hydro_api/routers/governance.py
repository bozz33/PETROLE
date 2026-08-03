"""Routes administratives de gouvernance et d'audit."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query, status

from hydro_api.errors import ResourceConflictError
from hydro_api.schemas import (
    AuditEventRead,
    Page,
    RuleCreate,
    RuleEvaluationRead,
    RuleRead,
    RuleSetCreate,
    RuleSetRead,
    StandardCreate,
    StandardRead,
    StandardUpdate,
)
from hydro_api.security import ApplicationAccess, DatabaseSession
from hydro_api.services import core, governance

router = APIRouter(tags=["gouvernance"])
StandardStatus = Literal["draft", "active", "withdrawn", "archived"]
RuleSetStatus = Literal["draft", "approved", "archived"]
EvaluationStatus = Literal["compliant", "non_compliant", "not_applicable", "error"]


@router.post(
    "/standards",
    response_model=StandardRead,
    status_code=status.HTTP_201_CREATED,
    summary="Enregistrer une édition normative",
)
def create_standard(
    data: StandardCreate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> StandardRead:
    return StandardRead.model_validate(
        governance.create_standard(session, data, actor_id=access.user_id)
    )


@router.get(
    "/standards",
    response_model=Page[StandardRead],
    summary="Lister les éditions normatives",
)
def list_standards(
    organization_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
    item_status: Annotated[StandardStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[StandardRead]:
    del access
    items, total = governance.list_standards(
        session,
        organization_id,
        status=item_status,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[StandardRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/standards/{standard_id}",
    response_model=StandardRead,
    summary="Lire une édition normative",
)
def get_standard(
    standard_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> StandardRead:
    del access
    return StandardRead.model_validate(governance.get_standard(session, standard_id))


@router.patch(
    "/standards/{standard_id}",
    response_model=StandardRead,
    summary="Modifier une édition normative en brouillon",
)
def update_standard(
    standard_id: uuid.UUID,
    data: StandardUpdate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> StandardRead:
    return StandardRead.model_validate(
        governance.update_standard(session, standard_id, data, actor_id=access.user_id)
    )


@router.post(
    "/standards/{standard_id}/approve",
    response_model=StandardRead,
    summary="Activer une édition normative vérifiée",
)
def approve_standard(
    standard_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> StandardRead:
    return StandardRead.model_validate(
        governance.approve_standard(session, standard_id, actor_id=access.user_id)
    )


@router.post(
    "/rule-sets",
    response_model=RuleSetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une version de jeu de règles",
)
def create_rule_set(
    data: RuleSetCreate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> RuleSetRead:
    item = governance.create_rule_set(session, data, actor_id=access.user_id)
    return RuleSetRead.model_validate(governance.serialize_rule_set(session, item))


@router.get(
    "/rule-sets",
    response_model=Page[RuleSetRead],
    summary="Lister les jeux de règles versionnés",
)
def list_rule_sets(
    organization_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
    item_status: Annotated[RuleSetStatus | None, Query(alias="status")] = None,
    domain: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[RuleSetRead]:
    del access
    items, total = governance.list_rule_sets(
        session,
        organization_id,
        status=item_status,
        domain=domain,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[
            RuleSetRead.model_validate(governance.serialize_rule_set(session, item))
            for item in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/rule-sets/{rule_set_id}",
    response_model=RuleSetRead,
    summary="Lire une version de jeu de règles",
)
def get_rule_set(
    rule_set_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> RuleSetRead:
    del access
    item = governance.get_rule_set(session, rule_set_id)
    return RuleSetRead.model_validate(governance.serialize_rule_set(session, item))


@router.post(
    "/rule-sets/{rule_set_id}/rules",
    response_model=RuleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une règle seuil synthétique",
)
def create_rule(
    rule_set_id: uuid.UUID,
    data: RuleCreate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> RuleRead:
    return RuleRead.model_validate(
        governance.create_rule(session, rule_set_id, data, actor_id=access.user_id)
    )


@router.get(
    "/rule-sets/{rule_set_id}/rules",
    response_model=list[RuleRead],
    summary="Lister les règles d'une version",
)
def list_rules(
    rule_set_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> list[RuleRead]:
    del access
    return [
        RuleRead.model_validate(item) for item in governance.list_rules(session, rule_set_id)
    ]


@router.post(
    "/rules/{rule_id}/approve",
    response_model=RuleRead,
    summary="Approuver une règle après revue experte",
)
def approve_rule(
    rule_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> RuleRead:
    return RuleRead.model_validate(
        governance.approve_rule(session, rule_id, actor_id=access.user_id)
    )


@router.post(
    "/rule-sets/{rule_set_id}/approve",
    response_model=RuleSetRead,
    summary="Approuver et figer un jeu de règles",
)
def approve_rule_set(
    rule_set_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> RuleSetRead:
    item = governance.approve_rule_set(session, rule_set_id, actor_id=access.user_id)
    return RuleSetRead.model_validate(governance.serialize_rule_set(session, item))


@router.get(
    "/evaluations",
    response_model=Page[RuleEvaluationRead],
    summary="Lister les évaluations normatives",
)
def list_evaluations(
    organization_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
    calculation_id: uuid.UUID | None = None,
    rule_set_id: uuid.UUID | None = None,
    evaluation_status: Annotated[EvaluationStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[RuleEvaluationRead]:
    del access
    items, total = governance.list_rule_evaluations(
        session,
        organization_id,
        calculation_id=calculation_id,
        rule_set_id=rule_set_id,
        status=evaluation_status,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[RuleEvaluationRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/calculations/{calculation_id}/evaluations",
    response_model=list[RuleEvaluationRead],
    summary="Évaluer les règles archivées d'un calcul terminé",
)
def evaluate_calculation(
    calculation_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> list[RuleEvaluationRead]:
    del access
    calculation = core.get_calculation(session, calculation_id)
    if calculation.result_payload is None:
        raise ResourceConflictError("Le calcul doit être terminé avant l'évaluation des règles.")
    return [
        RuleEvaluationRead.model_validate(item)
        for item in governance.evaluate_calculation_rules(
            session,
            calculation,
            calculation.result_payload,
        )
    ]


@router.get(
    "/audit-events",
    response_model=Page[AuditEventRead],
    summary="Consulter le journal d'audit filtrable",
)
def list_audit_events(
    organization_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
    action: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    object_type: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    object_id: uuid.UUID | None = None,
    correlation_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[AuditEventRead]:
    del access
    items, total = governance.list_audit_events(
        session,
        organization_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        correlation_id=correlation_id,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[AuditEventRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


__all__ = ["router"]
