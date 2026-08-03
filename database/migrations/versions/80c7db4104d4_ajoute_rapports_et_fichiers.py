"""ajoute rapports et fichiers

Identifiant : 80c7db4104d4
Parent : b0234888a40e
Créée le : 2026-08-03 00:51:52.859111
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "80c7db4104d4"
down_revision: str | Sequence[str] | None = "b0234888a40e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Applique la migration."""

    # Opérations de migration vérifiées.
    op.create_table(
        "files",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("bucket", sa.String(length=100), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=71), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_files_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_files")),
        sa.UniqueConstraint("bucket", "object_key", name=op.f("uq_files_bucket")),
    )
    op.create_index("ix_files_content_hash", "files", ["content_hash"], unique=False)
    op.create_index(
        "ix_files_organization_created", "files", ["organization_id", "created_at"], unique=False
    )
    op.create_table(
        "reports",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("calculation_id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("report_type", sa.String(length=50), nullable=False),
        sa.Column("template_version", sa.String(length=50), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("content_hash", sa.String(length=71), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_comment", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("format IN ('pdf')", name=op.f("ck_reports_format_valid")),
        sa.CheckConstraint(
            "status IN ('generated', 'approved', 'rejected')", name=op.f("ck_reports_status_valid")
        ),
        sa.ForeignKeyConstraint(
            ["calculation_id"],
            ["calculation_runs.id"],
            name=op.f("fk_reports_calculation_id_calculation_runs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["file_id"], ["files.id"], name=op.f("fk_reports_file_id_files"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_reports_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
        sa.UniqueConstraint(
            "calculation_id", "idempotency_key", name=op.f("uq_reports_calculation_id")
        ),
        sa.UniqueConstraint("file_id", name=op.f("uq_reports_file_id")),
    )
    op.create_index(
        "ix_reports_calculation_created", "reports", ["calculation_id", "created_at"], unique=False
    )
    # Fin des opérations de migration.


def downgrade() -> None:
    """Annule la migration."""

    # Opérations de migration vérifiées.
    op.drop_index("ix_reports_calculation_created", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_files_organization_created", table_name="files")
    op.drop_index("ix_files_content_hash", table_name="files")
    op.drop_table("files")
    # Fin des opérations de migration.
