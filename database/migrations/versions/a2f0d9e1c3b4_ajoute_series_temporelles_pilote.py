"""Ajoute les tags et séries temporelles immuables du pilote V1.

Les échantillons bruts sont distincts de leur projection SI afin de préserver
le lignage D09. Les index temporels respectent D12 et restent compatibles avec
un futur passage vers TimescaleDB ou un autre stockage spécialisé.

Revision ID: a2f0d9e1c3b4
Revises: 9f3b6e0d5c17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a2f0d9e1c3b4"
down_revision: str | Sequence[str] | None = "9f3b6e0d5c17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée la persistance temporelle du pilote sans modifier les datasets MVP."""

    op.create_table(
        "tags",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("asset_instance_id", sa.Uuid(), nullable=True),
        sa.Column("external_name", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("measurement_type", sa.String(length=30), nullable=False),
        sa.Column("dimension", sa.String(length=40), nullable=False),
        sa.Column("source_unit", sa.String(length=80), nullable=False),
        sa.Column("si_unit", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("metadata_payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "measurement_type IN "
            "('pressure', 'flow', 'level', 'temperature', 'status', 'vibration', 'energy')",
            name=op.f("ck_tags_measurement_type_valid"),
        ),
        sa.CheckConstraint("status IN ('active', 'archived')", name=op.f("ck_tags_status_valid")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_tags_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            name=op.f("fk_tags_site_id_sites"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["asset_instance_id"],
            ["asset_instances.id"],
            name=op.f("fk_tags_asset_instance_id_asset_instances"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tags")),
        sa.UniqueConstraint(
            "site_id",
            "external_name",
            name=op.f("uq_tags_site_external_name"),
        ),
    )
    op.create_index("ix_tags_organization_site", "tags", ["organization_id", "site_id"])
    op.create_index("ix_tags_asset_instance", "tags", ["asset_instance_id"])

    op.create_table(
        "time_series_imports",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("processing_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source_hash", sa.String(length=71), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'completed_with_errors', 'failed')",
            name=op.f("ck_time_series_imports_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_time_series_imports_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_time_series_imports_dataset_id_datasets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name=op.f("fk_time_series_imports_tag_id_tags"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_time_series_imports")),
        sa.UniqueConstraint(
            "dataset_id",
            "tag_id",
            "idempotency_key",
            name=op.f("uq_ts_import_dataset_tag_key"),
        ),
    )
    op.create_index(
        "ix_ts_imports_dataset_created",
        "time_series_imports",
        ["dataset_id", "created_at"],
    )
    op.create_index("ix_ts_imports_tag_created", "time_series_imports", ["tag_id", "created_at"])

    op.create_table(
        "samples_raw",
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("time_series_import_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_row_id", sa.Uuid(), nullable=True),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingest_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_value", sa.JSON(), nullable=False),
        sa.Column("source_unit", sa.String(length=80), nullable=False),
        sa.Column("quality", sa.String(length=20), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "quality IN ('good', 'uncertain', 'bad', 'substituted', 'estimated')",
            name=op.f("ck_samples_raw_quality_valid"),
        ),
        sa.CheckConstraint(
            "sequence_number IS NULL OR sequence_number >= 0",
            name=op.f("ck_samples_raw_sequence_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name=op.f("fk_samples_raw_tag_id_tags"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["time_series_import_id"],
            ["time_series_imports.id"],
            name=op.f("fk_samples_raw_time_series_import_id_time_series_imports"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_samples_raw_dataset_id_datasets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_row_id"],
            ["dataset_rows.id"],
            name=op.f("fk_samples_raw_dataset_row_id_dataset_rows"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_samples_raw")),
    )
    op.create_index(
        "ix_samples_raw_tag_source_timestamp",
        "samples_raw",
        ["tag_id", "source_timestamp"],
    )
    op.create_index(
        "ix_samples_raw_import_sequence",
        "samples_raw",
        ["time_series_import_id", "sequence_number"],
    )

    op.create_table(
        "samples_normalized",
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("raw_sample_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value_si", sa.Float(), nullable=False),
        sa.Column("si_unit", sa.String(length=80), nullable=False),
        sa.Column("quality", sa.String(length=20), nullable=False),
        sa.Column("processing_version", sa.String(length=80), nullable=False),
        sa.Column("processing_payload", sa.JSON(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "quality IN ('good', 'uncertain', 'bad', 'substituted', 'estimated')",
            name=op.f("ck_samples_normalized_quality_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name=op.f("fk_samples_normalized_tag_id_tags"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["raw_sample_id"],
            ["samples_raw.id"],
            name=op.f("fk_samples_normalized_raw_sample_id_samples_raw"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_samples_normalized")),
        sa.UniqueConstraint(
            "raw_sample_id",
            "processing_version",
            name=op.f("uq_samples_normalized_raw_version"),
        ),
    )
    op.create_index(
        "ix_samples_normalized_tag_timestamp",
        "samples_normalized",
        ["tag_id", "timestamp"],
    )


def downgrade() -> None:
    """Retire les tables pilote dans l'ordre des dépendances."""

    op.drop_index("ix_samples_normalized_tag_timestamp", table_name="samples_normalized")
    op.drop_table("samples_normalized")
    op.drop_index("ix_samples_raw_import_sequence", table_name="samples_raw")
    op.drop_index("ix_samples_raw_tag_source_timestamp", table_name="samples_raw")
    op.drop_table("samples_raw")
    op.drop_index("ix_ts_imports_tag_created", table_name="time_series_imports")
    op.drop_index("ix_ts_imports_dataset_created", table_name="time_series_imports")
    op.drop_table("time_series_imports")
    op.drop_index("ix_tags_asset_instance", table_name="tags")
    op.drop_index("ix_tags_organization_site", table_name="tags")
    op.drop_table("tags")
