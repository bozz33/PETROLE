"""Routes des réservoirs, transferts, comparaisons et optimisations."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from hydro_api.database.session import get_session
from hydro_api.schemas import Page
from hydro_api.schemas.operations import (
    ComparisonCreate,
    ComparisonRead,
    OptimizationCreate,
    OptimizationRead,
    TankCreate,
    TankRead,
    TankUpdate,
    TransferBalanceCreate,
    TransferBalanceRead,
    TransferCreate,
    TransferRead,
)
from hydro_api.services import operations

router = APIRouter(tags=["Opérations"])
DatabaseSession = Annotated[Session, Depends(get_session, scope="function")]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=100,
        description="Clé stable de déduplication de l'opération.",
    ),
]


@router.post(
    "/tanks",
    response_model=TankRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un réservoir et son barémage",
)
def create_tank(data: TankCreate, session: DatabaseSession):
    return operations.tank_payload(operations.create_tank(session, data))


@router.get(
    "/tanks",
    response_model=Page[TankRead],
    summary="Lister les réservoirs d'une organisation",
)
def list_tanks(
    organization_id: uuid.UUID,
    session: DatabaseSession,
    site_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items, total = operations.list_tanks(
        session,
        organization_id=organization_id,
        site_id=site_id,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[operations.tank_payload(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/tanks/{tank_id}",
    response_model=TankRead,
    summary="Lire un réservoir",
)
def read_tank(tank_id: uuid.UUID, session: DatabaseSession):
    return operations.tank_payload(operations.get_tank(session, tank_id))


@router.patch(
    "/tanks/{tank_id}",
    response_model=TankRead,
    summary="Mettre à jour l'état courant d'un réservoir",
)
def update_tank(
    tank_id: uuid.UUID,
    data: TankUpdate,
    session: DatabaseSession,
):
    return operations.tank_payload(operations.update_tank(session, tank_id, data))


@router.post(
    "/organizations/{organization_id}/transfers",
    response_model=TransferRead,
    status_code=status.HTTP_201_CREATED,
    summary="Simuler et archiver un transfert bac-à-bac",
)
def simulate_transfer(
    organization_id: uuid.UUID,
    data: TransferCreate,
    session: DatabaseSession,
    idempotency_key: IdempotencyKey,
):
    return operations.simulate_transfer(
        session,
        organization_id,
        data,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/transfers/{transfer_id}",
    response_model=TransferRead,
    summary="Lire une simulation de transfert",
)
def read_transfer(transfer_id: uuid.UUID, session: DatabaseSession):
    return operations.get_transfer(session, transfer_id)


@router.post(
    "/transfers/{transfer_id}/balance",
    response_model=TransferBalanceRead,
    summary="Calculer le bilan matière d'un transfert",
)
def transfer_balance(
    transfer_id: uuid.UUID,
    data: TransferBalanceCreate,
    session: DatabaseSession,
):
    return operations.compute_balance(session, transfer_id, data)


@router.post(
    "/projects/{project_id}/comparisons",
    response_model=ComparisonRead,
    status_code=status.HTTP_201_CREATED,
    summary="Comparer et classer plusieurs calculs",
)
def create_comparison(
    project_id: uuid.UUID,
    data: ComparisonCreate,
    session: DatabaseSession,
    idempotency_key: IdempotencyKey,
):
    return operations.create_comparison(
        session,
        project_id,
        data,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/comparisons/{comparison_id}",
    response_model=ComparisonRead,
    summary="Lire une comparaison persistée",
)
def read_comparison(comparison_id: uuid.UUID, session: DatabaseSession):
    return operations.get_comparison(session, comparison_id)


@router.post(
    "/scenarios/{scenario_id}/optimizations",
    response_model=OptimizationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Rechercher la meilleure configuration de pompes",
)
def run_optimization(
    scenario_id: uuid.UUID,
    data: OptimizationCreate,
    session: DatabaseSession,
    idempotency_key: IdempotencyKey,
):
    return operations.run_optimization(
        session,
        scenario_id,
        data,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/optimizations/{optimization_id}",
    response_model=OptimizationRead,
    summary="Lire une optimisation persistée",
)
def read_optimization(optimization_id: uuid.UUID, session: DatabaseSession):
    return operations.get_optimization(session, optimization_id)


__all__ = ["router"]
