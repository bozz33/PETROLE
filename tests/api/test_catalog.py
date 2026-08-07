"""Tests contractuels du catalogue technique versionné."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from tests.factories import brut_leger, modele_pompe

from hydro_api.models import AuditEvent, CatalogItem


@pytest.fixture
def catalog_api(
    api_client_factory,
    pg_session_factory: sessionmaker[Session],
) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    """API catalogue isolée par la transaction PostgreSQL du test."""

    with api_client_factory() as client:
        yield client, pg_session_factory


def create_organization(client: TestClient) -> dict:
    """Crée l'organisation isolant le catalogue du test."""

    response = client.post(
        "/api/v1/organizations",
        json={"name": "Catalogue Nord", "slug": "catalogue-nord"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_catalogue_produits_et_pompes_versionne(catalog_api) -> None:
    client, session_factory = catalog_api
    organization = create_organization(client)

    fluid_response = client.post(
        "/api/v1/catalog/fluids",
        json={
            "organization_id": organization["id"],
            "code": "brut-leger",
            "name": "Brut léger de référence",
            "payload": brut_leger().as_dict(),
            "source": "Analyse laboratoire LAB-2026-014",
        },
    )
    assert fluid_response.status_code == 201, fluid_response.text
    fluid = fluid_response.json()
    assert fluid["kind"] == "fluid"
    assert fluid["code"] == "BRUT-LEGER"
    assert fluid["payload"]["id"] == "BRUT-LEGER"
    assert fluid["content_hash"].startswith("sha256:")

    pump_response = client.post(
        "/api/v1/catalog/pumps",
        json={
            "organization_id": organization["id"],
            "code": "nm-8",
            "name": "Pompe principale NM-8",
            "payload": modele_pompe().as_dict(),
            "source": "Courbe constructeur révision 3",
        },
    )
    assert pump_response.status_code == 201, pump_response.text
    pump = pump_response.json()
    assert pump["payload"]["curve"]["flows_m3_s"]

    listed = client.get(
        "/api/v1/catalog/pumps",
        params={"organization_id": organization["id"]},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == pump["id"]

    approved = client.post(f"/api/v1/catalog/items/{pump['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["approved_at"]

    forbidden_update = client.patch(
        f"/api/v1/catalog/items/{pump['id']}",
        json={"name": "Modification silencieuse"},
    )
    assert forbidden_update.status_code == 409
    assert "immuable" in forbidden_update.json()["detail"]

    version_response = client.post(
        f"/api/v1/catalog/items/{pump['id']}/versions",
        json={"name": "Pompe principale NM-8, révision 4"},
    )
    assert version_response.status_code == 201, version_response.text
    version = version_response.json()
    assert version["version_number"] == 2
    assert version["parent_id"] == pump["id"]
    assert version["status"] == "draft"

    with session_factory() as session:
        item_count = session.scalar(select(func.count()).select_from(CatalogItem))
        audit_actions = set(session.scalars(select(AuditEvent.action)).all())
    assert item_count == 3
    assert "catalog_item.created" in audit_actions
    assert "catalog_item.approved" in audit_actions
    assert "catalog_item.versioned" in audit_actions


def test_catalogue_refuse_courbe_pompe_incoherente(catalog_api) -> None:
    client, _ = catalog_api
    organization = create_organization(client)

    response = client.post(
        "/api/v1/catalog/pumps",
        json={
            "organization_id": organization["id"],
            "code": "P-INVALIDE",
            "name": "Pompe invalide",
            "payload": {
                "curve": {
                    "flows_m3_s": [0.1, 0.2],
                    "heads_m": [100.0],
                }
            },
        },
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")


def test_schema_openapi_expose_catalogue(catalog_api) -> None:
    client, _ = catalog_api
    paths = client.get("/api/v1/openapi.json").json()["paths"]

    assert "/api/v1/catalog/{collection}" in paths
    assert "/api/v1/catalog/items/{catalog_item_id}/versions" in paths
    assert "/api/v1/catalog/items/{catalog_item_id}/approve" in paths


def test_familles_documentaires_conservent_leurs_champs_propres(catalog_api) -> None:
    """Vanne, matériau et accessoire gardent leurs champs après validation.

    Ces trois familles ont des schémas dont tous les champs sont facultatifs :
    une union les rendrait interchangeables et Pydantic pourrait retenir le
    mauvais modèle, effaçant silencieusement les champs de l'autre.
    """

    client, _ = catalog_api
    organization = create_organization(client)

    valve = client.post(
        "/api/v1/catalog/valves",
        json={
            "organization_id": organization["id"],
            "code": "VN-001",
            "name": "Vanne principale",
            "payload": {
                "valve_type": "ball",
                "nominal_diameter_m": 0.5,
                "k_coefficient": 0.2,
                "cv": 1200.0,
                "opening_time_s": 30.0,
                "fail_position": "fail_close",
                "pressure_class": "ANSI 300",
            },
        },
    )
    assert valve.status_code == 201, valve.text
    valve_payload = valve.json()["payload"]
    assert valve_payload["valve_type"] == "ball"
    assert valve_payload["fail_position"] == "fail_close"
    assert valve_payload["cv"] == 1200.0

    material = client.post(
        "/api/v1/catalog/materials",
        json={
            "organization_id": organization["id"],
            "code": "MAT-001",
            "name": "Acier API 5L X52",
            "payload": {
                "roughness_m": 4.5e-5,
                "mawp_pa": 8.0e6,
                "specification": "API 5L",
                "grade": "X52",
                "smys_pa": 3.59e8,
                "corrosion_allowance_m": 0.003,
            },
        },
    )
    assert material.status_code == 201, material.text
    material_payload = material.json()["payload"]
    assert material_payload["grade"] == "X52"
    assert material_payload["smys_pa"] == 3.59e8

    accessory = client.post(
        "/api/v1/catalog/accessories",
        json={
            "organization_id": organization["id"],
            "code": "ACC-001",
            "name": "Coude 90°",
            "payload": {"accessory_type": "elbow", "k_coefficient": 0.3},
        },
    )
    assert accessory.status_code == 201, accessory.text
    assert accessory.json()["payload"]["accessory_type"] == "elbow"


def test_famille_documentaire_refuse_une_valeur_physique_invalide(catalog_api) -> None:
    client, _ = catalog_api
    organization = create_organization(client)

    response = client.post(
        "/api/v1/catalog/valves",
        json={
            "organization_id": organization["id"],
            "code": "VN-002",
            "name": "Vanne incohérente",
            "payload": {"valve_type": "ball", "k_coefficient": -1.0},
        },
    )

    assert response.status_code == 422, response.text
