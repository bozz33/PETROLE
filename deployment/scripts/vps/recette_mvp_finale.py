#!/usr/bin/env python3
"""Exécute les portes automatisables restantes de la recette fonctionnelle MVP.

Le script part du dossier ``REF-MVP-01`` préparé par ``projet_reference.py`` et
n'utilise que les interfaces HTTP publiques de PETROLE. Il complète les preuves
qui ne figuraient pas encore explicitement dans le parcours de référence :

- cinquième scénario volontairement non réalisable ;
- rejeu de la baseline, des scénarios dégradés et de leur comparaison ;
- imports de profil, courbe de pompe, barémage et propriétés produit ;
- transfert bac-à-bac couplé à HydroLiquid et bilan matière ;
- optimisation bornée avec résultat archivé ;
- note de calcul, rapports opérationnels et exports ;
- identité de build contrôlée contre le SHA candidat et, si demandé, entre deux déploiements.

Il produit un JSON et un Markdown de preuve. Il ne remplace pas l'acceptation
humaine : la signature d'un ingénieur métier extérieur reste une porte manuelle.

Exemple :

    python deployment/scripts/vps/recette_mvp_finale.py \
      --base-url https://petrole.distesage.com/api/v1 \
      --email recette-engineer@petrole.distesage.com \
      --password '...' \
      --project-code REF-MVP-01

Pour comparer le même build avec une instance locale :

    ... --secondary-base-url http://127.0.0.1:8000/api/v1 \
        --secondary-email recette-engineer@petrole.distesage.com \
        --secondary-password '...'
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_CODE_DEFAULT = "REF-MVP-01"
IMPOSSIBLE_SCENARIO_NAME = "Configuration impossible"
TERMINAL_CALCULATION_PHASES = {"finished", "failed", "cancelled"}
CONVERGED_STATUSES = {"SIM_CONVERGED", "SIM_CONVERGED_WARN"}
REQUIRED_SCENARIO_STATUSES = {
    "Régime nominal": {"SIM_CONVERGED"},
    "Pompe indisponible": {"SIM_CONVERGED_WARN"},
    "Marche en secours": {"SIM_CONVERGED"},
    "Débit réduit": {"SIM_CONVERGED"},
}
BUILD_IDENTITY_FIELDS = (
    "application_version",
    "git_sha",
    "ref",
    "build_date",
    "scientific_engine_version",
    "database_migration_version",
)
STABLE_BUILD_IDENTITY_FIELDS = (
    "application_version",
    "git_sha",
    "scientific_engine_version",
    "database_migration_version",
)


class AcceptanceError(RuntimeError):
    """Échec d'une porte de recette ou d'un appel API."""


class Client:
    """Client HTTP minimal, sans dépendance externe."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None

    def request(
        self,
        method: str,
        path: str,
        payload: Any = None,
        *,
        idempotency_key: str | None = None,
        timeout: float = 180.0,
    ) -> Any:
        url = f"{self.base_url}{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Accept", "application/json")
        if payload is not None:
            request.add_header("Content-Type", "application/json")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        if idempotency_key:
            request.add_header("Idempotency-Key", idempotency_key)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise AcceptanceError(f"{method} {path} → HTTP {error.code}: {body}") from error
        except urllib.error.URLError as error:
            raise AcceptanceError(f"{method} {path} → {error}") from error

    def request_bytes(
        self,
        method: str,
        path: str,
        *,
        timeout: float = 180.0,
    ) -> tuple[bytes, str]:
        """Exécute un téléchargement public/privé sans tenter de le décoder en JSON."""

        request = urllib.request.Request(f"{self.base_url}{path}", method=method)
        request.add_header("Accept", "application/octet-stream, application/json")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), response.headers.get_content_type()
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise AcceptanceError(f"{method} {path} → HTTP {error.code}: {body}") from error
        except urllib.error.URLError as error:
            raise AcceptanceError(f"{method} {path} → {error}") from error

    def upload_dataset_file(
        self,
        *,
        organization_id: str,
        filename: str,
        content: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        boundary = f"petrole-{uuid.uuid4().hex}"
        chunks = [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="organization_id"\r\n\r\n',
            organization_id.encode(),
            b"\r\n",
            f"--{boundary}\r\n".encode(),
            (f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n').encode(),
            f"Content-Type: {media_type}\r\n\r\n".encode(),
            content,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
        request = urllib.request.Request(
            f"{self.base_url}/files",
            data=b"".join(chunks),
            method="POST",
        )
        request.add_header("Accept", "application/json")
        request.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise AcceptanceError(f"POST /files → HTTP {error.code}: {body}") from error

    def login(self, email: str, password: str) -> None:
        tokens = self.request("POST", "/auth/login", {"email": email, "password": password})
        self.token = str(tokens["access_token"])


def page(client: Client, path: str) -> list[dict[str, Any]]:
    response = client.request("GET", path)
    return list(response.get("items", []))


def first_by(items: list[dict[str, Any]], field: str, value: Any) -> dict[str, Any]:
    for item in items:
        if item.get(field) == value:
            return item
    raise AcceptanceError(f"Aucune ressource avec {field}={value!r}.")


def find_by(items: list[dict[str, Any]], field: str, value: Any) -> dict[str, Any] | None:
    return next((item for item in items if item.get(field) == value), None)


def latest_model(models: list[dict[str, Any]]) -> dict[str, Any]:
    if not models:
        raise AcceptanceError("Le projet ne possède aucune version de modèle.")
    return max(models, key=lambda item: int(item.get("version_number", 0)))


def wait_calculation(
    client: Client,
    calculation: dict[str, Any],
    *,
    timeout_s: float = 300.0,
) -> dict[str, Any]:
    calculation_id = calculation["id"]
    deadline = time.monotonic() + timeout_s
    current = calculation
    while time.monotonic() < deadline:
        phase = str(current.get("phase", "")).lower()
        if current.get("finished_at") or phase in TERMINAL_CALCULATION_PHASES:
            return current
        time.sleep(1.0)
        current = client.request("GET", f"/calculations/{calculation_id}")
    raise AcceptanceError(f"Le calcul {calculation_id} n'a pas terminé en {timeout_s:.0f} s.")


def run_calculation(
    client: Client,
    scenario_id: str,
    label: str,
    recipe_run_id: str,
) -> dict[str, Any]:
    calculation = client.request(
        "POST",
        f"/scenarios/{scenario_id}/calculations",
        {"engine": "long_distance_liquid"},
        idempotency_key=f"recette-finale-{recipe_run_id}-{label}-{scenario_id}",
    )
    return wait_calculation(client, calculation)


def run_required_scenarios(
    client: Client,
    scenarios: list[dict[str, Any]],
    recipe_run_id: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Rejoue les quatre scénarios de référence et vérifie leur verdict attendu."""

    calculations: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    for index, (name, expected_statuses) in enumerate(REQUIRED_SCENARIO_STATUSES.items(), start=1):
        scenario = first_by(scenarios, "name", name)
        calculation = run_calculation(
            client,
            scenario["id"],
            f"required-{index}",
            recipe_run_id,
        )
        status = str(calculation.get("status"))
        if status not in expected_statuses:
            raise AcceptanceError(
                f"Le scénario {name!r} a le statut {status!r}, attendu : "
                f"{sorted(expected_statuses)!r}."
            )
        result = client.request("GET", f"/calculations/{calculation['id']}/results")
        if not result.get("result"):
            raise AcceptanceError(f"Le scénario {name!r} n'a produit aucun résultat exploitable.")
        calculations[name] = calculation
        results[name] = result
    return calculations, results


def exercise_comparison(
    client: Client,
    *,
    project_id: str,
    calculations: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Archive le classement des scénarios réellement rejoués."""

    calculation_ids = [
        calculations[name]["id"] for name in REQUIRED_SCENARIO_STATUSES if name in calculations
    ]
    comparison = client.request(
        "POST",
        f"/projects/{project_id}/comparisons",
        {"calculation_ids": calculation_ids},
        idempotency_key=(
            "recette-comparison-"
            + hashlib.sha256("|".join(calculation_ids).encode("utf-8")).hexdigest()[:24]
        ),
    )
    payload = comparison.get("result_payload") or {}
    ranked = payload.get("ranked") or []
    recommended = payload.get("recommended_calculation_id")
    if len(ranked) != len(calculation_ids) or not recommended:
        raise AcceptanceError(
            "La comparaison ne publie pas un classement et une recommandation complets."
        )
    return {
        "comparison_id": comparison["id"],
        "calculation_ids": calculation_ids,
        "recommended_calculation_id": recommended,
        "ranked_count": len(ranked),
        "content_hash": comparison["content_hash"],
    }


def exercise_reports_and_exports(
    client: Client,
    *,
    nominal_calculation_id: str,
    comparison_id: str,
    transfer_id: str,
) -> dict[str, Any]:
    """Produit les preuves documentaires et les trois formats d'export D04."""

    note = client.request(
        "POST",
        f"/calculations/{nominal_calculation_id}/reports",
        {"report_type": "hydraulic_calculation", "template_version": "rpt-02/1.0"},
        idempotency_key=f"recette-note-calcul-{nominal_calculation_id}",
    )
    operational_specs = (
        ("scenario_comparison", comparison_id),
        ("transfer_simulation", transfer_id),
        ("material_balance", transfer_id),
    )
    operational_reports = []
    for report_type, source_id in operational_specs:
        report = client.request(
            "POST",
            "/reports",
            {"report_type": report_type, "source_id": source_id},
            idempotency_key=f"recette-{report_type}-{source_id}",
        )
        operational_reports.append(
            {
                "id": report["id"],
                "report_type": report["report_type"],
                "content_hash": report["content_hash"],
            }
        )

    exports = {}
    for export_format, section in (("xlsx", None), ("json", None), ("csv", "segments")):
        query = f"format={export_format}"
        if section:
            query += f"&section={section}"
        content, media_type = client.request_bytes(
            "GET",
            f"/calculations/{nominal_calculation_id}/export?{query}",
        )
        if not content:
            raise AcceptanceError(f"L'export {export_format} est vide.")
        exports[export_format] = {
            "media_type": media_type,
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    return {
        "calculation_note": {
            "id": note["id"],
            "content_hash": note["content_hash"],
            "file_id": note["file_id"],
        },
        "operational_reports": operational_reports,
        "exports": exports,
    }


def ensure_impossible_scenario(
    client: Client,
    model_id: str,
    nominal: dict[str, Any],
    assets: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = copy.deepcopy(nominal.get("payload") or {})
    pump_codes = sorted(
        item["code"]
        for item in assets
        if str(item.get("code", "")).startswith("P-") and item.get("role") in {"main", "standby"}
    )
    if not pump_codes:
        raise AcceptanceError(
            "Aucune pompe n'est disponible pour construire le scénario impossible."
        )

    # La pression d'entrée est volontairement sous la pression de vapeur du fluide
    # de référence. Le cas doit donc être refusé comme physiquement irréalisable,
    # indépendamment de la disponibilité des pompes.
    payload["inlet_pressure_pa"] = 4_000.0
    payload["outlet_pressure_pa"] = None
    payload["imposed_flow_m3_s"] = 0.25
    payload["pump_overrides"] = [
        {
            "pump_id": code,
            "status": "unavailable",
            "running": False,
            "speed_ratio": None,
        }
        for code in pump_codes
    ]
    description = (
        "Cas de recette volontairement impossible : pression amont sous la pression "
        "de vapeur et groupe de pompage indisponible."
    )

    scenarios = page(client, f"/models/{model_id}/scenarios?limit=200&offset=0")
    existing = find_by(scenarios, "name", IMPOSSIBLE_SCENARIO_NAME)
    if existing:
        current_payload = existing.get("payload") or {}
        expected_pumps = {item["pump_id"] for item in payload["pump_overrides"]}
        current_unavailable_pumps = {
            item.get("pump_id")
            for item in current_payload.get("pump_overrides", [])
            if isinstance(item, dict)
            and item.get("status") == "unavailable"
            and item.get("running") is False
        }
        if (
            current_payload.get("inlet_pressure_pa") == payload["inlet_pressure_pa"]
            and current_payload.get("imposed_flow_m3_s") == payload["imposed_flow_m3_s"]
            and expected_pumps <= current_unavailable_pumps
        ):
            return existing
        return client.request(
            "PATCH",
            f"/scenarios/{existing['id']}",
            {"description": description, "payload": payload},
        )

    return client.request(
        "POST",
        f"/models/{model_id}/scenarios",
        {
            "name": IMPOSSIBLE_SCENARIO_NAME,
            "parent_id": nominal["id"],
            "description": description,
            "payload": payload,
        },
    )


def assert_impossible_result(
    calculation: dict[str, Any],
    calculation_result: dict[str, Any],
) -> dict[str, Any]:
    """Vérifie qu'un scénario est non réalisable, même si le solveur a convergé.

    HydroLiquid distingue la convergence numérique de l'acceptabilité physique :
    un calcul peut atteindre sa solution tout en publiant une violation critique
    (pression sous la vapeur, cavitation, pression d'aspiration insuffisante…).
    Dans ce cas le statut est ``SIM_CONVERGED_WARN``, mais le résultat n'est ni
    physiquement approuvable ni éligible à une décision. C'est un cas de recette
    non réalisable valide, à condition que ces marqueurs et ses causes soient
    tous explicitement présents.
    """

    status = str(calculation.get("status"))
    result = calculation_result.get("result") or {}
    violations = result.get("violations") or []
    warnings = result.get("warnings") or []
    diagnostics = calculation_result.get("diagnostics") or {}
    physical_approvable = result.get("physical_approvable")
    decision_eligible = result.get("decision_eligible")
    non_approvable_convergence = (
        status == "SIM_CONVERGED_WARN"
        and physical_approvable is False
        and decision_eligible is False
        and bool(violations)
    )
    if status in CONVERGED_STATUSES and not non_approvable_convergence:
        raise AcceptanceError(
            "Le scénario volontairement impossible est considéré comme physiquement "
            "acceptable ; il doit être non convergé, ou SIM_CONVERGED_WARN avec des "
            "violations critiques et les indicateurs physical_approvable=false / "
            "decision_eligible=false."
        )
    if not diagnostics and not violations and not warnings:
        raise AcceptanceError(
            "Le scénario non réalisable ne publie aucune cause exploitable de son échec."
        )
    return {
        "status": status,
        "physical_approvable": physical_approvable,
        "decision_eligible": decision_eligible,
        "compliance_status": result.get("compliance_status"),
        "violation_count": len(violations),
        "warning_count": len(warnings),
        "diagnostics": diagnostics,
    }


def execute_import(
    client: Client,
    *,
    organization_id: str,
    project_id: str,
    name: str,
    kind: str,
    filename: str,
    content: bytes,
    media_type: str,
    mapping: dict[str, str],
) -> dict[str, Any]:
    stored = client.upload_dataset_file(
        organization_id=organization_id,
        filename=filename,
        content=content,
        media_type=media_type,
    )
    dataset = client.request(
        "POST",
        "/datasets",
        {
            "organization_id": organization_id,
            "project_id": project_id,
            "file_id": stored["id"],
            "name": name,
            "kind": kind,
        },
    )
    preview = client.request("POST", f"/datasets/{dataset['id']}/preview")
    client.request(
        "POST",
        f"/datasets/{dataset['id']}/mappings",
        {"fields": mapping, "constants": {}},
    )
    imported = client.request(
        "POST",
        f"/datasets/{dataset['id']}/imports",
        idempotency_key=f"recette-import-{dataset['id']}",
    )
    if int(imported.get("accepted_count", 0)) <= 0 or int(imported.get("rejected_count", 0)):
        raise AcceptanceError(f"L'import {name!r} n'est pas entièrement accepté : {imported}.")
    rows = client.request("GET", f"/datasets/{dataset['id']}/rows?limit=1000&offset=0")
    accepted_count = int(imported["accepted_count"])
    if int(rows.get("total", 0)) != accepted_count:
        raise AcceptanceError(
            f"L'import {name!r} ne restitue pas toutes ses lignes normalisées : {rows}."
        )
    if any(item.get("errors") or not item.get("normalized") for item in rows.get("items", [])):
        raise AcceptanceError(f"L'import {name!r} contient une ligne non normalisée ou en erreur.")
    return {
        "dataset_id": dataset["id"],
        "file_id": stored["id"],
        "row_count": preview["row_count"],
        "accepted_count": accepted_count,
        "rejected_count": imported["rejected_count"],
        "content_hash": imported["content_hash"],
        "normalized_row_count": rows["total"],
    }


def exercise_imports(
    client: Client,
    *,
    organization_id: str,
    project_id: str,
) -> dict[str, Any]:
    profile = execute_import(
        client,
        organization_id=organization_id,
        project_id=project_id,
        name="Recette — profil altimétrique",
        kind="profile",
        filename="recette-profil.csv",
        content=b"chainage_m,elevation_m\n0,90\n100000,72\n200000,45\n",
        media_type="text/csv",
        mapping={"chainage_m": "chainage_m", "elevation_m": "elevation_m"},
    )
    pump_curve = execute_import(
        client,
        organization_id=organization_id,
        project_id=project_id,
        name="Recette — courbe pompe",
        kind="pump_curve",
        filename="recette-pompe.csv",
        content=(
            b"flow_m3_s,head_m,efficiency,power_w,npshr_m\n"
            b"0.10,235,0.68,350000,3.0\n"
            b"0.20,210,0.81,560000,4.2\n"
            b"0.30,172,0.84,760000,6.1\n"
            b"0.40,118,0.74,980000,9.4\n"
        ),
        media_type="text/csv",
        mapping={
            "flow_m3_s": "flow_m3_s",
            "head_m": "head_m",
            "efficiency": "efficiency",
            "power_w": "power_w",
            "npshr_m": "npshr_m",
        },
    )
    strapping_document = {
        "points": [
            {"level_m": 0.0, "volume_m3": 0.0},
            {"level_m": 7.5, "volume_m3": 6_000.0},
            {"level_m": 15.0, "volume_m3": 12_000.0},
        ]
    }
    strapping = execute_import(
        client,
        organization_id=organization_id,
        project_id=project_id,
        name="Recette — barémage bac",
        kind="strapping",
        filename="recette-bareme.json",
        content=json.dumps(strapping_document).encode(),
        media_type="application/json",
        mapping={"level_m": "level_m", "volume_m3": "volume_m3"},
    )
    properties_document = [
        {"property": "density_kg_m3", "value": 845.0, "unit": "kg/m3"},
        {"property": "kinematic_viscosity_m2_s", "value": 5.5e-6, "unit": "m2/s"},
        {"property": "vapor_pressure_pa", "value": 4_500.0, "unit": "Pa"},
    ]
    properties = execute_import(
        client,
        organization_id=organization_id,
        project_id=project_id,
        name="Recette — propriétés produit",
        kind="generic",
        filename="recette-proprietes.json",
        content=json.dumps(properties_document).encode(),
        media_type="application/json",
        mapping={"property": "property", "value": "value", "unit": "unit"},
    )
    return {
        "profile": profile,
        "pump_curve": pump_curve,
        "strapping": strapping,
        "fluid_properties": properties,
    }


def tank_node(nodes: list[dict[str, Any]], tank_id: str) -> dict[str, Any]:
    for node in nodes:
        payload = node.get("payload") or {}
        if node.get("kind") == "tank" and str(payload.get("tank_id")) == str(tank_id):
            return node
    raise AcceptanceError(f"Aucun nœud réseau ne raccorde le bac {tank_id}.")


def exercise_transfer(
    client: Client,
    *,
    organization_id: str,
    model_id: str,
    nominal_scenario_id: str,
    tanks: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    recipe_run_id: str,
) -> dict[str, Any]:
    source = first_by(tanks, "code", "TK-01")
    destination = first_by(tanks, "code", "TK-02")
    source_node = tank_node(nodes, source["id"])
    destination_node = tank_node(nodes, destination["id"])
    ordered_edges = sorted(edges, key=lambda item: int(item.get("sequence", 0)))
    main_pumps = sorted(
        (
            item
            for item in assets
            if item.get("role") == "main" and str(item.get("code", "")).startswith("P-")
        ),
        key=lambda item: item["code"],
    )
    if len(main_pumps) < 5:
        raise AcceptanceError("Le transfert de recette exige les cinq pompes principales.")

    transfer = client.request(
        "POST",
        f"/organizations/{organization_id}/transfers",
        {
            "source_tank_id": source["id"],
            "destination_tank_id": destination["id"],
            "fluid_id": "REF-BRUT-01",
            "requested_flow_m3_s": 0.25,
            "target_volume_m3": 100.0,
            "time_step_s": 60.0,
            "maximum_duration_s": 7_200.0,
            "maximum_flow_m3_s": 0.5,
            "loss_fraction": 0.0,
            "hydraulic_context": {
                "model_version_id": model_id,
                "scenario_id": nominal_scenario_id,
                "source_node_id": source_node["id"],
                "destination_node_id": destination_node["id"],
                "path_edge_ids": [edge["id"] for edge in ordered_edges],
                "pump_asset_ids": [pump["id"] for pump in main_pumps],
                "level_step_m": 0.05,
                "maximum_evaluations": 200,
            },
        },
        idempotency_key=f"recette-transfer-{recipe_run_id}-{model_id}",
        timeout=300.0,
    )
    result = transfer.get("result_payload") or {}
    samples = result.get("samples") or []
    if not result.get("target_reached") or len(samples) < 2:
        raise AcceptanceError(
            "Le transfert n'a pas atteint son objectif avec une série temporelle exploitable."
        )

    withdrawn = float(result["withdrawn_volume_m3"])
    received = float(result["received_volume_m3"])
    source_opening = float(source["current_volume_m3"])
    destination_opening = float(destination["current_volume_m3"])
    balance = client.request(
        "POST",
        f"/transfers/{transfer['id']}/balance",
        {
            "source_opening": {"value_m3": source_opening, "standard_uncertainty_m3": 0.1},
            "source_closing": {
                "value_m3": source_opening - withdrawn,
                "standard_uncertainty_m3": 0.1,
            },
            "destination_opening": {
                "value_m3": destination_opening,
                "standard_uncertainty_m3": 0.1,
            },
            "destination_closing": {
                "value_m3": destination_opening + received,
                "standard_uncertainty_m3": 0.1,
            },
            "metered_volume": {"value_m3": received, "standard_uncertainty_m3": 0.1},
            "accounted_losses": {
                "value_m3": float(result.get("losses_m3", 0.0)),
                "standard_uncertainty_m3": 0.05,
            },
            "coverage_factor": 2.0,
            "absolute_tolerance_m3": 1.0,
            "relative_tolerance": 0.001,
        },
    )
    if not balance.get("within_tolerance"):
        raise AcceptanceError("Le bilan matière du transfert de recette est hors tolérance.")

    return {
        "transfer_id": transfer["id"],
        "status": transfer["status"],
        "stop_reason": result.get("stop_reason"),
        "duration_s": result.get("duration_s"),
        "withdrawn_volume_m3": withdrawn,
        "received_volume_m3": received,
        "energy_j": result.get("energy_j"),
        "sample_count": len(samples),
        "source_final_level_m": result.get("source_final_level_m"),
        "destination_final_level_m": result.get("destination_final_level_m"),
        "balance_within_tolerance": balance["within_tolerance"],
        "balance_residual_m3": balance["system_imbalance_m3"],
    }


def exercise_optimization(
    client: Client,
    *,
    scenario_id: str,
    assets: list[dict[str, Any]],
    recipe_run_id: str,
) -> dict[str, Any]:
    main_codes = sorted(
        item["code"]
        for item in assets
        if item.get("role") == "main" and str(item.get("code", "")).startswith("P-")
    )
    if len(main_codes) < 5:
        raise AcceptanceError("L'optimisation de recette exige cinq pompes principales.")

    optimization = client.request(
        "POST",
        f"/scenarios/{scenario_id}/optimizations",
        {
            "objective": "min_energy",
            "pump_ids": main_codes,
            "speed_options": [0.8, 1.0],
            "reference_duration_s": 3_600.0,
            "energy_price_per_kwh": 0.15,
            "constraints": {
                "minimum_flow_m3_s": 0.20,
                "maximum_flow_m3_s": 0.35,
                "maximum_active_pumps": 5,
                "required_pump_ids": main_codes,
                "forbidden_pump_ids": [],
                "allow_violations": False,
            },
            "maximum_configurations": 100_000,
            "maximum_evaluations": 25,
            "solver": "enumeration",
        },
        idempotency_key=f"recette-optimization-{recipe_run_id}-{scenario_id}",
        timeout=180.0,
    )
    result = optimization.get("result_payload") or {}
    best = result.get("best") or result.get("best_candidate")
    if not best:
        raise AcceptanceError("L'optimisation n'a retenu aucune configuration faisable.")
    return {
        "optimization_id": optimization["id"],
        "status": optimization["status"],
        "engine_version": optimization["engine_version"],
        "objective": optimization["input_payload"].get("objective"),
        "solver": optimization["input_payload"].get("solver"),
        "best": best,
        "search_complete": result.get("search_complete"),
        "evaluated_count": result.get("evaluated_count"),
        "generated_count": result.get("generated_count"),
    }


def build_identity(client: Client) -> dict[str, Any]:
    version = client.request("GET", "/version")
    missing = [key for key in BUILD_IDENTITY_FIELDS if not version.get(key)]
    if missing:
        raise AcceptanceError(
            "L'endpoint /version ne publie pas tous les champs de traçabilité : "
            + ", ".join(missing)
            + "."
        )
    return {key: version[key] for key in BUILD_IDENTITY_FIELDS}


def verify_expected_build(client: Client, expected_git_sha: str | None) -> dict[str, Any]:
    """Empêche d'attribuer une recette à une image qui n'est pas le candidat Git."""

    identity = build_identity(client)
    if expected_git_sha and identity["git_sha"] != expected_git_sha:
        raise AcceptanceError(
            "L'API cible ne sert pas le commit candidat : "
            f"attendu {expected_git_sha}, obtenu {identity['git_sha']}."
        )
    return identity


def compare_builds(
    primary: Client,
    secondary: Client | None,
    *,
    require_secondary: bool,
) -> dict[str, Any]:
    primary_identity = verify_expected_build(primary, expected_git_sha=None)
    if secondary is None:
        if require_secondary:
            raise AcceptanceError(
                "La recette de fermeture exige une instance secondaire du même build."
            )
        return {"status": "not_run", "primary": primary_identity}
    secondary_identity = verify_expected_build(secondary, expected_git_sha=None)
    differences = {
        key: {"primary": primary_identity.get(key), "secondary": secondary_identity.get(key)}
        for key in STABLE_BUILD_IDENTITY_FIELDS
        if primary_identity.get(key) != secondary_identity.get(key)
    }
    if differences:
        raise AcceptanceError(f"Les deux déploiements ne servent pas le même build : {differences}")
    return {
        "status": "passed",
        "primary": primary_identity,
        "secondary": secondary_identity,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    gates = summary["gates"]
    impossible = gates["impossible_scenario"]
    scenarios = gates["scenarios"]
    comparison = gates["comparison"]
    transfer = gates["transfer"]
    optimization = gates["optimization"]
    outputs = gates["outputs"]
    imports = gates["imports"]
    build = gates["same_build"]
    lines = [
        "# Recette fonctionnelle automatisable du MVP",
        "",
        f"- Date UTC : {summary['executed_at']}",
        f"- API : `{summary['base_url']}`",
        f"- Projet : `{summary['project']['code']}`",
        f"- Modèle : `{summary['model']['id']}`",
        "",
        "## Taille et validation du dossier",
        "",
        f"- Nœuds : **{summary['counts']['nodes']}**",
        f"- Tronçons : **{summary['counts']['edges']}**",
        f"- Équipements : **{summary['counts']['assets']}**",
        f"- Réservoirs : **{summary['counts']['tanks']}**",
        f"- Erreurs topologiques : **{summary['network_validation']['errors']}**",
        f"- Avertissements topologiques : **{summary['network_validation']['warnings']}**",
        "",
        "## Portes complémentaires",
        "",
        (
            "- Baseline et scénarios dégradés : **PASS** — "
            + ", ".join(f"{name} : `{item['status']}`" for name, item in scenarios.items())
        ),
        (
            "- 5e scénario non réalisable : **PASS** — "
            f"statut `{impossible['status']}`, "
            f"physiquement approuvable : `{impossible['physical_approvable']}`, "
            f"violations : {impossible['violation_count']}"
        ),
        (
            "- Imports profil / pompe / barémage / propriétés : **PASS** — "
            f"{sum(item['accepted_count'] for item in imports.values())} lignes acceptées"
        ),
        (
            "- Transfert HydroLiquid : **PASS** — "
            f"{transfer['received_volume_m3']:.3f} m³ reçus, "
            f"{transfer['sample_count']} échantillons"
        ),
        (f"- Bilan matière : **PASS** — résidu {transfer['balance_residual_m3']:.6g} m³"),
        (
            "- Optimisation : **PASS** — "
            f"solveur `{optimization['solver']}`, statut `{optimization['status']}`"
        ),
        (
            "- Comparaison : **PASS** — "
            f"{comparison['ranked_count']} calculs classés, recommandation "
            f"`{comparison['recommended_calculation_id']}`"
        ),
        (
            "- Note, rapports et exports : **PASS** — "
            f"note `{outputs['calculation_note']['id']}`, "
            f"formats {', '.join(sorted(outputs['exports']))}"
        ),
        f"- Identité local/serveur : **{build['status'].upper()}**",
        "",
        "## Porte humaine restante",
        "",
        "La présente exécution ne vaut pas acceptation métier. Un ingénieur extérieur à "
        "l'équipe doit examiner le dossier, reproduire les opérations jugées nécessaires, "
        "consigner ses réserves et signer la fiche d'acceptation.",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email")
    parser.add_argument("--password")
    parser.add_argument(
        "--access-token-env",
        help=(
            "Nom d'une variable d'environnement contenant un jeton Bearer court. "
            "Prévu pour l'automatisation sur un serveur ; incompatible avec --email/--password."
        ),
    )
    parser.add_argument("--project-code", default=PROJECT_CODE_DEFAULT)
    parser.add_argument(
        "--expected-git-sha",
        help="SHA Git exact que l'API primaire doit publier via /version.",
    )
    parser.add_argument("--secondary-base-url")
    parser.add_argument("--secondary-email")
    parser.add_argument("--secondary-password")
    parser.add_argument("--secondary-access-token-env")
    parser.add_argument(
        "--require-same-build",
        action="store_true",
        help="Échoue si aucune instance secondaire du même build n'est fournie.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/validation-vps/recette-mvp-finale",
        help="Dossier recevant summary.json et summary.md.",
    )
    return parser.parse_args()


def authenticate_client(
    client: Client,
    *,
    email: str | None,
    password: str | None,
    access_token_env: str | None,
) -> None:
    """Authentifie par session usuelle ou jeton court injecté par le VPS."""

    credentials_provided = bool(email) or bool(password)
    if credentials_provided and (not email or not password):
        raise AcceptanceError("--email et --password doivent être fournis ensemble.")
    if access_token_env and credentials_provided:
        raise AcceptanceError("--access-token-env est incompatible avec --email/--password.")
    if access_token_env:
        access_token = os.environ.get(access_token_env)
        if not access_token:
            raise AcceptanceError(f"La variable de jeton {access_token_env!r} est absente ou vide.")
        client.token = access_token
        return
    if email and password:
        client.login(email, password)
        return
    raise AcceptanceError("Une authentification est requise : session ou --access-token-env.")


def main() -> int:
    args = parse_args()
    client = Client(args.base_url)
    authenticate_client(
        client,
        email=args.email,
        password=args.password,
        access_token_env=args.access_token_env,
    )
    primary_build = verify_expected_build(client, args.expected_git_sha)

    secondary: Client | None = None
    if args.secondary_base_url:
        secondary = Client(args.secondary_base_url)
        authenticate_client(
            secondary,
            email=args.secondary_email,
            password=args.secondary_password,
            access_token_env=args.secondary_access_token_env,
        )
    elif args.require_same_build:
        raise AcceptanceError(
            "--secondary-base-url et son authentification sont requis avec --require-same-build."
        )

    organizations = page(client, "/organizations?limit=200&offset=0")
    if len(organizations) != 1:
        raise AcceptanceError(
            f"La recette single_org attend exactement un exploitant, obtenu : {len(organizations)}."
        )
    organization = organizations[0]
    projects = page(client, "/projects?include_archived=true&limit=200&offset=0")
    project = first_by(projects, "code", args.project_code)
    models = page(client, f"/projects/{project['id']}/models?limit=200&offset=0")
    model = latest_model(models)
    model_id = model["id"]

    nodes = page(client, f"/models/{model_id}/nodes?limit=1000&offset=0")
    edges = page(client, f"/models/{model_id}/edges?limit=200&offset=0")
    assets = page(client, f"/models/{model_id}/assets?limit=200&offset=0")
    tanks = page(
        client,
        f"/tanks?organization_id={organization['id']}&limit=200&offset=0",
    )
    if len(edges) < 100 or len(nodes) < 101 or len(tanks) < 10:
        raise AcceptanceError(
            "Le dossier ne satisfait pas la taille minimale 100 tronçons / 101 nœuds / 10 bacs."
        )
    station_count = sum(1 for node in nodes if node.get("kind") == "station")
    pump_count = sum(1 for asset in assets if str(asset.get("code", "")).startswith("P-"))
    if station_count < 5 or pump_count < 15:
        raise AcceptanceError(
            "Le dossier ne satisfait pas la taille minimale 5 stations / 15 pompes."
        )

    validation = client.request("POST", f"/models/{model_id}/validate")
    if validation.get("errors") or validation.get("warnings"):
        raise AcceptanceError(
            "Le réseau de référence doit être sans erreur ni avertissement : "
            f"{len(validation.get('errors') or [])} erreur(s), "
            f"{len(validation.get('warnings') or [])} avertissement(s)."
        )

    scenarios = page(client, f"/models/{model_id}/scenarios?limit=200&offset=0")
    nominal = first_by(scenarios, "name", "Régime nominal")
    impossible = ensure_impossible_scenario(client, model_id, nominal, assets)
    # Chaque contenu de modèle doit être réellement recalculé. Sans ce suffixe,
    # une exécution après modification du réseau pourrait réutiliser les calculs
    # et le transfert idempotents d'une ancienne géométrie.
    model = client.request("GET", f"/models/{model_id}")
    model_content_hash = str(model.get("content_hash") or "")
    if not model_content_hash:
        raise AcceptanceError("La version de modèle ne publie pas son content_hash.")
    recipe_run_id = hashlib.sha256(model_content_hash.encode("utf-8")).hexdigest()[:24]
    scenarios = page(client, f"/models/{model_id}/scenarios?limit=200&offset=0")
    required_scenario_names = set(REQUIRED_SCENARIO_STATUSES) | {IMPOSSIBLE_SCENARIO_NAME}
    present_scenario_names = {str(item.get("name")) for item in scenarios}
    missing_scenarios = sorted(required_scenario_names - present_scenario_names)
    if missing_scenarios:
        raise AcceptanceError("Scénarios obligatoires absents : " + ", ".join(missing_scenarios))
    scenario_calculations, scenario_results = run_required_scenarios(
        client,
        scenarios,
        recipe_run_id,
    )
    impossible_calculation = run_calculation(
        client,
        impossible["id"],
        "impossible",
        recipe_run_id,
    )
    impossible_result = client.request(
        "GET", f"/calculations/{impossible_calculation['id']}/results"
    )
    impossible_proof = assert_impossible_result(impossible_calculation, impossible_result)

    imports = exercise_imports(
        client,
        organization_id=organization["id"],
        project_id=project["id"],
    )
    transfer = exercise_transfer(
        client,
        organization_id=organization["id"],
        model_id=model_id,
        nominal_scenario_id=nominal["id"],
        tanks=tanks,
        nodes=nodes,
        edges=edges,
        assets=assets,
        recipe_run_id=recipe_run_id,
    )
    optimization = exercise_optimization(
        client,
        scenario_id=nominal["id"],
        assets=assets,
        recipe_run_id=recipe_run_id,
    )
    comparison = exercise_comparison(
        client,
        project_id=project["id"],
        calculations=scenario_calculations,
    )
    outputs = exercise_reports_and_exports(
        client,
        nominal_calculation_id=scenario_calculations["Régime nominal"]["id"],
        comparison_id=comparison["comparison_id"],
        transfer_id=transfer["transfer_id"],
    )
    same_build = compare_builds(
        client,
        secondary,
        require_secondary=args.require_same_build,
    )
    primary_build_after = verify_expected_build(client, args.expected_git_sha)

    summary = {
        "executed_at": datetime.now(UTC).isoformat(),
        "base_url": args.base_url,
        "build": {"before": primary_build, "after": primary_build_after},
        "organization": {"id": organization["id"], "name": organization["name"]},
        "project": {"id": project["id"], "code": project["code"], "name": project["name"]},
        "model": {
            "id": model_id,
            "version_number": model["version_number"],
            "content_hash": model["content_hash"],
        },
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
            "stations": station_count,
            "assets": len(assets),
            "pumps": pump_count,
            "tanks": len(tanks),
            "scenarios": len(page(client, f"/models/{model_id}/scenarios?limit=200&offset=0")),
        },
        "network_validation": {
            "errors": len(validation.get("errors") or []),
            "warnings": len(validation.get("warnings") or []),
        },
        "gates": {
            "impossible_scenario": {
                "scenario_id": impossible["id"],
                "calculation_id": impossible_calculation["id"],
                **impossible_proof,
            },
            "scenarios": {
                name: {
                    "scenario_id": first_by(scenarios, "name", name)["id"],
                    "calculation_id": calculation["id"],
                    "status": calculation["status"],
                    "result_status": scenario_results[name]["status"],
                }
                for name, calculation in scenario_calculations.items()
            },
            "imports": imports,
            "transfer": transfer,
            "optimization": optimization,
            "comparison": comparison,
            "outputs": outputs,
            "same_build": same_build,
        },
        "manual_gate": {
            "external_engineer_acceptance": "pending",
            "release_signature": "maintainer_decision",
        },
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(render_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AcceptanceError as error:
        print(f"ÉCHEC DE RECETTE : {error}", file=sys.stderr)
        raise SystemExit(1) from error
