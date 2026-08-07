"""Contrats HTTP des fichiers et jeux de données importés."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DatasetKind = Literal["profile", "pump_curve", "strapping", "measurements", "generic"]


class StoredFileRead(BaseModel):
    """Métadonnées publiques d'un fichier privé."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    filename: str
    media_type: str
    size_bytes: int
    content_hash: str
    purpose: str
    project_id: uuid.UUID | None
    description: str | None
    created_at: datetime


class DatasetCreate(BaseModel):
    """Création d'un jeu de données lié à un fichier déjà téléversé."""

    organization_id: uuid.UUID
    project_id: uuid.UUID | None = None
    file_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    kind: DatasetKind


class DatasetMapping(BaseModel):
    """Correspondance entre champs canoniques et colonnes du fichier."""

    fields: dict[str, str] = Field(default_factory=dict)
    constants: dict[str, str | float | int | None] = Field(default_factory=dict)


class DatasetRead(BaseModel):
    """État et traçabilité d'un jeu de données."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID | None
    file_id: uuid.UUID
    name: str
    kind: DatasetKind
    status: str
    mapping: dict[str, Any]
    preview: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DatasetPreview(BaseModel):
    """Aperçu borné avant confirmation de l'import."""

    dataset_id: uuid.UUID
    columns: list[str]
    detected_types: dict[str, str]
    rows: list[dict[str, Any]]
    row_count: int
    errors: list[dict[str, Any]]


class DatasetImportRead(BaseModel):
    """Bilan d'une exécution d'import."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    idempotency_key: str
    row_count: int
    accepted_count: int
    rejected_count: int
    content_hash: str
    errors: list[dict[str, Any]]
    created_at: datetime
    finished_at: datetime | None


class DatasetRowsRead(BaseModel):
    """Page de lignes normalisées avec lignage brut."""

    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


__all__ = [
    "DatasetCreate",
    "DatasetImportRead",
    "DatasetKind",
    "DatasetMapping",
    "DatasetPreview",
    "DatasetRead",
    "DatasetRowsRead",
    "StoredFileRead",
]
