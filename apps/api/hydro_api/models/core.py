"""Modèle relationnel du noyau projet, version, scénario et calcul."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hydro_api.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from hydro_shared.observability import correlation_id_var


class UserAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Compte humain authentifiable, indépendant des organisations."""

    __tablename__ = "user_accounts"
    __table_args__ = (Index("ix_user_accounts_email", "email", unique=True),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list[OrganizationMembership]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_sessions: Mapped[list[RefreshSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class OrganizationMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Rôle d'un utilisateur dans une organisation."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id"),
        CheckConstraint(
            "role IN ('admin', 'engineer', 'operator', 'approver', 'viewer')",
            name="role_valid",
        ),
        Index("ix_memberships_user_organization", "user_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="memberships")
    user: Mapped[UserAccount] = relationship(back_populates="memberships")


class RefreshSession(UUIDPrimaryKeyMixin, Base):
    """Jeton de renouvellement opaque, haché et révocable."""

    __tablename__ = "refresh_sessions"
    __table_args__ = (
        Index("ix_refresh_sessions_token_hash", "token_hash", unique=True),
        Index("ix_refresh_sessions_user_expires", "user_id", "expires_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserAccount] = relationship(back_populates="refresh_sessions")


class Site(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Site industriel rattaché à une organisation."""

    __tablename__ = "sites"
    __table_args__ = (
        UniqueConstraint("organization_id", "code"),
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="status_valid",
        ),
        Index("ix_sites_organization_status", "organization_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(2))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="sites")
    projects: Mapped[list[Project]] = relationship(back_populates="site")


class TankRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Fiche persistante d'un réservoir et de son barémage approuvé."""

    __tablename__ = "tanks"
    __table_args__ = (
        UniqueConstraint("organization_id", "code"),
        CheckConstraint(
            "status IN ('available', 'unavailable', 'maintenance', 'bypassed')",
            name="status_valid",
        ),
        Index("ix_tanks_organization_site", "organization_id", "site_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    tank_type: Mapped[str] = mapped_column(String(40), nullable=False)
    elevation_m: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    current_level_m: Mapped[float] = mapped_column(Float, nullable=False)
    fluid_id: Mapped[str | None] = mapped_column(String(100))
    compatible_fluid_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="available", nullable=False)
    dead_volume_m3: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    levels_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    strapping_payload: Mapped[list[dict[str, float]]] = mapped_column(JSON, nullable=False)


class TransferRun(UUIDPrimaryKeyMixin, Base):
    """Simulation de transfert immuable, avec bilan matière optionnel."""

    __tablename__ = "transfer_runs"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key"),
        Index("ix_transfer_runs_organization_created", "organization_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_tank_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tanks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    destination_tank_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tanks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    balance_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScenarioComparison(UUIDPrimaryKeyMixin, Base):
    """Comparaison persistée de calculs appartenant à un même projet."""

    __tablename__ = "scenario_comparisons"
    __table_args__ = (
        UniqueConstraint("project_id", "idempotency_key"),
        Index("ix_comparisons_project_created", "project_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    calculation_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OptimizationRun(UUIDPrimaryKeyMixin, Base):
    """Recherche discrète persistée et reproductible d'une configuration de pompes."""

    __tablename__ = "optimization_runs"
    __table_args__ = (
        UniqueConstraint("scenario_id", "idempotency_key"),
        Index("ix_optimizations_scenario_created", "scenario_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tenant logique isolant les données d'une organisation."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    default_locale: Mapped[str] = mapped_column(String(10), default="fr", nullable=False)
    default_unit_system: Mapped[str] = mapped_column(String(20), default="SI", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list[OrganizationMembership]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    sites: Mapped[list[Site]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list[Project]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Projet d'étude appartenant à une organisation."""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("organization_id", "code"),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="status_valid",
        ),
        CheckConstraint(
            "(status = 'archived' AND archived_from_status IN ('draft', 'active')) "
            "OR (status != 'archived' AND archived_from_status IS NULL)",
            name="archive_state_valid",
        ),
        CheckConstraint(
            "project_type IN ('liquid_pipeline', 'terminal', 'gas_pipeline', 'combined')",
            name="project_type_valid",
        ),
        CheckConstraint("unit_system IN ('SI')", name="unit_system_valid"),
        Index("ix_projects_organization_status", "organization_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    project_type: Mapped[str] = mapped_column(
        String(30),
        default="liquid_pipeline",
        nullable=False,
    )
    country_code: Mapped[str | None] = mapped_column(String(2))
    unit_system: Mapped[str] = mapped_column(String(20), default="SI", nullable=False)
    rule_set_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    responsible_user_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    archived_from_status: Mapped[str | None] = mapped_column(String(20))

    organization: Mapped[Organization] = relationship(back_populates="projects")
    site: Mapped[Site | None] = relationship(back_populates="projects")
    model_versions: Mapped[list[ModelVersion]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ModelVersion.version_number",
    )


class ModelVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Snapshot logique d'un modèle de réseau."""

    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("project_id", "version_number"),
        CheckConstraint(
            "status IN ('draft', 'approved', 'archived')",
            name="status_valid",
        ),
        Index("ix_model_versions_project_status", "project_id", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="RESTRICT"),
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="model_versions")
    parent: Mapped[ModelVersion | None] = relationship(remote_side="ModelVersion.id")
    scenarios: Mapped[list[ScenarioRecord]] = relationship(
        back_populates="model_version",
        cascade="all, delete-orphan",
    )


class ScenarioRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Conditions aux limites et surcharges liées à une version de modèle."""

    __tablename__ = "scenarios"
    __table_args__ = (
        UniqueConstraint("model_version_id", "name"),
        Index("ix_scenarios_model_version", "model_version_id"),
    )

    model_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="RESTRICT"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    model_version: Mapped[ModelVersion] = relationship(back_populates="scenarios")
    parent: Mapped[ScenarioRecord | None] = relationship(remote_side="ScenarioRecord.id")
    calculation_runs: Mapped[list[CalculationRun]] = relationship(
        back_populates="scenario",
        cascade="all, delete-orphan",
    )


class StoredFile(UUIDPrimaryKeyMixin, Base):
    """Métadonnées d'un objet privé conservé hors de la base relationnelle."""

    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("bucket", "object_key"),
        Index("ix_files_organization_created", "organization_id", "created_at"),
        Index("ix_files_content_hash", "content_hash"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Dataset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Jeu de données importé avec mapping et aperçu validables."""

    __tablename__ = "datasets"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('profile', 'pump_curve', 'strapping', 'measurements', 'generic')",
            name="kind_valid",
        ),
        CheckConstraint(
            "status IN ('uploaded', 'previewed', 'mapped', 'imported', 'failed')",
            name="status_valid",
        ),
        Index("ix_datasets_organization_created", "organization_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("files.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="uploaded", nullable=False)
    mapping: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    preview: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    file: Mapped[StoredFile] = relationship()
    rows: Mapped[list[DatasetRow]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DatasetRow.source_row",
    )
    imports: Mapped[list[DatasetImport]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DatasetImport.created_at",
    )


class DatasetRow(UUIDPrimaryKeyMixin, Base):
    """Ligne importée conservant les valeurs brutes, normalisées et corrigées."""

    __tablename__ = "dataset_rows"
    __table_args__ = (
        UniqueConstraint("dataset_id", "source_row"),
        Index("ix_dataset_rows_dataset_source", "dataset_id", "source_row"),
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    normalized_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    corrected_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    quality: Mapped[str] = mapped_column(String(20), nullable=False)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    dataset: Mapped[Dataset] = relationship(back_populates="rows")


class DatasetImport(UUIDPrimaryKeyMixin, Base):
    """Exécution idempotente de normalisation d'un jeu de données."""

    __tablename__ = "dataset_imports"
    __table_args__ = (
        UniqueConstraint("dataset_id", "idempotency_key"),
        CheckConstraint(
            "status IN ('completed', 'completed_with_errors', 'failed')",
            name="status_valid",
        ),
        Index("ix_dataset_imports_dataset_created", "dataset_id", "created_at"),
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    dataset: Mapped[Dataset] = relationship(back_populates="imports")


class BackgroundJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tâche persistante prise en charge atomiquement par un processus de calcul."""

    __tablename__ = "background_jobs"
    __table_args__ = (
        UniqueConstraint("kind", "resource_id"),
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="status_valid",
        ),
        Index("ix_background_jobs_status_available", "status", "available_at"),
    )

    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    maximum_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class CalculationRun(UUIDPrimaryKeyMixin, Base):
    """Exécution immuable avec entrée canonique et résultat complet."""

    __tablename__ = "calculation_runs"
    __table_args__ = (
        UniqueConstraint("scenario_id", "idempotency_key"),
        CheckConstraint(
            "status IN ('SIM_QUEUED', 'SIM_RUNNING', 'SIM_CONVERGED', "
            "'SIM_CONVERGED_WARN', 'SIM_INVALID_INPUT', 'SIM_NO_PHYSICAL_SOLUTION', "
            "'SIM_NOT_CONVERGED', 'SIM_CANCELLED')",
            name="status_valid",
        ),
        Index("ix_calculation_runs_scenario_created", "scenario_id", "created_at"),
        Index("ix_calculation_runs_input_hash", "input_hash"),
    )

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(100))
    engine: Mapped[str] = mapped_column(String(100), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    diagnostics: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    scenario: Mapped[ScenarioRecord] = relationship(back_populates="calculation_runs")
    reports: Mapped[list[GeneratedReport]] = relationship(
        back_populates="calculation",
        cascade="all, delete-orphan",
    )


class GeneratedReport(UUIDPrimaryKeyMixin, Base):
    """Rapport figé, haché et lié à une source métier archivée."""

    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", "idempotency_key"),
        CheckConstraint(
            "status IN ('generated', 'approved', 'rejected')",
            name="status_valid",
        ),
        CheckConstraint("format IN ('pdf')", name="format_valid"),
        Index("ix_reports_calculation_created", "calculation_id", "created_at"),
        Index("ix_reports_source_created", "source_type", "source_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    calculation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("calculation_runs.id", ondelete="RESTRICT"),
    )
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("files.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    template_version: Mapped[str] = mapped_column(String(50), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_comment: Mapped[str | None] = mapped_column(Text)

    calculation: Mapped[CalculationRun | None] = relationship(back_populates="reports")
    file: Mapped[StoredFile] = relationship()


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    """Événement append-only retraçant une mutation applicative."""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_organization_created", "organization_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    object_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(
        String(100),
        default=lambda: correlation_id_var.get(),
    )
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
