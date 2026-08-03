"""Services transactionnels des sites industriels."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hydro_api.database.base import utc_now
from hydro_api.errors import ResourceConflictError, ResourceNotFoundError
from hydro_api.models import AuditEvent, Organization, Site
from hydro_api.schemas.sites import SiteCreate, SiteUpdate


def get_site(session: Session, site_id: uuid.UUID) -> Site:
    site = session.get(Site, site_id)
    if site is None:
        raise ResourceNotFoundError("Site", site_id)
    return site


def create_site(session: Session, data: SiteCreate) -> Site:
    if session.get(Organization, data.organization_id) is None:
        raise ResourceNotFoundError("Organisation", data.organization_id)
    site = Site(**data.model_dump(), status="active")
    session.add(site)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ResourceConflictError(
            f"Le code site « {data.code} » existe déjà dans cette organisation."
        ) from exc
    session.add(
        AuditEvent(
            organization_id=site.organization_id,
            action="create",
            object_type="site",
            object_id=site.id,
            details={"code": site.code},
            created_at=utc_now(),
        )
    )
    return site


def list_sites(
    session: Session,
    *,
    organization_id: uuid.UUID,
    limit: int,
    offset: int,
) -> tuple[list[Site], int]:
    statement = select(Site).where(Site.organization_id == organization_id)
    total = session.scalar(
        select(func.count()).select_from(Site).where(Site.organization_id == organization_id)
    )
    items = session.scalars(statement.order_by(Site.name).limit(limit).offset(offset)).all()
    return list(items), int(total or 0)


def update_site(
    session: Session,
    site_id: uuid.UUID,
    data: SiteUpdate,
) -> Site:
    site = get_site(session, site_id)
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(site, field, value)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ResourceConflictError("La modification du site crée un conflit.") from exc
    session.add(
        AuditEvent(
            organization_id=site.organization_id,
            action="update",
            object_type="site",
            object_id=site.id,
            details={"fields": sorted(changes)},
            created_at=utc_now(),
        )
    )
    return site


__all__ = ["create_site", "get_site", "list_sites", "update_site"]
