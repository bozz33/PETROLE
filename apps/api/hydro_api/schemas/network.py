"""Contrats d'édition et de validation du réseau versionné."""

from __future__ import annotations

import uuid
from datetime import datetime
from itertools import pairwise
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hydro_api.schemas.scientific import (
    EdgeGeometryInput,
    InjectionNodePayloadInput,
    OfftakeNodePayloadInput,
    PumpAssetInput,
    StationConfigurationInput,
    TerminalNodePayloadInput,
    ValveAssetInput,
    payload_to_dict,
)

#: Type union du payload d'un nœud. La dernière branche ``dict`` accepte un
#: dictionnaire libre (y compris vide) pour les kinds sans configuration typée
#: (``source``, ``junction``) et préserve la rétro-compatibilité des données
#: déjà persistées. La valeur par défaut est définie au niveau du champ.
NodePayload = (
    StationConfigurationInput
    | InjectionNodePayloadInput
    | OfftakeNodePayloadInput
    | TerminalNodePayloadInput
    | dict[str, Any]
)

#: Compléments géométriques optionnels d'un tronçon, ou dictionnaire libre.
EdgePayload = EdgeGeometryInput | dict[str, Any]

#: Configuration d'un équipement posé sur le réseau, ou dictionnaire libre.
AssetPayload = PumpAssetInput | ValveAssetInput | dict[str, Any]


class ProfilePointInput(BaseModel):
    """Point altimétrique local à un tronçon."""

    chainage_m: float = Field(ge=0)
    elevation_m: float
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class ModelCloneCreate(BaseModel):
    """Nom de la nouvelle version issue d'un modèle existant."""

    name: str = Field(min_length=1, max_length=200)


class NetworkNodeCreate(BaseModel):
    """Nœud topologique d'une version de modèle."""

    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["source", "tank", "station", "junction", "terminal", "injection", "offtake"]
    elevation_m: float = 0.0
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    status: Literal["available", "maintenance", "unavailable"] = "available"
    payload: NodePayload = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def normalize_payload(self) -> NetworkNodeCreate:
        """Aplatit le payload typé en dictionnaire avant persistance."""

        self.payload = payload_to_dict(self.payload)
        return self


class NetworkNodeUpdate(BaseModel):
    """Champs modifiables d'un nœud appartenant à un brouillon."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    kind: (
        Literal["source", "tank", "station", "junction", "terminal", "injection", "offtake"] | None
    ) = None
    elevation_m: float | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    status: Literal["available", "maintenance", "unavailable"] | None = None
    payload: NodePayload | None = None

    @model_validator(mode="after")
    def normalize_payload(self) -> NetworkNodeUpdate:
        if self.payload is not None:
            self.payload = payload_to_dict(self.payload)
        return self


class NetworkNodeRead(BaseModel):
    """Nœud persisté avec identité et dates techniques."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_version_id: uuid.UUID
    code: str
    name: str
    kind: str
    elevation_m: float
    latitude: float | None
    longitude: float | None
    status: str
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class NetworkEdgeCreate(BaseModel):
    """Tronçon hydraulique orienté et son profil altimétrique local."""

    from_node_id: uuid.UUID
    to_node_id: uuid.UUID
    material_catalog_item_id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=200)
    sequence: int = Field(ge=1)
    length_m: float = Field(gt=0)
    inner_diameter_m: float = Field(gt=0)
    roughness_m: float = Field(ge=0)
    mawp_pa: float = Field(gt=0)
    status: Literal["available", "maintenance", "unavailable"] = "available"
    profile: list[ProfilePointInput] = Field(min_length=2)
    fittings: list[dict[str, Any]] = Field(default_factory=list)
    payload: EdgePayload = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_profile(self) -> Self:
        """Exige un profil croissant couvrant exactement le tronçon."""

        chainages = [point.chainage_m for point in self.profile]
        if any(right <= left for left, right in pairwise(chainages)):
            raise ValueError("Les chainages du profil doivent être strictement croissants.")
        tolerance = max(1.0e-6, self.length_m * 1.0e-9)
        if abs(chainages[0]) > tolerance:
            raise ValueError("Le profil du tronçon doit commencer au chainage 0 m.")
        if abs(chainages[-1] - self.length_m) > tolerance:
            raise ValueError(
                "Le dernier point du profil doit coïncider avec la longueur du tronçon."
            )
        if self.from_node_id == self.to_node_id:
            raise ValueError("Un tronçon doit relier deux nœuds différents.")
        self.payload = payload_to_dict(self.payload)
        return self


