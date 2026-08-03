"""Contrats d'identité, de session et d'autorisation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

OrganizationRole = Literal["admin", "engineer", "operator", "approver", "viewer"]


class AuthStatus(BaseModel):
    """État public minimal requis par l'écran d'accès."""

    authentication_required: bool
    initialized: bool


class BootstrapRequest(BaseModel):
    """Création atomique du premier administrateur et de son organisation."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=12, max_length=128)
    organization_name: str = Field(min_length=2, max_length=200)
    organization_slug: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=500)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=500)


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    role: OrganizationRole
    created_at: datetime


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    memberships: list[MembershipRead] = Field(default_factory=list)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserRead


class MemberCreate(BaseModel):
    """Création d'un compte membre directement dans une organisation."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=12, max_length=128)
    role: OrganizationRole


class MemberRoleUpdate(BaseModel):
    role: OrganizationRole


class MemberRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    role: OrganizationRole
    membership_id: uuid.UUID
    created_at: datetime


__all__ = [
    "AuthStatus",
    "BootstrapRequest",
    "LoginRequest",
    "LogoutRequest",
    "MemberCreate",
    "MemberRead",
    "MemberRoleUpdate",
    "MembershipRead",
    "OrganizationRole",
    "RefreshRequest",
    "TokenPair",
    "UserRead",
]
