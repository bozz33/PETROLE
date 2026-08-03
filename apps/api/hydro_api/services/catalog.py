"""Services transactionnels du catalogue technique versionné."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hydro_api.database.base import utc_now
from hydro_api.errors import ResourceConflictError, ResourceNotFoundError
from hydro_api.models import AuditEvent, CatalogItem, Organization
from hydro_api.schemas.catalog import (
    CatalogItemCreate,
    CatalogItemUpdate,
    CatalogItemVersionCreate,
)
from hydro_domain.serialization import fluid_from_dict, pump_model_from_dict
from hydro_shared.hashing import sha256_of

COLLECTION_KINDS = {
    "fluids": "fluid",
    "pumps": "pump",
    "valves": "valve",
    "materials": "material",
    "accessories": "accessory",
}


def kind_from_collection(collection: str) -> str:
    """Traduit le nom public pluriel vers le type persistant."""

    try:
        return COLLECTION_KINDS[collection]
    except KeyError as error:
        raise ValueError(f"Collection de catalogue inconnue : {collection}.") from error


def _validate_positive(payload: dict[str, Any], field: str) -> None:
    """Refuse un paramètre physique négatif lorsqu'il est fourni."""

    value = payload.get(field)
    if value is not None and (isinstance(value, bool) or not isinstance(value, int | float)):
        raise ValueError(f"Le champ {field} doit être numérique.")
    if value is not None and value < 0:
        raise ValueError(f"Le champ {field} doit être positif ou nul.")


