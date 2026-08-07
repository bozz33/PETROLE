"""Contrats publics du catalogue technique versionné."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hydro_api.schemas.scientific import FluidInput, PumpModelInput

#: Contenu technique d'un élément de catalogue. La nature exacte dépend du
#: ``kind`` fourni dans le chemin de la requête : ``fluid`` → FluidInput,
#: ``pump`` → PumpModelInput.
#:
#: Les familles vanne, matériau et accessoire transitent volontairement par la
#: branche ``dict`` : leurs modèles n'ont que des champs facultatifs, si bien
#: qu'une union les rendrait interchangeables et ferait perdre silencieusement
#: les champs propres à l'une lorsque Pydantic choisirait l'autre. Leur
#: validation typée est appliquée par le service, qui connaît le ``kind``
#: (``ValveInput``, ``MaterialInput``, ``AccessoryInput``).
CatalogPayload = FluidInput | PumpModelInput | dict[str, Any]


class CatalogItemCreate(BaseModel):
    """Première version d'un produit, équipement ou matériau."""

    organization_id: uuid.UUID
    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=200)
    payload: CatalogPayload
    source: str | None = Field(default=None, max_length=10_000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        """Normalise le code métier sans en modifier les séparateurs."""

        return value.upper()


class CatalogItemUpdate(BaseModel):
    """Modification autorisée tant que la version reste en brouillon."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    payload: CatalogPayload | None = None
    source: str | None = Field(default=None, max_length=10_000)
    status: str | None = Field(default=None, pattern=r"^(draft|archived)$")


class CatalogItemVersionCreate(BaseModel):
    """Nouvelle version dérivée, avec surcharge facultative du contenu."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    payload: CatalogPayload | None = None
    source: str | None = Field(default=None, max_length=10_000)


class CatalogItemRead(BaseModel):
    """Version complète exposée à l'API et aux assembleurs de modèles."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    parent_id: uuid.UUID | None
    kind: str
    code: str
    name: str
    version_number: int
    status: str
    payload: dict[str, Any]
    source: str | None
    content_hash: str
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


__all__ = [
    "CatalogItemCreate",
    "CatalogItemRead",
    "CatalogItemUpdate",
    "CatalogItemVersionCreate",
]
