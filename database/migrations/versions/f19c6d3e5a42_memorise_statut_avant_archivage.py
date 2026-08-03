"""Mémorise le statut précédant l'archivage d'un projet.

Identifiant : f19c6d3e5a42
Parent : e82f4b7a9d10
Créée le : 3 août 2026
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f19c6d3e5a42"
down_revision: str | Sequence[str] | None = "e82f4b7a9d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute l'état de restauration et normalise les archives historiques."""

    op.add_column(
        "projects",
        sa.Column("archived_from_status", sa.String(length=20), nullable=True),
    )
    op.execute(
        "UPDATE projects SET archived_from_status = 'draft' WHERE status = 'archived'"
    )
    op.create_check_constraint(
        op.f("ck_projects_archive_state_valid"),
        "projects",
        "(status = 'archived' AND archived_from_status IN ('draft', 'active')) "
        "OR (status != 'archived' AND archived_from_status IS NULL)",
    )


def downgrade() -> None:
    """Retire l'état de restauration lorsque aucune archive ne le requiert."""

    connection = op.get_bind()
    archived_count = connection.scalar(
        sa.text(
            "SELECT count(*) FROM projects "
            "WHERE status = 'archived' AND archived_from_status IS NOT NULL"
        )
    )
    if archived_count:
        raise RuntimeError(
            "Le retour arrière est impossible tant que des projets archivés sont présents."
        )
    op.drop_constraint(
        op.f("ck_projects_archive_state_valid"),
        "projects",
        type_="check",
    )
    op.drop_column("projects", "archived_from_status")
