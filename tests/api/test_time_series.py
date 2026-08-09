"""Tests d'intégration PostgreSQL des séries temporelles Pilote/V1."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def time_series_client(api_client_factory) -> Generator[TestClient, None, None]:
    with api_client_factory() as client:
        yield client


def _organization(client: TestClient, *, slug: str) -> dict:
    response = client.post(
        "/api/v1/organizations",
        json={
            "name": f"Opérateur {slug}",
            "slug": slug,
            "default_locale": "fr",
            "default_unit_system": "SI",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _site(client: TestClient, organization_id: str, *, code: str) -> dict:
    response = client.post(
        "/api/v1/sites",
        json={
            "organization_id": organization_id,
            "name": f"Site {code}",
            "code": code,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _project(client: TestClient, organization_id: str, site_id: str, *, code: str) -> dict:
    response = client.post(
        "/api/v1/projects",
        json={
            "organization_id": organization_id,
            "site_id": site_id,
            "name": f"Projet {code}",
            "code": code,
            "project_type": "liquid_pipeline",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _measurement_dataset(
    client: TestClient,
    *,
    organization_id: str,
    project_id: str,
) -> dict:
    content = (
        b"timestamp;pressure;unit;quality;source\n"
        b"2026-08-09T10:00:00Z;10;bar;good;PT-101\n"
        b"2026-08-09T10:01:00Z;11;bar;uncertain;PT-101\n"
        b"2026-08-09T10:02:00Z;12;bar;bad;PT-101\n"
    )
    uploaded = client.post(
        "/api/v1/files",
        data={"organization_id": organization_id},
        files={"file": ("pressures.csv", content, "text/csv")},
    )
    assert uploaded.status_code == 201, uploaded.text
    dataset_response = client.post(
        "/api/v1/datasets",
        json={
            "organization_id": organization_id,
            "project_id": project_id,
            "file_id": uploaded.json()["id"],
            "name": "Pressions pilote",
            "kind": "measurements",
        },
    )
    assert dataset_response.status_code == 201, dataset_response.text
    dataset = dataset_response.json()
    assert client.post(f"/api/v1/datasets/{dataset['id']}/preview").status_code == 200
    mapped = client.post(
        f"/api/v1/datasets/{dataset['id']}/mappings",
        json={
            "fields": {
                "timestamp": "timestamp",
                "value": "pressure",
                "unit": "unit",
                "quality": "quality",
                "source": "source",
            },
            "dimensions": {"value": "pressure"},
        },
    )
    assert mapped.status_code == 200, mapped.text
    imported = client.post(
        f"/api/v1/datasets/{dataset['id']}/imports",
        headers={"Idempotency-Key": "dataset-time-series-v1"},
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["accepted_count"] == 3
    return dataset


def _tag(client: TestClient, organization_id: str, site_id: str, *, external_name: str) -> dict:
    response = client.post(
        "/api/v1/measurement-tags",
        json={
            "organization_id": organization_id,
            "site_id": site_id,
            "external_name": external_name,
            "name": "Pression refoulement station A",
            "measurement_type": "pressure",
            "dimension": "pressure",
            "source_unit": "bar",
            "source": "fichier-pilote",
            "metadata": {"absolute_pressure": True},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_time_series_import_keeps_raw_bad_sample_and_is_idempotent(
    time_series_client: TestClient,
) -> None:
    organization = _organization(time_series_client, slug="operateur-serie")
    site = _site(time_series_client, organization["id"], code="SITE-TS")
    project = _project(time_series_client, organization["id"], site["id"], code="PRJ-TS")
    dataset = _measurement_dataset(
        time_series_client,
        organization_id=organization["id"],
        project_id=project["id"],
    )
    tag = _tag(time_series_client, organization["id"], site["id"], external_name="PT-101")

    request = {"tag_id": tag["id"], "processing_version": "pilot-v1-a2"}
    first = time_series_client.post(
        f"/api/v1/datasets/{dataset['id']}/time-series-imports",
        json=request,
        headers={"Idempotency-Key": "ts-import-pt-101"},
    )
    assert first.status_code == 201, first.text
    assert first.json()["status"] == "completed"
    assert first.json()["row_count"] == 3
    assert first.json()["accepted_count"] == 3
    assert first.json()["rejected_count"] == 0

    replay = time_series_client.post(
        f"/api/v1/datasets/{dataset['id']}/time-series-imports",
        json=request,
        headers={"Idempotency-Key": "ts-import-pt-101"},
    )
    assert replay.status_code == 201, replay.text
    assert replay.json()["id"] == first.json()["id"]

    listed_tags = time_series_client.get(
        "/api/v1/measurement-tags",
        params={"organization_id": organization["id"], "site_id": site["id"]},
    )
    assert listed_tags.status_code == 200, listed_tags.text
    assert listed_tags.json()["total"] == 1
    assert listed_tags.json()["items"][0]["si_unit"] == "Pa"
    assert listed_tags.json()["items"][0]["metadata"] == {"absolute_pressure": True}

    samples = time_series_client.get(f"/api/v1/measurement-tags/{tag['id']}/samples")
    assert samples.status_code == 200, samples.text
    body = samples.json()
    assert body["total"] == 3
    assert [sample["value_si"] for sample in body["items"]] == pytest.approx(
        [1_000_000.0, 1_100_000.0, 1_200_000.0]
    )
    assert [sample["quality"] for sample in body["items"]] == ["good", "uncertain", "bad"]
    assert all(sample["source_unit"] == "bar" for sample in body["items"])
    assert body["items"][0]["source_value"] == "10"
    assert body["items"][0]["dataset_id"] == dataset["id"]

    other_tag = _tag(time_series_client, organization["id"], site["id"], external_name="PT-102")
    mismatched_source = time_series_client.post(
        f"/api/v1/datasets/{dataset['id']}/time-series-imports",
        json={"tag_id": other_tag["id"]},
        headers={"Idempotency-Key": "ts-import-pt-102"},
    )
    assert mismatched_source.status_code == 201, mismatched_source.text
    assert mismatched_source.json()["status"] == "completed_with_errors"
    assert mismatched_source.json()["accepted_count"] == 0
    assert mismatched_source.json()["rejected_count"] == 3
    assert mismatched_source.json()["errors"][0]["code"] == "TAG_SOURCE_MISMATCH"


def test_tag_and_dataset_must_respect_organization_site_hierarchy(
    time_series_client: TestClient,
) -> None:
    first_organization = _organization(time_series_client, slug="operateur-a")
    second_organization = _organization(time_series_client, slug="operateur-b")
    first_site = _site(time_series_client, first_organization["id"], code="SITE-A")
    second_site = _site(time_series_client, second_organization["id"], code="SITE-B")

    wrong_tag = time_series_client.post(
        "/api/v1/measurement-tags",
        json={
            "organization_id": first_organization["id"],
            "site_id": second_site["id"],
            "external_name": "PT-WRONG",
            "name": "Capteur invalide",
            "measurement_type": "pressure",
            "dimension": "pressure",
            "source_unit": "bar",
            "source": "test",
        },
    )
    assert wrong_tag.status_code == 409

    project = _project(
        time_series_client,
        first_organization["id"],
        first_site["id"],
        code="PRJ-A",
    )
    dataset = _measurement_dataset(
        time_series_client,
        organization_id=first_organization["id"],
        project_id=project["id"],
    )
    tag = _tag(
        time_series_client,
        second_organization["id"],
        second_site["id"],
        external_name="PT-B",
    )
    response = time_series_client.post(
        f"/api/v1/datasets/{dataset['id']}/time-series-imports",
        json={"tag_id": tag["id"]},
        headers={"Idempotency-Key": "ts-cross-organization"},
    )
    assert response.status_code == 409
    assert "même organisation" in response.json()["detail"]
