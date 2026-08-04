"""Ajoute le statut d'erreur numérique aux calculs.

Identifiant : 8b1f2d6c4e90
Parent : 4d7f9a3b2c85
Créée le : 4 août 2026
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "8b1f2d6c4e90"
down_revision: str | Sequence[str] | None = "4d7f9a3b2c85"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT_NAME = "ck_calculation_runs_status_valid"
_STATUS_WITH_NUMERIC_ERROR = (
    "status IN ('SIM_QUEUED', 'SIM_RUNNING', 'SIM_CONVERGED', "
    "'SIM_CONVERGED_WARN', 'SIM_INVALID_INPUT', 'SIM_NO_PHYSICAL_SOLUTION', "
    "'SIM_NOT_CONVERGED', 'SIM_CANCELLED', 'SIM_NUMERIC_ERROR', "
    "'SIM_TECHNICAL_ERROR')"
)
_STATUS_BEFORE_NUMERIC_ERROR = (
    "status IN ('SIM_QUEUED', 'SIM_RUNNING', 'SIM_CONVERGED', "
    "'SIM_CONVERGED_WARN', 'SIM_INVALID_INPUT', 'SIM_NO_PHYSICAL_SOLUTION', "
    "'SIM_NOT_CONVERGED', 'SIM_CANCELLED', 'SIM_TECHNICAL_ERROR')"
)


def upgrade() -> None:
    """Autorise la classification explicite des incohérences numériques."""

    op.drop_constraint(
        op.f(_CONSTRAINT_NAME),
        "calculation_runs",
        type_="check",
    )
    op.create_check_constraint(
        op.f(_CONSTRAINT_NAME),
        "calculation_runs",
        _STATUS_WITH_NUMERIC_ERROR,
    )


def downgrade() -> None:
    """Restaure la contrainte antérieure sans réinterpréter les données."""

    # Un downgrade n'est sûr que si aucune ligne n'utilise le nouveau statut.
    # PostgreSQL refusera la contrainte précédente dans le cas contraire, ce qui
    # protège les données d'une conversion silencieuse.
    op.drop_constraint(
        op.f(_CONSTRAINT_NAME),
        "calculation_runs",
        type_="check",
    )
    op.create_check_constraint(
        op.f(_CONSTRAINT_NAME),
        "calculation_runs",
        _STATUS_BEFORE_NUMERIC_ERROR,
    )
