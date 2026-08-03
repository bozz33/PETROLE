"""Ajoute le catalogue technique versionné.

Identifiant : 90c74f2e1a3b
Parent : 5e9bbd221009
Créée le : 3 août 2026
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "90c74f2e1a3b"
down_revision: str | Sequence[str] | None = "5e9bbd221009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée les versions de produits, pompes, vannes et matériaux."""

    op.create_table(
        "catalog_items",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=71), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('fluid', 'pump', 'valve', 'material', 'accessory')",
            name=op.f("ck_catalog_items_kind_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'approved', 'archived')",
            name=op.f("ck_catalog_items_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_catalog_items_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["catalog_items.id"],
            name=op.f("fk_catalog_items_parent_id_catalog_items"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_catalog_items")),
        sa.UniqueConstraint(
            "organization_id",
            "kind",
            "code",
            "version_number",
            name="uq_catalog_item_version",
        ),
    )
    op.create_index(
        "ix_catalog_items_organization_kind",
        "catalog_items",
        ["organization_id", "kind"],
        unique=False,
    )
    op.create_index(
        "ix_catalog_items_code_version",
        "catalog_items",
        ["code", "version_number"],
        unique=False,
    )


def downgrade() -> None:
    """Supprime le catalogue technique versionné."""

    op.drop_index("ix_catalog_items_code_version", table_name="catalog_items")
    op.drop_index("ix_catalog_items_organization_kind", table_name="catalog_items")
    op.drop_table("catalog_items")
