"""Contrats API des tags et séries temporelles du Pilote/V1."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hydro_shared.units import Dimension

MeasurementType = Literal[
    "pressure",
    "flow",
    "level",
    "temperature",
    "status",
    "vibration",
    "energy",
]


class MeasurementTagCreate(BaseModel):
    """Métadonnées immuables d'une grandeur acquise sur un site."""

    organization_id: uuid.UUID
    site_id: uuid.UUID
    asset_instance_id: uuid.UUID | None = None
    external_name: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=200)
    measurement_type: MeasurementType
    dimension: Dimension
    source_unit: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=160)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("external_name", "name", "source_unit", "source")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Cette valeur ne peut pas être vide.")
        return normalized


class MeasurementTagRead(BaseModel):
    """Vue publique d'un tag stable et de son unité interne."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    site_id: uuid.UUID
    asset_instance_id: uuid.UUID | None
    external_name: str
    name: str
    measurement_type: str
    dimension: str
    source_unit: str
    si_unit: str
    source: str
    status: str
    metadata: dict[str, Any] = Field(validation_alias="metadata_payload")
    created_at: datetime
    updated_at: datetime


class TimeSeriesDatasetImportCreate(BaseModel):
    """Association explicite d'un dataset de mesures à un tag de site."""

    tag_id: uuid.UUID
    processing_version: str = Field(default="pilot-v1-a2", min_length=1, max_length=80)

    @field_validator("processing_version")
    @classmethod
    def normalize_processing_version(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La version de traitement ne peut pas être vide.")
        return normalized


class TimeSeriesImportRead(BaseModel):
    """Résultat idempotent d'une ingestion temporelle."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    dataset_id: uuid.UUID
    tag_id: uuid.UUID
    idempotency_key: str
    processing_version: str
    status: str
    source_hash: str
    row_count: int
    accepted_count: int
    rejected_count: int
    raw_created_count: int
    raw_reused_count: int
    errors: list[dict[str, Any]]
    created_at: datetime
    finished_at: datetime | None


class NormalizedSampleRead(BaseModel):
    """Projection SI d'un échantillon brut, avec son lignage minimal."""

    id: uuid.UUID
    raw_sample_id: uuid.UUID
    time_series_import_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_row_id: uuid.UUID | None
    source_timestamp: datetime
    ingest_timestamp: datetime
    source_value: Any
    source_unit: str
    timestamp: datetime
    value_si: float
    si_unit: str
    quality: str
    sequence_number: int | None
    processing_version: str


__all__ = [
    "MeasurementTagCreate",
    "MeasurementTagRead",
    "NormalizedSampleRead",
    "TimeSeriesDatasetImportCreate",
    "TimeSeriesImportRead",
]
