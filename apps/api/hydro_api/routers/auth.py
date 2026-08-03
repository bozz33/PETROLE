"""Routes d'authentification et d'administration des membres."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from hydro_api.database.session import get_session
from hydro_api.schemas.auth import (
    AuthStatus,
    BootstrapRequest,
    LoginRequest,
    LogoutRequest,
    MemberCreate,
    MemberRead,
    MemberRoleUpdate,
    RefreshRequest,
    TokenPair,
    UserRead,
)
from hydro_api.security import ApplicationAccess, AuthenticatedAccess
from hydro_api.services import auth

router = APIRouter(tags=["Identité"])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get(
    "/auth/status",
    response_model=AuthStatus,
    summary="Lire l'état d'initialisation de l'accès",
)
def authentication_status(request: Request, session: DatabaseSession):
    settings = request.app.state.settings
    return AuthStatus(
        authentication_required=settings.authentication_required,
        initialized=auth.is_initialized(session),
    )


@router.post(
    "/auth/bootstrap",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    summary="Initialiser le premier administrateur",
)
def bootstrap(
    data: BootstrapRequest,
    request: Request,
    session: DatabaseSession,
):
    return auth.bootstrap(session, data, request.app.state.settings)


@router.post(
    "/auth/login",
    response_model=TokenPair,
    summary="Ouvrir une session",
)
def login(
    data: LoginRequest,
    request: Request,
    session: DatabaseSession,
):
    return auth.login(session, data, request.app.state.settings)


@router.post(
    "/auth/refresh",
    response_model=TokenPair,
    summary="Renouveler et faire tourner la session",
)
def refresh_session(
    data: RefreshRequest,
    request: Request,
    session: DatabaseSession,
):
    return auth.refresh(session, data.refresh_token, request.app.state.settings)


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Révoquer une session",
)
def logout(data: LogoutRequest, session: DatabaseSession) -> Response:
    auth.logout(session, data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/auth/me",
    response_model=UserRead,
    summary="Lire le compte et ses rôles",
)
def me(access: AuthenticatedAccess):
    if access.user is None:  # pragma: no cover - garanti par la dépendance
        raise RuntimeError("Contexte authentifié sans utilisateur.")
    return access.user


@router.get(
    "/organizations/{organization_id}/members",
    response_model=list[MemberRead],
    summary="Lister les membres de l'organisation",
)
def list_organization_members(
    organization_id: uuid.UUID,
    session: DatabaseSession,
    access: ApplicationAccess,
):
    del access
    return auth.list_members(session, organization_id)


@router.post(
    "/organizations/{organization_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un membre dans l'organisation",
)
def create_organization_member(
    organization_id: uuid.UUID,
    data: MemberCreate,
    session: DatabaseSession,
    access: ApplicationAccess,
):
    del access
    user = auth.create_member(session, organization_id, data)
    membership = user.memberships[0]
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "role": membership.role,
        "membership_id": membership.id,
        "created_at": user.created_at,
    }


@router.patch(
    "/organizations/{organization_id}/members/{user_id}",
    response_model=MemberRead,
    summary="Modifier le rôle d'un membre",
)
def update_organization_member(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    data: MemberRoleUpdate,
    session: DatabaseSession,
    access: ApplicationAccess,
):
    del access
    membership = auth.update_member_role(session, organization_id, user_id, data)
    user = membership.user
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "role": membership.role,
        "membership_id": membership.id,
        "created_at": user.created_at,
    }


__all__ = ["router"]
