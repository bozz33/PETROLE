"""Authentification locale, renouvellement de session et gestion des membres."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, timedelta
from typing import Any

import jwt
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hydro_api.config import Settings
from hydro_api.database.base import utc_now
from hydro_api.errors import ResourceConflictError, ResourceNotFoundError
from hydro_api.models import (
    AuditEvent,
    Organization,
    OrganizationMembership,
    RefreshSession,
    UserAccount,
)
from hydro_api.schemas.auth import (
    BootstrapRequest,
    LoginRequest,
    MemberCreate,
    MemberRoleUpdate,
    TokenPair,
    UserRead,
)
from hydro_shared.hashing import sha256_of_bytes

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
PASSWORD_DERIVED_BYTES = 32
DUMMY_PASSWORD_HASH = (
    "scrypt$16384$8$1$N2ZpeGVkLWR1bW15LXNhbHQ$uBvyxajDjcBtgFphwTnVe2gNdUswfSJACrsMlEz9m4M"
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    """Dérive un secret avec scrypt et un sel aléatoire propre au compte."""

    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=PASSWORD_DERIVED_BYTES,
    )
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    derived_text = base64.urlsafe_b64encode(derived).decode("ascii").rstrip("=")
    return (
        "scrypt$"
        + str(SCRYPT_N)
        + "$"
        + str(SCRYPT_R)
        + "$"
        + str(SCRYPT_P)
        + "$"
        + salt_text
        + "$"
        + derived_text
    )


def _decode_base64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def verify_password(password: str, encoded: str) -> bool:
    """Vérifie un mot de passe en temps constant, sans lever sur un hash invalide."""

    try:
        algorithm, n_text, r_text, p_text, salt_text, expected_text = encoded.split("$")
        if algorithm != "scrypt":
            return False
        expected = _decode_base64(expected_text)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_decode_base64(salt_text),
            n=int(n_text),
            r=int(r_text),
            p=int(p_text),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _audit_security(
    session: Session,
    *,
    action: str,
    user: UserAccount | None,
    success: bool,
    details: dict[str, Any] | None = None,
) -> None:
    membership = user.memberships[0] if user and user.memberships else None
    session.add(
        AuditEvent(
            organization_id=membership.organization_id if membership else None,
            actor_id=user.id if user else None,
            action=action,
            object_type="user_account",
            object_id=user.id if user else uuid.UUID(int=0),
            details={"success": success, **(details or {})},
            created_at=utc_now(),
        )
    )


def is_initialized(session: Session) -> bool:
    """Indique si le premier compte a déjà été créé."""

    count = session.scalar(select(func.count()).select_from(UserAccount))
    return bool(count)


def bootstrap(
    session: Session,
    data: BootstrapRequest,
    settings: Settings,
) -> TokenPair:
    """Crée le premier administrateur ; l'opération devient ensuite indisponible."""

    existing_count = session.scalar(select(func.count()).select_from(UserAccount))
    if existing_count:
        raise ResourceConflictError(
            "L'initialisation est déjà terminée. Utilisez un compte administrateur."
        )
    organization = Organization(
        name=data.organization_name,
        slug=data.organization_slug,
        default_locale="fr",
        default_unit_system="SI",
    )
    user = UserAccount(
        email=normalize_email(str(data.email)),
        full_name=data.full_name.strip(),
        password_hash=hash_password(data.password),
        is_active=True,
    )
    session.add_all([organization, user])
    session.flush()
    membership = OrganizationMembership(
        organization_id=organization.id,
        user_id=user.id,
        role="admin",
    )
    session.add(membership)
    session.flush()
    user.last_login_at = utc_now()
    _audit_security(
        session,
        action="bootstrap",
        user=user,
        success=True,
        details={"organization_id": str(organization.id)},
    )
    return issue_token_pair(session, user, settings)


def _access_token(user: UserAccount, settings: Settings) -> tuple[str, int]:
    now = utc_now()
    expires = now + timedelta(minutes=settings.access_token_minutes)
    payload = {
        "sub": str(user.id),
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": str(uuid.uuid4()),
        "iss": "hydro-platform",
        "aud": "hydro-api",
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    return token, settings.access_token_minutes * 60


def _refresh_token() -> str:
    return secrets.token_urlsafe(48)


def _refresh_hash(token: str) -> str:
    return sha256_of_bytes(token.encode("utf-8"))


def issue_token_pair(
    session: Session,
    user: UserAccount,
    settings: Settings,
) -> TokenPair:
    """Crée un accès court et un renouvellement opaque conservé uniquement haché."""

    access_token, expires_in = _access_token(user, settings)
    refresh_token = _refresh_token()
    now = utc_now()
    session.add(
        RefreshSession(
            user_id=user.id,
            token_hash=_refresh_hash(refresh_token),
            created_at=now,
            expires_at=now + timedelta(days=settings.refresh_token_days),
        )
    )
    session.flush()
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=UserRead.model_validate(user),
    )


