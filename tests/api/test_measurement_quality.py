"""Tests Phase 2 / Pilote-V1 des contrôles qualité sur les mesures."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def quality_client(api_client_factory) -> Generator[TestClient, None, None]:
    with api_client_factory() as client:
        yield client


def _organization(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/organizations",
        json={
            "name": "Opérateur pilote",
            "slug": "operateur-pilote",
            "default_locale": "fr",
            "default_unit_system": "SI",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _upload(client: TestClient, organization_id: str, content: bytes) -> dict:
    response = client.post(
        "/api/v1/files",
        data={"organization_id": organization_id},
        files={"file": ("mesures.csv", content, "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _import_pressure_measurements(client: TestClient, organization_id: str) -> dict:
    stored_file = _upload(
        client,
        organization_id,
        (
            b"t;p;u;q;s\n"
            b"2026-08-09T10:00:00Z;10;bar;good;PT-101\n"
            b"2026-08-09T10:02:00Z;12;bar;good;PT-101\n"
            b"2026-08-09T10:01:00Z;11;bar;uncertain;PT-101\n"
            b"2026-08-09T10:01:00Z;11.5;bar;good;PT-101\n"
            b"2026-08-09T10:03:00Z;13;bar;bad;PT-101\n"
        ),
    )
    dataset_response = client.post(
        "/api/v1/datasets",
        json={
            "organization_id": organization_id,
            "file_id": stored_file["id"],
            "name": "Pression pilote",
            "kind": "measurements",
        },
    )
    assert dataset_response.status_code == 201, dataset_response.text
    dataset = dataset_response.json()

    preview = client.post(f"/api/v1/datasets/{dataset['id']}/preview")
    assert preview.status_code == 200, preview.text
    mapping = client.post(
        f"/api/v1/datasets/{dataset['id']}/mappings",
        json={
            "fields": {
                "timestamp": "t",
                "value": "p",
                "unit": "u",
                "quality": "q",
                "source": "s",
            },
            "dimensions": {"value": "pressure"},
        },
    )
    assert mapping.status_code == 200, mapping.text
    imported = client.post(
        f"/api/v1/datasets/{dataset['id']}/imports",
        headers={"Idempotency-Key": "qualite-pression-v1"},
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["accepted_count"] == 5
    return dataset


def test_measurement_quality_summary_excludes_bad_and_detects_time_issues(quality_client) -> None:
    organization = _organization(quality_client)
    dataset = _import_pressure_measurements(quality_client, organization["id"])

    response = quality_client.get(f"/api/v1/datasets/{dataset['id']}/quality-summary")

    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary["dimension"] == "pressure"
    assert summary["si_unit"] == "Pa"
    assert summary["sample_count"] == 5
    assert summary["usable_sample_count"] == 4
    assert summary["excluded_sample_count"] == 1
    assert summary["quality_counts"] == {"bad": 1, "good": 3, "uncertain": 1}
    assert summary["source_counts"] == {"PT-101": 5}
    assert summary["duplicate_timestamp_count"] == 1
    assert summary["out_of_order_count"] == 1
    assert summary["start_timestamp"] == "2026-08-09T10:00:00Z"
    assert summary["end_timestamp"] == "2026-08-09T10:02:00Z"
    assert summary["minimum_value_si"] == pytest.approx(1_000_000.0)
    assert summary["maximum_value_si"] == pytest.approx(1_200_000.0)
    assert summary["mean_value_si"] == pytest.approx(1_112_500.0)
    assert summary["stddev_value_si"] == pytest.approx(73_950.997, rel=1e-5)
    assert {issue["code"] for issue in summary["issues"]} == {
        "DQ-007",
        "DQ-008",
        "TS-DUPLICATE",
    }


def test_quality_summary_refuses_non_measurement_dataset(quality_client) -> None:
    organization = _organization(quality_client)
    stored_file = _upload(
        quality_client,
        organization["id"],
        b"PK,Altitude\n0,100\n",
    )
    dataset = quality_client.post(
        "/api/v1/datasets",
        json={
            "organization_id": organization["id"],
            "file_id": stored_file["id"],
            "name": "Profil",
            "kind": "profile",
        },
    ).json()

    response = quality_client.get(f"/api/v1/datasets/{dataset['id']}/quality-summary")

    assert response.status_code == 409
    assert "uniquement pour un jeu de mesures" in response.json()["detail"]
