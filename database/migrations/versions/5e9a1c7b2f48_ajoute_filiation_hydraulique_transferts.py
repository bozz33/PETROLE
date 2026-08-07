"""Ajoute la filiation hydraulique des transferts.

Un transfert peut désormais être calculé par HydroLiquid à partir d'un chemin et
d'un groupe de pompage. Les colonnes sont volontairement nullables : les
transferts existants, calculés à débit imposé, restent lisibles sans reprise.

Revision ID: 5e9a1c7b2f48
Revises: 8b1f2d6c4e90
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5e9a1c7b2f48"
down_revision: str | Sequence[str] | None = "8b1f2d6c4e90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transfer_runs",
        sa.Column("model_version_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.add_column(
        "transfer_runs",
        sa.Column("scenario_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.add_column(
        "transfer_runs",
        sa.Column("hydraulic_engine_version", sa.String(length=100), nullable=True),
    )
    op.create_foreign_key(
        "fk_transfer_runs_model_version",
        "transfer_runs",
        "model_versions",
        ["model_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_transfer_runs_scenario",
        "transfer_runs",
        "scenarios",
        ["scenario_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_transfer_runs_scenario", "transfer_runs", type_="foreignkey")
    op.drop_constraint("fk_transfer_runs_model_version", "transfer_runs", type_="foreignkey")
    op.drop_column("transfer_runs", "hydraulic_engine_version")
    op.drop_column("transfer_runs", "scenario_id")
    op.drop_column("transfer_runs", "model_version_id")
