"""Routes REST des sites industriels."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from hydro_api.database.session import get_session
from hydro_api.deployment import (
    bind_default_organization,
    is_single_organization,
    require_default_organization_id,
)
from hydro_api.schemas import Page
from hydro_api.schemas.sites import SiteCreate, SiteRead, SiteUpdate
from hydro_api.services import sites

router = APIRouter(tags=["Sites"])
DatabaseSession = Annotated[Session, Depends(get_session, scope="function")]


@router.post(
    "/sites",
    response_model=SiteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un site",
)
def create_site(data: SiteCreate, request: Request, session: DatabaseSession):
    data = bind_default_organization(request, session, data)
    return sites.create_site(session, data)


@router.get(
    "/sites",
    response_model=Page[SiteRead],
    summary="Lister les sites d'une organisation",
)
def list_sites(
    organization_id: uuid.UUID,
    request: Request,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    if is_single_organization(request.app.state.settings):
        organization_id = require_default_organization_id(request, session)
    items, total = sites.list_sites(
        session,
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/sites/{site_id}",
    response_model=SiteRead,
    summary="Lire un site",
)
def read_site(site_id: uuid.UUID, session: DatabaseSession):
    return sites.get_site(session, site_id)


@router.patch(
    "/sites/{site_id}",
    response_model=SiteRead,
    summary="Modifier ou archiver un site",
)
def update_site(
    site_id: uuid.UUID,
    data: SiteUpdate,
    session: DatabaseSession,
):
    return sites.update_site(session, site_id, data)


__all__ = ["router"]
