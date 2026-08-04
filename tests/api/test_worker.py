"""Tests d'intégration du worker sur PostgreSQL/PostGIS réel.

Ces scénarios utilisent plusieurs connexions indépendantes, comme en production :
l'API valide et commit la tâche, puis le worker l'acquiert dans une autre session.
La base dédiée est remise à zéro par l'infrastructure partagée avant et après
chaque test.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import entree_canonique

from hydro_api.config import Settings
from hydro_api.database.base import utc_now
from hydro_api.models import BackgroundJob, CalculationRun
from hydro_api.worker import _refresh_lock, process_one


def _settings(database_url: str) -> Settings:
    return Settings(
        environment="test",
        database_url=database_url,
        background_jobs_enabled=True,
    )


def _create_reseau(client, canonical: dict) -> str:
    """Crée le parcours minimal organisation → projet → modèle → scénario."""

    org = client.post(
        "/api/v1/organizations",
        json={
            "name": "Exploitant calcul",
            "slug": f"exploitant-{uuid.uuid4().hex[:8]}",
        },
    ).json()
    project = client.post(
        "/api/v1/projects",
        json={
            "organization_id": org["id"],
            "name": "Oléoduc",
            "code": f"CODE-{uuid.uuid4().hex[:4]}",
        },
    ).json()
    model = client.post(
        f"/api/v1/projects/{project['id']}/models",
        json={
            "name": "Modèle",
            "payload": {
                "units": canonical["units"],
                "fluid": canonical["fluid"],
                "network": canonical["network"],
                "equipment": canonical["equipment"],
                "rules": canonical["rules"],
            },
        },
    ).json()
    scenario = client.post(
        f"/api/v1/models/{model['id']}/scenarios",
        json={"name": "Nominal", "payload": canonical["scenario"]},
    ).json()
    return scenario["id"]


def test_worker_execute_un_calcul_mis_en_file(
    test_database_url: str,
    committed_api_client_factory,
    committed_session_factory: sessionmaker[Session],
) -> None:
    """Le worker traite une tâche commitée et expose son résultat par l'API."""

    settings = _settings(test_database_url)
    canonical = entree_canonique().payload()

    with committed_api_client_factory(background_jobs_enabled=True) as client:
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

    with committed_session_factory() as session:
        jobs = session.scalars(select(BackgroundJob).order_by(BackgroundJob.created_at)).all()
        assert [job.status for job in jobs] == ["completed", "completed"]
        assert jobs[0].attempts == 1
        assert jobs[0].payload["correlation_id"]


def test_worker_distingue_erreur_technique_et_non_convergence(
    test_database_url: str,
    committed_api_client_factory,
    committed_session_factory: sessionmaker[Session],
    monkeypatch,
) -> None:
    """Une panne de programmation devient une erreur technique après les reprises."""

    settings = _settings(test_database_url)
    canonical = entree_canonique().payload()

    with committed_api_client_factory(background_jobs_enabled=True) as client:
        scenario_id = _create_reseau(client, canonical)
        queued = client.post(
            f"/api/v1/scenarios/{scenario_id}/calculations",
            headers={"Idempotency-Key": f"err-{uuid.uuid4().hex}"},
            json={},
        ).json()

    def fail_execution(*_args, **_kwargs):
        raise RuntimeError("panne simulée")

    monkeypatch.setattr("hydro_api.worker.core.execute_calculation", fail_execution)
    assert process_one(settings) is True

    with committed_session_factory() as session:
        job = session.scalar(select(BackgroundJob))
        assert job is not None
        job.attempts = job.maximum_attempts - 1
        job.available_at = utc_now()
        session.commit()

    assert process_one(settings) is True

    with committed_session_factory() as session:
        job = session.scalar(select(BackgroundJob))
        calculation = session.get(CalculationRun, uuid.UUID(queued["id"]))
        assert job is not None and job.status == "failed"
        assert calculation is not None
        assert calculation.status == "SIM_TECHNICAL_ERROR"
        assert calculation.diagnostics["exception_type"] == "RuntimeError"

        job.status = "running"
        job_id = job.id
        previous_lock = job.locked_at
        session.commit()

    assert _refresh_lock(settings, job_id) is True

    with committed_session_factory() as session:
        refreshed = session.get(BackgroundJob, job_id)
        assert refreshed is not None
        assert refreshed.locked_at != previous_lock
