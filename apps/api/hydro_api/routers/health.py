"""Points de contrôle de santé de l'API."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from hydro_api import __version__
from hydro_api.config import Settings

router = APIRouter(prefix="/health", tags=["santé"])


class HealthResponse(BaseModel):
    """État minimal stable utilisé par Docker et les outils de supervision."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    service: str
    version: str
    environment: str


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
