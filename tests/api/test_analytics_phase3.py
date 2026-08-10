"""Tests PostgreSQL du premier sous-lot Phase 3 analytics."""

from __future__ import annotations

import hashlib
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def analytics_client(api_client_factory) -> Generator[TestClient, None, None]:
    with api_client_factory() as client:
        yield client


def test_phase3_analytics_buckets_exclude_bad_without_mutation(
    analytics_client: TestClient,
) -> None:
    organization = analytics_client.post(
        "/api/v1/organizations",
        json={
            "name": "Opérateur Analytics",
            "slug": "operateur-analytics",
            "default_locale": "fr",
            "default_unit_system": "SI",
        },
    )
    assert organization.status_code == 201, organization.text
    organization_id = organization.json()["id"]

    site = analytics_client.post(
        "/api/v1/sites",
        json={"organization_id": organization_id, "name": "Site Analytics", "code": "SITE-AN"},
    )
    assert site.status_code == 201, site.text
    site_id = site.json()["id"]

    project = analytics_client.post(
        "/api/v1/projects",
        json={
            "organization_id": organization_id,
            "site_id": site_id,
            "name": "Projet Analytics",
            "code": "PRJ-AN",
            "project_type": "liquid_pipeline",
        },
    )
    assert project.status_code == 201, project.text

    content = (
        b"timestamp;pressure;unit;quality;source\n"
        b"2026-08-09T10:00:00Z;10;bar;good;PT-301\n"
        b"2026-08-09T10:01:00Z;11;bar;good;PT-301\n"
        b"2026-08-09T10:02:00Z;12;bar;bad;PT-301\n"
        b"2026-08-09T10:03:00Z;13;bar;good;PT-301\n"
    )
    uploaded = analytics_client.post(
        "/api/v1/files",
        data={"organization_id": organization_id},
        files={"file": ("analytics.csv", content, "text/csv")},
    )
    assert uploaded.status_code == 201, uploaded.text

    dataset = analytics_client.post(
        "/api/v1/datasets",
        json={
            "organization_id": organization_id,
            "project_id": project.json()["id"],
            "file_id": uploaded.json()["id"],
            "name": "Série analytics",
            "kind": "measurements",
        },
    )
    assert dataset.status_code == 201, dataset.text
    dataset_id = dataset.json()["id"]
    assert analytics_client.post(f"/api/v1/datasets/{dataset_id}/preview").status_code == 200
    mapping = analytics_client.post(
        f"/api/v1/datasets/{dataset_id}/mappings",
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
    assert mapping.status_code == 200, mapping.text
    imported = analytics_client.post(
        f"/api/v1/datasets/{dataset_id}/imports",
        headers={"Idempotency-Key": "dataset-phase3-analytics"},
    )
    assert imported.status_code == 201, imported.text

    tag = analytics_client.post(
        "/api/v1/measurement-tags",
        json={
            "organization_id": organization_id,
            "site_id": site_id,
            "external_name": "PT-301",
            "name": "Pression Phase 3",
            "measurement_type": "pressure",
            "dimension": "pressure",
            "source_unit": "bar",
            "source": "fichier-pilote",
        },
    )
    assert tag.status_code == 201, tag.text
    tag_id = tag.json()["id"]

    projected = analytics_client.post(
        f"/api/v1/datasets/{dataset_id}/time-series-imports",
        json={"tag_id": tag_id, "processing_version": "phase3-test-v1"},
        headers={"Idempotency-Key": "phase3-series-v1"},
    )
    assert projected.status_code == 201, projected.text

    analytics_params = {
        "processing_version": "phase3-test-v1",
        "bucket_seconds": 120,
        "expected_interval_seconds": 60,
    }
    analytics_response = analytics_client.get(
        f"/api/v1/analytics/measurement-tags/{tag_id}/series",
        params=analytics_params,
    )
    assert analytics_response.status_code == 200, analytics_response.text
    body = analytics_response.json()
    assert body["candidate_sample_count"] == 4
    assert body["included_sample_count"] == 3
    assert body["excluded_sample_count"] == 1
    assert body["si_unit"] == "Pa"
    assert [bucket["sample_count"] for bucket in body["buckets"]] == [2, 1]
    assert [bucket["completeness_ratio"] for bucket in body["buckets"]] == pytest.approx([1.0, 0.5])
    assert body["buckets"][0]["mean_value_si"] == pytest.approx(1_050_000.0)
    assert body["buckets"][1]["mean_value_si"] == pytest.approx(1_300_000.0)
    assert body["trend"]["sample_count"] == 3
    assert body["trend"]["slope_si_per_second"] == pytest.approx(1666.6666667)

    json_export = analytics_client.get(
        f"/api/v1/analytics/measurement-tags/{tag_id}/series/export.json",
        params=analytics_params,
    )
    assert json_export.status_code == 200, json_export.text
    assert json_export.headers["content-disposition"] == 'attachment; filename="analytics.json"'
    assert json_export.headers["x-content-sha256"] == hashlib.sha256(json_export.content).hexdigest()
    exported_json = json_export.json()
    assert exported_json["export_version"] == "phase3-analytics/1.0"
    assert exported_json["processing_version"] == "phase3-test-v1"
    assert exported_json["si_unit"] == "Pa"
    assert exported_json["included_sample_count"] == 3
    assert [bucket["sample_count"] for bucket in exported_json["buckets"]] == [2, 1]

    csv_export = analytics_client.get(
        f"/api/v1/analytics/measurement-tags/{tag_id}/series/export.csv",
        params=analytics_params,
    )
    assert csv_export.status_code == 200, csv_export.text
    assert csv_export.headers["content-disposition"] == (
        'attachment; filename="analytics-buckets.csv"'
    )
    assert csv_export.headers["x-content-sha256"] == hashlib.sha256(csv_export.content).hexdigest()
    csv_text = csv_export.content.decode("utf-8-sig")
    assert csv_text.startswith("start_timestamp;end_timestamp;sample_count;")
    assert "1050000.0" in csv_text
    assert "1300000.0" in csv_text

    # L'analyse et ses exports ne suppriment pas la mesure bad : la projection reste complète.
    samples = analytics_client.get(
        f"/api/v1/measurement-tags/{tag_id}/samples",
        params={"processing_version": "phase3-test-v1"},
    )
    assert samples.status_code == 200, samples.text
    assert samples.json()["total"] == 4
