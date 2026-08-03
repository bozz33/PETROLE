"""Modèles relationnels du réseau versionné et de ses équipements placés."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from hydro_api.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NetworkNode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Nœud topologique appartenant à une version de modèle."""

    __tablename__ = "network_nodes"
    __table_args__ = (
        UniqueConstraint("model_version_id", "code", name="uq_network_node_code"),
        CheckConstraint(
            "kind IN ('source', 'tank', 'station', 'junction', 'terminal', 'injection', 'offtake')",
            name="kind_valid",
        ),
        CheckConstraint("status IN ('available', 'maintenance', 'unavailable')", name="status_valid"),
        Index("ix_network_nodes_model_kind", "model_version_id", "kind"),
    )

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    elevation_m: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="available", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class NetworkEdge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tronçon orienté reliant deux nœuds d'une même version."""

    __tablename__ = "network_edges"
    __table_args__ = (
        UniqueConstraint("model_version_id", "code", name="uq_network_edge_code"),
        UniqueConstraint("model_version_id", "sequence", name="uq_network_edge_sequence"),
        CheckConstraint("from_node_id <> to_node_id", name="different_nodes"),
        CheckConstraint("sequence > 0", name="sequence_positive"),
        CheckConstraint("length_m > 0", name="length_positive"),
        CheckConstraint("inner_diameter_m > 0", name="diameter_positive"),
        CheckConstraint("roughness_m >= 0", name="roughness_nonnegative"),
        CheckConstraint("mawp_pa > 0", name="mawp_positive"),
        CheckConstraint("status IN ('available', 'maintenance', 'unavailable')", name="status_valid"),
        Index("ix_network_edges_model_sequence", "model_version_id", "sequence"),
    )

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_node_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("network_nodes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    to_node_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("network_nodes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    material_catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("catalog_items.id", ondelete="RESTRICT"),
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    length_m: Mapped[float] = mapped_column(Float, nullable=False)
    inner_diameter_m: Mapped[float] = mapped_column(Float, nullable=False)
    roughness_m: Mapped[float] = mapped_column(Float, nullable=False)
    mawp_pa: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="available", nullable=False)
    profile_payload: Mapped[list[dict[str, float | None]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    fittings_payload: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class AssetInstance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Instance d'un équipement de catalogue placée sur un nœud ou un tronçon."""

    __tablename__ = "asset_instances"
    __table_args__ = (
        UniqueConstraint("model_version_id", "code", name="uq_asset_instance_code"),
        CheckConstraint(
            "(node_id IS NOT NULL AND edge_id IS NULL) OR "
            "(node_id IS NULL AND edge_id IS NOT NULL)",
            name="single_location",
        ),
        CheckConstraint(
            "status IN ('available', 'maintenance', 'unavailable', 'bypassed')",
            name="status_valid",
        ),
        CheckConstraint(
            "role IN ('main', 'standby', 'auxiliary', 'isolation', 'control', 'measurement')",
            name="role_valid",
        ),
        Index("ix_asset_instances_model_catalog", "model_version_id", "catalog_item_id"),
    )

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    catalog_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("catalog_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("network_nodes.id", ondelete="RESTRICT"),
    )
    edge_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("network_edges.id", ondelete="RESTRICT"),
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="available", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


__all__ = ["AssetInstance", "NetworkEdge", "NetworkNode"]
