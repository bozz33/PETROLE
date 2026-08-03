"""Ajoute le réseau versionné et les équipements placés.

Identifiant : a31d7e4c9b20
Parent : 90c74f2e1a3b
Créée le : 3 août 2026
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a31d7e4c9b20"
down_revision: str | Sequence[str] | None = "90c74f2e1a3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée nœuds, tronçons et instances d'équipements."""

    op.create_table(
        "network_nodes",
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("elevation_m", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('source', 'tank', 'station', 'junction', 'terminal', 'injection', 'offtake')",
            name=op.f("ck_network_nodes_kind_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('available', 'maintenance', 'unavailable')",
            name=op.f("ck_network_nodes_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["model_versions.id"],
            name=op.f("fk_network_nodes_model_version_id_model_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_network_nodes")),
        sa.UniqueConstraint(
            "model_version_id",
            "code",
            name="uq_network_node_code",
        ),
    )
    op.create_index(
        "ix_network_nodes_model_kind",
        "network_nodes",
        ["model_version_id", "kind"],
        unique=False,
    )

    op.create_table(
        "network_edges",
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("from_node_id", sa.Uuid(), nullable=False),
        sa.Column("to_node_id", sa.Uuid(), nullable=False),
        sa.Column("material_catalog_item_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("length_m", sa.Float(), nullable=False),
        sa.Column("inner_diameter_m", sa.Float(), nullable=False),
        sa.Column("roughness_m", sa.Float(), nullable=False),
        sa.Column("mawp_pa", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("profile_payload", sa.JSON(), nullable=False),
        sa.Column("fittings_payload", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "from_node_id <> to_node_id", name=op.f("ck_network_edges_different_nodes")
        ),
        sa.CheckConstraint("sequence > 0", name=op.f("ck_network_edges_sequence_positive")),
        sa.CheckConstraint("length_m > 0", name=op.f("ck_network_edges_length_positive")),
        sa.CheckConstraint(
            "inner_diameter_m > 0",
            name=op.f("ck_network_edges_diameter_positive"),
        ),
        sa.CheckConstraint(
            "roughness_m >= 0",
            name=op.f("ck_network_edges_roughness_nonnegative"),
        ),
        sa.CheckConstraint("mawp_pa > 0", name=op.f("ck_network_edges_mawp_positive")),
        sa.CheckConstraint(
            "status IN ('available', 'maintenance', 'unavailable')",
            name=op.f("ck_network_edges_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["model_versions.id"],
            name=op.f("fk_network_edges_model_version_id_model_versions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["from_node_id"],
            ["network_nodes.id"],
            name=op.f("fk_network_edges_from_node_id_network_nodes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["to_node_id"],
            ["network_nodes.id"],
            name=op.f("fk_network_edges_to_node_id_network_nodes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["material_catalog_item_id"],
            ["catalog_items.id"],
            name=op.f("fk_network_edges_material_catalog_item_id_catalog_items"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_network_edges")),
        sa.UniqueConstraint(
            "model_version_id",
            "code",
            name="uq_network_edge_code",
        ),
        sa.UniqueConstraint(
            "model_version_id",
            "sequence",
            name="uq_network_edge_sequence",
        ),
    )
    op.create_index(
        "ix_network_edges_model_sequence",
        "network_edges",
        ["model_version_id", "sequence"],
        unique=False,
    )

    op.create_table(
        "asset_instances",
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("catalog_item_id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.Uuid(), nullable=True),
        sa.Column("edge_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(node_id IS NOT NULL AND edge_id IS NULL) OR "
            "(node_id IS NULL AND edge_id IS NOT NULL)",
            name=op.f("ck_asset_instances_single_location"),
        ),
        sa.CheckConstraint(
            "status IN ('available', 'maintenance', 'unavailable', 'bypassed')",
            name=op.f("ck_asset_instances_status_valid"),
        ),
        sa.CheckConstraint(
            "role IN ('main', 'standby', 'auxiliary', 'isolation', 'control', 'measurement')",
            name=op.f("ck_asset_instances_role_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["model_versions.id"],
            name=op.f("fk_asset_instances_model_version_id_model_versions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["catalog_item_id"],
            ["catalog_items.id"],
            name=op.f("fk_asset_instances_catalog_item_id_catalog_items"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["network_nodes.id"],
            name=op.f("fk_asset_instances_node_id_network_nodes"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["edge_id"],
            ["network_edges.id"],
            name=op.f("fk_asset_instances_edge_id_network_edges"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_asset_instances")),
        sa.UniqueConstraint(
            "model_version_id",
            "code",
            name="uq_asset_instance_code",
        ),
    )
    op.create_index(
        "ix_asset_instances_model_catalog",
        "asset_instances",
        ["model_version_id", "catalog_item_id"],
        unique=False,
    )


def downgrade() -> None:
    """Supprime réseau et équipements placés."""

    op.drop_index("ix_asset_instances_model_catalog", table_name="asset_instances")
    op.drop_table("asset_instances")
    op.drop_index("ix_network_edges_model_sequence", table_name="network_edges")
    op.drop_table("network_edges")
    op.drop_index("ix_network_nodes_model_kind", table_name="network_nodes")
    op.drop_table("network_nodes")
