"""Test d'intégration de la file compatible PostgreSQL et du processus scientifique."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.factories import entree_canonique

from hydro_api.application import create_application
from hydro_api.config import Settings, get_settings
from hydro_api.database.base import Base
from hydro_api.database.session import database_engine, session_factory
from hydro_api.models import BackgroundJob
from hydro_api.worker import process_one


def test_worker_execute_un_calcul_mis_en_file() -> None:
    database_url = (
        "sqlite+pysqlite:///file:calcul-differe"
        "?mode=memory&cache=shared&uri=true"
    )
    settings = Settings(
        environment="test",
        database_url=database_url,
        background_jobs_enabled=True,
    )
    engine = database_engine(database_url)
    Base.metadata.create_all(engine)
    application = create_application(settings)
    application.dependency_overrides[get_settings] = lambda: settings

    canonical = entree_canonique().payload()
    with TestClient(application) as client:
        organization = client.post(
            "/api/v1/organizations",
            json={"name": "Exploitant calcul", "slug": "exploitant-calcul"},
        ).json()
        project = client.post(
            "/api/v1/projects",
            json={
                "organization_id": organization["id"],
                "name": "Oléoduc asynchrone",
                "code": "ASYNC-01",
            },
        ).json()
        model = client.post(
            f"/api/v1/projects/{project['id']}/models",
            json={
                "name": "Modèle calcul",
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

        queued = client.post(
            f"/api/v1/scenarios/{scenario['id']}/calculations",
            headers={"Idempotency-Key": "calcul-differe-001"},
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
            headers={"Idempotency-Key": "calcul-differe-relance-001"},
        )
        assert rerun.status_code == 202, rerun.text
        assert rerun.json()["id"] != calculation_id
        assert rerun.json()["input_hash"] == completed.json()["input_hash"]
        rerun_id = rerun.json()["id"]
        assert process_one(settings) is True
        replayed = client.get(f"/api/v1/calculations/{rerun_id}")
        assert replayed.json()["status"].startswith("SIM_CONVERGED")

        cancel_finished = client.post(f"/api/v1/calculations/{calculation_id}/cancel")
        assert cancel_finished.status_code == 409

        cancellable = client.post(
            f"/api/v1/scenarios/{scenario['id']}/calculations",
            headers={"Idempotency-Key": "calcul-differe-annulation-001"},
            json={"engine": "long_distance_liquid"},
        )
        assert cancellable.status_code == 202
        cancelled = client.post(
            f"/api/v1/calculations/{cancellable.json()['id']}/cancel"
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "SIM_CANCELLED"
        assert process_one(settings) is False

    with Session(engine) as session:
        jobs = session.scalars(select(BackgroundJob).order_by(BackgroundJob.created_at)).all()
        assert [job.status for job in jobs] == ["completed", "completed", "cancelled"]
        assert jobs[0].attempts == 1
        assert jobs[0].payload["correlation_id"]
        assert jobs[1].payload["source_calculation_id"] == calculation_id

    Base.metadata.drop_all(engine)
    engine.dispose()
    session_factory.cache_clear()
    database_engine.cache_clear()
