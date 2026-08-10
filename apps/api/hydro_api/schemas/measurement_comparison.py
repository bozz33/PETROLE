"""Contrats API de V1-B : mesures qualifiées comparées à un régime stationnaire."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hydro_api.schemas.time_series import SampleQuality

ComparisonTargetType = Literal["node", "edge", "pump"]
ComparisonMetric = Literal[
    "pressure_pa",
    "flow_m3_s",
    "pressure_min_pa",
    "pressure_max_pa",
    "suction_pressure_pa",
    "discharge_pressure_pa",
]
MappingStatus = Literal["draft", "approved", "archived"]

DEFAULT_COMPARISON_QUALITIES: tuple[SampleQuality, ...] = (
    "good",
    "uncertain",
    "substituted",
    "estimated",
)


class MeasurementModelMappingCreate(BaseModel):
    """Association explicite, d'abord en brouillon, d'un tag à une sortie calculée."""

    organization_id: uuid.UUID
    project_id: uuid.UUID
    tag_id: uuid.UUID
    target_type: ComparisonTargetType
    target_id: uuid.UUID
    metric: ComparisonMetric
    source_ref: str | None = Field(default=None, max_length=1_000)

    @field_validator("source_ref")
    @classmethod
    def normalize_source_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class MeasurementModelMappingRead(BaseModel):
    """Correspondance versionnée ; une fois approuvée, elle devient immuable."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    model_version_id: uuid.UUID
    tag_id: uuid.UUID
    version_number: int
    target_type: str
    target_id: uuid.UUID
    metric: str
    dimension: str
    si_unit: str
    status: str
    source_ref: str | None
    created_by: uuid.UUID | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MeasurementModelMappingApproval(BaseModel):
    """Approbation humaine d'une correspondance métier explicite."""

    comment: str | None = Field(default=None, max_length=1_000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class MeasurementComparisonCreate(BaseModel):
    """Demande déterministe de comparaison sur une fenêtre stationnaire explicite."""

    organization_id: uuid.UUID
    mapping_id: uuid.UUID
    calculation_id: uuid.UUID
    processing_version: str = Field(min_length=1, max_length=80)
    start_timestamp: datetime
    end_timestamp: datetime
    included_qualities: list[SampleQuality] = Field(
        default_factory=lambda: list(DEFAULT_COMPARISON_QUALITIES),
        min_length=1,
    )

    @field_validator("processing_version")
    @classmethod
    def normalize_processing_version(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La version de traitement ne peut pas être vide.")
        return normalized

    @field_validator("included_qualities")
    @classmethod
    def normalize_qualities(cls, values: list[SampleQuality]) -> list[SampleQuality]:
        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def validate_window(self) -> MeasurementComparisonCreate:
        if self.start_timestamp.tzinfo is None or self.end_timestamp.tzinfo is None:
            raise ValueError("Les bornes temporelles doivent inclure un fuseau horaire.")
        if self.start_timestamp > self.end_timestamp:
            raise ValueError("La borne de début doit précéder la borne de fin.")
        return self


class ComparisonKpisRead(BaseModel):
    """Indicateurs calculés sur les seuls points retenus par la politique qualité."""

    n_compared: int = Field(ge=0)
    bias_si: float | None
    mae_si: float | None
    rmse_si: float | None
    min_residual_si: float | None
    max_residual_si: float | None


class ComparisonExclusionsRead(BaseModel):
    """Bilan explicite des points non retenus ; aucun point n'est effacé."""

    n_candidates: int = Field(ge=0)
    n_excluded_quality: int = Field(ge=0)
    n_excluded_outlier: int = Field(ge=0)
    quality_counts: dict[str, int]
    exclusion_counts: dict[str, int]
    duplicate_timestamp_count: int = Field(ge=0)


class MeasurementComparisonRead(BaseModel):
    """Trace immuable d'une comparaison V1-B1 terminée."""

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    model_version_id: uuid.UUID
    mapping_id: uuid.UUID
    calculation_id: uuid.UUID
    tag_id: uuid.UUID
    processing_version: str
    start_timestamp: datetime
    end_timestamp: datetime
    included_qualities: list[SampleQuality]
    input_hash: str
    calculation_input_hash: str
    engine: str
    engine_version: str
    simulated_value_si: float
    si_unit: str
    status: str
    kpis: ComparisonKpisRead
    exclusions: ComparisonExclusionsRead
    mapping: MeasurementModelMappingRead
    created_by: uuid.UUID | None
    created_at: datetime


class MeasurementResidualRead(BaseModel):
    """Point de résidu consultable avec lignage jusqu'au brut et au dataset."""

    id: uuid.UUID
    comparison_id: uuid.UUID
    normalized_sample_id: uuid.UUID
    raw_sample_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_row_id: uuid.UUID | None
    timestamp: datetime
    measured_value_si: float
    simulated_value_si: float
    residual_si: float
    quality: str
    included_in_kpi: bool
    exclusion_reason: str | None
    source_timestamp: datetime
    ingest_timestamp: datetime
    source_value: object
    source_unit: str
    processing_version: str


__all__ = [
    "DEFAULT_COMPARISON_QUALITIES",
    "ComparisonExclusionsRead",
    "ComparisonKpisRead",
    "ComparisonMetric",
    "ComparisonTargetType",
    "MappingStatus",
    "MeasurementComparisonCreate",
    "MeasurementComparisonRead",
    "MeasurementModelMappingApproval",
    "MeasurementModelMappingCreate",
    "MeasurementModelMappingRead",
    "MeasurementResidualRead",
]
