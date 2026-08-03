"""Tests contractuels de l'identité, des rôles et de l'isolation des organisations."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from hydro_api.application import create_application
from hydro_api.config import Settings
from hydro_api.database.base import Base
from hydro_api.database.session import get_session
from hydro_api.models import Organization, OrganizationMembership, Site, UserAccount
from hydro_api.services.auth import hash_password

SECRET_TEST = "secret-de-test-strictement-local-0123456789"
MOT_DE_PASSE_ADMIN = "MotDePasse-Admin-2026!"
MOT_DE_PASSE_LECTEUR = "MotDePasse-Lecteur-2026!"


@pytest.fixture
def secured_api(tmp_path) -> Generator[tuple[TestClient, object], None, None]:
    """Fournit une API SQLite dont toutes les routes métier exigent un jeton."""

    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    application = create_application(
        Settings(
            environment="test",
            database_url="sqlite+pysqlite://",
            authentication_required=True,
            background_jobs_enabled=False,
            jwt_secret=SecretStr(SECRET_TEST),
            object_storage_backend="filesystem",
            object_storage_directory=tmp_path / "objects",
        )
    )

    def session_override():
        with Session(engine, expire_on_commit=False) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    application.dependency_overrides[get_session] = session_override
    try:
        with TestClient(application) as client:
            yield client, engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def _bootstrap(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": "admin@transport.example",
            "full_name": "Administrateur Transport",
            "password": MOT_DE_PASSE_ADMIN,
            "organization_name": "Transport Nord",
            "organization_slug": "transport-nord",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_configuration_de_production_refuse_une_securite_incomplete() -> None:
    with pytest.raises(ValidationError, match="AUTHENTICATION_REQUIRED"):
        Settings(environment="production", authentication_required=False)

    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(
            environment="production",
            authentication_required=True,
            background_jobs_enabled=True,
            jwt_secret=SecretStr("secret-trop-court"),
        )

    with pytest.raises(ValidationError, match="BACKGROUND_JOBS_ENABLED"):
        Settings(
            environment="production",
            authentication_required=True,
            background_jobs_enabled=False,
            jwt_secret=SecretStr(SECRET_TEST),
        )

    settings = Settings(
        environment="production",
        authentication_required=True,
        background_jobs_enabled=True,
        jwt_secret=SecretStr(SECRET_TEST),
    )
    assert settings.authentication_required is True


def test_initialisation_unique_et_routes_protegees(secured_api) -> None:
    client, _ = secured_api

    status_before = client.get("/api/v1/auth/status")
    assert status_before.status_code == 200
    assert status_before.json() == {
        "authentication_required": True,
        "initialized": False,
    }

    protected = client.get("/api/v1/organizations")
    assert protected.status_code == 401
    assert protected.headers["www-authenticate"] == "Bearer"

    tokens = _bootstrap(client)
    assert tokens["token_type"] == "bearer"
    assert tokens["user"]["memberships"][0]["role"] == "admin"
    assert client.get("/api/v1/auth/status").json()["initialized"] is True

    second = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": "autre@transport.example",
            "full_name": "Autre Administrateur",
            "password": MOT_DE_PASSE_ADMIN,
            "organization_name": "Autre Transport",
            "organization_slug": "autre-transport",
        },
    )
    assert second.status_code == 409


def test_connexion_rotation_et_revocation_des_jetons(secured_api) -> None:
    client, _ = secured_api
    initial = _bootstrap(client)

    refused = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@transport.example", "password": "mot-de-passe-errone"},
    )
    assert refused.status_code == 401
    assert "incorrect" in refused.json()["detail"].lower()

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "ADMIN@TRANSPORT.EXAMPLE",
            "password": MOT_DE_PASSE_ADMIN,
        },
    )
    assert login.status_code == 200, login.text
    tokens = login.json()

    me = client.get("/api/v1/auth/me", headers=_headers(tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "admin@transport.example"

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200, refreshed.text
    rotated = refreshed.json()
    assert rotated["refresh_token"] != tokens["refresh_token"]

    replay = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert replay.status_code == 401

    logout = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": rotated["refresh_token"]},
    )
    assert logout.status_code == 204

    revoked = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rotated["refresh_token"]},
    )
    assert revoked.status_code == 401

    # Le jeton émis pendant l'initialisation reste distinct de la session testée.
    assert initial["refresh_token"] != tokens["refresh_token"]


def test_roles_cloisonnement_et_protection_du_dernier_administrateur(
    secured_api,
) -> None:
    client, engine = secured_api
    tokens = _bootstrap(client)
    admin_headers = _headers(tokens["access_token"])
    organization_id = tokens["user"]["memberships"][0]["organization_id"]
    admin_id = tokens["user"]["id"]

    member = client.post(
        f"/api/v1/organizations/{organization_id}/members",
        headers=admin_headers,
        json={
            "email": "lecteur@transport.example",
            "full_name": "Lecteur Projet",
            "password": MOT_DE_PASSE_LECTEUR,
            "role": "viewer",
        },
    )
    assert member.status_code == 201, member.text

    viewer_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "lecteur@transport.example",
            "password": MOT_DE_PASSE_LECTEUR,
        },
    )
    assert viewer_login.status_code == 200
    viewer_headers = _headers(viewer_login.json()["access_token"])

    readable = client.get(
        f"/api/v1/organizations/{organization_id}",
        headers=viewer_headers,
    )
    assert readable.status_code == 200

    members_forbidden = client.get(
        f"/api/v1/organizations/{organization_id}/members",
        headers=viewer_headers,
    )
    assert members_forbidden.status_code == 403

    audit = client.get(
        "/api/v1/audit-events",
        headers=admin_headers,
        params={"organization_id": organization_id},
    )
    assert audit.status_code == 200
    assert audit.json()["total"] >= 1
    audit_forbidden = client.get(
        "/api/v1/audit-events",
        headers=viewer_headers,
        params={"organization_id": organization_id},
    )
    assert audit_forbidden.status_code == 403

    forbidden_write = client.post(
        "/api/v1/projects",
        headers=viewer_headers,
        json={
            "organization_id": organization_id,
            "name": "Projet interdit",
            "code": "INTERDIT",
        },
    )
    assert forbidden_write.status_code == 403

    promoted = client.patch(
        f"/api/v1/organizations/{organization_id}/members/{member.json()['id']}",
        headers=admin_headers,
        json={"role": "engineer"},
    )
    assert promoted.status_code == 200, promoted.text
    engineer_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "lecteur@transport.example",
            "password": MOT_DE_PASSE_LECTEUR,
        },
    )
    engineer_headers = _headers(engineer_login.json()["access_token"])
    engineer_project = client.post(
        "/api/v1/projects",
        headers=engineer_headers,
        json={
            "organization_id": organization_id,
            "name": "Projet ingénierie",
            "code": "ING-01",
            "responsible_user_ids": [member.json()["id"]],
        },
    )
    assert engineer_project.status_code == 201, engineer_project.text
    assert engineer_project.json()["responsible_user_ids"] == [member.json()["id"]]
    project_id = engineer_project.json()["id"]
    assert (
        client.post(
            f"/api/v1/projects/{project_id}/activate",
            headers=engineer_headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/projects/{project_id}/archive",
            headers=engineer_headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/projects/{project_id}/activate",
            headers=admin_headers,
        ).status_code
        == 200
    )

    with Session(engine) as session:
        other_organization = Organization(
            name="Transport Sud",
            slug="transport-sud",
            default_locale="fr",
            default_unit_system="SI",
        )
        other_user = UserAccount(
            email="admin.sud@transport.example",
            full_name="Administrateur Sud",
            password_hash=hash_password(MOT_DE_PASSE_ADMIN),
            is_active=True,
        )
        session.add_all([other_organization, other_user])
        session.flush()
        session.add(
            OrganizationMembership(
                organization_id=other_organization.id,
                user_id=other_user.id,
                role="admin",
            )
        )
        session.commit()
        other_id = str(other_organization.id)

    hidden = client.get(
        f"/api/v1/organizations/{other_id}",
        headers=admin_headers,
    )
    assert hidden.status_code == 403

    organizations = client.get("/api/v1/organizations", headers=admin_headers)
    assert organizations.status_code == 200
    assert organizations.json()["total"] == 1
    assert organizations.json()["items"][0]["id"] == organization_id

    demotion = client.patch(
        f"/api/v1/organizations/{organization_id}/members/{admin_id}",
        headers=admin_headers,
        json={"role": "engineer"},
    )
    assert demotion.status_code == 409
    assert "dernier administrateur" in demotion.json()["detail"].lower()


def test_sites_et_coherence_avec_les_projets(secured_api) -> None:
    client, engine = secured_api
    tokens = _bootstrap(client)
    headers = _headers(tokens["access_token"])
    organization_id = tokens["user"]["memberships"][0]["organization_id"]
    admin_id = tokens["user"]["id"]

    site = client.post(
        "/api/v1/sites",
        headers=headers,
        json={
            "organization_id": organization_id,
            "name": "Terminal Nord",
            "code": "tn-01",
            "country_code": "dz",
            "latitude": 36.75,
            "longitude": 3.05,
        },
    )
    assert site.status_code == 201, site.text
    assert site.json()["code"] == "TN-01"
    assert site.json()["country_code"] == "DZ"

    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "organization_id": organization_id,
            "site_id": site.json()["id"],
            "name": "Oléoduc Terminal",
            "code": "PL-TN-01",
        },
    )
    assert project.status_code == 201, project.text
    assert project.json()["site_id"] == site.json()["id"]

    with Session(engine) as session:
        other_organization = Organization(
            name="Organisation secondaire",
            slug="organisation-secondaire",
            default_locale="fr",
            default_unit_system="SI",
        )
        session.add(other_organization)
        session.flush()
        session.add(
            OrganizationMembership(
                organization_id=other_organization.id,
                user_id=uuid.UUID(admin_id),
                role="admin",
            )
        )
        other_site = Site(
            organization_id=other_organization.id,
            name="Terminal Sud",
            code="TS-01",
            country_code="DZ",
            status="active",
        )
        session.add(other_site)
        session.commit()
        other_site_id = str(other_site.id)

    conflict = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "organization_id": organization_id,
            "site_id": other_site_id,
            "name": "Projet incohérent",
            "code": "PL-ERREUR",
        },
    )
    assert conflict.status_code == 409
    assert "même organisation" in conflict.json()["detail"]

    archived = client.patch(
        f"/api/v1/sites/{site.json()['id']}",
        headers=headers,
        json={"status": "archived"},
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
