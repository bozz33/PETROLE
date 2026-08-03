"""Tests du socle HTTP de l'API."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hydro_api.application import create_application
from hydro_api.config import Settings, get_settings
from hydro_api.database.base import Base, utc_now
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
    assert response.json() == {
        "status": "ok",
        "service": "hydro-api",
        "version": "0.1.0",
        "environment": "test",
    }


def test_readiness_verifie_base_et_stockage(tmp_path) -> None:
    """La readiness confirme les deux dépendances requises par les routes métier."""

    application = create_application(
        Settings(
            environment="test",
            database_url="sqlite+pysqlite:///:memory:",
            background_jobs_enabled=False,
            object_storage_backend="filesystem",
            object_storage_directory=tmp_path / "objects",
        )
    )
    with TestClient(application) as client:
        response = client.get("/api/v1/health/ready")

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


def test_correlation_alimente_automatiquement_le_journal_audit() -> None:
    """Le contexte HTTP est copié dans tout événement créé pendant la requête."""

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    event = AuditEvent(
        organization_id=None,
        action="verification.correlation",
        object_type="controle",
        object_id=uuid.uuid4(),
        details={},
        created_at=utc_now(),
    )
    with Session(engine) as session, bound_context(correlation_id="test-audit-001"):
        session.add(event)
        session.flush()
        assert event.correlation_id == "test-audit-001"
    engine.dispose()
