"""Ajoute la décision humaine sur une simulation.

Le workflow du MVP distingue l'approbation du rapport, qui atteste d'une
rédaction, de l'approbation du calcul, qui retient un résultat physique comme
référence. Seule la première existait.

Revision ID: 9f3b6e0d5c17
Revises: 7c2d4f8b1a35
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9f3b6e0d5c17"
down_revision: str | Sequence[str] | None = "7c2d4f8b1a35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "calculation_runs",
        sa.Column(
            "approval_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "calculation_runs",
        sa.Column("approval_comment", sa.String(length=2_000), nullable=True),
    )
    op.add_column(
        "calculation_runs",
        sa.Column("approved_by", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.add_column(
        "calculation_runs",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "approval_status_valid",
        "calculation_runs",
        "approval_status IN ('pending', 'approved', 'rejected')",
    )
    op.create_foreign_key(
        "fk_calculation_runs_approved_by",
        "calculation_runs",
        "user_accounts",
        ["approved_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("calculation_runs", "approval_status", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_calculation_runs_approved_by", "calculation_runs", type_="foreignkey")
    op.drop_constraint("approval_status_valid", "calculation_runs", type_="check")
    op.drop_column("calculation_runs", "approved_at")
    op.drop_column("calculation_runs", "approved_by")
    op.drop_column("calculation_runs", "approval_comment")
    op.drop_column("calculation_runs", "approval_status")