class NetworkEdgeUpdate(BaseModel):
    """Champs modifiables d'un tronçon appartenant à un brouillon."""

    from_node_id: uuid.UUID | None = None
    to_node_id: uuid.UUID | None = None
    material_catalog_item_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    sequence: int | None = Field(default=None, ge=1)
    length_m: float | None = Field(default=None, gt=0)
    inner_diameter_m: float | None = Field(default=None, gt=0)
    roughness_m: float | None = Field(default=None, ge=0)
    mawp_pa: float | None = Field(default=None, gt=0)
    status: Literal["available", "maintenance", "unavailable"] | None = None
    profile: list[ProfilePointInput] | None = Field(default=None, min_length=2)
    fittings: list[dict[str, Any]] | None = None
    payload: EdgePayload | None = None

    @model_validator(mode="after")
    def normalize_payload(self) -> NetworkEdgeUpdate:
        if self.payload is not None:
            self.payload = payload_to_dict(self.payload)
        return self


class NetworkEdgeRead(BaseModel):
    """Tronçon persisté avec géométrie, limites et accessoires."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_version_id: uuid.UUID
    from_node_id: uuid.UUID
    to_node_id: uuid.UUID
    material_catalog_item_id: uuid.UUID | None
    code: str
    name: str
    sequence: int
    length_m: float
    inner_diameter_m: float
    roughness_m: float
    mawp_pa: float
    status: str
    profile_payload: list[dict[str, float | None]]
    fittings_payload: list[dict[str, Any]]
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AssetInstanceCreate(BaseModel):
    """Équipement de catalogue placé à un emplacement unique."""

    catalog_item_id: uuid.UUID
    node_id: uuid.UUID | None = None
    edge_id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=200)
    role: Literal["main", "standby", "auxiliary", "isolation", "control", "measurement"]
    status: Literal["available", "maintenance", "unavailable", "bypassed"] = "available"
    payload: AssetPayload = Field(default_factory=dict)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_location(self) -> AssetInstanceCreate:
        if (self.node_id is None) == (self.edge_id is None):
            raise ValueError("L'équipement doit être placé sur un seul nœud ou un seul tronçon.")
        self.payload = payload_to_dict(self.payload)
        return self


class AssetInstanceUpdate(BaseModel):
    """État et paramètres modifiables d'une instance placée."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    role: Literal["main", "standby", "auxiliary", "isolation", "control", "measurement"] | None = (
        None
    )
    status: Literal["available", "maintenance", "unavailable", "bypassed"] | None = None
    payload: AssetPayload | None = None

    @model_validator(mode="after")
    def normalize_payload(self) -> AssetInstanceUpdate:
        if self.payload is not None:
            self.payload = payload_to_dict(self.payload)
        return self


class AssetInstanceRead(BaseModel):
    """Instance persistée et référence exacte de catalogue."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_version_id: uuid.UUID
    catalog_item_id: uuid.UUID
    node_id: uuid.UUID | None
    edge_id: uuid.UUID | None
    code: str
    name: str
    role: str
    status: str
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class NetworkValidationIssue(BaseModel):
    """Erreur ou avertissement localisé sur une ressource du réseau."""

    code: str
    message: str
    object_type: str
    object_id: uuid.UUID | None = None


class NetworkValidationReport(BaseModel):
    """Résultat déterministe du contrôle topologique avant approbation."""

    model_version_id: uuid.UUID
    valid: bool
    errors: list[NetworkValidationIssue]
    warnings: list[NetworkValidationIssue]
    node_count: int
    edge_count: int
    asset_count: int


__all__ = [
    "AssetInstanceCreate",
    "AssetInstanceRead",
    "AssetInstanceUpdate",
    "NetworkEdgeCreate",
    "NetworkEdgeRead",
    "NetworkEdgeUpdate",
    "NetworkNodeCreate",
    "NetworkNodeRead",
    "NetworkNodeUpdate",
    "NetworkValidationIssue",
    "NetworkValidationReport",
    "ProfilePointInput",
]
