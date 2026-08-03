"""Fabrique de l'application FastAPI."""

from __future__ import annotations

import logging
import re
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from hydro_api import __version__
from hydro_api.config import Settings, get_settings
from hydro_api.errors import ResourceConflictError, ResourceNotFoundError
from hydro_api.routers.auth import router as auth_router
from hydro_api.routers.catalog import router as catalog_router
from hydro_api.routers.data import router as data_router
from hydro_api.routers.governance import router as governance_router
from hydro_api.routers.health import router as health_router
from hydro_api.routers.network import router as network_router
from hydro_api.routers.operations import router as operations_router
from hydro_api.routers.reports import router as reports_router
from hydro_api.routers.resources import router as resources_router
from hydro_api.routers.sites import router as sites_router
from hydro_api.security import authorize_application_request
from hydro_shared.errors import HydroError
from hydro_shared.observability import bound_context, configure_logging, get_logger

_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
_LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "trace": logging.DEBUG,
}


def create_application(settings: Settings | None = None) -> FastAPI:
    """Construit une application isolable dans les tests et les processus web."""

    active_settings = settings or get_settings()
    configure_logging(
        json_output=active_settings.environment != "development",
        level=_LOG_LEVELS[active_settings.log_level],
    )
    logger = get_logger("application")
    application = FastAPI(
        title=active_settings.application_name,
        summary="API d'ingénierie pour pipelines liquides, stations et réservoirs.",
        description=(
            "Backend central du MVP. Les calculs scientifiques restent isolés dans "
            "HydroLiquid Core et sont exposés par des contrats versionnés."
        ),
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
    )
    application.state.settings = active_settings

    @application.get("/", include_in_schema=False)
    def api_root() -> dict[str, str]:
        """Expose une réponse neutre pour les sondes qui ciblent la racine."""

        return {"service": "hydro-api", "status": "ok"}

    def application_settings() -> Settings:
        """Fournit la configuration appartenant à cette instance applicative."""

        return active_settings

    application.dependency_overrides[get_settings] = application_settings

    @application.middleware("http")
    async def correlate_request(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Corrèle la réponse, le journal applicatif et les événements d'audit."""

        supplied = request.headers.get("X-Correlation-ID")
        correlation_id = (
            supplied
            if supplied is not None and _CORRELATION_ID_PATTERN.fullmatch(supplied)
            else str(uuid.uuid4())
        )
        request.state.correlation_id = correlation_id
        started_at = time.perf_counter()
        with bound_context(correlation_id=correlation_id):
            try:
                response = await call_next(request)
            except Exception as error:
                logger.error(
                    "requete_http_echouee",
                    methode=request.method,
                    chemin=request.url.path,
                    type_exception=type(error).__name__,
                )
                raise
            response.headers["X-Correlation-ID"] = correlation_id
            # L'API transporte potentiellement des éléments d'exploitation et
            # d'authentification : elle ne doit pas être mise en cache par un
            # navigateur ou un proxy partagé. Les en-têtes de défense restent
            # applicables aussi aux réponses d'erreur générées par FastAPI.
            response.headers.setdefault("Cache-Control", "no-store")
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
            logger.info(
                "requete_http_terminee",
                methode=request.method,
                chemin=request.url.path,
                statut_http=response.status_code,
                duree_ms=round((time.perf_counter() - started_at) * 1_000, 3),
            )
            return response

    @application.exception_handler(PermissionError)
    def authentication_error(request: Request, error: PermissionError) -> JSONResponse:
        """Retourne une réponse uniforme sans révéler l'existence d'un compte."""

        return JSONResponse(
            status_code=401,
            media_type="application/problem+json",
            headers={"WWW-Authenticate": "Bearer"},
            content={
                "type": "urn:hydro:error:authentication-failed",
                "title": "Authentification refusée",
                "status": 401,
                "detail": str(error),
                "instance": str(request.url.path),
            },
        )

    @application.exception_handler(ValueError)
    def invalid_value(request: Request, error: ValueError) -> JSONResponse:
        """Expose une erreur de saisie ou de fichier avec une action claire."""

        return JSONResponse(
            status_code=422,
            media_type="application/problem+json",
            content={
                "type": "urn:hydro:error:invalid-value",
                "title": "Valeur invalide",
                "status": 422,
                "detail": str(error),
                "instance": str(request.url.path),
            },
        )

    @application.exception_handler(HydroError)
    def invalid_domain_input(request: Request, error: HydroError) -> JSONResponse:
        """Expose les erreurs de données métier selon RFC 7807."""

        return JSONResponse(
            status_code=422,
            media_type="application/problem+json",
            content={
                "type": f"urn:hydro:error:{error.code.lower().replace('_', '-')}",
                "title": "Données de calcul invalides",
                "status": 422,
                "detail": error.message,
                "instance": str(request.url.path),
                "code": error.code,
                "context": error.context,
            },
        )

    @application.exception_handler(ResourceNotFoundError)
    def resource_not_found(request: Request, error: ResourceNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            media_type="application/problem+json",
            content={
                "type": "urn:hydro:error:resource-not-found",
                "title": "Ressource introuvable",
                "status": 404,
                "detail": str(error),
                "instance": str(request.url.path),
            },
        )

    @application.exception_handler(ResourceConflictError)
    def resource_conflict(request: Request, error: ResourceConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            media_type="application/problem+json",
            content={
                "type": "urn:hydro:error:resource-conflict",
                "title": "Conflit de ressource",
                "status": 409,
                "detail": error.message,
                "instance": str(request.url.path),
            },
        )

    protected_dependencies = [Depends(authorize_application_request)]
    application.include_router(health_router, prefix="/api/v1")
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(
        catalog_router,
        prefix="/api/v1",
        dependencies=protected_dependencies,
    )
    application.include_router(
        data_router,
        prefix="/api/v1",
        dependencies=protected_dependencies,
    )
    application.include_router(
        governance_router,
        prefix="/api/v1",
        dependencies=protected_dependencies,
    )
    application.include_router(
        resources_router,
        prefix="/api/v1",
        dependencies=protected_dependencies,
    )
    application.include_router(
        sites_router,
        prefix="/api/v1",
        dependencies=protected_dependencies,
    )
    application.include_router(
        network_router,
        prefix="/api/v1",
        dependencies=protected_dependencies,
    )
    application.include_router(
        operations_router,
        prefix="/api/v1",
        dependencies=protected_dependencies,
    )
    application.include_router(
        reports_router,
        prefix="/api/v1",
        dependencies=protected_dependencies,
    )
    return application


app = create_application()
