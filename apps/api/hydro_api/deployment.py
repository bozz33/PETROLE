"""Règles d'isolation liées au mode de déploiement.

Le mode ``single_org`` conserve le modèle de données multi-organisation, mais
verrouille toute l'instance sur un seul espace. Les identifiants envoyés par le
navigateur ne décident donc jamais du périmètre effectif.
"""

from __future__ import annotations

import uuid
from typing import TypeVar

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from hydro_api.config import Settings
from hydro_api.errors import ResourceConflictError
from hydro_api.models import Organization

OrganizationBound = TypeVar("OrganizationBound")


def is_single_organization(settings: Settings) -> bool:
    """Indique si l'instance doit être limitée à un exploitant."""

    return settings.deployment_mode == "single_org"


def resolve_default_organization_id(
    session: Session,
    settings: Settings,
) -> uuid.UUID | None:
    """Résout organisation unique configurée ou seule organisation existante.

    Durant bootstrap aucun espace n'existe encore : ``None`` permet au service
    d'identité de créer automatiquement celui configuré. Sans identifiant
    configuré, une instance mono-organisation doit contenir exactement un
    espace ; cela évite tout choix silencieux et non déterministe.
    """

    if not is_single_organization(settings):
        return None
    if settings.default_organization_id is not None:
        if session.get(Organization, settings.default_organization_id) is None:
            raise ResourceConflictError(
                "HYDRO_DEFAULT_ORGANIZATION_ID ne correspond à aucune organisation."
            )
        return settings.default_organization_id
    organization_ids = session.scalars(
        select(Organization.id).where(Organization.archived_at.is_(None)).limit(2)
    ).all()
    if not organization_ids:
        return None
    if len(organization_ids) != 1:
        raise ResourceConflictError(
            "Le mode single_org exige une seule organisation active ou "
            "HYDRO_DEFAULT_ORGANIZATION_ID."
        )
    return organization_ids[0]


def require_default_organization_id(request: Request, session: Session) -> uuid.UUID:
    """Retourne organisation imposée par l'instance mono-organisation."""

    organization_id = resolve_default_organization_id(session, request.app.state.settings)
    if organization_id is None:
        raise ResourceConflictError("Initialisez d'abord l'organisation unique de cette instance.")
    return organization_id


def bind_default_organization(
    request: Request,
    session: Session,
    data: OrganizationBound,
) -> OrganizationBound:
    """Remplace l'organisation reçue par celle imposée côté serveur.

    Les schémas Pydantic utilisés par les créations possèdent ``model_copy``.
    Le type reste volontairement générique pour ne pas coupler cette règle aux
    modules catalogue, projets, gouvernance et opérations.
    """

    settings: Settings = request.app.state.settings
    if not is_single_organization(settings) or not hasattr(data, "organization_id"):
        return data
    organization_id = require_default_organization_id(request, session)
    return data.model_copy(update={"organization_id": organization_id})  # type: ignore[attr-defined, no-any-return]


def require_default_organization_access(
    request: Request,
    session: Session,
    organization_id: uuid.UUID,
) -> None:
    """Refuse accès par URL à un espace hors périmètre mono-organisation."""

    settings: Settings = request.app.state.settings
    if not is_single_organization(settings):
        return
    if organization_id != require_default_organization_id(request, session):
        raise ResourceConflictError("Cette instance est limitée à son organisation configurée.")


__all__ = [
    "bind_default_organization",
    "is_single_organization",
    "require_default_organization_access",
    "require_default_organization_id",
    "resolve_default_organization_id",
]
