"""Contrats PostgreSQL de V1-B : comparaison mesure ↔ calcul stationnaire."""

from __future__ import annotations

from collections.abc import Generator
from math import isclose, sqrt

import pytest
from fastapi.testclient import TestClient
from tests.factories import brut_leger, entree_canonique

FLOW_MAPPING = {
    "fields": {
        "timestamp": "timestamp",
        "value": "flow",
        "unit": "unit",
        "quality": "quality",
        "source": "source",
    },
    "dimensions": {"value": "volumetric_flow"},
}
PRESSURE_MAPPING = {
    "fields": {
        "timestamp": "timestamp",
        "value": "pressure",
        "unit": "unit",
        "quality": "quality",
        "source": "source",
    },
    "dimensions": {"value": "pressure"},
}


@pytest.fixture
def comparison_client(api_client_factory) -> Generator[TestClient, None, None]:
    with api_client_factory() as client:
        yield client


def _fixture_network(client: TestClient) -> dict:
    organization_response = client.post(
        "/api/v1/organizations",
        json={"name": "Opérateur comparaison", "slug": "operateur-comparaison"},
    )
    assert organization_response.status_code == 201, organization_response.text
    organization = organization_response.json()
    site_response = client.post(
        "/api/v1/sites",
        json={
            "organization_id": organization["id"],
            "name": "Station de comparaison",
            "code": "SITE-CMP",
        },
    )
    assert site_response.status_code == 201, site_response.text
    site = site_response.json()
    project_response = client.post(
        "/api/v1/projects",
        json={
            "organization_id": organization["id"],
            "site_id": site["id"],
            "name": "Oléoduc de comparaison",
            "code": "PL-CMP",
            "project_type": "liquid_pipeline",
        },
    )
    assert project_response.status_code == 201, project_response.text
    project = project_response.json()
    fluid_response = client.post(
        "/api/v1/catalog/fluids",
        json={
            "organization_id": organization["id"],
            "code": "BRUT-CMP",
            "name": "Brut de comparaison",
            "payload": brut_leger().as_dict(),
            "source": "Analyse laboratoire de test",
        },
    )
    assert fluid_response.status_code == 201, fluid_response.text
    approved_fluid = client.post(f"/api/v1/catalog/items/{fluid_response.json()['id']}/approve")
    assert approved_fluid.status_code == 200, approved_fluid.text
    model_response = client.post(
        f"/api/v1/projects/{project['id']}/models",
        json={
            "name": "Régime stationnaire de comparaison",
            "payload": {
                "units": entree_canonique().payload()["units"],
                "fluid_catalog_item_id": approved_fluid.json()["id"],
            },
        },
    )
    assert model_response.status_code == 201, model_response.text
    model = model_response.json()

    def node(code: str, kind: str, elevation_m: float) -> dict:
        response = client.post(
            f"/api/v1/models/{model['id']}/nodes",
            json={
                "code": code,
                "name": f"Nœud {code}",
                "kind": kind,
                "elevation_m": elevation_m,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    source = node("SRC", "source", 100.0)
    terminal = node("DST", "terminal", 90.0)
    edge_response = client.post(
        f"/api/v1/models/{model['id']}/edges",
        json={
            "from_node_id": source["id"],
            "to_node_id": terminal["id"],
            "code": "T-CMP",
            "name": "Tronçon de comparaison",
            "sequence": 1,
            "length_m": 1_000.0,
            "inner_diameter_m": 0.5,
            "roughness_m": 0.000045,
            "mawp_pa": 8_000_000.0,
            "profile": [
                {"chainage_m": 0.0, "elevation_m": source["elevation_m"]},
                {"chainage_m": 1_000.0, "elevation_m": terminal["elevation_m"]},
            ],
        },
    )
    assert edge_response.status_code == 201, edge_response.text
    edge = edge_response.json()
    scenario_response = client.post(
        f"/api/v1/models/{model['id']}/scenarios",
        json={"name": "Régime stable", "payload": entree_canonique().payload()["scenario"]},
    )
    assert scenario_response.status_code == 201, scenario_response.text
    calculation_response = client.post(
        f"/api/v1/scenarios/{scenario_response.json()['id']}/calculations",
        json={"engine": "long_distance_liquid"},
        headers={"Idempotency-Key": "comparison-stationary-calculation"},
    )
    assert calculation_response.status_code == 202, calculation_response.text
    calculation = calculation_response.json()
    result_response = client.get(f"/api/v1/calculations/{calculation['id']}/results")
    assert result_response.status_code == 200, result_response.text
    return {
        "organization": organization,
        "site": site,
        "project": project,
        "model": model,
        "source": source,
        "terminal": terminal,
        "edge": edge,
        "calculation": calculation,
        "result": result_response.json()["result"],
    }


def _dataset_and_tag(
    client: TestClient,
    *,
    context: dict,
    content: bytes,
    mapping: dict,
    tag_payload: dict,
    import_key: str,
) -> tuple[dict, dict]:
    uploaded = client.post(
        "/api/v1/files",
        data={"organization_id": context["organization"]["id"]},
        files={"file": ("measurements.csv", content, "text/csv")},
    )
    assert uploaded.status_code == 201, uploaded.text
    dataset_response = client.post(
        "/api/v1/datasets",
        json={
            "organization_id": context["organization"]["id"],
            "project_id": context["project"]["id"],
            "file_id": uploaded.json()["id"],
            "name": "Mesures pour comparaison",
            "kind": "measurements",
        },
    )
    assert dataset_response.status_code == 201, dataset_response.text
    dataset = dataset_response.json()
    assert client.post(f"/api/v1/datasets/{dataset['id']}/preview").status_code == 200
    mapped = client.post(f"/api/v1/datasets/{dataset['id']}/mappings", json=mapping)
    assert mapped.status_code == 200, mapped.text
    imported = client.post(
        f"/api/v1/datasets/{dataset['id']}/imports",
        headers={"Idempotency-Key": f"dataset-{import_key}"},
    )
    assert imported.status_code == 201, imported.text
    tag_response = client.post("/api/v1/measurement-tags", json=tag_payload)
    assert tag_response.status_code == 201, tag_response.text
    tag = tag_response.json()
    time_series = client.post(
        f"/api/v1/datasets/{dataset['id']}/time-series-imports",
        json={"tag_id": tag["id"], "processing_version": "pilot-v1-b1-source"},
        headers={"Idempotency-Key": f"time-series-{import_key}"},
    )
    assert time_series.status_code == 201, time_series.text
    return dataset, tag


def _approved_mapping(
    client: TestClient,
    *,
    context: dict,
    tag_id: str,
    target_type: str,
    target_id: str,
    metric: str,
) -> dict:
    mapping_response = client.post(
        "/api/v1/measurement-model-mappings",
        json={
            "organization_id": context["organization"]["id"],
            "project_id": context["project"]["id"],
            "tag_id": tag_id,
            "target_type": target_type,
            "target_id": target_id,
            "metric": metric,
            "source_ref": "Schéma de mesure approuvé pour l'essai V1-B.",
        },
    )
    assert mapping_response.status_code == 201, mapping_response.text
    assert mapping_response.json()["status"] == "draft"
    approval = client.post(
        f"/api/v1/measurement-model-mappings/{mapping_response.json()['id']}/approve",
        json={"comment": "Correspondance vérifiée pendant le test."},
    )
    assert approval.status_code == 200, approval.text
    assert approval.json()["status"] == "approved"
    assert approval.json()["approved_at"]
    return approval.json()


def test_comparison_calculates_signed_residuals_kpis_and_lineage(
    comparison_client: TestClient,
) -> None:
    context = _fixture_network(comparison_client)
    dataset, tag = _dataset_and_tag(
        comparison_client,
        context=context,
        content=(
            b"timestamp;flow;unit;quality;source\n"
            b"2026-08-10T10:00:00Z;0.20;m ** 3 / s;good;FT-CMP\n"
            b"2026-08-10T10:01:00Z;0.21;m ** 3 / s;uncertain;FT-CMP\n"
            b"2026-08-10T10:02:00Z;0.19;m ** 3 / s;bad;FT-CMP\n"
        ),
        mapping=FLOW_MAPPING,
        tag_payload={
            "organization_id": context["organization"]["id"],
            "site_id": context["site"]["id"],
            "external_name": "FT-CMP",
            "name": "Débit tronçon comparaison",
            "measurement_type": "flow",
            "dimension": "volumetric_flow",
            "source_unit": "m ** 3 / s",
            "source": "fichier-test",
        },
        import_key="flow",
    )
    mapping = _approved_mapping(
        comparison_client,
        context=context,
        tag_id=tag["id"],
        target_type="edge",
        target_id=context["edge"]["id"],
        metric="flow_m3_s",
    )
    request = {
        "organization_id": context["organization"]["id"],
        "mapping_id": mapping["id"],
        "calculation_id": context["calculation"]["id"],
        "processing_version": "pilot-v1-b1-source",
        "start_timestamp": "2026-08-10T10:00:00Z",
        "end_timestamp": "2026-08-10T10:02:00Z",
    }
    before = comparison_client.get(f"/api/v1/calculations/{context['calculation']['id']}/results")
    response = comparison_client.post("/api/v1/measurement-comparisons", json=request)
    assert response.status_code == 201, response.text
    comparison = response.json()
    simulated = comparison["simulated_value_si"]
    expected = [0.20 - simulated, 0.21 - simulated]
    assert comparison["si_unit"] == "m ** 3 / s"
    assert comparison["kpis"]["n_compared"] == 2
    assert isclose(comparison["kpis"]["bias_si"], sum(expected) / 2, abs_tol=1e-12)
    assert isclose(
        comparison["kpis"]["mae_si"], sum(abs(value) for value in expected) / 2, abs_tol=1e-12
    )
    assert isclose(
        comparison["kpis"]["rmse_si"],
        sqrt(sum(value * value for value in expected) / 2),
        abs_tol=1e-12,
    )
    assert comparison["exclusions"]["n_candidates"] == 3
    assert comparison["exclusions"]["n_excluded_quality"] == 1
    assert comparison["exclusions"]["exclusion_counts"] == {"quality:bad": 1}
    assert comparison["exclusions"]["n_excluded_outlier"] == 0
    assert comparison["mapping"]["id"] == mapping["id"]
    assert (
        comparison_client.get(f"/api/v1/calculations/{context['calculation']['id']}/results").json()
        == before.json()
    )

    residuals = comparison_client.get(
        f"/api/v1/measurement-comparisons/{comparison['id']}/residuals"
    )
    assert residuals.status_code == 200, residuals.text
    assert residuals.json()["total"] == 3
    bad = next(item for item in residuals.json()["items"] if item["quality"] == "bad")
    assert bad["included_in_kpi"] is False
    assert bad["exclusion_reason"] == "quality:bad"
    assert bad["dataset_id"] == dataset["id"]
    assert bad["raw_sample_id"]
    assert bad["normalized_sample_id"]
    assert bad["source_timestamp"] == "2026-08-10T10:02:00Z"

    replay = comparison_client.post("/api/v1/measurement-comparisons", json=request)
    assert replay.status_code == 201, replay.text
    assert replay.json()["id"] == comparison["id"]
    assert (
        comparison_client.post(
            f"/api/v1/measurement-model-mappings/{mapping['id']}/approve",
            json={},
        ).status_code
        == 409
    )


def test_pressure_from_bar_is_compared_in_pa_and_incompatible_mapping_is_refused(
    comparison_client: TestClient,
) -> None:
    context = _fixture_network(comparison_client)
    terminal_pressure_pa = next(
        item["pressure_pa"]
        for item in context["result"]["profile"]
        if isclose(item["chainage_m"], 1_000.0, abs_tol=1e-6)
    )
    pressure_bar = terminal_pressure_pa / 100_000.0
    _, pressure_tag = _dataset_and_tag(
        comparison_client,
        context=context,
        content=(
            "timestamp;pressure;unit;quality;source\n"
            f"2026-08-10T11:00:00Z;{pressure_bar};bar;good;PT-CMP\n"
            f"2026-08-10T11:01:00Z;{pressure_bar + 0.1};bar;good;PT-CMP\n"
        ).encode(),
        mapping=PRESSURE_MAPPING,
        tag_payload={
            "organization_id": context["organization"]["id"],
            "site_id": context["site"]["id"],
            "external_name": "PT-CMP",
            "name": "Pression terminal comparaison",
            "measurement_type": "pressure",
            "dimension": "pressure",
            "source_unit": "bar",
            "source": "fichier-test",
        },
        import_key="pressure",
    )
    wrong_target = comparison_client.post(
        "/api/v1/measurement-model-mappings",
        json={
            "organization_id": context["organization"]["id"],
            "project_id": context["project"]["id"],
            "tag_id": pressure_tag["id"],
            "target_type": "edge",
            "target_id": context["edge"]["id"],
            "metric": "flow_m3_s",
        },
    )
    assert wrong_target.status_code == 409
    mapping = _approved_mapping(
        comparison_client,
        context=context,
        tag_id=pressure_tag["id"],
        target_type="node",
        target_id=context["terminal"]["id"],
        metric="pressure_pa",
    )
    response = comparison_client.post(
        "/api/v1/measurement-comparisons",
        json={
            "organization_id": context["organization"]["id"],
            "mapping_id": mapping["id"],
            "calculation_id": context["calculation"]["id"],
            "processing_version": "pilot-v1-b1-source",
            "start_timestamp": "2026-08-10T11:00:00Z",
            "end_timestamp": "2026-08-10T11:01:00Z",
        },
    )
    assert response.status_code == 201, response.text
    comparison = response.json()
    assert comparison["si_unit"] == "Pa"
    assert isclose(comparison["simulated_value_si"], terminal_pressure_pa, abs_tol=1e-6)
    assert isclose(comparison["kpis"]["bias_si"], 5_000.0, abs_tol=1e-6)
    assert isclose(comparison["kpis"]["mae_si"], 5_000.0, abs_tol=1e-6)
    assert isclose(comparison["kpis"]["rmse_si"], sqrt(50_000_000.0), abs_tol=1e-6)
