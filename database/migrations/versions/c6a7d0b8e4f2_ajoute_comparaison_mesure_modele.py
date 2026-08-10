"""Ajoute les correspondances et résidus immuables du Pilote V1-B.

La migration ne touche ni aux échantillons bruts/normalisés ni aux calculs du
MVP : elle ajoute une couche de comparaison traçable entre leurs snapshots.

Revision ID: c6a7d0b8e4f2
Revises: a2f0d9e1c3b4
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c6a7d0b8e4f2"
down_revision: str | Sequence[str] | None = "a2f0d9e1c3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée les objets V1-B sans modifier les deux sources immuables."""

    op.create_table(
        "measurement_model_mappings",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("metric", sa.String(length=40), nullable=False),
        sa.Column("dimension", sa.String(length=40), nullable=False),
        sa.Column("si_unit", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source_ref", sa.String(length=1_000), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "version_number > 0", name=op.f("ck_measurement_model_mappings_version_positive")
        ),
        sa.CheckConstraint(
            "target_type IN ('node', 'edge', 'pump')",
            name=op.f("ck_measurement_model_mappings_target_type_valid"),
        ),
        sa.CheckConstraint(
            "metric IN ('pressure_pa', 'flow_m3_s', 'pressure_min_pa', "
            "'pressure_max_pa', 'suction_pressure_pa', 'discharge_pressure_pa')",
            name=op.f("ck_measurement_model_mappings_metric_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'approved', 'archived')",
            name=op.f("ck_measurement_model_mappings_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_measurement_model_mappings_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_measurement_model_mappings_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["model_versions.id"],
            name=op.f("fk_measurement_model_mappings_model_version_id_model_versions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name=op.f("fk_measurement_model_mappings_tag_id_tags"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user_accounts.id"],
            name=op.f("fk_measurement_model_mappings_created_by_user_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["user_accounts.id"],
            name=op.f("fk_measurement_model_mappings_approved_by_user_accounts"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_measurement_model_mappings")),
        sa.UniqueConstraint(
            "tag_id",
            "version_number",
            name=op.f("uq_measurement_mapping_tag_version"),
        ),
    )
    op.create_index(
        "ix_measurement_mappings_project_status",
        "measurement_model_mappings",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_measurement_mappings_model_status",
        "measurement_model_mappings",
        ["model_version_id", "status"],
    )
    op.create_index(
        "ix_measurement_mappings_tag_status",
        "measurement_model_mappings",
        ["tag_id", "status"],
    )

    op.create_table(
        "measurement_comparisons",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("mapping_id", sa.Uuid(), nullable=False),
        sa.Column("calculation_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.Column("processing_version", sa.String(length=80), nullable=False),
        sa.Column("start_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("included_qualities", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=71), nullable=False),
        sa.Column("calculation_input_hash", sa.String(length=71), nullable=False),
        sa.Column("engine", sa.String(length=100), nullable=False),
        sa.Column("engine_version", sa.String(length=100), nullable=False),
        sa.Column("simulated_value_si", sa.Float(), nullable=False),
        sa.Column("si_unit", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('completed')",
            name=op.f("ck_measurement_comparisons_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_measurement_comparisons_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_measurement_comparisons_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["mapping_id"],
            ["measurement_model_mappings.id"],
            name=op.f("fk_measurement_comparisons_mapping_id_measurement_model_mappings"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["calculation_id"],
            ["calculation_runs.id"],
            name=op.f("fk_measurement_comparisons_calculation_id_calculation_runs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name=op.f("fk_measurement_comparisons_tag_id_tags"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user_accounts.id"],
            name=op.f("fk_measurement_comparisons_created_by_user_accounts"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_measurement_comparisons")),
        sa.UniqueConstraint(
            "organization_id",
            "input_hash",
            name=op.f("uq_measurement_comparison_input"),
        ),
    )
    op.create_index(
        "ix_measurement_comparisons_project_created",
        "measurement_comparisons",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_measurement_comparisons_mapping_created",
        "measurement_comparisons",
        ["mapping_id", "created_at"],
    )
    op.create_index(
        "ix_measurement_comparisons_calculation",
        "measurement_comparisons",
        ["calculation_id"],
    )

    op.create_table(
        "measurement_residuals",
        sa.Column("comparison_id", sa.Uuid(), nullable=False),
        sa.Column("normalized_sample_id", sa.Uuid(), nullable=False),
        sa.Column("raw_sample_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_row_id", sa.Uuid(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("measured_value_si", sa.Float(), nullable=False),
        sa.Column("simulated_value_si", sa.Float(), nullable=False),
        sa.Column("residual_si", sa.Float(), nullable=False),
        sa.Column("quality", sa.String(length=20), nullable=False),
        sa.Column("included_in_kpi", sa.Boolean(), nullable=False),
        sa.Column("exclusion_reason", sa.String(length=80), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["comparison_id"],
            ["measurement_comparisons.id"],
            name=op.f("fk_measurement_residuals_comparison_id_measurement_comparisons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["normalized_sample_id"],
            ["samples_normalized.id"],
            name=op.f("fk_measurement_residuals_normalized_sample_id_samples_normalized"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["raw_sample_id"],
            ["samples_raw.id"],
            name=op.f("fk_measurement_residuals_raw_sample_id_samples_raw"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_measurement_residuals_dataset_id_datasets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_row_id"],
            ["dataset_rows.id"],
            name=op.f("fk_measurement_residuals_dataset_row_id_dataset_rows"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_measurement_residuals")),
        sa.UniqueConstraint(
            "comparison_id",
            "normalized_sample_id",
            name=op.f("uq_measurement_residual_comparison_sample"),
        ),
    )
    op.create_index(
        "ix_measurement_residuals_comparison_timestamp",
        "measurement_residuals",
        ["comparison_id", "timestamp"],
    )
    op.create_index(
        "ix_measurement_residuals_raw_sample",
        "measurement_residuals",
        ["raw_sample_id"],
    )


def downgrade() -> None:
    """Retire les artefacts V1-B sans toucher aux séries ou aux calculs sources."""

    op.drop_index("ix_measurement_residuals_raw_sample", table_name="measurement_residuals")
    op.drop_index(
        "ix_measurement_residuals_comparison_timestamp",
        table_name="measurement_residuals",
    )
    op.drop_table("measurement_residuals")
    op.drop_index("ix_measurement_comparisons_calculation", table_name="measurement_comparisons")
    op.drop_index(
        "ix_measurement_comparisons_mapping_created",
        table_name="measurement_comparisons",
    )
    op.drop_index(
        "ix_measurement_comparisons_project_created",
        table_name="measurement_comparisons",
    )
    op.drop_table("measurement_comparisons")
    op.drop_index(
        "ix_measurement_mappings_model_status",
        table_name="measurement_model_mappings",
    )
    op.drop_index(
        "ix_measurement_mappings_tag_status",
        table_name="measurement_model_mappings",
    )
    op.drop_index(
        "ix_measurement_mappings_project_status",
        table_name="measurement_model_mappings",
    )
    op.drop_table("measurement_model_mappings")
