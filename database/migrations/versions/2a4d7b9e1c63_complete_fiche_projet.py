"""Complète la fiche projet du MVP.

Identifiant : 2a4d7b9e1c63
Parent : f19c6d3e5a42
Créée le : 3 août 2026
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2a4d7b9e1c63"
down_revision: str | Sequence[str] | None = "f19c6d3e5a42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute le type, les unités, les référentiels et les responsables."""

    op.add_column(
        "projects",
        sa.Column(
            "project_type",
            sa.String(length=30),
            server_default="liquid_pipeline",
            nullable=False,
        ),
    )
    op.add_column(
        "projects",
        sa.Column("unit_system", sa.String(length=20), server_default="SI", nullable=False),
    )
    op.add_column(
        "projects",
        sa.Column("rule_set_ids", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
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
    op.create_check_constraint(
        op.f("ck_projects_project_type_valid"),
        "projects",
        "project_type IN ('liquid_pipeline', 'terminal', 'gas_pipeline', 'combined')",
    )
    op.create_check_constraint(
        op.f("ck_projects_unit_system_valid"),
        "projects",
        "unit_system IN ('SI')",
    )


def downgrade() -> None:
    """Restaure la fiche projet antérieure."""

    op.drop_constraint(op.f("ck_projects_unit_system_valid"), "projects", type_="check")
    op.drop_constraint(op.f("ck_projects_project_type_valid"), "projects", type_="check")
    op.drop_column("projects", "responsible_user_ids")
    op.drop_column("projects", "rule_set_ids")
    op.drop_column("projects", "unit_system")
    op.drop_column("projects", "project_type")
