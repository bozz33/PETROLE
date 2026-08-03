"""etend les rapports aux sources operationnelles

Identifiant : 5e5679809deb
Parent : cb72698e40e8
Créée le : 2026-08-03 02:29:39.973658
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5e5679809deb"
down_revision: str | Sequence[str] | None = "cb72698e40e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Applique la migration."""

    # Les rapports RPT-02 existants restent rattachés à leur calcul.
    op.add_column("reports", sa.Column("source_type", sa.String(length=30), nullable=True))
    op.add_column("reports", sa.Column("source_id", sa.Uuid(), nullable=True))
    op.execute("UPDATE reports SET source_type = 'calculation', source_id = calculation_id")
    op.alter_column("reports", "source_type", nullable=False)
    op.alter_column("reports", "source_id", nullable=False)
    op.alter_column("reports", "calculation_id", existing_type=sa.UUID(), nullable=True)
    op.create_index(
        "ix_reports_source_created",
        "reports",
        ["source_type", "source_id", "created_at"],
        unique=False,
    )
    op.create_unique_constraint(
        op.f("uq_reports_source_type"), "reports", ["source_type", "source_id", "idempotency_key"]
    )


def downgrade() -> None:
    """Annule la migration."""

    # Un retour arrière est refusé s'il supprimerait le rattachement d'un rapport opérationnel.
    op.drop_constraint(op.f("uq_reports_source_type"), "reports", type_="unique")
    op.drop_index("ix_reports_source_created", table_name="reports")
    op.alter_column("reports", "calculation_id", existing_type=sa.UUID(), nullable=False)
    op.drop_column("reports", "source_id")
    op.drop_column("reports", "source_type")
