"""Dépendances d'authentification et de contrôle d'accès organisationnel."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from hydro_api.config import Settings
from hydro_api.database.session import get_session
from hydro_api.deployment import is_single_organization, require_default_organization_id
from hydro_api.models import (
    AssetInstance,
    CalculationRun,
    CatalogItem,
    Dataset,
    DatasetImport,
    GeneratedReport,
    ModelVersion,
    NetworkEdge,
    NetworkNode,
    OptimizationRun,
    OrganizationMembership,
    Project,
    RuleDefinition,
    RuleSet,
    ScenarioComparison,
    ScenarioRecord,
    Site,
    StandardReference,
    StoredFile,
    TankRecord,
    TransferRun,
    UserAccount,
)
from hydro_api.services import auth

DatabaseSession = Annotated[Session, Depends(get_session, scope="function")]
AuthorizationHeader = Annotated[str | None, Header(alias="Authorization")]


@dataclass(frozen=True, slots=True)
class AccessContext:
    """Identité courante et rôles chargés depuis la base."""

    user: UserAccount | None
    roles: dict[uuid.UUID, str]
    local_bypass: bool = False

    @property
    def user_id(self) -> uuid.UUID | None:
        return self.user.id if self.user else None

    @property
    def organization_ids(self) -> tuple[uuid.UUID, ...]:
        return tuple(self.roles)


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized("L'en-tête Authorization doit utiliser le schéma Bearer.")
    return token.strip()


def _context_from_token(
    session: Session,
    token: str,
    settings: Settings,
) -> AccessContext:
    try:
        user_id = auth.decode_access_token(token, settings)
        user = auth.get_user(session, user_id)
    except PermissionError as exc:
        raise _unauthorized(str(exc)) from exc
    memberships = session.scalars(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
        )
    ).all()
    return AccessContext(
        user=user,
        roles={membership.organization_id: membership.role for membership in memberships},
    )


async def access_context(
    request: Request,
    session: DatabaseSession,
    authorization: AuthorizationHeader = None,
) -> AccessContext:
    """Retourne le contexte ou un bypass explicite uniquement en développement."""

    settings = _settings(request)
    token = _bearer_token(authorization)
    if token is None:
        if settings.authentication_required:
            raise _unauthorized("Une authentification est requise.")
        context = AccessContext(user=None, roles={}, local_bypass=True)
    else:
        context = _context_from_token(session, token, settings)
    request.state.access_context = context
    return context


async def authenticated_context(
    request: Request,
    session: DatabaseSession,
    authorization: AuthorizationHeader = None,
) -> AccessContext:
    """Exige toujours un jeton, même lorsque le mode local est ouvert."""

    token = _bearer_token(authorization)
    if token is None:
        raise _unauthorized("Une authentification est requise.")
    context = _context_from_token(session, token, _settings(request))
    request.state.access_context = context
    return context


def _organization_for_resource(
    session: Session,
    path_parameters: dict[str, str],
) -> uuid.UUID | None:
    try:
        if value := path_parameters.get("organization_id"):
            return uuid.UUID(value)
        if value := path_parameters.get("catalog_item_id"):
            catalog_item = session.get(CatalogItem, uuid.UUID(value))
            return catalog_item.organization_id if catalog_item else None
        if value := path_parameters.get("standard_id"):
            standard = session.get(StandardReference, uuid.UUID(value))
            return standard.organization_id if standard else None
        if value := path_parameters.get("rule_set_id"):
            rule_set = session.get(RuleSet, uuid.UUID(value))
            return rule_set.organization_id if rule_set else None
        if value := path_parameters.get("rule_id"):
            rule = session.get(RuleDefinition, uuid.UUID(value))
            rule_set = session.get(RuleSet, rule.rule_set_id) if rule else None
            return rule_set.organization_id if rule_set else None
        if value := path_parameters.get("node_id"):
            node = session.get(NetworkNode, uuid.UUID(value))
            model = session.get(ModelVersion, node.model_version_id) if node else None
            return model.project.organization_id if model else None
        if value := path_parameters.get("edge_id"):
            edge = session.get(NetworkEdge, uuid.UUID(value))
            model = session.get(ModelVersion, edge.model_version_id) if edge else None
            return model.project.organization_id if model else None
        if value := path_parameters.get("asset_id"):
            asset = session.get(AssetInstance, uuid.UUID(value))
            model = session.get(ModelVersion, asset.model_version_id) if asset else None
            return model.project.organization_id if model else None
        if value := path_parameters.get("site_id"):
            site = session.get(Site, uuid.UUID(value))
            return site.organization_id if site else None
        if value := path_parameters.get("tank_id"):
            tank = session.get(TankRecord, uuid.UUID(value))
            return tank.organization_id if tank else None
        if value := path_parameters.get("transfer_id"):
            transfer = session.get(TransferRun, uuid.UUID(value))
            return transfer.organization_id if transfer else None
        if value := path_parameters.get("comparison_id"):
            comparison = session.get(ScenarioComparison, uuid.UUID(value))
            return comparison.organization_id if comparison else None
        if value := path_parameters.get("optimization_id"):
            optimization = session.get(OptimizationRun, uuid.UUID(value))
            return optimization.organization_id if optimization else None
        if value := path_parameters.get("project_id"):
            project = session.get(Project, uuid.UUID(value))
            return project.organization_id if project else None
        if value := path_parameters.get("model_id"):
            model = session.get(ModelVersion, uuid.UUID(value))
            return model.project.organization_id if model else None
        if value := path_parameters.get("scenario_id"):
            scenario = session.get(ScenarioRecord, uuid.UUID(value))
            return scenario.model_version.project.organization_id if scenario else None
        if value := path_parameters.get("calculation_id"):
            calculation = session.get(CalculationRun, uuid.UUID(value))
            return (
                calculation.scenario.model_version.project.organization_id if calculation else None
            )
        if value := path_parameters.get("report_id"):
            report = session.get(GeneratedReport, uuid.UUID(value))
            return report.organization_id if report else None
        if value := path_parameters.get("dataset_id"):
            dataset = session.get(Dataset, uuid.UUID(value))
            return dataset.organization_id if dataset else None
        if value := path_parameters.get("file_id"):
            stored_file = session.get(StoredFile, uuid.UUID(value))
            return stored_file.organization_id if stored_file else None
        if value := path_parameters.get("import_id"):
            import_run = session.get(DatasetImport, uuid.UUID(value))
            return import_run.dataset.organization_id if import_run else None
    except ValueError:
        return None
    return None


async def _organization_from_request(
    request: Request,
    session: Session,
) -> uuid.UUID | None:
    organization_id = _organization_for_resource(session, request.path_params)
    if organization_id is not None:
        return organization_id
    query_value = request.query_params.get("organization_id")
    if query_value:
        try:
            return uuid.UUID(query_value)
        except ValueError:
            return None
    if request.method not in {"POST", "PUT", "PATCH"}:
        return None
    content_type = request.headers.get("content-type", "")
    data: Any = None
    try:
        if content_type.startswith("application/json"):
            data = await request.json()
        elif content_type.startswith("multipart/form-data"):
            data = await request.form()
    except Exception:
        return None
    if data is None:
        return None
    if request.url.path == "/api/v1/reports" and data.get("source_id"):
        source_parameters: dict[str, str] = {}
        report_type = str(data.get("report_type", ""))
        source_id = str(data.get("source_id"))
        if report_type == "project_sheet":
            source_parameters["project_id"] = source_id
        elif report_type == "scenario_comparison":
            source_parameters["comparison_id"] = source_id
        elif report_type == "station_pumps":
            source_parameters["calculation_id"] = source_id
        else:
            source_parameters["transfer_id"] = source_id
        return _organization_for_resource(session, source_parameters)
    value = data.get("organization_id")
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _allowed_roles(request: Request) -> frozenset[str]:
    """Détermine les rôles autorisés, des routes sensibles aux routes générales."""

    path = request.url.path
    if path.startswith("/api/v1/audit-events"):
        return frozenset({"admin", "approver"})
    if "/members" in path:
        return frozenset({"admin"})
    if path.endswith(("/activate", "/archive", "/restore")):
        return frozenset({"admin"})
    if path.endswith("/approve"):
        return frozenset({"admin", "approver"})
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return frozenset({"admin", "engineer", "operator", "approver", "viewer"})
    if path.startswith("/api/v1/organizations/") or path.startswith("/api/v1/sites"):
        return frozenset({"admin"})
    return frozenset({"admin", "engineer", "operator"})


async def authorize_application_request(
    request: Request,
    session: DatabaseSession,
    context: Annotated[AccessContext, Depends(access_context)],
) -> AccessContext:
    """Vérifie le rôle sur l'organisation résolue depuis la requête ou la ressource."""

    settings = _settings(request)
    organization_id: uuid.UUID | None
    if is_single_organization(settings):
        organization_id = require_default_organization_id(request, session)
        resource_organization_id = _organization_for_resource(session, request.path_params)
        if resource_organization_id is not None and resource_organization_id != organization_id:
            # Une réponse neutre évite de confirmer l'existence d'une ressource
            # appartenant à un autre espace, même pour un compte multi-rôle.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ressource introuvable dans l'espace de travail courant.",
            )
    else:
        organization_id = await _organization_from_request(request, session)
    if context.local_bypass:
        return context
    if organization_id is None:
        return context
    role = context.roles.get(organization_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette organisation n'est pas accessible avec le compte courant.",
        )
    if role not in _allowed_roles(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le rôle courant ne permet pas cette action.",
        )
    return context


ApplicationAccess = Annotated[AccessContext, Depends(authorize_application_request)]
AuthenticatedAccess = Annotated[AccessContext, Depends(authenticated_context)]


__all__ = [
    "AccessContext",
    "ApplicationAccess",
    "AuthenticatedAccess",
    "access_context",
    "authenticated_context",
    "authorize_application_request",
]
