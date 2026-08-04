"""Test d'integration de la file compatible PostgreSQL et du processus scientifique.

Tous les tests utilisent exclusivement PostgreSQL via les fixtures partagees
du conftest (ADR-TEST-DB-001).
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.factories import entree_canonique

from hydro_api.application import create_application
from hydro_api.config import Settings, get_settings
from hydro_api.database.base import utc_now
from hydro_api.database.session import database_engine, session_factory
from hydro_api.models import BackgroundJob, CalculationRun
from hydro_api.worker import _refresh_lock, process_one

# URL de la base PostgreSQL partagee (meme instance que les tests API)
from tests.conftest import _postgres_engine, _test_database_url


def _settings() -> Settings:
    return Settings(
        environment="test",
        database_url=_test_database_url(),
        background_jobs_enabled=True,
    )


def _create_reseau(client: TestClient, canonical: dict) -> str:
    """Cree le parcours minimal org -> projet -> modele -> scenario et
    retourne l'identifiant du scenario."""

    org = client.post(
        "/api/v1/organizations",
        json={"name": "Exploitant calcul", "slug": f"exploitant-{uuid.uuid4().hex[:8]}"},
    ).json()
    project = client.post(
        "/api/v1/projects",
        json={"organization_id": org["id"], "name": "Oleaduc", "code": f"CODE-{uuid.uuid4().hex[:4]}"},
    ).json()
    model = client.post(
        f"/api/v1/projects/{project['id']}/models",
        json={"name": "Modele", "payload": {
            "units": canonical["units"], "fluid": canonical["fluid"],
            "network": canonical["network"], "equipment": canonical["equipment"],
            "rules": canonical["rules"],
        }},
    ).json()
    scenario = client.post(
        f"/api/v1/models/{model['id']}/scenarios",
        json={"name": "Nominal", "payload": canonical["scenario"]},
    ).json()
    return scenario["id"]


def test_worker_execute_un_calcul_mis_en_file(pg_session) -> None:
    """Le worker traite un calcul en file et le resultat est accessible via l'API."""

    settings = _settings()
    canonical = entree_canonique().payload()

    engine = _postgres_engine()
    application = create_application(settings)
    application.dependency_overrides[get_settings] = lambda: settings

    with TestClient(application) as client:
        # Mapper le client a la session PostgreSQL partagee
        from hydro_api.database.session import get_session as real_get_session

        def session_override():
            yield pg_session

        application.dependency_overrides[real_get_session] = session_override

        scenario_id = _create_reseau(client, canonical)

        queued = client.post(
            f"/api/v1/scenarios/{scenario_id}/calculations",
            headers={"Idempotency-Key": f"worker-{uuid.uuid4().hex}"},
            json={"engine": "long_distance_liquid"},
        )
        assert queued.status_code == 202, queued.text
        assert queued.json()["status"] == "SIM_QUEUED"
        calculation_id = queued.json()["id"]

        assert process_one(settings) is True
        assert process_one(settings) is False

        completed = client.get(f"/api/v1/calculations/{calculation_id}")
        assert completed.status_code == 200
        assert completed.json()["status"].startswith("SIM_CONVERGED")
        result = client.get(f"/api/v1/calculations/{calculation_id}/results")
        assert result.json()["result"]["flow_m3_s"] > 0

        rerun = client.post(
            f"/api/v1/calculations/{calculation_id}/rerun",
            headers={"Idempotency-Key": f"relance-{uuid.uuid4().hex}"},
        )
        assert rerun.status_code == 202
        assert rerun.json()["id"] != calculation_id
        assert process_one(settings) is True
        replayed = client.get(f"/api/v1/calculations/{rerun.json()['id']}")
        assert replayed.json()["status"].startswith("SIM_CONVERGED")

        cancel_finished = client.post(f"/api/v1/calculations/{calculation_id}/cancel")
        assert cancel_finished.status_code == 409

    # Verifier l'etat des jobs via la session PostgreSQL
    jobs = pg_session.scalars(select(BackgroundJob).order_by(BackgroundJob.created_at)).all()
    assert [job.status for job in jobs] == ["completed", "completed"]
    assert jobs[0].attempts == 1
    assert jobs[0].payload["correlation_id"]

    # Nettoyer les caches d'engine entre les tests
    database_engine.cache_clear()
    session_factory.cache_clear()


def test_worker_distingue_erreur_technique_et_non_convergence(pg_session, monkeypatch) -> None:
    """Une panne simulee pendant le calcul devient SIM_TECHNICAL_ERROR."""

    settings = _settings()
    canonical = entree_canonique().payload()

    application = create_application(settings)
    application.dependency_overrides[get_settings] = lambda: settings

    with TestClient(application) as client:
        from hydro_api.database.session import get_session as real_get_session

        def session_override():
            yield pg_session

        application.dependency_overrides[real_get_session] = session_override

        scenario_id = _create_reseau(client, canonical)

        queued = client.post(
            f"/api/v1/scenarios/{scenario_id}/calculations",
            headers={"Idempotency-Key": f"err-{uuid.uuid4().hex}"},
            json={},
        ).json()

    def fail_execution(*_args, **_kwargs):
        raise RuntimeError("panne simulee")

    monkeypatch.setattr("hydro_api.worker.core.execute_calculation", fail_execution)
    assert process_one(settings) is True

    job = pg_session.scalar(select(BackgroundJob))
    assert job is not None
    job.attempts = job.maximum_attempts - 1
    job.available_at = utc_now()
    pg_session.commit()

    assert process_one(settings) is True

    pg_session.expire_all()
    job = pg_session.scalar(select(BackgroundJob))
    calculation = pg_session.get(CalculationRun, uuid.UUID(queued["id"]))
    assert job is not None and job.status == "failed"
    assert calculation is not None
    assert calculation.status == "SIM_TECHNICAL_ERROR"
    assert calculation.diagnostics["exception_type"] == "RuntimeError"

    job.status = "running"
    job_id = job.id
    previous_lock = job.locked_at
    pg_session.commit()

    assert _refresh_lock(settings, job_id) is True
    refreshed = pg_session.get(BackgroundJob, job_id)
    assert refreshed is not None
    assert refreshed.locked_at != previous_lock

    database_engine.cache_clear()
    session_factory.cache_clear()
