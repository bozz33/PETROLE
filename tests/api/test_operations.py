"""Tests API des réservoirs, transferts, comparaisons et optimisations."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from tests.factories import entree_canonique, pipeline, scenario, station_serie

from hydro_api.application import create_application
from hydro_api.config import Settings
from hydro_api.database.base import Base
from hydro_api.database.session import get_session


@pytest.fixture
def operations_client(tmp_path) -> Generator[TestClient, None, None]:
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
            background_jobs_enabled=False,
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
            yield client
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def _organization(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/organizations",
        json={"name": "Exploitant intégré", "slug": "exploitant-integre"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _project(client: TestClient, organization_id: str) -> dict:
    response = client.post(
        "/api/v1/projects",
        json={
            "organization_id": organization_id,
            "name": "Chaîne logistique",
            "code": "LOG-01",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _tank(
    client: TestClient,
    organization_id: str,
    *,
    code: str,
    level_m: float,
    fluid_id: str | None,
    compatible: list[str],
) -> dict:
    response = client.post(
        "/api/v1/tanks",
        json={
            "organization_id": organization_id,
            "name": "Bac " + code,
            "code": code,
            "current_level_m": level_m,
            "fluid_id": fluid_id,
            "compatible_fluid_ids": compatible,
            "levels": {
                "minimum_m": 1.0,
                "low_m": 1.5,
                "normal_m": 5.0,
                "high_m": 7.0,
                "high_high_m": 9.0,
            },
            "strapping": [
                {"height_m": 0.0, "volume_m3": 0.0},
                {"height_m": 5.0, "volume_m3": 500.0},
                {"height_m": 10.0, "volume_m3": 1_000.0},
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _calculation(
    client: TestClient,
    project_id: str,
    canonical: dict,
    suffix: str,
) -> tuple[dict, dict]:
    model = client.post(
        f"/api/v1/projects/{project_id}/models",
        json={
            "name": "Modèle " + suffix,
            "payload": {
                "units": canonical["units"],
                "fluid": canonical["fluid"],
                "network": canonical["network"],
                "equipment": canonical["equipment"],
                "rules": canonical["rules"],
            },
        },
    )
    assert model.status_code == 201, model.text
    scenario_response = client.post(
        f"/api/v1/models/{model.json()['id']}/scenarios",
        json={
            "name": "Scénario " + suffix,
            "payload": canonical["scenario"],
        },
    )
    assert scenario_response.status_code == 201, scenario_response.text
    calculation = client.post(
        f"/api/v1/scenarios/{scenario_response.json()['id']}/calculations",
        headers={"Idempotency-Key": "calcul-" + suffix},
        json={"engine": "long_distance_liquid"},
    )
    assert calculation.status_code == 202, calculation.text
    return scenario_response.json(), calculation.json()


def _report(
    client: TestClient,
    report_type: str,
    source_id: str,
    key: str,
) -> dict:
    response = client.post(
        "/api/v1/reports",
        headers={"Idempotency-Key": key},
        json={"report_type": report_type, "source_id": source_id},
    )
    assert response.status_code == 201, response.text
    report = response.json()
    download = client.get(f"/api/v1/reports/{report['id']}/download")
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")
    return report


def test_cycle_complet_reservoir_transfert_et_bilan(operations_client) -> None:
    organization = _organization(operations_client)
    source = _tank(
        operations_client,
        organization["id"],
        code="TK-S",
        level_m=8.0,
        fluid_id="diesel",
        compatible=[],
    )
    destination = _tank(
        operations_client,
        organization["id"],
        code="TK-D",
        level_m=2.0,
        fluid_id=None,
        compatible=["diesel"],
    )

    assert source["current_volume_m3"] == pytest.approx(800.0)
    assert destination["available_capacity_m3"] == pytest.approx(700.0)

    transfer = operations_client.post(
        f"/api/v1/organizations/{organization['id']}/transfers",
        headers={"Idempotency-Key": "transfert-001"},
        json={
            "source_tank_id": source["id"],
            "destination_tank_id": destination["id"],
            "fluid_id": "diesel",
            "requested_flow_m3_s": 0.1,
            "target_volume_m3": 100.0,
            "time_step_s": 333.0,
            "loss_fraction": 0.01,
            "absorbed_power_w": 50_000.0,
        },
    )
    assert transfer.status_code == 201, transfer.text
    result = transfer.json()["result_payload"]
    assert result["stop_reason"] == "target_volume_reached"
    assert result["duration_s"] == pytest.approx(1_000.0)
    assert result["withdrawn_volume_m3"] == pytest.approx(100.0)
    assert result["received_volume_m3"] == pytest.approx(99.0)
    assert result["energy_j"] == pytest.approx(50_000_000.0)

    replay = operations_client.post(
        f"/api/v1/organizations/{organization['id']}/transfers",
        headers={"Idempotency-Key": "transfert-001"},
        json={
            "source_tank_id": source["id"],
            "destination_tank_id": destination["id"],
            "fluid_id": "diesel",
            "requested_flow_m3_s": 0.1,
            "target_volume_m3": 100.0,
            "time_step_s": 333.0,
            "loss_fraction": 0.01,
            "absorbed_power_w": 50_000.0,
        },
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == transfer.json()["id"]
    transfers = operations_client.get(
        f"/api/v1/organizations/{organization['id']}/transfers",
        params={"tank_id": source["id"]},
    )
    assert transfers.status_code == 200
    assert transfers.json()["total"] == 1
    assert transfers.json()["items"][0]["id"] == transfer.json()["id"]

    balance = operations_client.post(
        f"/api/v1/transfers/{transfer.json()['id']}/balance",
        json={
            "source_opening": {"value_m3": 800.0, "standard_uncertainty_m3": 1.0},
            "source_closing": {"value_m3": 700.0, "standard_uncertainty_m3": 1.0},
            "destination_opening": {"value_m3": 200.0, "standard_uncertainty_m3": 1.0},
            "destination_closing": {"value_m3": 299.0, "standard_uncertainty_m3": 1.0},
            "metered_volume": {"value_m3": 100.0, "standard_uncertainty_m3": 0.5},
            "accounted_losses": {"value_m3": 1.0, "standard_uncertainty_m3": 0.2},
        },
    )
    assert balance.status_code == 200, balance.text
    assert balance.json()["system_imbalance_m3"] == pytest.approx(0.0)
    assert balance.json()["within_tolerance"] is True

    transfer_report = _report(
        operations_client,
        "transfer_simulation",
        transfer.json()["id"],
        "rapport-transfert-001",
    )
    balance_report = _report(
        operations_client,
        "material_balance",
        transfer.json()["id"],
        "rapport-bilan-001",
    )
    assert transfer_report["template_version"] == "rpt-05/1.0"
    assert balance_report["template_version"] == "rpt-06/1.0"

    tanks = operations_client.get(
        "/api/v1/tanks",
        params={"organization_id": organization["id"]},
    )
    assert tanks.status_code == 200
    assert tanks.json()["total"] == 2


def test_baremage_non_monotone_est_refuse(operations_client) -> None:
    organization = _organization(operations_client)
    response = operations_client.post(
        "/api/v1/tanks",
        json={
            "organization_id": organization["id"],
            "name": "Bac invalide",
            "code": "TK-X",
            "current_level_m": 1.0,
            "levels": {"minimum_m": 0.0, "high_high_m": 2.0},
            "strapping": [
                {"height_m": 0.0, "volume_m3": 0.0},
                {"height_m": 2.0, "volume_m3": 10.0},
                {"height_m": 1.0, "volume_m3": 20.0},
            ],
        },
    )
    assert response.status_code == 422


def test_comparaison_persistante_de_calculs(operations_client) -> None:
    organization = _organization(operations_client)
    project = _project(operations_client, organization["id"])
    first_input = entree_canonique(
        cas=scenario(imposed_flow_m3_s=0.15, inlet_pressure_pa=5_000_000.0)
    ).payload()
    second_input = entree_canonique(
        cas=scenario(imposed_flow_m3_s=0.20, inlet_pressure_pa=5_000_000.0)
    ).payload()
    _, first = _calculation(operations_client, project["id"], first_input, "A")
    _, second = _calculation(operations_client, project["id"], second_input, "B")

    response = operations_client.post(
        f"/api/v1/projects/{project['id']}/comparisons",
        headers={"Idempotency-Key": "comparaison-001"},
        json={"calculation_ids": [first["id"], second["id"]]},
    )
    assert response.status_code == 201, response.text
    comparison = response.json()
    assert comparison["result_payload"]["reference_calculation_id"] == first["id"]
    assert len(comparison["result_payload"]["ranked"]) == 2
    assert comparison["content_hash"].startswith("sha256:")
    comparisons = operations_client.get(f"/api/v1/projects/{project['id']}/comparisons")
    assert comparisons.status_code == 200
    assert comparisons.json()["total"] == 1
    assert comparisons.json()["items"][0]["id"] == comparison["id"]

    project_report = _report(
        operations_client,
        "project_sheet",
        project["id"],
        "rapport-projet-001",
    )
    comparison_report = _report(
        operations_client,
        "scenario_comparison",
        comparison["id"],
        "rapport-comparaison-001",
    )
    station_report = _report(
        operations_client,
        "station_pumps",
        first["id"],
        "rapport-station-001",
    )
    assert project_report["template_version"] == "rpt-01/1.0"
    assert comparison_report["template_version"] == "rpt-03/1.0"
    assert station_report["template_version"] == "rpt-04/1.0"


def test_optimisation_evalue_les_configurations_du_modele(operations_client) -> None:
    organization = _organization(operations_client)
    project = _project(operations_client, organization["id"])
    canonical = entree_canonique(
        conduite=pipeline(stations=(station_serie(nombre_de_pompes=2),)),
        cas=scenario(imposed_flow_m3_s=0.2, inlet_pressure_pa=3_000_000.0),
    ).payload()
    scenario_record, _ = _calculation(
        operations_client,
        project["id"],
        canonical,
        "OPT",
    )

    response = operations_client.post(
        f"/api/v1/scenarios/{scenario_record['id']}/optimizations",
        headers={"Idempotency-Key": "optimisation-001"},
        json={
            "objective": "min_energy",
            "speed_options": [0.8, 1.0],
            "reference_duration_s": 3_600.0,
            "constraints": {"minimum_flow_m3_s": 0.19},
        },
    )
    assert response.status_code == 201, response.text
    optimization = response.json()
    assert optimization["engine_version"].startswith("long_distance_liquid-")
    assert optimization["result_payload"]["generated_count"] == 8
    assert optimization["result_payload"]["evaluated_count"] > 0
    assert optimization["input_hash"].startswith("sha256:")
    optimizations = operations_client.get(
        f"/api/v1/scenarios/{scenario_record['id']}/optimizations"
    )
    assert optimizations.status_code == 200
    assert optimizations.json()["total"] == 1
    assert optimizations.json()["items"][0]["id"] == optimization["id"]
