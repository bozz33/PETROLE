"""Ajoute l'annulation explicite des tâches différées.

Identifiant : d47e8a6f1c32
Parent : a31d7e4c9b20
Créée le : 3 août 2026
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d47e8a6f1c32"
down_revision: str | Sequence[str] | None = "a31d7e4c9b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Autorise le statut terminal cancelled dans la file persistante."""

    op.drop_constraint(
        op.f("ck_background_jobs_status_valid"),
        "background_jobs",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_background_jobs_status_valid"),
        "background_jobs",
        "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
    )


def downgrade() -> None:
    """Restaure les statuts historiques après vérification des données."""

    connection = op.get_bind()
    cancelled_count = connection.scalar(
        sa.text("SELECT count(*) FROM background_jobs WHERE status = 'cancelled'")
    )
    if cancelled_count:
        raise RuntimeError(
            "Le retour arrière est impossible tant que des tâches annulées sont présentes."
        )
    op.drop_constraint(
        op.f("ck_background_jobs_status_valid"),
        "background_jobs",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_background_jobs_status_valid"),
        "background_jobs",
        "status IN ('queued', 'running', 'completed', 'failed')",
    )
