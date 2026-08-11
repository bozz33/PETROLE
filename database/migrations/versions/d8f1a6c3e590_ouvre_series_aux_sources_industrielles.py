"""Ouvre les séries temporelles aux sources industrielles sans faux dataset.

Les imports fichiers existants restent inchangés. Une ingestion OPC UA ou
historian peut désormais conserver un échantillon brut avec ``dataset_id`` nul,
tout en restant liée à un ``time_series_import`` et à un tag existants.

Revision ID: d8f1a6c3e590
Revises: c6a7d0b8e4f2
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d8f1a6c3e590"
down_revision: str | Sequence[str] | None = "c6a7d0b8e4f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Autorise une filiation industrielle sans affaiblir l'idempotence."""

    op.alter_column(
        "time_series_imports",
        "dataset_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.alter_column(
        "samples_raw",
        "dataset_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.alter_column(
        "measurement_residuals",
        "dataset_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.create_index(
        "ux_ts_imports_industrial_tag_key",
        "time_series_imports",
        ["tag_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("dataset_id IS NULL"),
    )
    op.create_index(
        "ux_samples_raw_import_sequence",
        "samples_raw",
        ["time_series_import_id", "sequence_number"],
        unique=True,
        postgresql_where=sa.text("sequence_number IS NOT NULL"),
    )


def downgrade() -> None:
    """Refuse un retour arrière destructif si des données industrielles existent."""

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM samples_raw WHERE dataset_id IS NULL)
               OR EXISTS (SELECT 1 FROM time_series_imports WHERE dataset_id IS NULL)
               OR EXISTS (SELECT 1 FROM measurement_residuals WHERE dataset_id IS NULL) THEN
                RAISE EXCEPTION
                    'Downgrade bloqué: des séries industrielles sans dataset sont présentes.';
            END IF;
        END
        $$;
        """
    )
    op.drop_index("ux_samples_raw_import_sequence", table_name="samples_raw")
    op.drop_index("ux_ts_imports_industrial_tag_key", table_name="time_series_imports")
    op.alter_column(
        "measurement_residuals",
        "dataset_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.alter_column(
        "samples_raw",
        "dataset_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.alter_column(
        "time_series_imports",
        "dataset_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
