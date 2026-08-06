"""Contrats Pydantic des ressources persistantes du MVP."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hydro_api.schemas.scientific import ScenarioPayloadInput, payload_to_dict

T = TypeVar("T")

#: Contenu scientifique d'un scénario (conditions aux limites, surcharges,
#: options du solveur). La branche ``dict`` préserve la rétro-compatibilité des
#: scénarios déjà persistés ou partiellement renseignés. La valeur par défaut
#: est définie au niveau du champ (``Field(default_factory=dict)``).
ScenarioPayload = ScenarioPayloadInput | dict[str, Any]


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
    project_type: Literal[
        "liquid_pipeline",
        "terminal",
        "gas_pipeline",
        "combined",
    ] = "liquid_pipeline"
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    unit_system: Literal["SI"] = "SI"
    rule_set_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    responsible_user_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)

    @field_validator("rule_set_ids", "responsible_user_ids")
    @classmethod
    def unique_identifiers(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        return list(dict.fromkeys(value))


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    project_type: (
        Literal[
            "liquid_pipeline",
            "terminal",
            "gas_pipeline",
            "combined",
        ]
        | None
    ) = None
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    unit_system: Literal["SI"] | None = None
    rule_set_ids: list[uuid.UUID] | None = Field(default=None, max_length=100)
    responsible_user_ids: list[uuid.UUID] | None = Field(default=None, max_length=100)

    @field_validator("rule_set_ids", "responsible_user_ids")
    @classmethod
    def unique_optional_identifiers(
        cls,
        value: list[uuid.UUID] | None,
    ) -> list[uuid.UUID] | None:
        return None if value is None else list(dict.fromkeys(value))


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    site_id: uuid.UUID | None
    name: str
    code: str
    description: str | None
    project_type: str
    country_code: str | None
    unit_system: str
    rule_set_ids: list[uuid.UUID]
    responsible_user_ids: list[uuid.UUID]
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
    payload: ScenarioPayload = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_payload(self) -> ScenarioCreate:
        """Aplatit le payload typé en dictionnaire avant persistance."""

        self.payload = payload_to_dict(self.payload)
        return self


class ScenarioCloneCreate(BaseModel):
    """Nom de la variante dérivée d'un scénario existant."""

    name: str = Field(min_length=1, max_length=200)


class ScenarioUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    payload: ScenarioPayload | None = None

    @model_validator(mode="after")
    def normalize_payload(self) -> ScenarioUpdate:
        if self.payload is not None:
            self.payload = payload_to_dict(self.payload)
        return self


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
    job_id: uuid.UUID | None = None
    scenario_id: uuid.UUID
    idempotency_key: str | None
    engine: str
    engine_version: str
    status: str
    phase: str
    progress_percent: int = Field(ge=0, le=100)
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
