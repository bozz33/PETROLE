"""ajoute operations de stockage et decision

Identifiant : cb72698e40e8
Parent : 7d85db0b6563
Créée le : 2026-08-03 02:17:53.071811
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "cb72698e40e8"
down_revision: str | Sequence[str] | None = "7d85db0b6563"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Applique la migration."""

    # Tables persistantes des opérations du MVP.
    op.create_table(
        "tanks",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("tank_type", sa.String(length=40), nullable=False),
        sa.Column("elevation_m", sa.Float(), nullable=False),
        sa.Column("current_level_m", sa.Float(), nullable=False),
        sa.Column("fluid_id", sa.String(length=100), nullable=True),
        sa.Column("compatible_fluid_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("dead_volume_m3", sa.Float(), nullable=False),
        sa.Column("levels_payload", sa.JSON(), nullable=False),
        sa.Column("strapping_payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('available', 'unavailable', 'maintenance', 'bypassed')",
            name=op.f("ck_tanks_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_tanks_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"], ["sites.id"], name=op.f("fk_tanks_site_id_sites"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tanks")),
        sa.UniqueConstraint("organization_id", "code", name=op.f("uq_tanks_organization_id")),
    )
    op.create_index(
        "ix_tanks_organization_site", "tanks", ["organization_id", "site_id"], unique=False
    )
    op.create_table(
        "scenario_comparisons",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("calculation_ids", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=71), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_scenario_comparisons_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_scenario_comparisons_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenario_comparisons")),
        sa.UniqueConstraint(
            "project_id", "idempotency_key", name=op.f("uq_scenario_comparisons_project_id")
        ),
    )
    op.create_index(
        "ix_comparisons_project_created",
        "scenario_comparisons",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "transfer_runs",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_tank_id", sa.Uuid(), nullable=False),
        sa.Column("destination_tank_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("input_hash", sa.String(length=71), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=False),
        sa.Column("balance_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["destination_tank_id"],
            ["tanks.id"],
            name=op.f("fk_transfer_runs_destination_tank_id_tanks"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_transfer_runs_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_tank_id"],
            ["tanks.id"],
            name=op.f("fk_transfer_runs_source_tank_id_tanks"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transfer_runs")),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name=op.f("uq_transfer_runs_organization_id")
        ),
    )
    op.create_index(
        "ix_transfer_runs_organization_created",
        "transfer_runs",
        ["organization_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "optimization_runs",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("input_hash", sa.String(length=71), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=False),
        sa.Column("engine_version", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_optimization_runs_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.id"],
            name=op.f("fk_optimization_runs_scenario_id_scenarios"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_optimization_runs")),
        sa.UniqueConstraint(
            "scenario_id", "idempotency_key", name=op.f("uq_optimization_runs_scenario_id")
        ),
    )
    op.create_index(
        "ix_optimizations_scenario_created",
        "optimization_runs",
        ["scenario_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Annule la migration."""

    # Tables persistantes des opérations du MVP.
    op.drop_index("ix_optimizations_scenario_created", table_name="optimization_runs")
    op.drop_table("optimization_runs")
    op.drop_index("ix_transfer_runs_organization_created", table_name="transfer_runs")
    op.drop_table("transfer_runs")
    op.drop_index("ix_comparisons_project_created", table_name="scenario_comparisons")
    op.drop_table("scenario_comparisons")
    op.drop_index("ix_tanks_organization_site", table_name="tanks")
    op.drop_table("tanks")
