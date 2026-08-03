"""schema initial du MVP

Identifiant : b0234888a40e
Parent :
Créée le : 2026-08-03 00:17:23.017865
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b0234888a40e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Applique la migration."""

    # Opérations de migration vérifiées.
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("default_locale", sa.String(length=10), nullable=False),
        sa.Column("default_unit_system", sa.String(length=20), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("slug", name=op.f("uq_organizations_slug")),
    )
    op.create_table(
        "audit_events",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("object_type", sa.String(length=100), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_audit_events_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(
        "ix_audit_events_organization_created",
        "audit_events",
        ["organization_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "projects",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived')", name=op.f("ck_projects_status_valid")
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_projects_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("organization_id", "code", name=op.f("uq_projects_organization_id")),
    )
    op.create_index(
        "ix_projects_organization_status", "projects", ["organization_id", "status"], unique=False
    )
    op.create_table(
        "model_versions",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("content_hash", sa.String(length=71), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'approved', 'archived')",
            name=op.f("ck_model_versions_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["model_versions.id"],
            name=op.f("fk_model_versions_parent_id_model_versions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_model_versions_project_id_projects"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_versions")),
        sa.UniqueConstraint(
            "project_id", "version_number", name=op.f("uq_model_versions_project_id")
        ),
    )
    op.create_index(
        "ix_model_versions_project_status", "model_versions", ["project_id", "status"], unique=False
    )
    op.create_table(
        "scenarios",
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["model_versions.id"],
            name=op.f("fk_scenarios_model_version_id_model_versions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["scenarios.id"],
            name=op.f("fk_scenarios_parent_id_scenarios"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenarios")),
        sa.UniqueConstraint("model_version_id", "name", name=op.f("uq_scenarios_model_version_id")),
    )
    op.create_index("ix_scenarios_model_version", "scenarios", ["model_version_id"], unique=False)
    op.create_table(
        "calculation_runs",
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=True),
        sa.Column("engine", sa.String(length=100), nullable=False),
        sa.Column("engine_version", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("input_hash", sa.String(length=71), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("diagnostics", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "status IN ('SIM_QUEUED', 'SIM_RUNNING', 'SIM_CONVERGED', 'SIM_CONVERGED_WARN', 'SIM_INVALID_INPUT', 'SIM_NO_PHYSICAL_SOLUTION', 'SIM_NOT_CONVERGED', 'SIM_CANCELLED')",
            name=op.f("ck_calculation_runs_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.id"],
            name=op.f("fk_calculation_runs_scenario_id_scenarios"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calculation_runs")),
        sa.UniqueConstraint(
            "scenario_id", "idempotency_key", name=op.f("uq_calculation_runs_scenario_id")
        ),
    )
    op.create_index(
        "ix_calculation_runs_input_hash", "calculation_runs", ["input_hash"], unique=False
    )
    op.create_index(
        "ix_calculation_runs_scenario_created",
        "calculation_runs",
        ["scenario_id", "created_at"],
        unique=False,
    )
    # Fin des opérations de migration.


def downgrade() -> None:
    """Annule la migration."""

    # Opérations de migration vérifiées.
    op.drop_index("ix_calculation_runs_scenario_created", table_name="calculation_runs")
    op.drop_index("ix_calculation_runs_input_hash", table_name="calculation_runs")
    op.drop_table("calculation_runs")
    op.drop_index("ix_scenarios_model_version", table_name="scenarios")
    op.drop_table("scenarios")
    op.drop_index("ix_model_versions_project_status", table_name="model_versions")
    op.drop_table("model_versions")
    op.drop_index("ix_projects_organization_status", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_audit_events_organization_created", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("organizations")
    # Fin des opérations de migration.
