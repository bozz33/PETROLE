"""Tests contractuels du CRUD projet, versionnement et audit."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.factories import entree_canonique, pipeline, station_serie

from hydro_api.models import AuditEvent, CalculationRun, GeneratedReport, StoredFile


def create_organization(client: TestClient, slug: str = "operateur-nord") -> dict:
    response = client.post(
        "/api/v1/organizations",
        json={
            "name": "Opérateur Nord",
            "slug": slug,
            "default_locale": "fr",
            "default_unit_system": "SI",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_project(client: TestClient, organization_id: str) -> dict:
    response = client.post(
        "/api/v1/projects",
        json={
            "organization_id": organization_id,
            "name": "Oléoduc Nord",
            "code": "PL-NORD",
            "country_code": "dz",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_model(client: TestClient, project_id: str, name: str = "Baseline") -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/models",
        json={
            "name": name,
            "payload": {
                "network": {"pipeline_id": "PL-1"},
                "units": {"pressure": "Pa"},
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_workflow_projet_version_scenario(client):
    organization = create_organization(client)
    project = create_project(client, organization["id"])
    model = create_model(client, project["id"])

    scenario_response = client.post(
        f"/api/v1/models/{model['id']}/scenarios",
        json={
            "name": "Régime nominal",
            "payload": {
                "imposed_flow_m3_s": 0.5,
                "inlet_pressure_pa": 5_000_000,
            },
        },
    )
    assert scenario_response.status_code == 201
    scenario = scenario_response.json()

    assert project["country_code"] == "DZ"
    assert model["version_number"] == 1
    assert model["status"] == "draft"
    assert model["content_hash"].startswith("sha256:")
    assert len(model["content_hash"]) == 71
    assert scenario["model_version_id"] == model["id"]

    projects = client.get(
        "/api/v1/projects",
        params={"organization_id": organization["id"]},
    ).json()
    models = client.get(f"/api/v1/projects/{project['id']}/models").json()
    scenarios = client.get(f"/api/v1/models/{model['id']}/scenarios").json()

    assert projects["total"] == 1
    assert models["total"] == 1
    assert scenarios["total"] == 1
    assert scenarios["items"][0]["id"] == scenario["id"]

    clone_response = client.post(
        f"/api/v1/scenarios/{scenario['id']}/clone",
        json={"name": "Nominal dégradé"},
    )
    assert clone_response.status_code == 201, clone_response.text
    cloned_scenario = clone_response.json()
    assert cloned_scenario["parent_id"] == scenario["id"]
    assert cloned_scenario["payload"] == scenario["payload"]
    assert (
        client.patch(
            f"/api/v1/scenarios/{cloned_scenario['id']}",
            json={"payload": {"flow_m3_s": 0.3}},
        ).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/scenarios/{scenario['id']}").json()["payload"] == scenario["payload"]
    )


def test_cycle_de_vie_projet_et_restauration_du_statut(client, database_engine):
    organization = create_organization(client)
    project = create_project(client, organization["id"])

    direct_status = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "archived"},
    )
    assert direct_status.status_code == 422

    activated = client.post(f"/api/v1/projects/{project['id']}/activate")
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "active"
    assert client.post(f"/api/v1/projects/{project['id']}/activate").status_code == 409

    archived = client.post(f"/api/v1/projects/{project['id']}/archive")
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"
    assert client.post(f"/api/v1/projects/{project['id']}/archive").status_code == 409

    visible = client.get(
        "/api/v1/projects",
        params={"organization_id": organization["id"]},
    ).json()
    complete = client.get(
        "/api/v1/projects",
        params={"organization_id": organization["id"], "include_archived": True},
    ).json()
    assert visible["total"] == 0
    assert complete["total"] == 1
    assert complete["items"][0]["status"] == "archived"

    blocked_update = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"name": "Modification interdite"},
    )
    assert blocked_update.status_code == 409
    blocked_model = client.post(
        f"/api/v1/projects/{project['id']}/models",
        json={"name": "Version interdite"},
    )
    assert blocked_model.status_code == 409

    restored = client.post(f"/api/v1/projects/{project['id']}/restore")
    assert restored.status_code == 200, restored.text
    assert restored.json()["status"] == "active"
    assert client.post(f"/api/v1/projects/{project['id']}/restore").status_code == 409
    assert create_model(client, project["id"])["version_number"] == 1

    with Session(database_engine) as session:
        actions = set(
            session.scalars(
                select(AuditEvent.action).where(AuditEvent.object_id == uuid.UUID(project["id"]))
            )
        )
    assert {"project.activated", "project.archived", "project.restored"} <= actions


def test_numerotation_et_filiation_des_versions(client):
    organization = create_organization(client)
    project = create_project(client, organization["id"])
    first = create_model(client, project["id"], "Version initiale")

    second_response = client.post(
        f"/api/v1/projects/{project['id']}/models",
        json={
            "name": "Version corrigée",
            "parent_id": first["id"],
            "payload": {"network": {"revision": 2}},
        },
    )

    assert second_response.status_code == 201
    second = second_response.json()
    assert second["version_number"] == 2
    assert second["parent_id"] == first["id"]


def test_approbation_unique_et_immutabilite_scenario(client):
    organization = create_organization(client)
    project = create_project(client, organization["id"])
    first = create_model(client, project["id"], "Version 1")
    scenario = client.post(
        f"/api/v1/models/{first['id']}/scenarios",
        json={"name": "Nominal", "payload": {"flow_m3_s": 0.4}},
    ).json()

    approval = client.post(f"/api/v1/models/{first['id']}/approve")
    assert approval.status_code == 200
    assert approval.json()["status"] == "approved"
    assert approval.json()["approved_at"]

    mutation = client.patch(
        f"/api/v1/scenarios/{scenario['id']}",
        json={"payload": {"flow_m3_s": 0.5}},
    )
    assert mutation.status_code == 409
    assert mutation.headers["content-type"].startswith("application/problem+json")
    assert "immuable" in mutation.json()["detail"]

    second = create_model(client, project["id"], "Version 2")
    conflict = client.post(f"/api/v1/models/{second['id']}/approve")
    assert conflict.status_code == 409
    assert "déjà approuvée" in conflict.json()["detail"]

    archived = client.post(f"/api/v1/models/{first['id']}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert archived.json()["approved_at"].removesuffix("Z") == approval.json()[
        "approved_at"
    ].removesuffix("Z")
    still_immutable = client.patch(
        f"/api/v1/scenarios/{scenario['id']}",
        json={"payload": {"flow_m3_s": 0.6}},
    )
    assert still_immutable.status_code == 409
    assert client.post(f"/api/v1/models/{second['id']}/approve").status_code == 200
    forbidden_scenario = client.post(
        f"/api/v1/models/{second['id']}/scenarios",
        json={"name": "Ajout tardif"},
    )
    assert forbidden_scenario.status_code == 409


def test_conflit_unicite_retourne_409(client):
    create_organization(client, "meme-slug")

    response = client.post(
        "/api/v1/organizations",
        json={"name": "Doublon", "slug": "meme-slug"},
    )

    assert response.status_code == 409
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 409


def test_ressource_absente_retourne_probleme_json(client):
    response = client.get("/api/v1/projects/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"] == "urn:hydro:error:resource-not-found"
    assert response.json()["instance"].endswith("/projects/00000000-0000-0000-0000-000000000001")


def test_validation_du_contrat(client):
    response = client.post(
        "/api/v1/organizations",
        json={"name": "Slug invalide", "slug": "Contient Des Espaces"},
    )

    assert response.status_code == 422


def test_audit_append_only_cree_un_evenement_par_mutation(client, database_engine):
    organization = create_organization(client)
    project = create_project(client, organization["id"])
    model = create_model(client, project["id"])
    client.post(
        f"/api/v1/models/{model['id']}/scenarios",
        json={"name": "Nominal"},
    )
    client.post(f"/api/v1/projects/{project['id']}/activate")

    with Session(database_engine) as session:
        count = session.scalar(select(func.count()).select_from(AuditEvent))
        actions = list(session.scalars(select(AuditEvent.action).order_by(AuditEvent.created_at)))

    assert count == 5
    assert actions == [
        "organization.created",
        "project.created",
        "model_version.created",
        "scenario.created",
        "project.activated",
    ]


def test_schema_openapi_expose_les_ressources(client):
    schema = client.get("/api/v1/openapi.json").json()

    assert "/api/v1/organizations" in schema["paths"]
    assert "/api/v1/projects" in schema["paths"]
    assert "/api/v1/projects/{project_id}/models" in schema["paths"]
    assert "/api/v1/models/{model_id}/scenarios" in schema["paths"]


def create_calculable_scenario(client: TestClient) -> dict:
    """Crée un scénario adossé à un paquet de modèle réellement calculable."""

    organization = create_organization(client)
    project = create_project(client, organization["id"])
    canonical = entree_canonique(conduite=pipeline(stations=(station_serie(),))).payload()
    model_response = client.post(
        f"/api/v1/projects/{project['id']}/models",
        json={
            "name": "Modèle calculable",
            "payload": {
                "manifest": canonical["manifest"],
                "units": canonical["units"],
                "fluid": canonical["fluid"],
                "network": canonical["network"],
                "equipment": canonical["equipment"],
                "rules": canonical["rules"],
            },
        },
    )
    assert model_response.status_code == 201, model_response.text
    scenario_response = client.post(
        f"/api/v1/models/{model_response.json()['id']}/scenarios",
        json={
            "name": "Régime nominal",
            "payload": canonical["scenario"],
        },
    )
    assert scenario_response.status_code == 201, scenario_response.text
    return scenario_response.json()


def test_calcul_persistant_et_lecture_des_resultats(client):
    scenario = create_calculable_scenario(client)

    response = client.post(
        f"/api/v1/scenarios/{scenario['id']}/calculations",
        headers={"Idempotency-Key": "calcul-nominal-v1"},
        json={"engine": "long_distance_liquid"},
    )

    assert response.status_code == 202, response.text
    calculation = response.json()
    assert calculation["status"].startswith("SIM_")
    assert calculation["job_id"]
    assert calculation["phase"] == "completed"
    assert calculation["progress_percent"] == 100
    assert len(calculation["input_hash"]) == 71
    assert calculation["finished_at"] is not None

    state = client.get(f"/api/v1/calculations/{calculation['id']}")
    summary = client.get(f"/api/v1/calculations/{calculation['id']}/summary")
    results = client.get(f"/api/v1/calculations/{calculation['id']}/results")
    history = client.get(f"/api/v1/scenarios/{scenario['id']}/calculations")

    assert state.status_code == 200
    assert summary.status_code == 200
    assert results.status_code == 200
    assert history.status_code == 200
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["job_id"] == calculation["job_id"]
    assert summary.json()["summary"]["input_hash"] == calculation["input_hash"]
    assert "profile" not in summary.json()["summary"]
    assert results.json()["result"]["profile"]
    assert results.json()["result"]["explanation"]["summary"]
    assert isinstance(results.json()["result"]["physical_approvable"], bool)
    assert results.json()["result"]["compliance_status"] == "not_evaluated"
    assert results.json()["result"]["decision_eligible"] is False
    assert results.json()["diagnostics"]["method"]


def test_cle_d_idempotence_rejoue_le_meme_calcul(client, database_engine):
    scenario = create_calculable_scenario(client)
    path = f"/api/v1/scenarios/{scenario['id']}/calculations"
    headers = {"Idempotency-Key": "rejeu-stable"}

    first = client.post(path, headers=headers, json={})
    second = client.post(path, headers=headers, json={})

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    with Session(database_engine) as session:
        count = session.scalar(select(func.count()).select_from(CalculationRun))
    assert count == 1


def test_cle_d_idempotence_refuse_des_entrees_modifiees(client):
    scenario = create_calculable_scenario(client)
    path = f"/api/v1/scenarios/{scenario['id']}/calculations"
    headers = {"Idempotency-Key": "rejeu-entrees-figees"}
    first = client.post(path, headers=headers, json={})
    assert first.status_code == 202

    changed_payload = {**scenario["payload"], "imposed_flow_m3_s": 0.31}
    changed = client.patch(
        f"/api/v1/scenarios/{scenario['id']}",
        json={"payload": changed_payload},
    )
    assert changed.status_code == 200, changed.text

    conflict = client.post(path, headers=headers, json={})

    assert conflict.status_code == 409
    assert "entrées canoniques différents" in conflict.json()["detail"]


def test_calcul_exige_une_cle_d_idempotence(client):
    scenario = create_calculable_scenario(client)

    response = client.post(
        f"/api/v1/scenarios/{scenario['id']}/calculations",
        json={},
    )

    assert response.status_code == 422


def test_modele_de_calcul_incomplet_retourne_un_probleme_422(client):
    organization = create_organization(client)
    project = create_project(client, organization["id"])
    model = create_model(client, project["id"])
    scenario = client.post(
        f"/api/v1/models/{model['id']}/scenarios",
        json={
            "name": "Scénario incomplet",
            "payload": {
                "imposed_flow_m3_s": 0.2,
                "inlet_pressure_pa": 5_000_000,
            },
        },
    ).json()

    response = client.post(
        f"/api/v1/scenarios/{scenario['id']}/calculations",
        headers={"Idempotency-Key": "modele-incomplet"},
        json={},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "ERR_SCENARIO_INVALID"


def create_persisted_calculation(client: TestClient) -> dict:
    scenario = create_calculable_scenario(client)
    response = client.post(
        f"/api/v1/scenarios/{scenario['id']}/calculations",
        headers={"Idempotency-Key": "calcul-pour-rapport"},
        json={},
    )
    assert response.status_code == 202, response.text
    return response.json()


def test_generation_telechargement_et_approbation_du_rapport(
    client,
    database_engine,
):
    calculation = create_persisted_calculation(client)
    path = f"/api/v1/calculations/{calculation['id']}/reports"
    headers = {"Idempotency-Key": "rapport-rpt-02-v1"}

    first = client.post(path, headers=headers, json={})
    replay = client.post(path, headers=headers, json={})

    assert first.status_code == 201, first.text
    assert replay.status_code == 201
    report = first.json()
    assert replay.json()["id"] == report["id"]
    assert report["status"] == "generated"
    assert report["content_hash"].startswith("sha256:")

    metadata = client.get(f"/api/v1/reports/{report['id']}")
    listed = client.get(
        "/api/v1/reports",
        params={"calculation_id": calculation["id"]},
    )
    download = client.get(f"/api/v1/reports/{report['id']}/download")
    assert metadata.status_code == 200
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == report["id"]
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert "attachment;" in download.headers["content-disposition"]
    assert download.content.startswith(b"%PDF-")
    assert len(download.content) > 50_000

    forbidden_approval = client.post(
        f"/api/v1/reports/{report['id']}/approve",
        json={"decision": "approved", "comment": "Revue technique terminée."},
    )
    assert forbidden_approval.status_code == 409
    assert "not_evaluated" in forbidden_approval.text

    rejection = client.post(
        f"/api/v1/reports/{report['id']}/approve",
        json={"decision": "rejected", "comment": "Conformité normative non établie."},
    )
    assert rejection.status_code == 200
    assert rejection.json()["status"] == "rejected"
    assert rejection.json()["approved_at"]

    contradictory = client.post(
        f"/api/v1/reports/{report['id']}/approve",
        json={"decision": "approved", "comment": "Décision différente."},
    )
    assert contradictory.status_code == 409

    with Session(database_engine) as session:
        report_count = session.scalar(select(func.count()).select_from(GeneratedReport))
        file_count = session.scalar(select(func.count()).select_from(StoredFile))
        download_audit_count = session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.action == "report.downloaded")
        )
    assert report_count == 1
    assert file_count == 1
    assert download_audit_count == 1
