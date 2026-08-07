"""Tests contractuels des imports CSV/XLSX et de leur lignage."""

from __future__ import annotations

import json
from collections.abc import Generator
from io import BytesIO

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from hydro_api.services.data_import import _start_import_hash
from hydro_shared.hashing import canonical_json, sha256_of


@pytest.fixture
def import_client(api_client_factory) -> Generator[TestClient, None, None]:
    """Client d'import utilisant la base PostgreSQL transactionnelle du test."""

    with api_client_factory() as client:
        yield client


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


def test_import_hash_streaming_matches_canonical_hash() -> None:
    """Garantit que le traitement par lots ne change pas l'identité du jeu importé."""

    file_hash = "sha256:fichier"
    mapping = {"units": {"Débit": "m3/s"}, "fields": {"flow_m3_s": "Débit"}}
    rows = [
        {"flow_m3_s": 0.125, "quality": "good"},
        {"flow_m3_s": 0.25, "quality": "estimé"},
    ]
    digest = _start_import_hash(file_hash, mapping)
    for index, row in enumerate(rows):
        if index:
            digest.update(b",")
        digest.update(canonical_json(row).encode("utf-8"))
    digest.update(b"]}")

    expected = sha256_of({"file_hash": file_hash, "mapping": mapping, "rows": rows})
    assert f"sha256:{digest.hexdigest()}" == expected


def test_import_accepte_un_document_json(import_client) -> None:
    """Le MVP exige CSV, XLSX et JSON ; seuls les deux premiers étaient acceptés."""

    organization = _organization(import_client)
    document = json.dumps(
        {
            "points": [
                {"chainage_m": 0.0, "elevation_m": 10.0},
                {"chainage_m": 500.0, "elevation_m": 18.5},
                {"chainage_m": 1000.0, "elevation_m": 12.25},
            ]
        }
    ).encode("utf-8")
    stored_file = _upload(
        import_client,
        organization["id"],
        "profil.json",
        document,
        "application/json",
    )

    dataset = import_client.post(
        "/api/v1/datasets",
        json={
            "organization_id": organization["id"],
            "file_id": stored_file["id"],
            "name": "Profil importé en JSON",
            "kind": "profile",
        },
    )
    assert dataset.status_code == 201, dataset.text

    preview = import_client.post(f"/api/v1/datasets/{dataset.json()['id']}/preview")
    assert preview.status_code == 200, preview.text
    assert preview.json()["columns"] == ["chainage_m", "elevation_m"]
    assert preview.json()["row_count"] == 3


def test_import_json_refuse_une_forme_ambigue(import_client) -> None:
    """Deux listes candidates : le service refuse au lieu de deviner la bonne."""

    organization = _organization(import_client)
    document = json.dumps({"a": [{"x": 1}], "b": [{"y": 2}]}).encode("utf-8")
    stored_file = _upload(
        import_client,
        organization["id"],
        "ambigu.json",
        document,
        "application/json",
    )

    dataset = import_client.post(
        "/api/v1/datasets",
        json={
            "organization_id": organization["id"],
            "file_id": stored_file["id"],
            "name": "Document ambigu",
            "kind": "generic",
        },
    )
    assert dataset.status_code == 201, dataset.text

    preview = import_client.post(f"/api/v1/datasets/{dataset.json()['id']}/preview")
    assert preview.status_code == 422, preview.text


def test_piece_jointe_documentaire_est_separee_des_donnees(import_client) -> None:
    """Un plan PDF se stocke comme document, jamais comme tableau de données."""

    organization = _organization(import_client)
    pdf = b"%PDF-1.4\n%stub\n"

    document = import_client.post(
        "/api/v1/documents",
        data={"organization_id": organization["id"], "description": "Fiche constructeur"},
        files={"file": ("fiche.pdf", pdf, "application/pdf")},
    )
    assert document.status_code == 201, document.text
    body = document.json()
    assert body["purpose"] == "document"
    assert body["description"] == "Fiche constructeur"

    listing = import_client.get("/api/v1/documents", params={"organization_id": organization["id"]})
    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] == 1

    download = import_client.get(f"/api/v1/files/{body['id']}/download")
    assert download.status_code == 200
    assert download.content == pdf


def test_import_de_donnees_refuse_un_pdf(import_client) -> None:
    organization = _organization(import_client)

    response = import_client.post(
        "/api/v1/files",
        data={"organization_id": organization["id"]},
        files={"file": ("plan.pdf", b"%PDF-1.4\n", "application/pdf")},
    )

    assert response.status_code == 422, response.text


def test_piece_jointe_refuse_un_format_non_documentaire(import_client) -> None:
    organization = _organization(import_client)

    response = import_client.post(
        "/api/v1/documents",
        data={"organization_id": organization["id"]},
        files={"file": ("script.exe", b"MZ", "application/octet-stream")},
    )

    assert response.status_code == 422, response.text
