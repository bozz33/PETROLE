"""Tests contractuels du référentiel normatif et de l'évaluation sûre."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from tests.factories import entree_canonique

from hydro_api.application import create_application
from hydro_api.config import Settings
from hydro_api.database.base import Base
from hydro_api.database.session import get_session


@pytest.fixture
def governance_api() -> Generator[TestClient, None, None]:
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


def create_organization(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/organizations",
        json={"name": "Gouvernance locale", "slug": "gouvernance-locale"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_standard(client: TestClient, organization_id: str) -> dict:
    response = client.post(
        "/api/v1/standards",
        json={
            "organization_id": organization_id,
            "code": "REF-INTERNE-001",
            "title": "Référence de validation acquise",
            "issuing_body": "Organisme de validation",
            "edition": "2026",
            "publication_date": "2026-01-15",
            "licensed_copy_ref": "coffre-documentaire/ref-001",
            "source_url": "https://standards.example/ref-001",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_rule_set(client: TestClient, organization_id: str, standard_id: str) -> dict:
    response = client.post(
        "/api/v1/rule-sets",
        json={
            "organization_id": organization_id,
            "code": "PRESSION-MVP",
            "title": "Limites de pression du pilote",
            "country_code": "dz",
            "domain": "pipeline_liquide",
            "standard_ids": [standard_id],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_cycle_normatif_et_evaluation_d_un_calcul(governance_api) -> None:
    client = governance_api
    organization = create_organization(client)
    standard = create_standard(client, organization["id"])

    premature_rule_set = client.post(
        "/api/v1/rule-sets",
        json={
            "organization_id": organization["id"],
            "code": "REFUSE",
            "title": "Jeu prématuré",
            "domain": "pipeline_liquide",
            "standard_ids": [standard["id"]],
        },
    )
    assert premature_rule_set.status_code == 409

    standard_approval = client.post(f"/api/v1/standards/{standard['id']}/approve")
    assert standard_approval.status_code == 200
    assert standard_approval.json()["status"] == "active"
    protected_standard = client.patch(
        f"/api/v1/standards/{standard['id']}",
        json={"title": "Modification interdite"},
    )
    assert protected_standard.status_code == 409

    rule_set = create_rule_set(client, organization["id"], standard["id"])
    assert rule_set["country_code"] == "DZ"
    assert rule_set["standard_ids"] == [standard["id"]]
    assert client.post(f"/api/v1/rule-sets/{rule_set['id']}/approve").status_code == 409

    rule_response = client.post(
        f"/api/v1/rule-sets/{rule_set['id']}/rules",
        json={
            "standard_id": standard["id"],
            "code": "P-MAX-001",
            "title": "Pression maximale du réseau",
            "severity": "blocking",
            "domain": "hydraulique",
            "metric_path": "max_pressure_pa",
            "operator": "le",
            "limit_value": 1.0,
            "unit": "Pa",
            "message": "La pression calculée dépasse la limite approuvée.",
            "source_clause_ref": "clause interne 4.2",
        },
    )
    assert rule_response.status_code == 201, rule_response.text
    rule = rule_response.json()
    assert client.post(f"/api/v1/rules/{rule['id']}/approve").status_code == 200
    rule_set_approval = client.post(f"/api/v1/rule-sets/{rule_set['id']}/approve")
    assert rule_set_approval.status_code == 200
    assert rule_set_approval.json()["status"] == "approved"
    immutable = client.post(
        f"/api/v1/rule-sets/{rule_set['id']}/rules",
        json={
            "code": "P-MIN-002",
            "title": "Pression minimale",
            "severity": "warning",
            "domain": "hydraulique",
            "metric_path": "min_pressure_pa",
            "operator": "ge",
            "limit_value": 0.0,
            "message": "La pression est trop faible.",
        },
    )
    assert immutable.status_code == 409

    canonical = entree_canonique().payload()
    project = client.post(
        "/api/v1/projects",
        json={
            "organization_id": organization["id"],
            "name": "Projet avec règles",
            "code": "RULE-01",
            "project_type": "liquid_pipeline",
            "unit_system": "SI",
            "rule_set_ids": [rule_set["id"]],
        },
    ).json()
    assert project["rule_set_ids"] == [rule_set["id"]]
    model = client.post(
        f"/api/v1/projects/{project['id']}/models",
        json={
            "name": "Modèle normatif",
            "payload": {
                "units": canonical["units"],
                "fluid": canonical["fluid"],
                "network": canonical["network"],
                "equipment": canonical["equipment"],
            },
        },
    ).json()
    scenario = client.post(
        f"/api/v1/models/{model['id']}/scenarios",
        json={"name": "Nominal", "payload": canonical["scenario"]},
    ).json()
    calculation = client.post(
        f"/api/v1/scenarios/{scenario['id']}/calculations",
        headers={"Idempotency-Key": "calcul-regles-001"},
        json={"engine": "long_distance_liquid"},
    )
    assert calculation.status_code == 202, calculation.text
    assert calculation.json()["status"].startswith("SIM_CONVERGED")

    result = client.get(f"/api/v1/calculations/{calculation.json()['id']}/results").json()
    evaluations = result["result"]["rule_evaluations"]
    assert len(evaluations) == 1
    assert evaluations[0]["status"] == "non_compliant"
    assert evaluations[0]["rule_code"] == "P-MAX-001"
    assert evaluations[0]["rule_set_hash"] == rule_set_approval.json()["content_hash"]
    assert evaluations[0]["severity"] == "blocking"
    assert evaluations[0]["measured_value"] > evaluations[0]["limit_value"]
    assert result["result"]["physical_approvable"] is True
    assert result["result"]["compliance_status"] == "non_compliant"
    assert result["result"]["compliance"]["blocking_failure_count"] == 1
    assert result["result"]["decision_eligible"] is False
    assert result["result"]["approvable"] is False
    listed = client.get(
        "/api/v1/evaluations",
        params={
            "organization_id": organization["id"],
            "calculation_id": calculation.json()["id"],
        },
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    repeated = client.post(f"/api/v1/calculations/{calculation.json()['id']}/evaluations")
    assert repeated.status_code == 200
    assert repeated.json()[0]["id"] == evaluations[0]["id"]


def test_schema_openapi_expose_gouvernance(governance_api) -> None:
    paths = governance_api.get("/api/v1/openapi.json").json()["paths"]

    assert "/api/v1/standards" in paths
    assert "/api/v1/rule-sets" in paths
    assert "/api/v1/evaluations" in paths
    assert "/api/v1/audit-events" in paths
