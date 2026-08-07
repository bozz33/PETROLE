"""Distingue les données importables des pièces jointes documentaires.

Le MVP prévoit deux flux distincts : l'import scientifique (CSV, XLSX, JSON) et
les documents de projet (fiches constructeur, plans, rapports). Ils partagent le
même stockage privé mais n'acceptent pas les mêmes formats.

Revision ID: 7c2d4f8b1a35
Revises: 5e9a1c7b2f48
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7c2d4f8b1a35"
down_revision: str | Sequence[str] | None = "5e9a1c7b2f48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "files",
        sa.Column("purpose", sa.String(length=20), nullable=False, server_default="dataset"),
    )
    op.add_column("files", sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=True))
    op.add_column("files", sa.Column("description", sa.String(length=1_000), nullable=True))
    op.create_check_constraint(
        "purpose_valid", "files", "purpose IN ('dataset', 'document')"
    )
    op.create_foreign_key(
        "fk_files_project",
        "files",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_files_organization_purpose", "files", ["organization_id", "purpose"])
    op.alter_column("files", "purpose", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_files_organization_purpose", table_name="files")
    op.drop_constraint("fk_files_project", "files", type_="foreignkey")
    op.drop_constraint("purpose_valid", "files", type_="check")
    op.drop_column("files", "description")
    op.drop_column("files", "project_id")
    op.drop_column("files", "purpose")