def login(
    session: Session,
    data: LoginRequest,
    settings: Settings,
) -> TokenPair:
    """Authentifie sans révéler si l'adresse existe."""

    email = normalize_email(str(data.email))
    user = session.scalar(select(UserAccount).where(UserAccount.email == email))
    encoded_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
    password_valid = verify_password(data.password, encoded_hash)
    if user is None or not password_valid or not user.is_active:
        _audit_security(
            session,
            action="login_failed",
            user=user,
            success=False,
            details={"email_hash": sha256_of_bytes(email.encode("utf-8"))},
        )
        session.flush()
        raise PermissionError("Adresse ou mot de passe incorrect.")
    user.last_login_at = utc_now()
    _audit_security(session, action="login", user=user, success=True)
    return issue_token_pair(session, user, settings)


def refresh(
    session: Session,
    token: str,
    settings: Settings,
) -> TokenPair:
    """Fait tourner le jeton de renouvellement et révoque immédiatement l'ancien."""

    now = utc_now()
    refresh_session = session.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == _refresh_hash(token),
        )
    )
    expiration = None if refresh_session is None else refresh_session.expires_at
    if expiration is not None and expiration.tzinfo is None:
        expiration = expiration.replace(tzinfo=UTC)
    if (
        refresh_session is None
        or refresh_session.revoked_at is not None
        or expiration is None
        or expiration <= now
        or not refresh_session.user.is_active
    ):
        raise PermissionError("Le jeton de renouvellement est invalide ou expiré.")
    refresh_session.last_used_at = now
    refresh_session.revoked_at = now
    _audit_security(
        session,
        action="refresh",
        user=refresh_session.user,
        success=True,
    )
    return issue_token_pair(session, refresh_session.user, settings)


def logout(session: Session, token: str) -> None:
    refresh_session = session.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == _refresh_hash(token),
        )
    )
    if refresh_session is None:
        return
    if refresh_session.revoked_at is None:
        refresh_session.revoked_at = utc_now()
    _audit_security(
        session,
        action="logout",
        user=refresh_session.user,
        success=True,
    )
    session.flush()


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    """Valide signature, audience, émetteur, expiration et type du JWT."""

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            audience="hydro-api",
            issuer="hydro-platform",
            options={"require": ["sub", "typ", "iat", "exp", "jti"]},
        )
        if payload.get("typ") != "access":
            raise PermissionError("Type de jeton invalide.")
        return uuid.UUID(str(payload["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise PermissionError("Le jeton d'accès est invalide ou expiré.") from exc


def get_user(session: Session, user_id: uuid.UUID) -> UserAccount:
    user = session.get(UserAccount, user_id)
    if user is None or not user.is_active:
        raise PermissionError("Le compte associé au jeton est indisponible.")
    return user


def create_member(
    session: Session,
    organization_id: uuid.UUID,
    data: MemberCreate,
) -> UserAccount:
    """Crée un compte et son rôle dans l'organisation en une transaction."""

    if session.get(Organization, organization_id) is None:
        raise ResourceNotFoundError("Organisation", organization_id)
    email = normalize_email(str(data.email))
    if session.scalar(select(UserAccount).where(UserAccount.email == email)):
        raise ResourceConflictError(
            "Cette adresse possède déjà un compte. Ajoutez son appartenance séparément."
        )
    user = UserAccount(
        email=email,
        full_name=data.full_name.strip(),
        password_hash=hash_password(data.password),
        is_active=True,
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ResourceConflictError("Cette adresse possède déjà un compte.") from exc
    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user.id,
        role=data.role,
    )
    session.add(membership)
    session.flush()
    return user


def list_members(
    session: Session,
    organization_id: uuid.UUID,
) -> list[dict[str, Any]]:
    if session.get(Organization, organization_id) is None:
        raise ResourceNotFoundError("Organisation", organization_id)
    rows = session.execute(
        select(UserAccount, OrganizationMembership)
        .join(
            OrganizationMembership,
            OrganizationMembership.user_id == UserAccount.id,
        )
        .where(OrganizationMembership.organization_id == organization_id)
        .order_by(UserAccount.full_name)
    ).all()
    return [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "role": membership.role,
            "membership_id": membership.id,
            "created_at": user.created_at,
        }
        for user, membership in rows
    ]


def update_member_role(
    session: Session,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    data: MemberRoleUpdate,
) -> OrganizationMembership:
    membership = session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    if membership is None:
        raise ResourceNotFoundError("Membre", user_id)
    if membership.role == "admin" and data.role != "admin":
        admin_count = session.scalar(
            select(func.count())
            .select_from(OrganizationMembership)
            .where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.role == "admin",
            )
        )
        if admin_count == 1:
            raise ResourceConflictError(
                "Le dernier administrateur de l'organisation ne peut pas perdre son rôle."
            )
    membership.role = data.role
    session.flush()
    return membership


__all__ = [
    "bootstrap",
    "create_member",
    "decode_access_token",
    "get_user",
    "hash_password",
    "is_initialized",
    "issue_token_pair",
    "list_members",
    "login",
    "logout",
    "normalize_email",
    "refresh",
    "update_member_role",
    "verify_password",
]
