"""Normalise les référentiels et responsables des projets.

Identifiant : 4d7f9a3b2c85
Parent : 3c6e8f2a1b74
Créée le : 3 août 2026
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4d7f9a3b2c85"
down_revision: str | Sequence[str] | None = "3c6e8f2a1b74"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Migre les tableaux JSON vers deux associations avec intégrité référentielle."""

    op.create_table(
        "project_rule_sets",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("rule_set_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_rule_sets_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rule_set_id"],
            ["rule_sets.id"],
            name=op.f("fk_project_rule_sets_rule_set_id_rule_sets"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "project_id",
            "rule_set_id",
            name=op.f("pk_project_rule_sets"),
        ),
    )
    op.create_table(
        "project_responsibles",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_responsibles_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_accounts.id"],
            name=op.f("fk_project_responsibles_user_id_user_accounts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "project_id",
            "user_id",
            name=op.f("pk_project_responsibles"),
        ),
    )
    op.execute(
        "INSERT INTO project_rule_sets (project_id, rule_set_id) "
        "SELECT projects.id, selected.value::uuid FROM projects "
        "CROSS JOIN LATERAL json_array_elements_text(projects.rule_set_ids) AS selected(value)"
    )
    op.execute(
        "INSERT INTO project_responsibles (project_id, user_id) "
        "SELECT projects.id, selected.value::uuid FROM projects "
        "CROSS JOIN LATERAL json_array_elements_text(projects.responsible_user_ids) "
        "AS selected(value)"
    )
    op.drop_column("projects", "responsible_user_ids")
    op.drop_column("projects", "rule_set_ids")


def downgrade() -> None:
    """Restaure les tableaux JSON en conservant toutes les associations."""

    op.add_column(
        "projects",
        sa.Column(
            "rule_set_ids",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "responsible_user_ids",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE projects SET rule_set_ids = COALESCE(("
        "SELECT json_agg(project_rule_sets.rule_set_id::text ORDER BY "
        "project_rule_sets.rule_set_id) FROM project_rule_sets "
        "WHERE project_rule_sets.project_id = projects.id), '[]'::json)"
    )
    op.execute(
        "UPDATE projects SET responsible_user_ids = COALESCE(("
        "SELECT json_agg(project_responsibles.user_id::text ORDER BY "
        "project_responsibles.user_id) FROM project_responsibles "
        "WHERE project_responsibles.project_id = projects.id), '[]'::json)"
    )
    op.drop_table("project_responsibles")
    op.drop_table("project_rule_sets")
