"""Tests du socle HTTP de l'API.

Les tests qui necessitent une base de donnees utilisent exclusivement
PostgreSQL via les fixtures partagees du conftest (ADR-TEST-DB-001).
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from hydro_api.application import create_application
from hydro_api.config import Settings
from hydro_api.models import AuditEvent
from hydro_api.database.base import utc_now
from hydro_api.storage import object_storage_for
from hydro_shared.observability import bound_context


def test_sante_api() -> None:
    """Le controle de sante expose un contrat stable et l'environnement actif."""

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
    }


def test_racine_api_expose_sonde_neutre() -> None:
    """La racine evite une erreur 404 aux sondes generiques sans etre documentee."""

    application = create_application(Settings(environment="test", background_jobs_enabled=False))
    with TestClient(application) as client:
        response = client.get("/")
        openapi = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert response.json() == {"service": "hydro-api", "status": "ok"}
    assert "/" not in openapi.json()["paths"]


def test_erreur_http_ne_peut_pas_etre_mise_en_cache() -> None:
    """Les reponses d'erreur heritent des en-tetes de defense de l'API."""

    application = create_application(Settings(environment="test", background_jobs_enabled=False))
    with TestClient(application) as client:
        response = client.get("/route-inconnue")

    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_readiness_verifie_base_et_stockage(api_client, tmp_path) -> None:
    """La readiness confirme les deux dependances requises par les routes metier."""

    # api_client fournit deja PostgreSQL via le conftest.
    response = api_client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ready",
        "object_storage": "ready",
    }


def test_stockage_local_recree_un_repertoire_supprime(tmp_path) -> None:
    """Le controle local restaure le repertoire puis confirme son ecriture."""

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
    """Le schema OpenAPI reste sous le prefixe contractuel /api/v1."""

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


def test_correlation_alimente_automatiquement_le_journal_audit(pg_session) -> None:
    """Le contexte HTTP est copie dans tout evenement cree pendant la requete."""

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
