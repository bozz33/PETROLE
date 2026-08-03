"""Routes REST du catalogue technique versionné."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query, status

from hydro_api.schemas.catalog import (
    CatalogItemCreate,
    CatalogItemRead,
    CatalogItemUpdate,
    CatalogItemVersionCreate,
)
from hydro_api.schemas.core import Page
from hydro_api.security import ApplicationAccess, DatabaseSession
from hydro_api.services import catalog

CatalogCollection = Literal["fluids", "pumps", "valves", "materials", "accessories"]
CatalogStatus = Literal["draft", "approved", "archived"]

router = APIRouter(prefix="/catalog", tags=["catalogue technique"])


@router.post(
    "/{collection}",
    response_model=CatalogItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une ressource technique versionnée",
)
def create_item(
    collection: CatalogCollection,
    data: CatalogItemCreate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> CatalogItemRead:
    """Valide les propriétés scientifiques avant toute persistance."""

    item = catalog.create_catalog_item(
        session,
        catalog.kind_from_collection(collection),
        data,
        actor_id=access.user_id,
    )
    return CatalogItemRead.model_validate(item)


@router.get(
    "/{collection}",
    response_model=Page[CatalogItemRead],
    summary="Lister une famille du catalogue",
)
def list_items(
    collection: CatalogCollection,
    session: DatabaseSession,
    access: ApplicationAccess,
    organization_id: Annotated[uuid.UUID, Query()],
    item_status: Annotated[CatalogStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[CatalogItemRead]:
    """Retourne seulement les versions appartenant à l'organisation demandée."""

    del access
    items, total = catalog.list_catalog_items(
        session,
        organization_id=organization_id,
        kind=catalog.kind_from_collection(collection),
        status=item_status,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[CatalogItemRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/items/{catalog_item_id}",
    response_model=CatalogItemRead,
    summary="Lire une version du catalogue",
)
def get_item(
    catalog_item_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> CatalogItemRead:
    """Expose contenu, source, statut et empreinte de la version."""

    del access
    return CatalogItemRead.model_validate(catalog.get_catalog_item(session, catalog_item_id))


@router.patch(
    "/items/{catalog_item_id}",
    response_model=CatalogItemRead,
    summary="Modifier un brouillon du catalogue",
)
def update_item(
    catalog_item_id: uuid.UUID,
    data: CatalogItemUpdate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> CatalogItemRead:
    """Interdit toute modification silencieuse d'une version approuvée."""

    return CatalogItemRead.model_validate(
        catalog.update_catalog_item(
            session,
            catalog_item_id,
            data,
            actor_id=access.user_id,
        )
    )


@router.post(
    "/items/{catalog_item_id}/versions",
    response_model=CatalogItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une nouvelle version du catalogue",
)
def create_version(
    catalog_item_id: uuid.UUID,
    data: CatalogItemVersionCreate,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> CatalogItemRead:
    """Conserve la filiation et incrémente la version du même code."""

    return CatalogItemRead.model_validate(
        catalog.create_catalog_version(
            session,
            catalog_item_id,
            data,
            actor_id=access.user_id,
        )
    )


@router.post(
    "/items/{catalog_item_id}/approve",
    response_model=CatalogItemRead,
    summary="Approuver et figer une version du catalogue",
)
def approve_item(
    catalog_item_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
) -> CatalogItemRead:
    """Fige le contenu technique tout en conservant sa source et son empreinte."""

    return CatalogItemRead.model_validate(
        catalog.approve_catalog_item(
            session,
            catalog_item_id,
            actor_id=access.user_id,
        )
    )


__all__ = ["router"]
