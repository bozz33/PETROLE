"""Tests API des réservoirs, transferts, comparaisons et optimisations."""

from __future__ import annotations

import time
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from tests.factories import (
    brut_leger,
    entree_canonique,
    pipeline,
    scenario,
    station_serie,
)


@pytest.fixture
def operations_client(api_client_factory) -> Generator[TestClient, None, None]:
    """Client métier isolé par la transaction PostgreSQL du test."""

    with api_client_factory() as client:
        yield client


def _organization(client: TestClient, slug: str = "exploitant-integre") -> dict:
    response = client.post(
        "/api/v1/organizations",
        json={"name": "Exploitant " + slug, "slug": slug},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _project(client: TestClient, organization_id: str) -> dict:
    response = client.post(
        "/api/v1/projects",
        json={
            "organization_id": organization_id,
            "name": "Chaîne logistique",
            "code": "LOG-01",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _tank(
    client: TestClient,
    organization_id: str,
    *,
    code: str,
    level_m: float,
    fluid_id: str | None,
    compatible: list[str],
) -> dict:
    response = client.post(
        "/api/v1/tanks",
        json={
            "organization_id": organization_id,
            "name": "Bac " + code,
            "code": code,
            "current_level_m": level_m,
            "fluid_id": fluid_id,
            "compatible_fluid_ids": compatible,
            "levels": {
                "minimum_m": 1.0,
                "low_m": 1.5,
                "normal_m": 5.0,
                "high_m": 7.0,
                "high_high_m": 9.0,
            },
            "strapping": [
                {"height_m": 0.0, "volume_m3": 0.0},
                {"height_m": 5.0, "volume_m3": 500.0},
                {"height_m": 10.0, "volume_m3": 1_000.0},
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _calculation(
    client: TestClient,
    project_id: str,
    canonical: dict,
    suffix: str,
) -> tuple[dict, dict]:
    model = client.post(
        f"/api/v1/projects/{project_id}/models",
        json={
            "name": "Modèle " + suffix,
            "payload": {
                "units": canonical["units"],
                "fluid": canonical["fluid"],
                "network": canonical["network"],
                "equipment": canonical["equipment"],
                "rules": canonical["rules"],
            },
        },
    )
    assert model.status_code == 201, model.text
    scenario_response = client.post(
        f"/api/v1/models/{model.json()['id']}/scenarios",
        json={
            "name": "Scénario " + suffix,
            "payload": canonical["scenario"],
        },
    )
    assert scenario_response.status_code == 201, scenario_response.text
    calculation = client.post(
        f"/api/v1/scenarios/{scenario_response.json()['id']}/calculations",
        headers={"Idempotency-Key": "calcul-" + suffix},
        json={"engine": "long_distance_liquid"},
    )
    assert calculation.status_code == 202, calculation.text
    return scenario_response.json(), calculation.json()


def _report(
    client: TestClient,
    report_type: str,
    source_id: str,
    key: str,
) -> dict:
    response = client.post(
        "/api/v1/reports",
        headers={"Idempotency-Key": key},
        json={"report_type": report_type, "source_id": source_id},
    )
    assert response.status_code == 201, response.text
    report = response.json()
    download = client.get(f"/api/v1/reports/{report['id']}/download")
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")
    return report


def test_cycle_complet_reservoir_transfert_et_bilan(operations_client) -> None:
    organization = _organization(operations_client)
    source = _tank(
        operations_client,
        organization["id"],
        code="TK-S",
        level_m=8.0,
        fluid_id="diesel",
        compatible=[],
    )
    destination = _tank(
        operations_client,
        organization["id"],
        code="TK-D",
        level_m=2.0,
        fluid_id=None,
        compatible=["diesel"],
    )

    assert source["current_volume_m3"] == pytest.approx(800.0)
    assert destination["available_capacity_m3"] == pytest.approx(700.0)

    transfer = operations_client.post(
        f"/api/v1/organizations/{organization['id']}/transfers",
        headers={"Idempotency-Key": "transfert-001"},
        json={
            "source_tank_id": source["id"],
            "destination_tank_id": destination["id"],
            "fluid_id": "diesel",
            "requested_flow_m3_s": 0.1,
            "target_volume_m3": 100.0,
            "time_step_s": 333.0,
            "loss_fraction": 0.01,
            "absorbed_power_w": 50_000.0,
        },
    )
    assert transfer.status_code == 201, transfer.text
    result = transfer.json()["result_payload"]
    assert result["stop_reason"] == "target_volume_reached"
    assert result["duration_s"] == pytest.approx(1_000.0)
    assert result["withdrawn_volume_m3"] == pytest.approx(100.0)
    assert result["received_volume_m3"] == pytest.approx(99.0)
    assert result["energy_j"] == pytest.approx(50_000_000.0)

    replay = operations_client.post(
        f"/api/v1/organizations/{organization['id']}/transfers",
        headers={"Idempotency-Key": "transfert-001"},
        json={
            "source_tank_id": source["id"],
            "destination_tank_id": destination["id"],
            "fluid_id": "diesel",
            "requested_flow_m3_s": 0.1,
            "target_volume_m3": 100.0,
            "time_step_s": 333.0,
            "loss_fraction": 0.01,
            "absorbed_power_w": 50_000.0,
        },
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == transfer.json()["id"]
    transfers = operations_client.get(
        f"/api/v1/organizations/{organization['id']}/transfers",
        params={"tank_id": source["id"]},
    )
    assert transfers.status_code == 200
    assert transfers.json()["total"] == 1
    assert transfers.json()["items"][0]["id"] == transfer.json()["id"]

    balance = operations_client.post(
        f"/api/v1/transfers/{transfer.json()['id']}/balance",
        json={
            "source_opening": {"value_m3": 800.0, "standard_uncertainty_m3": 1.0},
            "source_closing": {"value_m3": 700.0, "standard_uncertainty_m3": 1.0},
            "destination_opening": {"value_m3": 200.0, "standard_uncertainty_m3": 1.0},
            "destination_closing": {"value_m3": 299.0, "standard_uncertainty_m3": 1.0},
            "metered_volume": {"value_m3": 100.0, "standard_uncertainty_m3": 0.5},
            "accounted_losses": {"value_m3": 1.0, "standard_uncertainty_m3": 0.2},
        },
    )
    assert balance.status_code == 200, balance.text
    assert balance.json()["system_imbalance_m3"] == pytest.approx(0.0)
    assert balance.json()["within_tolerance"] is True

    transfer_report = _report(
        operations_client,
        "transfer_simulation",
        transfer.json()["id"],
        "rapport-transfert-001",
    )
    balance_report = _report(
        operations_client,
        "material_balance",
        transfer.json()["id"],
        "rapport-bilan-001",
    )
    assert transfer_report["template_version"] == "rpt-05/1.0"
    assert balance_report["template_version"] == "rpt-06/1.0"

    tanks = operations_client.get(
        "/api/v1/tanks",
        params={"organization_id": organization["id"]},
    )
    assert tanks.status_code == 200
    assert tanks.json()["total"] == 2


def test_baremage_non_monotone_est_refuse(operations_client) -> None:
    organization = _organization(operations_client)
    response = operations_client.post(
        "/api/v1/tanks",
        json={
            "organization_id": organization["id"],
            "name": "Bac invalide",
            "code": "TK-X",
            "current_level_m": 1.0,
            "levels": {"minimum_m": 0.0, "high_high_m": 2.0},
            "strapping": [
                {"height_m": 0.0, "volume_m3": 0.0},
                {"height_m": 2.0, "volume_m3": 10.0},
                {"height_m": 1.0, "volume_m3": 20.0},
            ],
        },
    )
    assert response.status_code == 422


@pytest.mark.performance
def test_comparaison_persistante_de_calculs(operations_client) -> None:
    organization = _organization(operations_client)
    project = _project(operations_client, organization["id"])
    first_input = entree_canonique(
        cas=scenario(imposed_flow_m3_s=0.15, inlet_pressure_pa=5_000_000.0)
    ).payload()
    second_input = entree_canonique(
        cas=scenario(imposed_flow_m3_s=0.20, inlet_pressure_pa=5_000_000.0)
    ).payload()
    _, first = _calculation(operations_client, project["id"], first_input, "A")
    _, second = _calculation(operations_client, project["id"], second_input, "B")

    started = time.perf_counter()
    response = operations_client.post(
        f"/api/v1/projects/{project['id']}/comparisons",
        headers={"Idempotency-Key": "comparaison-001"},
        json={"calculation_ids": [first["id"], second["id"]]},
    )
    comparison_duration_s = time.perf_counter() - started
    assert response.status_code == 201, response.text
    assert comparison_duration_s < 60.0
    comparison = response.json()
    assert comparison["result_payload"]["reference_calculation_id"] == first["id"]
    assert len(comparison["result_payload"]["ranked"]) == 2
    assert comparison["content_hash"].startswith("sha256:")
    comparisons = operations_client.get(f"/api/v1/projects/{project['id']}/comparisons")
    assert comparisons.status_code == 200
    assert comparisons.json()["total"] == 1
    assert comparisons.json()["items"][0]["id"] == comparison["id"]

    project_report = _report(
        operations_client,
        "project_sheet",
        project["id"],
        "rapport-projet-001",
    )
    comparison_report = _report(
        operations_client,
        "scenario_comparison",
        comparison["id"],
        "rapport-comparaison-001",
    )
    station_report = _report(
        operations_client,
        "station_pumps",
        first["id"],
        "rapport-station-001",
    )
    assert project_report["template_version"] == "rpt-01/1.0"
    assert comparison_report["template_version"] == "rpt-03/1.0"
    assert station_report["template_version"] == "rpt-04/1.0"


def test_optimisation_evalue_les_configurations_du_modele(operations_client) -> None:
    organization = _organization(operations_client)
    project = _project(operations_client, organization["id"])
    canonical = entree_canonique(
        conduite=pipeline(stations=(station_serie(nombre_de_pompes=2),)),
        cas=scenario(imposed_flow_m3_s=0.2, inlet_pressure_pa=3_000_000.0),
    ).payload()
    scenario_record, _ = _calculation(
        operations_client,
        project["id"],
        canonical,
        "OPT",
    )

    response = operations_client.post(
        f"/api/v1/scenarios/{scenario_record['id']}/optimizations",
        headers={"Idempotency-Key": "optimisation-001"},
        json={
            "objective": "min_energy",
            "speed_options": [0.8, 1.0],
            "reference_duration_s": 3_600.0,
            "constraints": {"minimum_flow_m3_s": 0.19},
        },
    )
    assert response.status_code == 201, response.text
    optimization = response.json()
    assert optimization["engine_version"].startswith("long_distance_liquid-")
    assert optimization["result_payload"]["generated_count"] == 8
    assert optimization["result_payload"]["evaluated_count"] > 0
    assert optimization["input_hash"].startswith("sha256:")
    optimizations = operations_client.get(
        f"/api/v1/scenarios/{scenario_record['id']}/optimizations"
    )
    assert optimizations.status_code == 200
    assert optimizations.json()["total"] == 1
    assert optimizations.json()["items"][0]["id"] == optimization["id"]


# --- Transfert couplé au réseau hydraulique (MVP-F05) -------------------------


def _network_transfer_fixture(client: TestClient, suffix: str = "a") -> dict:
    """Construit un exploitant, deux bacs, un modèle réseau et son scénario.

    Les deux nœuds d'extrémité déclarent explicitement le réservoir qu'ils
    raccordent : sans cette liaison, le transfert ne peut pas être rattaché au
    réseau de façon déterministe.
    """

    organization = _organization(client, slug="exploitant-hydraulique-" + suffix)
    project = _project(client, organization["id"])

    source_tank = _tank(
        client,
        organization["id"],
        code="TK-NS-" + suffix.upper(),
        level_m=8.0,
        fluid_id="diesel",
        compatible=[],
    )
    destination_tank = _tank(
        client,
        organization["id"],
        code="TK-ND-" + suffix.upper(),
        level_m=2.0,
        fluid_id=None,
        compatible=["diesel"],
    )

    canonical = entree_canonique(
        cas=scenario(imposed_flow_m3_s=0.15, inlet_pressure_pa=5_000_000.0)
    ).payload()
    fluid = client.post(
        "/api/v1/catalog/fluids",
        json={
            "organization_id": organization["id"],
            "code": "BRUT-TRANSFERT-" + suffix.upper(),
            "name": "Brut du transfert couplé",
            "payload": brut_leger().as_dict(),
            "source": "Analyse laboratoire",
        },
    )
    assert fluid.status_code == 201, fluid.text
    fluid_approval = client.post(f"/api/v1/catalog/items/{fluid.json()['id']}/approve")
    assert fluid_approval.status_code == 200, fluid_approval.text

    model = client.post(
        f"/api/v1/projects/{project['id']}/models",
        json={
            "name": "Modèle réseau transfert",
            "payload": {
                "units": canonical["units"],
                "fluid_catalog_item_id": fluid_approval.json()["id"],
                "rules": canonical["rules"],
            },
        },
    )
    assert model.status_code == 201, model.text
    model_id = model.json()["id"]

    source_node = client.post(
        f"/api/v1/models/{model_id}/nodes",
        json={
            "code": "ND-S",
            "name": "Piquage bac source",
            "kind": "tank",
            "elevation_m": 10.0,
            "payload": {"tank_id": source_tank["id"]},
        },
    )
    assert source_node.status_code == 201, source_node.text
    middle_node = client.post(
        f"/api/v1/models/{model_id}/nodes",
        json={"code": "ND-J", "name": "Jonction", "kind": "junction", "elevation_m": 5.0},
    )
    assert middle_node.status_code == 201, middle_node.text
    destination_node = client.post(
        f"/api/v1/models/{model_id}/nodes",
        json={
            "code": "ND-D",
            "name": "Piquage bac destination",
            "kind": "tank",
            "elevation_m": 2.0,
            "payload": {"tank_id": destination_tank["id"]},
        },
    )
    assert destination_node.status_code == 201, destination_node.text

    def _edge(code: str, sequence: int, start: dict, end: dict) -> dict:
        response = client.post(
            f"/api/v1/models/{model_id}/edges",
            json={
                "from_node_id": start["id"],
                "to_node_id": end["id"],
                "code": code,
                "name": "Tronçon " + code,
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

    first = _edge("TR-1", 1, source_node.json(), middle_node.json())
    second = _edge("TR-2", 2, middle_node.json(), destination_node.json())

    scenario_response = client.post(
        f"/api/v1/models/{model_id}/scenarios",
        json={"name": "Transfert nominal", "payload": canonical["scenario"]},
    )
    assert scenario_response.status_code == 201, scenario_response.text

    return {
        "organization": organization,
        "project": project,
        "source_tank": source_tank,
        "destination_tank": destination_tank,
        "model_id": model_id,
        "source_node": source_node.json(),
        "middle_node": middle_node.json(),
        "destination_node": destination_node.json(),
        "edges": [first, second],
        "scenario": scenario_response.json(),
    }


def _transfer_body(fixture: dict, **overrides) -> dict:
    body = {
        "source_tank_id": fixture["source_tank"]["id"],
        "destination_tank_id": fixture["destination_tank"]["id"],
        "fluid_id": "diesel",
        "requested_flow_m3_s": 0.1,
        "target_volume_m3": 50.0,
        "time_step_s": 120.0,
        "hydraulic_context": {
            "model_version_id": fixture["model_id"],
            "scenario_id": fixture["scenario"]["id"],
            "source_node_id": fixture["source_node"]["id"],
            "destination_node_id": fixture["destination_node"]["id"],
            "path_edge_ids": [edge["id"] for edge in fixture["edges"]],
            "pump_asset_ids": [],
            "level_step_m": 0.02,
        },
    }
    body.update(overrides)
    return body


def test_transfert_couple_publie_sa_filiation_hydraulique(operations_client) -> None:
    """Le débit provient du réseau et la filiation est enregistrée en base."""

    fixture = _network_transfer_fixture(operations_client)

    response = operations_client.post(
        f"/api/v1/organizations/{fixture['organization']['id']}/transfers",
        headers={"Idempotency-Key": "transfert-hydraulique-001"},
        json=_transfer_body(fixture),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    coupling = body["result_payload"]["hydraulic_coupling"]
    assert coupling["scenario_id"] == fixture["scenario"]["id"]
    assert coupling["model_version_id"] == fixture["model_id"]
    assert coupling["engine_version"].startswith("long_distance_liquid-")
    assert coupling["path_edge_ids"] == [edge["id"] for edge in fixture["edges"]]
    assert coupling["evaluations"] >= 1


def test_transfert_sans_contexte_conserve_le_comportement_historique(operations_client) -> None:
    """L'ancien contrat reste accepté et produit exactement le même résultat."""

    organization = _organization(operations_client, slug="exploitant-historique")
    source = _tank(
        operations_client,
        organization["id"],
        code="TK-HS2",
        level_m=8.0,
        fluid_id="diesel",
        compatible=[],
    )
    destination = _tank(
        operations_client,
        organization["id"],
        code="TK-HD2",
        level_m=2.0,
        fluid_id=None,
        compatible=["diesel"],
    )

    response = operations_client.post(
        f"/api/v1/organizations/{organization['id']}/transfers",
        headers={"Idempotency-Key": "transfert-historique-001"},
        json={
            "source_tank_id": source["id"],
            "destination_tank_id": destination["id"],
            "fluid_id": "diesel",
            "requested_flow_m3_s": 0.1,
            "target_volume_m3": 100.0,
            "time_step_s": 333.0,
            "loss_fraction": 0.01,
            "absorbed_power_w": 50_000.0,
        },
    )

    assert response.status_code == 201, response.text
    result = response.json()["result_payload"]
    assert result["stop_reason"] == "target_volume_reached"
    assert result["duration_s"] == pytest.approx(1_000.0)
    assert result["withdrawn_volume_m3"] == pytest.approx(100.0)
    assert result["energy_j"] == pytest.approx(50_000_000.0)
    assert "hydraulic_coupling" not in result


def test_transfert_couple_refuse_les_grandeurs_calculees(operations_client) -> None:
    """Pression de refoulement et puissance sont des sorties, pas des entrées."""

    fixture = _network_transfer_fixture(operations_client)

    response = operations_client.post(
        f"/api/v1/organizations/{fixture['organization']['id']}/transfers",
        headers={"Idempotency-Key": "transfert-hydraulique-002"},
        json=_transfer_body(fixture, absorbed_power_w=50_000.0),
    )

    assert response.status_code == 422, response.text


def test_transfert_refuse_un_chemin_discontinu(operations_client) -> None:
    fixture = _network_transfer_fixture(operations_client)
    body = _transfer_body(fixture)
    # Le second tronçon seul ne part pas du nœud source.
    body["hydraulic_context"]["path_edge_ids"] = [fixture["edges"][1]["id"]]

    response = operations_client.post(
        f"/api/v1/organizations/{fixture['organization']['id']}/transfers",
        headers={"Idempotency-Key": "transfert-hydraulique-003"},
        json=body,
    )

    assert response.status_code == 409, response.text
    assert "discontinu" in response.json()["detail"]


def test_transfert_refuse_un_chemin_qui_n_aboutit_pas(operations_client) -> None:
    fixture = _network_transfer_fixture(operations_client)
    body = _transfer_body(fixture)
    body["hydraulic_context"]["path_edge_ids"] = [fixture["edges"][0]["id"]]

    response = operations_client.post(
        f"/api/v1/organizations/{fixture['organization']['id']}/transfers",
        headers={"Idempotency-Key": "transfert-hydraulique-004"},
        json=body,
    )

    assert response.status_code == 409, response.text
    assert "aboutit" in response.json()["detail"]


def test_transfert_refuse_un_noeud_ne_raccordant_pas_le_bac(operations_client) -> None:
    fixture = _network_transfer_fixture(operations_client)
    body = _transfer_body(fixture)
    # La jonction ne déclare aucun réservoir raccordé.
    body["hydraulic_context"]["source_node_id"] = fixture["middle_node"]["id"]
    body["hydraulic_context"]["path_edge_ids"] = [fixture["edges"][1]["id"]]

    response = operations_client.post(
        f"/api/v1/organizations/{fixture['organization']['id']}/transfers",
        headers={"Idempotency-Key": "transfert-hydraulique-005"},
        json=body,
    )

    assert response.status_code == 409, response.text
    assert "raccordement" in response.json()["detail"]


def test_transfert_refuse_un_scenario_d_une_autre_version(operations_client) -> None:
    fixture = _network_transfer_fixture(operations_client)
    other = _network_transfer_fixture(operations_client, suffix="b")
    body = _transfer_body(fixture)
    body["hydraulic_context"]["scenario_id"] = other["scenario"]["id"]

    response = operations_client.post(
        f"/api/v1/organizations/{fixture['organization']['id']}/transfers",
        headers={"Idempotency-Key": "transfert-hydraulique-006"},
        json=body,
    )

    assert response.status_code == 409, response.text


def test_transfert_change_d_empreinte_avec_le_chemin(operations_client) -> None:
    """Changer le chemin ou le scénario doit produire un autre transfert."""

    fixture = _network_transfer_fixture(operations_client)

    first = operations_client.post(
        f"/api/v1/organizations/{fixture['organization']['id']}/transfers",
        headers={"Idempotency-Key": "transfert-hydraulique-007"},
        json=_transfer_body(fixture),
    )
    assert first.status_code == 201, first.text

    replay = operations_client.post(
        f"/api/v1/organizations/{fixture['organization']['id']}/transfers",
        headers={"Idempotency-Key": "transfert-hydraulique-007"},
        json=_transfer_body(fixture),
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == first.json()["id"]

    changed = _transfer_body(fixture)
    changed["hydraulic_context"]["level_step_m"] = 0.5
    conflict = operations_client.post(
        f"/api/v1/organizations/{fixture['organization']['id']}/transfers",
        headers={"Idempotency-Key": "transfert-hydraulique-007"},
        json=changed,
    )
    assert conflict.status_code == 409, conflict.text


def test_export_des_resultats_en_xlsx_csv_et_json(operations_client) -> None:
    """Le MVP exige PDF, XLSX, CSV et JSON ; seul le PDF existait."""

    organization = _organization(operations_client, slug="exploitant-exports")
    project = _project(operations_client, organization["id"])
    canonical = entree_canonique(
        conduite=pipeline(stations=(station_serie(),)),
        cas=scenario(imposed_flow_m3_s=0.15, inlet_pressure_pa=5_000_000.0),
    ).payload()
    _, calculation = _calculation(operations_client, project["id"], canonical, "EXP")

    workbook = operations_client.get(
        f"/api/v1/calculations/{calculation['id']}/export", params={"format": "xlsx"}
    )
    assert workbook.status_code == 200, workbook.text
    assert workbook.content[:2] == b"PK"
    assert "calcul-" in workbook.headers["content-disposition"]

    profile_csv = operations_client.get(
        f"/api/v1/calculations/{calculation['id']}/export",
        params={"format": "csv", "section": "profile"},
    )
    assert profile_csv.status_code == 200, profile_csv.text
    text = profile_csv.content.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("chainage_m;elevation_m")

    document = operations_client.get(
        f"/api/v1/calculations/{calculation['id']}/export", params={"format": "json"}
    )
    assert document.status_code == 200, document.text
    payload = document.json()
    assert payload["calculation_id"] == calculation["id"]
    assert set(payload["sections"]) == {"profile", "segments", "stations", "pumps"}
    assert payload["sections"]["segments"]


def test_export_csv_exige_une_section(operations_client) -> None:
    """Un fichier plat ne peut pas porter plusieurs tableaux sans ambiguïté."""

    organization = _organization(operations_client, slug="exploitant-exports-csv")
    project = _project(operations_client, organization["id"])
    canonical = entree_canonique(
        cas=scenario(imposed_flow_m3_s=0.15, inlet_pressure_pa=5_000_000.0)
    ).payload()
    _, calculation = _calculation(operations_client, project["id"], canonical, "EXPCSV")

    response = operations_client.get(
        f"/api/v1/calculations/{calculation['id']}/export", params={"format": "csv"}
    )

    assert response.status_code == 409, response.text


def test_optimisation_par_voie_pyomo_retient_le_meme_optimum(operations_client) -> None:
    """Les deux voies doivent converger sur un espace de recherche identique."""

    organization = _organization(operations_client, slug="exploitant-pyomo")
    project = _project(operations_client, organization["id"])
    canonical = entree_canonique(
        conduite=pipeline(stations=(station_serie(),)),
        cas=scenario(imposed_flow_m3_s=0.15, inlet_pressure_pa=5_000_000.0),
    ).payload()
    scenario_record, _ = _calculation(operations_client, project["id"], canonical, "PYO")

    body = {"objective": "min_energy", "speed_options": [0.9, 1.0]}
    enumerated = operations_client.post(
        f"/api/v1/scenarios/{scenario_record['id']}/optimizations",
        headers={"Idempotency-Key": "optimisation-enumeration"},
        json=body,
    )
    assert enumerated.status_code == 201, enumerated.text

    with_pyomo = operations_client.post(
        f"/api/v1/scenarios/{scenario_record['id']}/optimizations",
        headers={"Idempotency-Key": "optimisation-pyomo"},
        json={**body, "solver": "pyomo"},
    )
    assert with_pyomo.status_code == 201, with_pyomo.text

    first = enumerated.json()["result_payload"]
    second = with_pyomo.json()["result_payload"]
    assert first["best"] is not None
    assert second["best"] is not None
    assert second["best"]["configuration"]["id"] == first["best"]["configuration"]["id"]
    assert second["best"]["objective_value"] == pytest.approx(first["best"]["objective_value"])


def test_approbation_du_calcul_est_distincte_de_celle_du_rapport(operations_client) -> None:
    """Un résultat physique se retient comme référence, indépendamment du document."""

    organization = _organization(operations_client, slug="exploitant-approbation")
    project = _project(operations_client, organization["id"])
    canonical = entree_canonique(
        cas=scenario(imposed_flow_m3_s=0.15, inlet_pressure_pa=5_000_000.0)
    ).payload()
    _, calculation = _calculation(operations_client, project["id"], canonical, "APP")

    assert calculation["approval_status"] == "pending"

    results = operations_client.get(f"/api/v1/calculations/{calculation['id']}/results")
    assert results.status_code == 200
    eligible = results.json()["result"]["decision_eligible"]

    decision = operations_client.post(
        f"/api/v1/calculations/{calculation['id']}/approve",
        json={"decision": "approved", "comment": "Retenu comme référence."},
    )

    if not eligible:
        # Sans jeu de règles approuvé, la décision positive reste interdite :
        # c'est la garde attendue, pas un défaut du parcours.
        assert decision.status_code == 409, decision.text
        rejection = operations_client.post(
            f"/api/v1/calculations/{calculation['id']}/approve",
            json={"decision": "rejected", "comment": "Écarté faute d'évaluation normative."},
        )
        assert rejection.status_code == 200, rejection.text
        assert rejection.json()["approval_status"] == "rejected"
        return

    assert decision.status_code == 200, decision.text
    assert decision.json()["approval_status"] == "approved"

    replay = operations_client.post(
        f"/api/v1/calculations/{calculation['id']}/approve",
        json={"decision": "rejected", "comment": "Changement d'avis."},
    )
    assert replay.status_code == 409, replay.text


def test_optimisation_borne_les_evaluations_par_defaut(operations_client) -> None:
    """Chaque évaluation est une simulation complète : la recherche doit être bornée.

    Sans borne par défaut, une optimisation lancée sur un grand réseau ne rend
    jamais la main. Le résultat signale alors une exploration incomplète plutôt
    que de laisser croire à un optimum global.
    """

    organization = _organization(operations_client, slug="exploitant-bornes")
    project = _project(operations_client, organization["id"])
    canonical = entree_canonique(
        conduite=pipeline(stations=(station_serie(nombre_de_pompes=3),)),
        cas=scenario(imposed_flow_m3_s=0.15, inlet_pressure_pa=5_000_000.0),
    ).payload()
    scenario_record, _ = _calculation(operations_client, project["id"], canonical, "BORNE")

    response = operations_client.post(
        f"/api/v1/scenarios/{scenario_record['id']}/optimizations",
        headers={"Idempotency-Key": "optimisation-bornee"},
        json={
            "objective": "min_energy",
            "speed_options": [0.8, 0.9, 1.0],
            "maximum_evaluations": 4,
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()["result_payload"]
    assert payload["evaluated_count"] <= 4
    assert payload["complete"] is False
