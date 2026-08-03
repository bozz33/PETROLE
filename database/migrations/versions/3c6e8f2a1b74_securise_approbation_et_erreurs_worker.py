"""Sécurise l'approbation des modèles et les erreurs techniques du worker.

Identifiant : 3c6e8f2a1b74
Parent : 2a4d7b9e1c63
Créée le : 3 août 2026
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3c6e8f2a1b74"
down_revision: str | Sequence[str] | None = "2a4d7b9e1c63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute unicité partielle et statut réservé aux pannes techniques."""

    op.create_index(
        "uq_model_versions_one_approved_per_project",
        "model_versions",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status = 'approved'"),
    )
    op.drop_constraint(
        op.f("ck_calculation_runs_status_valid"),
        "calculation_runs",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_calculation_runs_status_valid"),
        "calculation_runs",
        "status IN ('SIM_QUEUED', 'SIM_RUNNING', 'SIM_CONVERGED', "
        "'SIM_CONVERGED_WARN', 'SIM_INVALID_INPUT', 'SIM_NO_PHYSICAL_SOLUTION', "
        "'SIM_NOT_CONVERGED', 'SIM_CANCELLED', 'SIM_TECHNICAL_ERROR')",
    )


def downgrade() -> None:
    """Restaure le contrat de statut et l'index antérieurs."""

    op.execute(
        "UPDATE calculation_runs SET status = 'SIM_NOT_CONVERGED' "
        "WHERE status = 'SIM_TECHNICAL_ERROR'"
    )
    op.drop_constraint(
        op.f("ck_calculation_runs_status_valid"),
        "calculation_runs",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_calculation_runs_status_valid"),
        "calculation_runs",
        "status IN ('SIM_QUEUED', 'SIM_RUNNING', 'SIM_CONVERGED', "
        "'SIM_CONVERGED_WARN', 'SIM_INVALID_INPUT', 'SIM_NO_PHYSICAL_SOLUTION', "
        "'SIM_NOT_CONVERGED', 'SIM_CANCELLED')",
    )
    op.drop_index(
        "uq_model_versions_one_approved_per_project",
        table_name="model_versions",
    )
