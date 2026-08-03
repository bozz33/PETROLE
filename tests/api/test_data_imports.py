"""Tests contractuels des imports CSV/XLSX et de leur lignage."""

from __future__ import annotations

from collections.abc import Generator
from io import BytesIO

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from hydro_api.application import create_application
from hydro_api.config import Settings
from hydro_api.database.base import Base
from hydro_api.database.session import get_session


@pytest.fixture
def import_client(tmp_path) -> Generator[TestClient, None, None]:
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


def _organization(import_client: TestClient) -> dict:
    response = import_client.post(
        "/api/v1/organizations",
        json={
            "name": "Société de transport",
            "slug": "societe-transport",
            "default_locale": "fr",
            "default_unit_system": "SI",
        },
    )
    assert response.status_code == 201
    return response.json()


def _upload(
    import_client: TestClient,
    organization_id: str,
    filename: str,
    content: bytes,
    media_type: str,
) -> dict:
    response = import_client.post(
        "/api/v1/files",
        data={"organization_id": organization_id},
        files={"file": (filename, content, media_type)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_csv_profile_import_keeps_raw_and_normalized_lineage(import_client) -> None:
    organization = _organization(import_client)
    content = b"PK;Altitude\n0;120,5\n1000;118,2\n2500;135,0\n"
    stored_file = _upload(
        import_client,
        organization["id"],
        "profil.csv",
        content,
        "text/csv",
    )

    dataset_response = import_client.post(
        "/api/v1/datasets",
        json={
            "organization_id": organization["id"],
            "file_id": stored_file["id"],
            "name": "Profil principal",
            "kind": "profile",
        },
    )
    assert dataset_response.status_code == 201
    dataset = dataset_response.json()

    preview_response = import_client.post(f"/api/v1/datasets/{dataset['id']}/preview")
    assert preview_response.status_code == 200, preview_response.text
    preview = preview_response.json()
    assert preview["columns"] == ["PK", "Altitude"]
    assert preview["row_count"] == 3

    mapping_response = import_client.post(
        f"/api/v1/datasets/{dataset['id']}/mappings",
        json={
            "fields": {
                "chainage_m": "PK",
                "elevation_m": "Altitude",
            }
        },
    )
    assert mapping_response.status_code == 200, mapping_response.text

    import_response = import_client.post(
        f"/api/v1/datasets/{dataset['id']}/imports",
        headers={"Idempotency-Key": "profil-v1"},
    )
    assert import_response.status_code == 201, import_response.text
    imported = import_response.json()
    assert imported["status"] == "completed"
    assert imported["accepted_count"] == 3
    assert imported["rejected_count"] == 0

    replay = import_client.post(
        f"/api/v1/datasets/{dataset['id']}/imports",
        headers={"Idempotency-Key": "profil-v1"},
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == imported["id"]

    rows_response = import_client.get(f"/api/v1/datasets/{dataset['id']}/rows")
    assert rows_response.status_code == 200
    rows = rows_response.json()
    assert rows["total"] == 3
    assert rows["items"][0]["source_row"] == 2
    assert rows["items"][0]["raw"]["Altitude"] == "120,5"
    assert rows["items"][0]["normalized"]["elevation_m"] == 120.5
    assert rows["items"][0]["corrected"] is None

    download = import_client.get(f"/api/v1/files/{stored_file['id']}/download")
    assert download.status_code == 200
    assert download.content == content
    audit = import_client.get(
        "/api/v1/audit-events",
        params={"organization_id": organization["id"], "action": "file.downloaded"},
    )
    assert audit.status_code == 200
    assert audit.json()["total"] == 1


def test_import_reports_invalid_number_and_non_monotonic_profile(import_client) -> None:
    organization = _organization(import_client)
    stored_file = _upload(
        import_client,
        organization["id"],
        "profil.csv",
        b"PK,Altitude\n0,120\n1000,invalide\n900,130\n",
        "text/csv",
    )
    dataset = import_client.post(
        "/api/v1/datasets",
        json={
            "organization_id": organization["id"],
            "file_id": stored_file["id"],
            "name": "Profil erroné",
            "kind": "profile",
        },
    ).json()
    import_client.post(f"/api/v1/datasets/{dataset['id']}/preview")
    import_client.post(
        f"/api/v1/datasets/{dataset['id']}/mappings",
        json={"fields": {"chainage_m": "PK", "elevation_m": "Altitude"}},
    )

    response = import_client.post(
        f"/api/v1/datasets/{dataset['id']}/imports",
        headers={"Idempotency-Key": "profil-erreur"},
    )

    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "completed_with_errors"
    assert result["rejected_count"] == 2
    codes = {error["code"] for error in result["errors"]}
    assert codes == {"INVALID_NUMBER", "NOT_STRICTLY_INCREASING"}

    errors = import_client.get(f"/api/v1/imports/{result['id']}/errors").json()
    assert errors["count"] == 2


def test_xlsx_strapping_preview_and_import(import_client) -> None:
    organization = _organization(import_client)
    output = BytesIO()
    pd.DataFrame(
        {
            "Niveau": [0.0, 1.0, 2.0],
            "Volume": [0.0, 80.0, 165.0],
        }
    ).to_excel(output, index=False)
    stored_file = _upload(
        import_client,
        organization["id"],
        "baremage.xlsx",
        output.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    dataset = import_client.post(
        "/api/v1/datasets",
        json={
            "organization_id": organization["id"],
            "file_id": stored_file["id"],
            "name": "Barémage bac 101",
            "kind": "strapping",
        },
    ).json()

    preview = import_client.post(f"/api/v1/datasets/{dataset['id']}/preview")
    assert preview.status_code == 200
    assert preview.json()["row_count"] == 3
    mapped = import_client.post(
        f"/api/v1/datasets/{dataset['id']}/mappings",
        json={"fields": {"level_m": "Niveau", "volume_m3": "Volume"}},
    )
    assert mapped.status_code == 200

    imported = import_client.post(
        f"/api/v1/datasets/{dataset['id']}/imports",
        headers={"Idempotency-Key": "baremage-v1"},
    )
    assert imported.status_code == 201
    assert imported.json()["accepted_count"] == 3


def test_mapping_rejects_missing_required_fields(import_client) -> None:
    organization = _organization(import_client)
    stored_file = _upload(
        import_client,
        organization["id"],
        "profil.csv",
        b"PK,Altitude\n0,120\n",
        "text/csv",
    )
    dataset = import_client.post(
        "/api/v1/datasets",
        json={
            "organization_id": organization["id"],
            "file_id": stored_file["id"],
            "name": "Profil incomplet",
            "kind": "profile",
        },
    ).json()
    import_client.post(f"/api/v1/datasets/{dataset['id']}/preview")

    response = import_client.post(
        f"/api/v1/datasets/{dataset['id']}/mappings",
        json={"fields": {"chainage_m": "PK"}},
    )

    assert response.status_code == 422
    assert "elevation_m" in response.json()["detail"]
