"""Routes de génération des rapports opérationnels du MVP."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from hydro_api.database.session import get_session
from hydro_api.schemas import ReportRead
from hydro_api.schemas.reports import OperationalReportCreate
from hydro_api.services import reports
from hydro_api.storage import ObjectStorageDependency

router = APIRouter(tags=["Rapports"])
DatabaseSession = Annotated[Session, Depends(get_session, scope="function")]
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=100,
        description="Clé stable de déduplication de la génération.",
    ),
]


@router.post(
    "/reports",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Générer un rapport opérationnel RPT-01 ou RPT-03 à RPT-06",
)
def create_operational_report(
    data: OperationalReportCreate,
    session: DatabaseSession,
    storage: ObjectStorageDependency,
    idempotency_key: IdempotencyKey,
):
    return reports.create_operational_report(
        session,
        data,
        idempotency_key=idempotency_key,
        storage=storage,
    )


__all__ = ["router"]
