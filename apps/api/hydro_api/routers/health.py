"""Points de contrôle de santé de l'API."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from hydro_api import __version__
from hydro_api.config import Settings
from hydro_api.database.session import get_session
from hydro_api.storage import object_storage_for

router = APIRouter(prefix="/health", tags=["santé"])


class HealthResponse(BaseModel):
    """État minimal stable utilisé par Docker et les outils de supervision."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    service: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    """Disponibilité des dépendances indispensables au service métier."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "not_ready"]
    database: Literal["ready", "unavailable"]
    object_storage: Literal["ready", "unavailable"]


@router.get(
    "",
    response_model=HealthResponse,
    summary="Vérifier l'état du processus API",
)
def health(request: Request) -> HealthResponse:
    """Retourne l'état du processus HTTP sans masquer l'état des dépendances futures."""

    settings: Settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service="hydro-api",
        version=__version__,
        environment=settings.environment,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
    summary="Vérifier la disponibilité des dépendances",
)
def readiness(
    request: Request,
    session: Annotated[Session, Depends(get_session, scope="function")],
):
    """Contrôle réellement PostgreSQL et le stockage sans exposer leurs secrets."""

    database_status: Literal["ready", "unavailable"] = "ready"
    storage_status: Literal["ready", "unavailable"] = "ready"
    try:
        session.scalar(select(1))
    except Exception:
        database_status = "unavailable"
    try:
        object_storage_for(request.app.state.settings).check()
    except Exception:
        storage_status = "unavailable"
    ready = database_status == "ready" and storage_status == "ready"
    payload = ReadinessResponse(
        status="ready" if ready else "not_ready",
        database=database_status,
        object_storage=storage_status,
    )
    if not ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )
    return payload
