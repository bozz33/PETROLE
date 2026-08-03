"""Contrats du référentiel normatif, des règles et de leurs évaluations."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class StandardCreate(BaseModel):
    """Référence d'une édition officielle sans son texte protégé."""

    organization_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    title: str = Field(min_length=1, max_length=300)
    issuing_body: str = Field(min_length=1, max_length=120)
    edition: str = Field(min_length=1, max_length=80)
    publication_date: date | None = None
    effective_date: date | None = None
    licensed_copy_ref: str | None = Field(default=None, max_length=500)
    source_url: HttpUrl | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()


class StandardUpdate(BaseModel):
    """Champs modifiables avant activation ou statut d'archivage."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    publication_date: date | None = None
    effective_date: date | None = None
    licensed_copy_ref: str | None = Field(default=None, max_length=500)
    source_url: HttpUrl | None = None
    status: Literal["draft", "withdrawn", "archived"] | None = None


class StandardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    parent_id: uuid.UUID | None
    code: str
    title: str
    issuing_body: str
    edition: str
    publication_date: date | None
    effective_date: date | None
    status: str
    licensed_copy_ref: str | None
    source_url: str | None
    content_hash: str
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RuleSetCreate(BaseModel):
    """Première version d'un jeu de règles lié à des éditions actives."""

    organization_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    title: str = Field(min_length=1, max_length=300)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    domain: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=10_000)
    standard_ids: list[uuid.UUID] = Field(min_length=1)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()

    @field_validator("country_code")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @field_validator("standard_ids")
    @classmethod
    def unique_standards(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Une édition normative ne peut être référencée qu'une fois.")
        return value


class RuleSetRead(BaseModel):
    """Version complète d'un jeu de règles et ses sources."""

    id: uuid.UUID
    organization_id: uuid.UUID
    parent_id: uuid.UUID | None
    code: str
    title: str
    country_code: str | None
    domain: str
    version_number: int
    description: str | None
    status: str
    standard_ids: list[uuid.UUID]
    content_hash: str
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RuleCreate(BaseModel):
    """Contrôle numérique limité à une comparaison sûre et explicable."""

    standard_id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    title: str = Field(min_length=1, max_length=300)
    severity: Literal["information", "warning", "error", "blocking"]
    domain: str = Field(min_length=1, max_length=80)
    metric_path: str = Field(min_length=1, max_length=300, pattern=r"^[A-Za-z0-9_.-]+$")
    operator: Literal["le", "lt", "ge", "gt", "eq", "between"]
    limit_value: float | None = None
    upper_limit_value: float | None = None
    unit: str | None = Field(default=None, max_length=40)
    applicability: dict[str, Any] = Field(default_factory=lambda: {"type": "always"})
    parameters: dict[str, Any] = Field(default_factory=dict)
    message: str = Field(min_length=1, max_length=2_000)
    source_clause_ref: str | None = Field(default=None, max_length=300)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_limits(self) -> RuleCreate:
        if self.limit_value is None:
            raise ValueError("La valeur limite est obligatoire.")
        if self.operator == "between":
            if self.upper_limit_value is None:
                raise ValueError("La borne supérieure est obligatoire pour l'opérateur between.")
            if self.upper_limit_value < self.limit_value:
                raise ValueError("La borne supérieure doit être supérieure à la borne inférieure.")
        elif self.upper_limit_value is not None:
            raise ValueError("La borne supérieure est réservée à l'opérateur between.")
        if self.applicability != {"type": "always"}:
            raise ValueError("Le MVP accepte uniquement l'applicabilité explicite always.")
        return self


class RuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_set_id: uuid.UUID
    standard_id: uuid.UUID | None
    code: str
    title: str
    severity: str
    domain: str
    metric_path: str
    operator: str
    limit_value: float | None
    upper_limit_value: float | None
    unit: str | None
    applicability: dict[str, Any]
    parameters: dict[str, Any]
    message: str
    source_clause_ref: str | None
    status: str
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RuleEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    calculation_id: uuid.UUID
    rule_set_id: uuid.UUID
    rule_id: uuid.UUID
    object_type: str
    object_id: uuid.UUID
    status: str
    measured_value: float | None
    limit_value: float | None
    margin: float | None
    unit: str | None
    message: str
    details: dict[str, Any]
    created_at: datetime
