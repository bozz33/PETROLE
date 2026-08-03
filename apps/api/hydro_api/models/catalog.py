"""Modèles relationnels du catalogue technique versionné."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hydro_api.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CatalogItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Version immuable après approbation d'une ressource technique."""

    __tablename__ = "catalog_items"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "kind",
            "code",
            "version_number",
            name="uq_catalog_item_version",
        ),
        CheckConstraint(
            "kind IN ('fluid', 'pump', 'valve', 'material', 'accessory')",
            name="kind_valid",
        ),
        CheckConstraint(
            "status IN ('draft', 'approved', 'archived')",
            name="status_valid",
        ),
        Index("ix_catalog_items_organization_kind", "organization_id", "kind"),
        Index("ix_catalog_items_code_version", "code", "version_number"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("catalog_items.id", ondelete="RESTRICT"),
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    parent: Mapped[CatalogItem | None] = relationship(remote_side="CatalogItem.id")


__all__ = ["CatalogItem"]
