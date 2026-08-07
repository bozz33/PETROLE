"""Points de contrôle de santé de l'API."""

from __future__ import annotations

import json
from importlib.resources import files
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
from hydro_shared.versioning import ENGINE_VERSION

router = APIRouter(prefix="/health", tags=["santé"])
version_router = APIRouter(tags=["santé"])


class HealthResponse(BaseModel):
    """État minimal stable utilisé par Docker et les outils de supervision."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    service: str
    version: str
    environment: str
    build: BuildMetadata
    deployment: DeploymentMetadata


class BuildMetadata(BaseModel):
    """Identité traçable de l'image en cours d'exécution."""

    model_config = ConfigDict(extra="forbid")

    application_version: str
    git_sha: str
    ref: str
    build_date: str
    scientific_engine_version: str
    database_migration_version: str


class DeploymentMetadata(BaseModel):
    """Mode de déploiement affichable sans révéler les secrets."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["single_org", "multi_org", "saas"]
    organization_label: str


class ScientificValidationResponse(BaseModel):
    """Preuve scientifique publiée avec l'image, jamais une métrique fictive."""

    model_config = ConfigDict(extra="forbid")

    suite: str
    passed: int
    total: int
    proof_hash: str
    engine_version: str
    executed_at: str
    environment: str
    source: str


class ReadinessResponse(BaseModel):
    """Disponibilité des dépendances indispensables au service métier."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "not_ready"]
    database: Literal["ready", "unavailable"]
    object_storage: Literal["ready", "unavailable"]


def build_metadata(settings: Settings) -> BuildMetadata:
    """Construit métadonnées injectées au build de l'image immuable."""

    return BuildMetadata(
        application_version=__version__,
        git_sha=settings.build_git_sha,
        ref=settings.build_ref,
        build_date=settings.build_date,
        scientific_engine_version=ENGINE_VERSION,
        database_migration_version=settings.database_migration_version,
    )


def published_scientific_validation() -> ScientificValidationResponse:
    """Lit attestation de qualification versionnée avec le paquet API."""

    content = (
        files("hydro_api").joinpath("scientific_validation_proof.json").read_text(encoding="utf-8")
    )
    return ScientificValidationResponse.model_validate(json.loads(content))


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
        build=build_metadata(settings),
        deployment=DeploymentMetadata(
            mode=settings.deployment_mode,
            organization_label=(
                "Exploitant / espace de travail"
                if settings.deployment_mode == "single_org"
                else "Organisations"
            ),
        ),
    )


@version_router.get(
    "/version",
    response_model=BuildMetadata,
    summary="Lire l'identité de build et des moteurs",
)
def version(request: Request) -> BuildMetadata:
    """Expose version, SHA, build, moteur et migration sans dépendance DB."""

    return build_metadata(request.app.state.settings)


@router.get(
    "/validation",
    response_model=ScientificValidationResponse,
    summary="Lire la preuve de validation scientifique publiée",
)
def scientific_validation() -> ScientificValidationResponse:
    """Expose la dernière attestation embarquée par la release."""

    return published_scientific_validation()


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
