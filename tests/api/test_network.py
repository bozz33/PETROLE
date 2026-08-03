"""Tests contractuels du réseau normalisé et de sa validation."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from tests.factories import brut_leger, entree_canonique, modele_pompe

from hydro_api.application import create_application
from hydro_api.config import Settings
from hydro_api.database.base import Base
from hydro_api.database.session import get_session


@pytest.fixture
def network_api() -> Generator[TestClient, None, None]:
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


def create_model(client: TestClient) -> tuple[dict, dict]:
    organization = client.post(
        "/api/v1/organizations",
        json={"name": "Réseau Nord", "slug": "reseau-nord"},
    ).json()
    project = client.post(
        "/api/v1/projects",
        json={
            "organization_id": organization["id"],
            "name": "Oléoduc normalisé",
            "code": "OLN-01",
        },
    ).json()
    fluid_response = client.post(
        "/api/v1/catalog/fluids",
        json={
            "organization_id": organization["id"],
            "code": "BRUT-RESEAU",
            "name": "Brut de validation réseau",
            "payload": brut_leger().as_dict(),
            "source": "Analyse laboratoire de validation",
        },
    )
    assert fluid_response.status_code == 201, fluid_response.text
    fluid_approval = client.post(f"/api/v1/catalog/items/{fluid_response.json()['id']}/approve")
    assert fluid_approval.status_code == 200, fluid_approval.text
    response = client.post(
        f"/api/v1/projects/{project['id']}/models",
        json={
            "name": "Baseline normalisée",
            "payload": {
                "units": entree_canonique().payload()["units"],
                "fluid_catalog_item_id": fluid_approval.json()["id"],
            },
        },
    )
    assert response.status_code == 201, response.text
    return organization, response.json()


def create_node(
    client: TestClient,
    model_id: str,
    *,
    code: str,
    kind: str,
    elevation_m: float,
    payload: dict | None = None,
) -> dict:
    response = client.post(
        f"/api/v1/models/{model_id}/nodes",
        json={
            "code": code,
            "name": f"Nœud {code}",
            "kind": kind,
            "elevation_m": elevation_m,
            "payload": payload or {},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_edge(
    client: TestClient,
    model_id: str,
    *,
    code: str,
    sequence: int,
    start: dict,
    end: dict,
    material_catalog_item_id: str | None = None,
) -> dict:
    response = client.post(
        f"/api/v1/models/{model_id}/edges",
        json={
            "from_node_id": start["id"],
            "to_node_id": end["id"],
            "material_catalog_item_id": material_catalog_item_id,
            "code": code,
            "name": f"Tronçon {code}",
            "sequence": sequence,
            "length_m": 1000.0,
            "inner_diameter_m": 0.5,
            "roughness_m": 0.000045,
            "mawp_pa": 8_000_000.0,
            "profile": [
                {"chainage_m": 0.0, "elevation_m": start["elevation_m"]},
                {"chainage_m": 1000.0, "elevation_m": end["elevation_m"]},
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_approved_pump(client: TestClient, organization_id: str) -> dict:
    response = client.post(
        "/api/v1/catalog/pumps",
        json={
            "organization_id": organization_id,
            "code": "P-MVP-01",
            "name": "Pompe MVP",
            "payload": modele_pompe().as_dict(),
            "source": "Courbe constructeur validée",
        },
    )
    assert response.status_code == 201, response.text
    approval = client.post(f"/api/v1/catalog/items/{response.json()['id']}/approve")
    assert approval.status_code == 200, approval.text
    return approval.json()


def test_reseau_lineaire_valide_et_immuable_apres_approbation(network_api) -> None:
    client = network_api
    organization, model = create_model(client)
    original_hash = model["content_hash"]
    source = create_node(client, model["id"], code="SRC", kind="source", elevation_m=100.0)
    station = create_node(client, model["id"], code="ST-01", kind="station", elevation_m=120.0)
    terminal = create_node(client, model["id"], code="DST", kind="terminal", elevation_m=90.0)
    first_edge = create_edge(
        client,
        model["id"],
        code="T-01",
        sequence=1,
        start=source,
        end=station,
    )
    create_edge(
        client,
        model["id"],
        code="T-02",
        sequence=2,
        start=station,
        end=terminal,
    )
    pump = create_approved_pump(client, organization["id"])
    asset_response = client.post(
        f"/api/v1/models/{model['id']}/assets",
        json={
            "catalog_item_id": pump["id"],
            "node_id": station["id"],
            "code": "ST-01-P1",
            "name": "Pompe principale 1",
            "role": "main",
            "payload": {"running": True, "speed_ratio": 1.0},
        },
    )
    assert asset_response.status_code == 201, asset_response.text

    report = client.post(f"/api/v1/models/{model['id']}/validate")
    assert report.status_code == 200
    assert report.json()["valid"] is True
    assert report.json()["node_count"] == 3
    assert report.json()["edge_count"] == 2
    assert report.json()["asset_count"] == 1

    refreshed_model = client.get(f"/api/v1/models/{model['id']}").json()
    assert refreshed_model["content_hash"] != original_hash
    assert client.get(f"/api/v1/edges/{first_edge['id']}").status_code == 200

    approval = client.post(f"/api/v1/models/{model['id']}/approve")
    assert approval.status_code == 200
    mutation = client.patch(
        f"/api/v1/nodes/{source['id']}",
        json={"elevation_m": 101.0},
    )
    assert mutation.status_code == 409
    assert "immuable" in mutation.json()["detail"]


def test_reseau_refuse_profil_incomplet_et_pompe_sur_troncon(network_api) -> None:
    client = network_api
    organization, model = create_model(client)
    source = create_node(client, model["id"], code="SRC", kind="source", elevation_m=100.0)
    terminal = create_node(client, model["id"], code="DST", kind="terminal", elevation_m=90.0)

    invalid_profile = client.post(
        f"/api/v1/models/{model['id']}/edges",
        json={
            "from_node_id": source["id"],
            "to_node_id": terminal["id"],
            "code": "T-INVALIDE",
            "name": "Profil incomplet",
            "sequence": 1,
            "length_m": 1000.0,
            "inner_diameter_m": 0.5,
            "roughness_m": 0.000045,
            "mawp_pa": 8_000_000.0,
            "profile": [
                {"chainage_m": 0.0, "elevation_m": 100.0},
                {"chainage_m": 900.0, "elevation_m": 90.0},
            ],
        },
    )
    assert invalid_profile.status_code == 422

    edge = create_edge(
        client,
        model["id"],
        code="T-01",
        sequence=1,
        start=source,
        end=terminal,
    )
    pump = create_approved_pump(client, organization["id"])
    invalid_asset = client.post(
        f"/api/v1/models/{model['id']}/assets",
        json={
            "catalog_item_id": pump["id"],
            "edge_id": edge["id"],
            "code": "P-SUR-LIGNE",
            "name": "Pompe mal placée",
            "role": "main",
        },
    )
    assert invalid_asset.status_code == 409
    assert "station" in invalid_asset.json()["detail"]


def test_approbation_refuse_un_reseau_normalise_invalide(network_api) -> None:
    client = network_api
    _, model = create_model(client)
    create_node(client, model["id"], code="SRC", kind="source", elevation_m=100.0)

    approval = client.post(f"/api/v1/models/{model['id']}/approve")

    assert approval.status_code == 409
    assert "réseau normalisé doit être valide" in approval.json()["detail"]
    assert "NET_NODE_COUNT" in approval.json()["detail"]


def test_clone_reseau_remappe_les_references_sans_modifier_la_source(network_api) -> None:
    client = network_api
    _, model = create_model(client)
    source = create_node(client, model["id"], code="SRC", kind="source", elevation_m=100.0)
    terminal = create_node(client, model["id"], code="DST", kind="terminal", elevation_m=90.0)
    create_edge(
        client,
        model["id"],
        code="T-01",
        sequence=1,
        start=source,
        end=terminal,
    )
    source_scenario = client.post(
        f"/api/v1/models/{model['id']}/scenarios",
        json={"name": "Nominal", "payload": {"imposed_flow_m3_s": 0.2}},
    )
    assert source_scenario.status_code == 201, source_scenario.text
    source_model = client.get(f"/api/v1/models/{model['id']}").json()

    response = client.post(
        f"/api/v1/models/{model['id']}/clone",
        json={"name": "Variante clonée"},
    )

    assert response.status_code == 201, response.text
    clone = response.json()
    assert clone["parent_id"] == model["id"]
    assert clone["status"] == "draft"
    assert clone["content_hash"] == source_model["content_hash"]
    cloned_nodes = client.get(f"/api/v1/models/{clone['id']}/nodes").json()["items"]
    cloned_edges = client.get(f"/api/v1/models/{clone['id']}/edges").json()["items"]
    cloned_scenarios = client.get(f"/api/v1/models/{clone['id']}/scenarios").json()["items"]
    assert {item["code"] for item in cloned_nodes} == {"SRC", "DST"}
    assert {item["id"] for item in cloned_nodes}.isdisjoint({source["id"], terminal["id"]})
    assert cloned_edges[0]["from_node_id"] in {item["id"] for item in cloned_nodes}
    assert len(cloned_scenarios) == 1
    assert cloned_scenarios[0]["id"] != source_scenario.json()["id"]
    assert cloned_scenarios[0]["payload"] == source_scenario.json()["payload"]
    mutation = client.patch(
        f"/api/v1/nodes/{cloned_nodes[0]['id']}",
        json={"elevation_m": 80.0},
    )
    assert mutation.status_code == 200
    assert client.get(f"/api/v1/nodes/{source['id']}").json()["elevation_m"] == 100.0


def test_calcul_assemble_automatiquement_le_reseau_normalise(network_api) -> None:
    client = network_api
    _, model = create_model(client)
    source = create_node(client, model["id"], code="SRC", kind="source", elevation_m=100.0)
    terminal = create_node(client, model["id"], code="DST", kind="terminal", elevation_m=90.0)
    create_edge(
        client,
        model["id"],
        code="T-01",
        sequence=1,
        start=source,
        end=terminal,
    )
    preview = client.get(f"/api/v1/models/{model['id']}/canonical-sections")
    assert preview.status_code == 200, preview.text
    assert preview.json()["network"]["segments"][0]["id"] == "T-01"
    assert preview.json()["fluid"]["id"] == "BRUT-RESEAU"

    scenario_payload = entree_canonique().payload()["scenario"]
    scenario = client.post(
        f"/api/v1/models/{model['id']}/scenarios",
        json={"name": "Nominal normalisé", "payload": scenario_payload},
    )
    assert scenario.status_code == 201, scenario.text
    calculation = client.post(
        f"/api/v1/scenarios/{scenario.json()['id']}/calculations",
        headers={"Idempotency-Key": "calcul-reseau-normalise-001"},
        json={"engine": "long_distance_liquid"},
    )
    assert calculation.status_code == 202, calculation.text
    assert calculation.json()["status"].startswith("SIM_CONVERGED")
    result = client.get(f"/api/v1/calculations/{calculation.json()['id']}/results")
    assert result.json()["result"]["segment_count"] == 1
    assert result.json()["result"]["flow_m3_s"] > 0


def test_compilation_conserve_injections_et_soutirages_normalises(network_api) -> None:
    client = network_api
    _, model = create_model(client)
    source = create_node(client, model["id"], code="SRC", kind="source", elevation_m=100.0)
    injection = create_node(
        client,
        model["id"],
        code="INJ-01",
        kind="injection",
        elevation_m=105.0,
        payload={"flow_m3_s": 0.03},
    )
    offtake = create_node(
        client,
        model["id"],
        code="SOU-01",
        kind="offtake",
        elevation_m=95.0,
        payload={"flow_m3_s": 0.01},
    )
    terminal = create_node(client, model["id"], code="DST", kind="terminal", elevation_m=90.0)
    create_edge(client, model["id"], code="T-01", sequence=1, start=source, end=injection)
    create_edge(client, model["id"], code="T-02", sequence=2, start=injection, end=offtake)
    create_edge(client, model["id"], code="T-03", sequence=3, start=offtake, end=terminal)

    preview = client.get(f"/api/v1/models/{model['id']}/canonical-sections")

    assert preview.status_code == 200, preview.text
    compiled = preview.json()["network"]["injections"]
    assert [item["id"] for item in compiled] == ["INJ-01", "SOU-01"]
    assert compiled[0]["chainage_m"] == 1000.0
    assert compiled[0]["flow_m3_s"] == 0.03
    assert compiled[1]["chainage_m"] == 2000.0
    assert compiled[1]["flow_m3_s"] == -0.01


def test_validation_refuse_noeud_ignore_et_debit_intermediaire_invalide(network_api) -> None:
    client = network_api
    _, model = create_model(client)
    source = create_node(client, model["id"], code="SRC", kind="source", elevation_m=100.0)
    tank = create_node(client, model["id"], code="TK-01", kind="tank", elevation_m=95.0)
    invalid_injection = create_node(
        client,
        model["id"],
        code="INJ-01",
        kind="injection",
        elevation_m=92.0,
    )
    terminal = create_node(client, model["id"], code="DST", kind="terminal", elevation_m=90.0)
    create_edge(client, model["id"], code="T-01", sequence=1, start=source, end=tank)
    create_edge(client, model["id"], code="T-02", sequence=2, start=tank, end=invalid_injection)
    create_edge(client, model["id"], code="T-03", sequence=3, start=invalid_injection, end=terminal)

    validation = client.post(f"/api/v1/models/{model['id']}/validate")

    assert validation.status_code == 200
    assert validation.json()["valid"] is False
    codes = {item["code"] for item in validation.json()["errors"]}
    assert {"NET_NODE_UNSUPPORTED", "NET_NODE_FLOW"} <= codes


def test_validation_exige_un_materiau_approuve(network_api) -> None:
    client = network_api
    organization, model = create_model(client)
    source = create_node(client, model["id"], code="SRC", kind="source", elevation_m=100.0)
    terminal = create_node(client, model["id"], code="DST", kind="terminal", elevation_m=90.0)
    material = client.post(
        "/api/v1/catalog/materials",
        json={
            "organization_id": organization["id"],
            "code": "ACIER-L450",
            "name": "Acier de conduite L450",
            "payload": {"roughness_m": 0.000045, "mawp_pa": 8_000_000.0},
            "source": "Fiche matériau approuvable",
        },
    )
    assert material.status_code == 201, material.text
    create_edge(
        client,
        model["id"],
        code="T-01",
        sequence=1,
        start=source,
        end=terminal,
        material_catalog_item_id=material.json()["id"],
    )

    invalid = client.post(f"/api/v1/models/{model['id']}/validate")
    assert "NET_MATERIAL_UNAPPROVED" in {item["code"] for item in invalid.json()["errors"]}

    approval = client.post(f"/api/v1/catalog/items/{material.json()['id']}/approve")
    assert approval.status_code == 200, approval.text
    valid = client.post(f"/api/v1/models/{model['id']}/validate")
    assert valid.json()["valid"] is True


def test_suppressions_reseau_refusent_les_cascades_implicites(network_api) -> None:
    client = network_api
    organization, model = create_model(client)
    source = create_node(client, model["id"], code="SRC", kind="source", elevation_m=100.0)
    terminal = create_node(client, model["id"], code="DST", kind="terminal", elevation_m=90.0)
    edge = create_edge(
        client,
        model["id"],
        code="T-01",
        sequence=1,
        start=source,
        end=terminal,
    )
    valve = client.post(
        "/api/v1/catalog/valves",
        json={
            "organization_id": organization["id"],
            "code": "V-ISO-01",
            "name": "Vanne d'isolement",
            "payload": {"kind": "gate_valve", "k_coefficient": 0.2},
            "source": "Fiche constructeur validée",
        },
    )
    assert valve.status_code == 201, valve.text
    valve = client.post(f"/api/v1/catalog/items/{valve.json()['id']}/approve").json()
    asset = client.post(
        f"/api/v1/models/{model['id']}/assets",
        json={
            "catalog_item_id": valve["id"],
            "edge_id": edge["id"],
            "code": "T-01-V1",
            "name": "Vanne principale",
            "role": "isolation",
            "payload": {"chainage_m": 500.0, "opening_ratio": 1.0},
        },
    )
    assert asset.status_code == 201, asset.text

    assert client.delete(f"/api/v1/nodes/{source['id']}").status_code == 409
    assert client.delete(f"/api/v1/edges/{edge['id']}").status_code == 409
    assert client.delete(f"/api/v1/assets/{asset.json()['id']}").status_code == 204
    assert client.delete(f"/api/v1/edges/{edge['id']}").status_code == 204
    assert client.delete(f"/api/v1/nodes/{source['id']}").status_code == 204
    assert client.delete(f"/api/v1/nodes/{terminal['id']}").status_code == 204


def test_schema_openapi_expose_reseau_normalise(network_api) -> None:
    paths = network_api.get("/api/v1/openapi.json").json()["paths"]

    assert "/api/v1/models/{model_id}/nodes" in paths
    assert "/api/v1/models/{model_id}/edges" in paths
    assert "/api/v1/models/{model_id}/assets" in paths
    assert "/api/v1/models/{model_id}/validate" in paths
    assert "/api/v1/models/{model_id}/clone" in paths
    assert "/api/v1/models/{model_id}/canonical-sections" in paths
