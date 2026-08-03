"""ajoute les jeux de donnees et imports

Identifiant : 540e26fff170
Parent : 80c7db4104d4
Créée le : 2026-08-03 01:20:20.469125
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "540e26fff170"
down_revision: str | Sequence[str] | None = "80c7db4104d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Applique la migration."""

    # Opérations de migration vérifiées.
    op.create_table(
        "datasets",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("mapping", sa.JSON(), nullable=False),
        sa.Column("preview", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('profile', 'pump_curve', 'strapping', 'measurements', 'generic')",
            name=op.f("ck_datasets_kind_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('uploaded', 'previewed', 'mapped', 'imported', 'failed')",
            name=op.f("ck_datasets_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["file_id"], ["files.id"], name=op.f("fk_datasets_file_id_files"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_datasets_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_datasets_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_datasets")),
    )
    op.create_index(
        "ix_datasets_organization_created",
        "datasets",
        ["organization_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "dataset_imports",
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=71), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "status IN ('completed', 'completed_with_errors', 'failed')",
            name=op.f("ck_dataset_imports_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_dataset_imports_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dataset_imports")),
        sa.UniqueConstraint(
            "dataset_id", "idempotency_key", name=op.f("uq_dataset_imports_dataset_id")
        ),
    )
    op.create_index(
        "ix_dataset_imports_dataset_created",
        "dataset_imports",
        ["dataset_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "dataset_rows",
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("normalized_payload", sa.JSON(), nullable=False),
        sa.Column("corrected_payload", sa.JSON(), nullable=True),
        sa.Column("quality", sa.String(length=20), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_dataset_rows_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dataset_rows")),
        sa.UniqueConstraint("dataset_id", "source_row", name=op.f("uq_dataset_rows_dataset_id")),
    )
    op.create_index(
        "ix_dataset_rows_dataset_source", "dataset_rows", ["dataset_id", "source_row"], unique=False
    )
    # Fin des opérations de migration.


def downgrade() -> None:
    """Annule la migration."""

    # Opérations de migration vérifiées.
    op.drop_index("ix_dataset_rows_dataset_source", table_name="dataset_rows")
    op.drop_table("dataset_rows")
    op.drop_index("ix_dataset_imports_dataset_created", table_name="dataset_imports")
    op.drop_table("dataset_imports")
    op.drop_index("ix_datasets_organization_created", table_name="datasets")
    op.drop_table("datasets")
    # Fin des opérations de migration.