def _canonical_payload(
    kind: str,
    code: str,
    name: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Valide puis canonise les familles utilisées par le moteur scientifique."""

    candidate = {**payload, "id": code, "name": name}
    if kind == "fluid":
        return fluid_from_dict(candidate, "catalog.fluid").as_dict()
    if kind == "pump":
        return pump_model_from_dict(candidate, "catalog.pump").as_dict()
    if kind in {"valve", "accessory"}:
        _validate_positive(candidate, "k_coefficient")
    if kind == "material":
        _validate_positive(candidate, "roughness_m")
        _validate_positive(candidate, "mawp_pa")
    return candidate


def _fingerprint(item: CatalogItem) -> str:
    """Calcule l'empreinte fonctionnelle, indépendante des dates SQL."""

    return sha256_of(
        {
            "organization_id": item.organization_id,
            "parent_id": item.parent_id,
            "kind": item.kind,
            "code": item.code,
            "name": item.name,
            "version_number": item.version_number,
            "payload": item.payload,
            "source": item.source,
        }
    )


def get_catalog_item(session: Session, catalog_item_id: uuid.UUID) -> CatalogItem:
    """Charge une version du catalogue ou retourne une erreur métier stable."""

    item = session.get(CatalogItem, catalog_item_id)
    if item is None:
        raise ResourceNotFoundError("Élément de catalogue", catalog_item_id)
    return item


def create_catalog_item(
    session: Session,
    kind: str,
    data: CatalogItemCreate,
    *,
    actor_id: uuid.UUID | None = None,
) -> CatalogItem:
    """Crée la version initiale validée d'une ressource technique."""

    if session.get(Organization, data.organization_id) is None:
        raise ResourceNotFoundError("Organisation", data.organization_id)
    item = CatalogItem(
        organization_id=data.organization_id,
        kind=kind,
        code=data.code,
        name=data.name,
        version_number=1,
        status="draft",
        payload=_canonical_payload(kind, data.code, data.name, data.payload),
        source=data.source,
        content_hash="",
    )
    item.content_hash = _fingerprint(item)
    session.add(item)
    try:
        session.flush()
    except IntegrityError as error:
        session.rollback()
        raise ResourceConflictError(
            f"Le code « {data.code} » existe déjà pour ce type de catalogue."
        ) from error
    session.add(
        AuditEvent(
            organization_id=item.organization_id,
            actor_id=actor_id,
            action="catalog_item.created",
            object_type="catalog_item",
            object_id=item.id,
            details={"kind": item.kind, "code": item.code, "version": item.version_number},
            created_at=utc_now(),
        )
    )
    return item


def list_catalog_items(
    session: Session,
    *,
    organization_id: uuid.UUID,
    kind: str,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[CatalogItem], int]:
    """Liste une collection privée avec pagination déterministe."""

    conditions = [
        CatalogItem.organization_id == organization_id,
        CatalogItem.kind == kind,
    ]
    if status is not None:
        conditions.append(CatalogItem.status == status)
    statement = select(CatalogItem).where(*conditions)
    total = session.scalar(select(func.count()).select_from(CatalogItem).where(*conditions))
    items = session.scalars(
        statement.order_by(CatalogItem.code, CatalogItem.version_number.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), int(total or 0)


def update_catalog_item(
    session: Session,
    catalog_item_id: uuid.UUID,
    data: CatalogItemUpdate,
    *,
    actor_id: uuid.UUID | None = None,
) -> CatalogItem:
    """Modifie un brouillon ou archive une version approuvée."""

    item = get_catalog_item(session, catalog_item_id)
    changes = data.model_dump(exclude_unset=True)
    if item.status == "approved":
        if changes != {"status": "archived"}:
            raise ResourceConflictError(
                "Une version approuvée est immuable ; créez une nouvelle version."
            )
        item.status = "archived"
    elif item.status == "archived":
        raise ResourceConflictError("Une version archivée est immuable.")
    else:
        name = str(changes.get("name", item.name))
        payload = changes.get("payload", item.payload)
        item.name = name
        item.payload = _canonical_payload(item.kind, item.code, name, payload)
        if "source" in changes:
            item.source = changes["source"]
        if "status" in changes:
            item.status = changes["status"]
        item.content_hash = _fingerprint(item)
    session.flush()
    session.add(
        AuditEvent(
            organization_id=item.organization_id,
            actor_id=actor_id,
            action="catalog_item.updated",
            object_type="catalog_item",
            object_id=item.id,
            details={"fields": sorted(changes)},
            created_at=utc_now(),
        )
    )
    return item


def create_catalog_version(
    session: Session,
    catalog_item_id: uuid.UUID,
    data: CatalogItemVersionCreate,
    *,
    actor_id: uuid.UUID | None = None,
) -> CatalogItem:
    """Crée une version indépendante dérivée d'une ressource existante."""

    parent = get_catalog_item(session, catalog_item_id)
    latest = session.scalar(
        select(func.max(CatalogItem.version_number)).where(
            CatalogItem.organization_id == parent.organization_id,
            CatalogItem.kind == parent.kind,
            CatalogItem.code == parent.code,
        )
    )
    name = data.name or parent.name
    payload = data.payload if data.payload is not None else parent.payload
    source = data.source if data.source is not None else parent.source
    item = CatalogItem(
        organization_id=parent.organization_id,
        parent_id=parent.id,
        kind=parent.kind,
        code=parent.code,
        name=name,
        version_number=int(latest or 0) + 1,
        status="draft",
        payload=_canonical_payload(parent.kind, parent.code, name, payload),
        source=source,
        content_hash="",
    )
    item.content_hash = _fingerprint(item)
    session.add(item)
    session.flush()
    session.add(
        AuditEvent(
            organization_id=item.organization_id,
            actor_id=actor_id,
            action="catalog_item.versioned",
            object_type="catalog_item",
            object_id=item.id,
            details={"parent_id": str(parent.id), "version": item.version_number},
            created_at=utc_now(),
        )
    )
    return item


def approve_catalog_item(
    session: Session,
    catalog_item_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None = None,
) -> CatalogItem:
    """Approuve une version et fige son contenu technique."""

    item = get_catalog_item(session, catalog_item_id)
    if item.status != "draft":
        raise ResourceConflictError("Seule une version en brouillon peut être approuvée.")
    item.status = "approved"
    item.approved_at = utc_now()
    session.flush()
    session.add(
        AuditEvent(
            organization_id=item.organization_id,
            actor_id=actor_id,
            action="catalog_item.approved",
            object_type="catalog_item",
            object_id=item.id,
            details={"content_hash": item.content_hash},
            created_at=utc_now(),
        )
    )
    return item


__all__ = [
    "COLLECTION_KINDS",
    "approve_catalog_item",
    "create_catalog_item",
    "create_catalog_version",
    "get_catalog_item",
    "kind_from_collection",
    "list_catalog_items",
    "update_catalog_item",
]
