"""Contrats Pydantic des ressources persistantes du MVP."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Page simple et déterministe de ressources."""

    items: list[T]
    total: int
    limit: int
    offset: int


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    default_locale: str = Field(default="fr", min_length=2, max_length=10)
    default_unit_system: str = Field(default="SI", min_length=1, max_length=20)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    default_locale: str | None = Field(default=None, min_length=2, max_length=10)
    default_unit_system: str | None = Field(default=None, min_length=1, max_length=20)


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    default_locale: str
    default_unit_system: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    organization_id: uuid.UUID
    site_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    description: str | None = Field(default=None, max_length=10_000)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)


class ProjectUpdate(BaseModel):
    site_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    status: str | None = Field(default=None, pattern=r"^(draft|active|archived)$")


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    site_id: uuid.UUID | None
    name: str
    code: str
    description: str | None
    country_code: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ModelVersionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    parent_id: uuid.UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ModelVersionUpdate(BaseModel):
    """Métadonnées modifiables tant que la version reste en brouillon."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    payload: dict[str, Any] | None = None


class ModelVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    parent_id: uuid.UUID | None
    version_number: int
    name: str
    status: str
    content_hash: str
    payload: dict[str, Any]
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ScenarioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    parent_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=10_000)
    payload: dict[str, Any] = Field(default_factory=dict)


class ScenarioUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    payload: dict[str, Any] | None = None


class ScenarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_version_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    description: str | None
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    status: str
    approved_at: datetime

    @field_validator("approved_at")
    @classmethod
    def approved_at_required(cls, value: datetime) -> datetime:
        if value is None:
            raise ValueError("La date d'approbation est obligatoire.")
        return value


class AuditEventRead(BaseModel):
    """Événement immuable du journal métier et de sécurité."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    action: str
    object_type: str
    object_id: uuid.UUID
    correlation_id: str | None
    details: dict[str, Any]
    created_at: datetime


class CalculationCreate(BaseModel):
    """Choix explicite du moteur pour une nouvelle exécution."""

    engine: str = Field(
        default="long_distance_liquid",
        min_length=1,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
    )


class CalculationRead(BaseModel):
    """Métadonnées immuables d'une exécution scientifique."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scenario_id: uuid.UUID
    idempotency_key: str | None
    engine: str
    engine_version: str
    status: str
    input_hash: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class CalculationSummaryRead(BaseModel):
    """Synthèse légère sans profil ni détail des tronçons."""

    calculation_id: uuid.UUID
    status: str
    summary: dict[str, Any]


class CalculationResultRead(BaseModel):
    """Résultat scientifique complet et diagnostics associés."""

    calculation_id: uuid.UUID
    status: str
    result: dict[str, Any] | None
    diagnostics: dict[str, Any] | None


class ReportCreate(BaseModel):
    """Paramètres figés de génération d'un rapport."""

    report_type: Literal["hydraulic_calculation"] = "hydraulic_calculation"
    template_version: str = Field(default="rpt-02/1.0", min_length=1, max_length=50)
    format: Literal["pdf"] = "pdf"
    locale: Literal["fr"] = "fr"


class ReportRead(BaseModel):
    """Métadonnées et empreinte d'un rapport archivé."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    calculation_id: uuid.UUID | None
    source_type: str
    source_id: uuid.UUID
    file_id: uuid.UUID
    idempotency_key: str
    report_type: str
    template_version: str
    format: str
    locale: str
    status: str
    content_hash: str
    created_at: datetime
    approved_at: datetime | None
    approval_comment: str | None


class ReportApproval(BaseModel):
    """Décision humaine irréversible portée sur un rapport."""

    decision: Literal["approved", "rejected"]
    comment: str | None = Field(default=None, max_length=10_000)
