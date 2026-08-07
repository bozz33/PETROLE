"""Tests du socle HTTP de l'API.

Les tests qui nécessitent une base utilisent exclusivement PostgreSQL via les
fixtures partagées (ADR-TEST-DB-001).
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from hydro_api.application import create_application
from hydro_api.config import Settings
from hydro_api.database.base import utc_now
from hydro_api.models import AuditEvent
from hydro_api.storage import object_storage_for
from hydro_shared.observability import bound_context


def test_sante_api() -> None:
    """Le contrôle de santé expose un contrat stable et l'environnement actif."""

    application = create_application(Settings(environment="test", background_jobs_enabled=False))
    with TestClient(application) as client:
        response = client.get(
            "/api/v1/health",
            headers={"X-Correlation-ID": "test-sante-001"},
        )

    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == "test-sante-001"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert response.json() == {
        "status": "ok",
        "service": "hydro-api",
        "version": "0.1.0",
        "environment": "test",
        "build": {
            "application_version": "0.1.0",
            "git_sha": "unknown",
            "ref": "unknown",
            "build_date": "unknown",
            "scientific_engine_version": "hydroliquid-0.1.0",
            "database_migration_version": "9f3b6e0d5c17",
        },
        "deployment": {
            "mode": "multi_org",
            "organization_label": "Organisations",
        },
    }


def test_version_expose_identite_build_et_moteur() -> None:
    """La version de build est disponible sans dépendre de PostgreSQL."""

    application = create_application(
        Settings(
            environment="test",
            background_jobs_enabled=False,
            build_git_sha="a1b2c3d4e5f6",
            build_ref="v0.1.0-rc.1",
            build_date="2026-08-06T10:00:00Z",
        )
    )
    with TestClient(application) as client:
        response = client.get("/api/v1/version")
        scientific_validation = client.get("/api/v1/health/validation")

    assert response.status_code == 200
    assert response.json() == {
        "application_version": "0.1.0",
        "git_sha": "a1b2c3d4e5f6",
        "ref": "v0.1.0-rc.1",
        "build_date": "2026-08-06T10:00:00Z",
        "scientific_engine_version": "hydroliquid-0.1.0",
        "database_migration_version": "9f3b6e0d5c17",
    }
    assert scientific_validation.status_code == 200
    assert scientific_validation.json()["passed"] == 41
    assert scientific_validation.json()["total"] == 41


def test_racine_api_expose_sonde_neutre() -> None:
    """La racine évite une erreur 404 aux sondes génériques sans être documentée."""

    application = create_application(Settings(environment="test", background_jobs_enabled=False))
    with TestClient(application) as client:
        response = client.get("/")
        openapi = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert response.json() == {"service": "hydro-api", "status": "ok"}
    assert "/" not in openapi.json()["paths"]


def test_erreur_http_ne_peut_pas_etre_mise_en_cache() -> None:
    """Les réponses d'erreur héritent des en-têtes de défense de l'API."""

    application = create_application(Settings(environment="test", background_jobs_enabled=False))
    with TestClient(application) as client:
        response = client.get("/route-inconnue")

    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_readiness_verifie_base_et_stockage(api_client) -> None:
    """La readiness confirme les deux dépendances requises par les routes métier."""

    response = api_client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ready",
        "object_storage": "ready",
    }


def test_stockage_local_recree_un_repertoire_supprime(tmp_path) -> None:
    """Le contrôle local restaure le répertoire puis confirme son écriture."""

    root = tmp_path / "objects-recreated"
    storage = object_storage_for(
        Settings(
            environment="test",
            background_jobs_enabled=False,
            object_storage_backend="filesystem",
            object_storage_directory=root,
        )
    )
    root.rmdir()

    storage.check()

    assert root.is_dir()
    assert list(root.iterdir()) == []


def test_schema_openapi_versionne() -> None:
    """Le schéma OpenAPI reste sous le préfixe contractuel /api/v1."""

    application = create_application(Settings(environment="test", background_jobs_enabled=False))
    with TestClient(application) as client:
        response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    generated_correlation = uuid.UUID(response.headers["x-correlation-id"])
    assert generated_correlation.version == 4
    schema = response.json()
    assert schema["info"]["version"] == "0.1.0"
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/health/ready" in schema["paths"]
    assert "/api/v1/health/validation" in schema["paths"]
    assert "/api/v1/version" in schema["paths"]


def test_correlation_alimente_automatiquement_le_journal_audit(pg_session) -> None:
    """Le contexte HTTP est copié dans tout événement créé pendant la requête."""

    event = AuditEvent(
        organization_id=None,
        action="verification.correlation",
        object_type="controle",
        object_id=uuid.uuid4(),
        details={},
        created_at=utc_now(),
    )
    with bound_context(correlation_id="test-audit-001"):
        pg_session.add(event)
        pg_session.flush()
        assert event.correlation_id == "test-audit-001"
