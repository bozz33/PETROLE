"""Ajoute le référentiel normatif et les évaluations de règles.

Identifiant : e82f4b7a9d10
Parent : d47e8a6f1c32
Créée le : 3 août 2026
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e82f4b7a9d10"
down_revision: str | Sequence[str] | None = "d47e8a6f1c32"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée les éditions, jeux, règles et résultats de contrôle."""

    op.create_table(
        "standards",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("issuing_body", sa.String(length=120), nullable=False),
        sa.Column("edition", sa.String(length=80), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("licensed_copy_ref", sa.String(length=500), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("content_hash", sa.String(length=71), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'withdrawn', 'archived')",
            name=op.f("ck_standards_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_standards_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["standards.id"],
            name=op.f("fk_standards_parent_id_standards"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_standards")),
        sa.UniqueConstraint(
            "organization_id",
            "code",
            "edition",
            name=op.f("uq_standard_edition"),
        ),
    )
    op.create_index(
        "ix_standards_organization_status",
        "standards",
        ["organization_id", "status"],
    )
    op.create_table(
        "rule_sets",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("domain", sa.String(length=80), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("content_hash", sa.String(length=71), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'approved', 'archived')",
            name=op.f("ck_rule_sets_status_valid"),
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name=op.f("ck_rule_sets_version_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_rule_sets_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["rule_sets.id"],
            name=op.f("fk_rule_sets_parent_id_rule_sets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_sets")),
        sa.UniqueConstraint(
            "organization_id",
            "code",
            "version_number",
            name=op.f("uq_rule_set_version"),
        ),
    )
    op.create_index(
        "ix_rule_sets_organization_domain",
        "rule_sets",
        ["organization_id", "domain", "status"],
    )
    op.create_table(
        "rule_set_standards",
        sa.Column("rule_set_id", sa.Uuid(), nullable=False),
        sa.Column("standard_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rule_set_id"],
            ["rule_sets.id"],
            name=op.f("fk_rule_set_standards_rule_set_id_rule_sets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["standard_id"],
            ["standards.id"],
            name=op.f("fk_rule_set_standards_standard_id_standards"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_set_standards")),
        sa.UniqueConstraint(
            "rule_set_id",
            "standard_id",
            name=op.f("uq_rule_set_standard"),
        ),
    )
    op.create_table(
        "rules",
        sa.Column("rule_set_id", sa.Uuid(), nullable=False),
        sa.Column("standard_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("domain", sa.String(length=80), nullable=False),
        sa.Column("metric_path", sa.String(length=300), nullable=False),
        sa.Column("operator", sa.String(length=20), nullable=False),
        sa.Column("limit_value", sa.Float(), nullable=True),
        sa.Column("upper_limit_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("applicability", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source_clause_ref", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "operator IN ('le', 'lt', 'ge', 'gt', 'eq', 'between')",
            name=op.f("ck_rules_operator_valid"),
        ),
        sa.CheckConstraint(
            "severity IN ('information', 'warning', 'error', 'blocking')",
            name=op.f("ck_rules_severity_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'approved', 'rejected')",
            name=op.f("ck_rules_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["rule_set_id"],
            ["rule_sets.id"],
            name=op.f("fk_rules_rule_set_id_rule_sets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["standard_id"],
            ["standards.id"],
            name=op.f("fk_rules_standard_id_standards"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rules")),
        sa.UniqueConstraint("rule_set_id", "code", name=op.f("uq_rule_code")),
    )
    op.create_index("ix_rules_rule_set_status", "rules", ["rule_set_id", "status"])
    op.create_table(
        "rule_evaluations",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("calculation_id", sa.Uuid(), nullable=False),
        sa.Column("rule_set_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("object_type", sa.String(length=100), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("measured_value", sa.Float(), nullable=True),
        sa.Column("limit_value", sa.Float(), nullable=True),
        sa.Column("margin", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "status IN ('compliant', 'non_compliant', 'not_applicable', 'error')",
            name=op.f("ck_rule_evaluations_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["calculation_id"],
            ["calculation_runs.id"],
            name=op.f("fk_rule_evaluations_calculation_id_calculation_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_rule_evaluations_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["rules.id"],
            name=op.f("fk_rule_evaluations_rule_id_rules"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["rule_set_id"],
            ["rule_sets.id"],
            name=op.f("fk_rule_evaluations_rule_set_id_rule_sets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_evaluations")),
        sa.UniqueConstraint(
            "calculation_id",
            "rule_id",
            name=op.f("uq_rule_evaluation"),
        ),
    )
    op.create_index(
        "ix_rule_evaluations_calculation",
        "rule_evaluations",
        ["calculation_id"],
    )
    op.create_index(
        "ix_rule_evaluations_organization_created",
        "rule_evaluations",
        ["organization_id", "created_at"],
    )


def downgrade() -> None:
    """Supprime le référentiel normatif dans l'ordre des dépendances."""

    op.drop_index(
        "ix_rule_evaluations_organization_created",
        table_name="rule_evaluations",
    )
    op.drop_index("ix_rule_evaluations_calculation", table_name="rule_evaluations")
    op.drop_table("rule_evaluations")
    op.drop_index("ix_rules_rule_set_status", table_name="rules")
    op.drop_table("rules")
    op.drop_table("rule_set_standards")
    op.drop_index("ix_rule_sets_organization_domain", table_name="rule_sets")
    op.drop_table("rule_sets")
    op.drop_index("ix_standards_organization_status", table_name="standards")
    op.drop_table("standards")
