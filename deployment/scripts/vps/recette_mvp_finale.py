#!/usr/bin/env python3
"""Exécute les portes automatisables restantes de la recette fonctionnelle MVP.

Le script part du dossier ``REF-MVP-01`` préparé par ``projet_reference.py`` et
n'utilise que les interfaces HTTP publiques de PETROLE. Il complète les preuves
qui ne figuraient pas encore explicitement dans le parcours de référence :

- cinquième scénario volontairement non réalisable ;
- imports de profil, courbe de pompe, barémage et propriétés produit ;
- transfert bac-à-bac couplé à HydroLiquid et bilan matière ;
- optimisation bornée avec résultat archivé ;
- comparaison facultative de l'identité de build entre deux déploiements.

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
import json
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
            raise AcceptanceError(
                f"{method} {path} → HTTP {error.code}: {body}"
            ) from error
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
            (
                'Content-Disposition: form-data; name="file"; '
                f'filename="{filename}"\r\n'
            ).encode(),
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


def run_calculation(client: Client, scenario_id: str, label: str) -> dict[str, Any]:
    calculation = client.request(
        "POST",
        f"/scenarios/{scenario_id}/calculations",
        {"engine": "long_distance_liquid"},
        idempotency_key=f"recette-finale-{label}-{scenario_id}",
    )
    return wait_calculation(client, calculation)


def ensure_impossible_scenario(
    client: Client,
    model_id: str,
    nominal: dict[str, Any],
    assets: list[dict[str, Any]],
) -> dict[str, Any]:
    scenarios = page(client, f"/models/{model_id}/scenarios?limit=200&offset=0")
    existing = find_by(scenarios, "name", IMPOSSIBLE_SCENARIO_NAME)
    if existing:
        return existing

    payload = copy.deepcopy(nominal.get("payload") or {})
    pump_codes = sorted(
        item["code"]
        for item in assets
        if str(item.get("code", "")).startswith("P-")
        and item.get("role") in {"main", "standby"}
    )
    if not pump_codes:
        raise AcceptanceError("Aucune pompe n'est disponible pour construire le scénario impossible.")

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

    return client.request(
        "POST",
        f"/models/{model_id}/scenarios",
        {
            "name": IMPOSSIBLE_SCENARIO_NAME,
            "parent_id": nominal["id"],
            "description": (
                "Cas de recette volontairement impossible : pression amont sous la pression "
                "de vapeur et groupe de pompage indisponible."
            ),
            "payload": payload,
        },
    )


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
        raise AcceptanceError(
            f"L'import {name!r} n'est pas entièrement accepté : {imported}."
        )
    return {
        "dataset_id": dataset["id"],
        "file_id": stored["id"],
        "row_count": preview["row_count"],
        "accepted_count": imported["accepted_count"],
        "rejected_count": imported["rejected_count"],
        "content_hash": imported["content_hash"],
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
        content=(
            "chainage_m,elevation_m\n"
            "0,90\n"
            "100000,72\n"
            "200000,45\n"
        ).encode(),
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
            "flow_m3_s,head_m,efficiency,power_w,npshr_m\n"
            "0.10,235,0.68,350000,3.0\n"
            "0.20,210,0.81,560000,4.2\n"
            "0.30,172,0.84,760000,6.1\n"
            "0.40,118,0.74,980000,9.4\n"
        ).encode(),
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
        idempotency_key=f"recette-transfer-{model_id}",
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
        idempotency_key=f"recette-optimization-{scenario_id}",
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
    return {
        key: version.get(key)
        for key in (
            "git_sha",
            "git_ref",
            "build_time",
            "engine_version",
            "migration_revision",
        )
        if key in version
    }


def compare_builds(primary: Client, secondary: Client | None) -> dict[str, Any]:
    primary_identity = build_identity(primary)
    if secondary is None:
        return {"status": "not_run", "primary": primary_identity}
    secondary_identity = build_identity(secondary)
    stable_keys = ("git_sha", "engine_version", "migration_revision")
    differences = {
        key: {"primary": primary_identity.get(key), "secondary": secondary_identity.get(key)}
        for key in stable_keys
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
    transfer = gates["transfer"]
    optimization = gates["optimization"]
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
        f"- 5e scénario non réalisable : **PASS** — statut `{impossible['status']}`",
        (
            "- Imports profil / pompe / barémage / propriétés : **PASS** — "
            f"{sum(item['accepted_count'] for item in imports.values())} lignes acceptées"
        ),
        (
            "- Transfert HydroLiquid : **PASS** — "
            f"{transfer['received_volume_m3']:.3f} m³ reçus, "
            f"{transfer['sample_count']} échantillons"
        ),
        (
            "- Bilan matière : **PASS** — résidu "
            f"{transfer['balance_residual_m3']:.6g} m³"
        ),
        (
            "- Optimisation : **PASS** — "
            f"solveur `{optimization['solver']}`, statut `{optimization['status']}`"
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
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--project-code", default=PROJECT_CODE_DEFAULT)
    parser.add_argument("--secondary-base-url")
    parser.add_argument("--secondary-email")
    parser.add_argument("--secondary-password")
    parser.add_argument(
        "--output-dir",
        default="var/validation-vps/recette-mvp-finale",
        help="Dossier recevant summary.json et summary.md.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = Client(args.base_url)
    client.login(args.email, args.password)

    secondary: Client | None = None
    if args.secondary_base_url:
        if not args.secondary_email or not args.secondary_password:
            raise AcceptanceError(
                "--secondary-email et --secondary-password sont requis avec --secondary-base-url."
            )
        secondary = Client(args.secondary_base_url)
        secondary.login(args.secondary_email, args.secondary_password)

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
    if validation.get("errors"):
        raise AcceptanceError(
            f"Le réseau de référence contient {len(validation['errors'])} erreur(s)."
        )

    scenarios = page(client, f"/models/{model_id}/scenarios?limit=200&offset=0")
    nominal = first_by(scenarios, "name", "Régime nominal")
    impossible = ensure_impossible_scenario(client, model_id, nominal, assets)
    impossible_calculation = run_calculation(client, impossible["id"], "impossible")
    if impossible_calculation.get("status") in CONVERGED_STATUSES:
        raise AcceptanceError(
            "Le scénario volontairement impossible a convergé ; le cas de recette doit être renforcé."
        )
    impossible_result = client.request(
        "GET", f"/calculations/{impossible_calculation['id']}/results"
    )

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
    )
    optimization = exercise_optimization(client, scenario_id=nominal["id"], assets=assets)
    same_build = compare_builds(client, secondary)

    summary = {
        "executed_at": datetime.now(UTC).isoformat(),
        "base_url": args.base_url,
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
            "scenarios": len(
                page(client, f"/models/{model_id}/scenarios?limit=200&offset=0")
            ),
        },
        "network_validation": {
            "errors": len(validation.get("errors") or []),
            "warnings": len(validation.get("warnings") or []),
        },
        "gates": {
            "impossible_scenario": {
                "scenario_id": impossible["id"],
                "calculation_id": impossible_calculation["id"],
                "status": impossible_calculation["status"],
                "diagnostics": impossible_result.get("diagnostics"),
            },
            "imports": imports,
            "transfer": transfer,
            "optimization": optimization,
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
