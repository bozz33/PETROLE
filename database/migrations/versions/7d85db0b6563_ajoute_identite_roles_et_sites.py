"""ajoute identite roles et sites

Identifiant : 7d85db0b6563
Parent : 540e26fff170
Créée le : 2026-08-03 01:57:07.713912
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7d85db0b6563"
down_revision: str | Sequence[str] | None = "540e26fff170"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Applique la migration."""

    # Identité des utilisateurs et rattachement aux organisations.
    op.create_table(
        "user_accounts",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_accounts")),
    )
    op.create_index("ix_user_accounts_email", "user_accounts", ["email"], unique=True)
    op.create_table(
        "organization_memberships",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('admin', 'engineer', 'operator', 'approver', 'viewer')",
            name=op.f("ck_organization_memberships_role_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_organization_memberships_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_accounts.id"],
            name=op.f("fk_organization_memberships_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_memberships")),
        sa.UniqueConstraint(
            "organization_id", "user_id", name=op.f("uq_organization_memberships_organization_id")
        ),
    )
    op.create_index(
        "ix_memberships_user_organization",
        "organization_memberships",
        ["user_id", "organization_id"],
        unique=False,
    )
    op.create_table(
        "refresh_sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=71), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_accounts.id"],
            name=op.f("fk_refresh_sessions_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_sessions")),
    )
    op.create_index(
        "ix_refresh_sessions_token_hash", "refresh_sessions", ["token_hash"], unique=True
    )
    op.create_index(
        "ix_refresh_sessions_user_expires",
        "refresh_sessions",
        ["user_id", "expires_at"],
        unique=False,
    )
    op.create_table(
        "sites",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'archived')", name=op.f("ck_sites_status_valid")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_sites_organization_id_organizations"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sites")),
        sa.UniqueConstraint("organization_id", "code", name=op.f("uq_sites_organization_id")),
    )
    op.create_index(
        "ix_sites_organization_status", "sites", ["organization_id", "status"], unique=False
    )
    op.alter_column("audit_events", "organization_id", existing_type=sa.UUID(), nullable=True)
    op.add_column("projects", sa.Column("site_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_projects_site_id_sites"),
        "projects",
        "sites",
        ["site_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Annule la migration."""

    # Identité des utilisateurs et rattachement aux organisations.
    op.drop_constraint(op.f("fk_projects_site_id_sites"), "projects", type_="foreignkey")
    op.drop_column("projects", "site_id")
    op.alter_column("audit_events", "organization_id", existing_type=sa.UUID(), nullable=False)
    op.drop_index("ix_sites_organization_status", table_name="sites")
    op.drop_table("sites")
    op.drop_index("ix_refresh_sessions_user_expires", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_token_hash", table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
    op.drop_index("ix_memberships_user_organization", table_name="organization_memberships")
    op.drop_table("organization_memberships")
    op.drop_index("ix_user_accounts_email", table_name="user_accounts")
    op.drop_table("user_accounts")
