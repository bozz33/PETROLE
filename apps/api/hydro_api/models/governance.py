"""Modèles relationnels du référentiel normatif et de ses évaluations."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from hydro_api.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StandardReference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Référence bibliographique d'une édition acquise légalement."""

    __tablename__ = "standards"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", "edition", name="uq_standard_edition"),
        CheckConstraint(
            "status IN ('draft', 'active', 'withdrawn', 'archived')",
            name="status_valid",
        ),
        Index("ix_standards_organization_status", "organization_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("standards.id", ondelete="RESTRICT"),
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    issuing_body: Mapped[str] = mapped_column(String(120), nullable=False)
    edition: Mapped[str] = mapped_column(String(80), nullable=False)
    publication_date: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    licensed_copy_ref: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(1_000))
    content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RuleSet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Version immuable d'un ensemble de contrôles synthétiques."""

    __tablename__ = "rule_sets"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "code",
            "version_number",
            name="uq_rule_set_version",
        ),
        CheckConstraint("version_number > 0", name="version_positive"),
        CheckConstraint(
            "status IN ('draft', 'approved', 'archived')",
            name="status_valid",
        ),
        Index("ix_rule_sets_organization_domain", "organization_id", "domain", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rule_sets.id", ondelete="RESTRICT"),
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(2))
    domain: Mapped[str] = mapped_column(String(80), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RuleSetStandard(UUIDPrimaryKeyMixin, Base):
    """Association explicite entre un jeu de règles et ses éditions sources."""

    __tablename__ = "rule_set_standards"
    __table_args__ = (
        UniqueConstraint("rule_set_id", "standard_id", name="uq_rule_set_standard"),
    )

    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rule_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    standard_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("standards.id", ondelete="RESTRICT"),
        nullable=False,
    )


class RuleDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Contrôle seuil paramétré sans exécution de code arbitraire."""

    __tablename__ = "rules"
    __table_args__ = (
        UniqueConstraint("rule_set_id", "code", name="uq_rule_code"),
        CheckConstraint(
            "severity IN ('information', 'warning', 'error', 'blocking')",
            name="severity_valid",
        ),
        CheckConstraint(
            "operator IN ('le', 'lt', 'ge', 'gt', 'eq', 'between')",
            name="operator_valid",
        ),
        CheckConstraint(
            "status IN ('draft', 'approved', 'rejected')",
            name="status_valid",
        ),
        Index("ix_rules_rule_set_status", "rule_set_id", "status"),
    )

    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rule_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    standard_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("standards.id", ondelete="RESTRICT"),
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    domain: Mapped[str] = mapped_column(String(80), nullable=False)
    metric_path: Mapped[str] = mapped_column(String(300), nullable=False)
    operator: Mapped[str] = mapped_column(String(20), nullable=False)
    limit_value: Mapped[float | None] = mapped_column(Float)
    upper_limit_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(40))
    applicability: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_clause_ref: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RuleEvaluation(UUIDPrimaryKeyMixin, Base):
    """Résultat figé d'une règle sur une exécution scientifique."""

    __tablename__ = "rule_evaluations"
    __table_args__ = (
        UniqueConstraint("calculation_id", "rule_id", name="uq_rule_evaluation"),
        CheckConstraint(
            "status IN ('compliant', 'non_compliant', 'not_applicable', 'error')",
            name="status_valid",
        ),
        Index("ix_rule_evaluations_organization_created", "organization_id", "created_at"),
        Index("ix_rule_evaluations_calculation", "calculation_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    calculation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("calculation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rule_sets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("rules.id", ondelete="RESTRICT"),
        nullable=False,
    )
    object_type: Mapped[str] = mapped_column(String(100), default="calculation", nullable=False)
    object_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    measured_value: Mapped[float | None] = mapped_column(Float)
    limit_value: Mapped[float | None] = mapped_column(Float)
    margin: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
