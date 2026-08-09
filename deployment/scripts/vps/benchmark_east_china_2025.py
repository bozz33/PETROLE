#!/usr/bin/env python3
"""Rejoue sans pression inventée le tronçon terrain East China 2025 dans PETROLE.

Le cas impose le débit *mesuré* de 270 m3/h pour vérifier la géométrie, le
fluide, le régime, les pertes Altshul et leur écart déclaré avec Leibenzon.
L'article ne publie pas les pressions amont/aval numériques : ce runner refuse
donc de présenter ce rejet comme une prédiction pression → débit ou une
validation terrain prédictive.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "validation/public/field_east_china_2025"
PROJECT_CODE_DEFAULT = "BENCH-EAST-CHINA-2025"
OUTPUT_DEFAULT = ROOT / "var/validation-vps/benchmark-east-china-2025.json"

RHO_KG_M3 = 847.4
NU_M2_S = 4.72e-6
DIAMETER_M = 0.2731
MEASURED_FLOW_M3_H = 270.0
MEASURED_FLOW_M3_S = MEASURED_FLOW_M3_H / 3600.0
LEIBENZON_BETA = 0.0246
LEIBENZON_M = 0.25
PETROLE_G = 9.80665
# L'API exige une pression absolue de départ. Ni cette pression ni une MAWP par
# tronçon ne sont publiées : elles sont exclues des conclusions physiques.
ASSUMED_INLET_PRESSURE_PA = 5_000_000.0
ASSUMED_MAWP_PA = 8_000_000.0
PUBLISHED_REYNOLDS = 76_918.0
# Critère diagnostique défini avant exécution. Ce n'est pas une tolérance de
# qualification produit, seulement le seuil qui déclenche une investigation de
# cohérence des chiffres publiés.
PUBLISHED_REYNOLDS_RECONCILIATION_TOLERANCE_PERCENT = 0.5
# Porte de reproduction du moteur, définie indépendamment de la cohérence des
# chiffres publiés. Les formules et le moteur doivent coïncider à 0,001 %.
PHYSICS_REPRODUCTION_TOLERANCE_PERCENT = 0.001

NODES = [
    ("EC-PS2", "Pigging Station 2", "source", 59.80),
    ("EC-VC3", "Valve Chamber 3", "junction", 80.20),
    ("EC-PUMP2", "Pumping Station 2", "terminal", 72.50),
]
EDGES = [
    ("EC-L7A", "EC-PS2", "EC-VC3", 11_842.0),
    ("EC-L7B", "EC-VC3", "EC-PUMP2", 28_236.0),
]
EXPECTED_WARNING_CODES = frozenset({"WARN_PROPERTY_DEFAULTED"})
ACCEPTED_CALCULATION_STATUSES = frozenset({"SIM_CONVERGED", "SIM_CONVERGED_WARN"})


class BenchmarkError(RuntimeError):
    """Erreur de préparation, contrat API ou exécution du benchmark."""


class Client:
    """Client HTTP minimal, limité aux APIs publiques PETROLE."""

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
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            method=method,
        )
        request.add_header("Accept", "application/json")
        if payload is not None:
            request.add_header("Content-Type", "application/json")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        if idempotency_key:
            request.add_header("Idempotency-Key", idempotency_key)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise BenchmarkError(f"{method} {path} → HTTP {error.code}: {body}") from error
        except urllib.error.URLError as error:
            raise BenchmarkError(f"{method} {path} → {error}") from error

    def login(self, email: str, password: str) -> None:
        response = self.request("POST", "/auth/login", {"email": email, "password": password})
        self.token = str(response["access_token"])


def authenticate(
    client: Client,
    *,
    email: str | None,
    password: str | None,
    token_env: str | None,
) -> None:
    if token_env:
        if email or password:
            raise BenchmarkError("Le jeton d'environnement est incompatible avec email/password.")
        client.token = os.environ.get(token_env)
        if not client.token:
            raise BenchmarkError(f"La variable {token_env!r} est absente ou vide.")
        return
    if not email or not password:
        raise BenchmarkError("Fournissez email/password ou un jeton court via --*-token-env.")
    client.login(email, password)


def page(client: Client, path: str) -> list[dict[str, Any]]:
    return list(client.request("GET", path).get("items", []))


def load_csv(name: str) -> list[dict[str, str]]:
    with (DATA_DIR / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def published_observation() -> dict[str, float]:
    rows = load_csv("reference_observation.csv")
    if len(rows) != 1 or rows[0]["case_id"] != "EC07-1401":
        raise BenchmarkError("La référence East China attend une observation EC07-1401 unique.")
    row = rows[0]
    return {
        "measured_flow_m3_h": float(row["measured_flow_m3_h"]),
        "published_calculated_flow_m3_h": float(row["published_calculated_flow_m3_h"]),
        "published_relative_error_percent": float(row["published_relative_error_percent"]),
        "published_reynolds": float(row["published_reynolds"]),
        "beta": float(row["beta"]),
        "m": float(row["m"]),
    }


def field_geometry() -> dict[str, Any]:
    rows = load_csv("segment7.csv")
    if len(rows) != 3:
        raise BenchmarkError("Le tronçon East China doit contenir exactement trois points publiés.")
    lengths_m = [float(row["spacing_from_previous_km"] or 0.0) * 1_000.0 for row in rows]
    total_length_m = sum(lengths_m)
    if abs(total_length_m - 40_078.0) > 1e-6:
        raise BenchmarkError(f"Longueur East China inattendue : {total_length_m} m.")
    for row in rows:
        if float(row["internal_diameter_m"]) != DIAMETER_M:
            raise BenchmarkError("Le diamètre East China n'est pas homogène dans le dataset.")
        if float(row["density_kg_m3"]) != RHO_KG_M3:
            raise BenchmarkError("La masse volumique East China est incohérente.")
        if float(row["kinematic_viscosity_m2_s"]) != NU_M2_S:
            raise BenchmarkError("La viscosité East China est incohérente.")
    observation = published_observation()
    if observation["measured_flow_m3_h"] != MEASURED_FLOW_M3_H:
        raise BenchmarkError("Le débit mesuré du dataset ne correspond pas au runner.")
    return {"points": rows, "lengths_m": lengths_m, "total_length_m": total_length_m}


def physics_at_measured_flow() -> dict[str, float]:
    area_m2 = math.pi * DIAMETER_M**2 / 4.0
    velocity_m_s = MEASURED_FLOW_M3_S / area_m2
    reynolds = velocity_m_s * DIAMETER_M / NU_M2_S
    leibenzon_loss_m = (
        1.02
        * LEIBENZON_BETA
        * MEASURED_FLOW_M3_S ** (2.0 - LEIBENZON_M)
        * NU_M2_S**LEIBENZON_M
        / DIAMETER_M ** (5.0 - LEIBENZON_M)
        * 40_078.0
    )
    altshul_friction_factor = 0.11 * (68.0 / reynolds) ** 0.25
    altshul_loss_m = (
        altshul_friction_factor * (40_078.0 / DIAMETER_M) * velocity_m_s**2 / (2.0 * PETROLE_G)
    )
    return {
        "flow_m3_s": MEASURED_FLOW_M3_S,
        "area_m2": area_m2,
        "velocity_m_s": velocity_m_s,
        "reynolds": reynolds,
        "leibenzon_loss_m": leibenzon_loss_m,
        "altshul_friction_factor": altshul_friction_factor,
        "altshul_loss_m": altshul_loss_m,
        "altshul_vs_leibenzon_percent": 100.0
        * (altshul_loss_m - leibenzon_loss_m)
        / leibenzon_loss_m,
    }


def source_checks() -> dict[str, Any]:
    geometry = field_geometry()
    physics = physics_at_measured_flow()
    observation = published_observation()
    published_reynolds_difference_percent = (
        100.0
        * (physics["reynolds"] - observation["published_reynolds"])
        / observation["published_reynolds"]
    )
    return {
        "geometry": geometry,
        "published_observation": observation,
        "physics_from_published_inputs": physics,
        "published_reynolds_difference_percent": published_reynolds_difference_percent,
        "published_reynolds_reconciled": abs(published_reynolds_difference_percent)
        <= PUBLISHED_REYNOLDS_RECONCILIATION_TOLERANCE_PERCENT,
    }


def next_project_code(client: Client, requested_code: str) -> str:
    codes = {
        str(project.get("code") or "")
        for project in page(client, "/projects?include_archived=true&limit=200&offset=0")
    }
    if requested_code not in codes:
        return requested_code
    index = 2
    while f"{requested_code}-R{index}" in codes:
        index += 1
    return f"{requested_code}-R{index}"


def create_or_reuse_catalog_item(
    engineer: Client,
    approver: Client,
    *,
    collection: str,
    organization_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    items = page(
        engineer, f"/catalog/{collection}?organization_id={organization_id}&limit=200&offset=0"
    )
    matches = [item for item in items if item.get("code") == payload["code"]]
    if matches:
        item = max(matches, key=lambda value: int(value.get("version_number") or 0))
        if item.get("status") != "approved":
            item = approver.request("POST", f"/catalog/items/{item['id']}/approve")
        return item
    item = engineer.request("POST", f"/catalog/{collection}", payload)
    return approver.request("POST", f"/catalog/items/{item['id']}/approve")


def create_catalog(
    engineer: Client, approver: Client, organization_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    fluid = create_or_reuse_catalog_item(
        engineer,
        approver,
        collection="fluids",
        organization_id=organization_id,
        payload={
            "organization_id": organization_id,
            "code": "EAST-CHINA-DIESEL-2025",
            "name": "Diesel — East China 2025 field benchmark",
            "source": "Wang et al. 2025, Table 2 (public field data)",
            "payload": {
                "category": "diesel",
                "reference_temperature_k": 288.15,
                "reference_pressure_pa": 101325.0,
                "density_kg_m3": RHO_KG_M3,
                "kinematic_viscosity_m2_s": NU_M2_S,
                "data_source": "Public field benchmark; vapor pressure is not published.",
            },
        },
    )
    material = create_or_reuse_catalog_item(
        engineer,
        approver,
        collection="materials",
        organization_id=organization_id,
        payload={
            "organization_id": organization_id,
            "code": "EAST-CHINA-PIPE-2025-ADAPTER",
            "name": "East China 2025 — hydraulic smooth adapter",
            "source": (
                "Wang et al. 2025, Table 2: D=273.1 mm. Roughness=0 and MAWP=8 MPa "
                "are adapter assumptions, not segment-certified values."
            ),
            "payload": {
                "roughness_m": 0.0,
                "mawp_pa": ASSUMED_MAWP_PA,
                "material_family": "Benchmark — unspecified",
                "specification": "Public field data does not publish per-segment MAWP or roughness.",
            },
        },
    )
    return fluid, material


def persisted_resource_contract(topology: dict[str, Any]) -> dict[str, Any]:
    nodes = {str(node.get("code")): node for node in list(topology.get("nodes") or [])}
    edges = {str(edge.get("code")): edge for edge in list(topology.get("edges") or [])}
    assets = list(topology.get("assets") or [])
    expected_nodes = {code: (kind, elevation) for code, _, kind, elevation in NODES}
    expected_edges = {
        code: (from_code, to_code, length_m) for code, from_code, to_code, length_m in EDGES
    }
    if set(nodes) != set(expected_nodes) or set(edges) != set(expected_edges) or assets:
        raise BenchmarkError("La topologie API East China ne respecte pas le modèle source adapté.")
    for code, (expected_kind, expected_elevation_m) in expected_nodes.items():
        node = nodes[code]
        if node.get("kind") != expected_kind or node.get("status") != "available":
            raise BenchmarkError(f"Type ou statut persistant inattendu pour le nœud {code}.")
        if abs(float(node["elevation_m"]) - expected_elevation_m) > 1e-9:
            raise BenchmarkError(f"Altitude persistante inattendue pour le nœud {code}.")
    required_edge_fields = {
        "from_node_code",
        "to_node_code",
        "length_m",
        "inner_diameter_m",
        "roughness_m",
        "mawp_pa",
        "status",
        "profile",
    }
    for code, (expected_from, expected_to, expected_length_m) in expected_edges.items():
        edge = edges[code]
        missing = required_edge_fields - set(edge)
        if missing:
            raise BenchmarkError(f"Champs d'arête absents pour {code}: {sorted(missing)}.")
        if edge["from_node_code"] != expected_from or edge["to_node_code"] != expected_to:
            raise BenchmarkError(f"Hiérarchie persistante inattendue pour l'arête {code}.")
        if abs(float(edge["length_m"]) - expected_length_m) > 1e-9:
            raise BenchmarkError(f"Longueur persistante inattendue pour l'arête {code}.")
        if abs(float(edge["inner_diameter_m"]) - DIAMETER_M) > 1e-12:
            raise BenchmarkError(f"Diamètre persistant inattendu pour l'arête {code}.")
        if abs(float(edge["roughness_m"])) > 1e-12 or float(edge["mawp_pa"]) != ASSUMED_MAWP_PA:
            raise BenchmarkError(f"Paramètres persistants inattendus pour l'arête {code}.")
        if edge["status"] != "available" or len(list(edge["profile"])) != 2:
            raise BenchmarkError(f"Profil ou statut persistant inattendu pour l'arête {code}.")
    return {
        "verified": True,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "asset_count": len(assets),
        "required_edge_fields": sorted(required_edge_fields),
    }


def build_model(
    engineer: Client, approver: Client, organization_id: str, project_code: str
) -> dict[str, Any]:
    geometry = field_geometry()
    project = engineer.request(
        "POST",
        "/projects",
        {
            "organization_id": organization_id,
            "name": "Benchmark terrain — East China 2025",
            "code": next_project_code(engineer, project_code),
            "description": (
                "Tronçon industriel à débit imposé. Reproduction physique et formulation, "
                "pas prédiction pression-débit sans pressions terrain brutes."
            ),
            "project_type": "liquid_pipeline",
            "country_code": "CN",
        },
    )
    fluid, material = create_catalog(engineer, approver, organization_id)
    model = engineer.request(
        "POST",
        f"/projects/{project['id']}/models",
        {
            "name": "East China section 7 — débit mesuré imposé",
            "payload": {
                "units": {"system": "SI"},
                "fluid_catalog_item_id": fluid["id"],
                "network_name": "East China 2025 section 7 — transformed public field data",
                "validation_source": "Wang et al. 2025, Processes 13(8), 2459",
            },
        },
    )
    nodes: dict[str, dict[str, Any]] = {}
    for code, name, kind, elevation_m in NODES:
        nodes[code] = engineer.request(
            "POST",
            f"/models/{model['id']}/nodes",
            {
                "code": code,
                "name": name,
                "kind": kind,
                "elevation_m": elevation_m,
                "status": "available",
                "payload": {},
            },
        )
    for sequence, (code, from_code, to_code, length_m) in enumerate(EDGES, start=1):
        engineer.request(
            "POST",
            f"/models/{model['id']}/edges",
            {
                "from_node_id": nodes[from_code]["id"],
                "to_node_id": nodes[to_code]["id"],
                "material_catalog_item_id": material["id"],
                "code": code,
                "name": f"East China section 7 — {code}",
                "sequence": sequence,
                "length_m": length_m,
                "inner_diameter_m": DIAMETER_M,
                "roughness_m": 0.0,
                "mawp_pa": ASSUMED_MAWP_PA,
                "status": "available",
                "profile": [
                    {"chainage_m": 0.0, "elevation_m": nodes[from_code]["elevation_m"]},
                    {"chainage_m": length_m, "elevation_m": nodes[to_code]["elevation_m"]},
                ],
                "fittings": [],
            },
        )
    validation = engineer.request("POST", f"/models/{model['id']}/validate")
    if not validation.get("valid"):
        raise BenchmarkError(f"Le modèle East China n'est pas valide : {validation}")
    topology = engineer.request("GET", f"/models/{model['id']}/topology")
    contract = persisted_resource_contract(topology)
    scenario = engineer.request(
        "POST",
        f"/models/{model['id']}/scenarios",
        {
            "name": "EC-01 — débit terrain 270 m3/h imposé",
            "description": (
                "Débit mesuré imposé. Pression d'entrée 5 MPa uniquement comme ancrage API, "
                "explicitement exclue de toute conclusion terrain."
            ),
            "payload": {
                "temperature_k": 288.15,
                "imposed_flow_m3_s": MEASURED_FLOW_M3_S,
                "inlet_pressure_pa": ASSUMED_INLET_PRESSURE_PA,
                "outlet_pressure_pa": None,
                "inlet_tank_level_m": None,
                "outlet_tank_level_m": None,
                "pump_overrides": [],
                "station_overrides": [],
                "segment_overrides": [],
                "solver": {
                    "friction_model": "altshul",
                    "pressure_tolerance_pa": 1.0,
                    "flow_tolerance_m3_s": 1e-9,
                    "mass_balance_tolerance": 1e-7,
                    "max_iterations": 100,
                    "profile_step_m": 1_000.0,
                    "store_iterations": False,
                    "use_quadratic_pump_fit": True,
                    "max_flow_m3_s": 1.0,
                    "detect_gravity_zones": True,
                    "apply_gravity_model": False,
                    "min_velocity_m_s": None,
                    "max_velocity_m_s": None,
                },
                "objective": None,
                "energy_price_per_joule": None,
            },
        },
    )
    return {
        "project": project,
        "model": model,
        "scenario": scenario,
        "resource_contract": contract,
        "geometry": geometry,
    }


def wait_calculation(client: Client, calculation: dict[str, Any]) -> dict[str, Any]:
    current = calculation
    deadline = time.monotonic() + 300.0
    while time.monotonic() < deadline:
        status = str(current.get("status") or "")
        if "QUEUED" not in status and "RUNNING" not in status:
            return current
        time.sleep(1.0)
        current = client.request("GET", f"/calculations/{calculation['id']}")
    raise BenchmarkError("Le calcul East China n'a pas terminé en 300 s.")


def execution_gate(calculation: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    calculation_status = str(calculation.get("status") or "")
    result_status = str(result.get("status") or calculation_status)
    warnings = list(result.get("warnings") or [])
    warning_codes = [str(warning.get("code") or "") for warning in warnings]
    unexpected_warning_codes = sorted(set(warning_codes) - EXPECTED_WARNING_CODES)
    checks = {
        "calculation_status": calculation_status in ACCEPTED_CALCULATION_STATUSES,
        "result_status": result_status in ACCEPTED_CALCULATION_STATUSES,
        "feasible": bool(result.get("feasible")),
        "violations": not list(result.get("violations") or []),
        "warning_codes": not unexpected_warning_codes,
    }
    failures = [name for name, passed in checks.items() if not passed]
    passed = not failures
    return {
        "status": "PASS_WITH_EXPECTED_WARNINGS"
        if passed and warnings
        else "PASS"
        if passed
        else "FAIL",
        "passed": passed,
        "checks": checks,
        "calculation_status": calculation_status,
        "result_status": result_status,
        "violation_count": len(result.get("violations") or []),
        "warning_count": len(warnings),
        "warning_codes": warning_codes,
        "unexpected_warning_codes": unexpected_warning_codes,
        "failures": failures,
    }


def compare_result(result: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    physics = source["physics_from_published_inputs"]
    # Le contrat public actuel expose les résultats détaillés sous `segments`.
    # Le nom est contrôlé ici après inspection de la réponse VPS, sans reposer
    # sur une structure interne du moteur.
    segments = list(result.get("segments") or [])
    if len(segments) != 2:
        raise BenchmarkError("Le résultat East China doit contenir deux tronçons hydrauliques.")
    engine_reynolds = [float(segment["reynolds"]) for segment in segments]
    engine_friction_loss_m = sum(float(segment["friction_head_loss_m"]) for segment in segments)
    engine_flow_m3_s = float(segments[0]["flow_m3_s"])
    engine_reynolds_error_percent = (
        100.0 * (engine_reynolds[0] - physics["reynolds"]) / physics["reynolds"]
    )
    engine_friction_error_percent = (
        100.0 * (engine_friction_loss_m - physics["altshul_loss_m"]) / physics["altshul_loss_m"]
    )
    published_reynolds_difference_percent = float(source["published_reynolds_difference_percent"])
    observation = source["published_observation"]
    published_flow_error_percent = (
        100.0
        * (observation["published_calculated_flow_m3_h"] - observation["measured_flow_m3_h"])
        / observation["measured_flow_m3_h"]
    )
    return {
        "measured_flow_is_imposed_input": True,
        "engine_flow_m3_s": engine_flow_m3_s,
        "engine_flow_error_percent": 100.0
        * (engine_flow_m3_s - MEASURED_FLOW_M3_S)
        / MEASURED_FLOW_M3_S,
        "engine_reynolds": engine_reynolds,
        "reynolds_from_published_inputs": physics["reynolds"],
        "engine_reynolds_error_percent": engine_reynolds_error_percent,
        "published_reynolds": observation["published_reynolds"],
        "published_reynolds_difference_percent": published_reynolds_difference_percent,
        "published_reynolds_reconciliation_tolerance_percent": PUBLISHED_REYNOLDS_RECONCILIATION_TOLERANCE_PERCENT,
        "engine_altshul_friction_loss_m": engine_friction_loss_m,
        "analytical_altshul_friction_loss_m": physics["altshul_loss_m"],
        "engine_altshul_friction_error_percent": engine_friction_error_percent,
        "analytical_leibenzon_friction_loss_m": physics["leibenzon_loss_m"],
        "altshul_vs_leibenzon_percent": physics["altshul_vs_leibenzon_percent"],
        "published_pressure_based_flow_m3_h": observation["published_calculated_flow_m3_h"],
        "published_pressure_based_flow_error_percent": published_flow_error_percent,
    }


def physics_reproduction_gate(comparison: dict[str, Any] | None) -> dict[str, Any]:
    """Contrôle que le moteur reproduit les équations avec les entrées EC-01."""

    if comparison is None:
        return {
            "status": "NOT_EVALUATED",
            "passed": False,
            "reason": "EXECUTION_GATE_FAILED",
        }
    checks = {
        "flow": abs(float(comparison["engine_flow_error_percent"]))
        <= PHYSICS_REPRODUCTION_TOLERANCE_PERCENT,
        "reynolds": abs(float(comparison["engine_reynolds_error_percent"]))
        <= PHYSICS_REPRODUCTION_TOLERANCE_PERCENT,
        "altshul_friction": abs(float(comparison["engine_altshul_friction_error_percent"]))
        <= PHYSICS_REPRODUCTION_TOLERANCE_PERCENT,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "status": "PASS" if not failures else "FAIL",
        "passed": not failures,
        "tolerance_percent": PHYSICS_REPRODUCTION_TOLERANCE_PERCENT,
        "checks": checks,
        "failures": failures,
    }


def run_benchmark(
    engineer: Client,
    approver: Client,
    *,
    project_code: str,
    expected_git_sha: str | None,
) -> dict[str, Any]:
    version = engineer.request("GET", "/version")
    actual_sha = str(version.get("git_sha") or "")
    if not actual_sha:
        raise BenchmarkError("L'endpoint /version ne publie pas git_sha à la racine.")
    if expected_git_sha and actual_sha != expected_git_sha:
        raise BenchmarkError(f"L'API sert {actual_sha!r}, pas le SHA attendu {expected_git_sha!r}.")
    organizations = page(engineer, "/organizations?limit=20&offset=0")
    if len(organizations) != 1:
        raise BenchmarkError(
            f"Le benchmark attend une seule organisation, trouvé={len(organizations)}."
        )
    source = source_checks()
    built = build_model(engineer, approver, str(organizations[0]["id"]), project_code)
    calculation = engineer.request(
        "POST",
        f"/scenarios/{built['scenario']['id']}/calculations",
        {"engine": "long_distance_liquid"},
        idempotency_key=f"benchmark-east-china-{uuid.uuid4()}",
    )
    calculation = wait_calculation(engineer, calculation)
    result_response = engineer.request("GET", f"/calculations/{calculation['id']}/results")
    result = result_response.get("result") or {}
    if not result:
        raise BenchmarkError(f"Le calcul East China ne contient aucun résultat : {result_response}")
    gate = execution_gate(calculation, result)
    comparison = compare_result(result, source) if gate["passed"] else None
    physics_gate = physics_reproduction_gate(comparison)
    published_reynolds_reconciled = bool(source["published_reynolds_reconciled"])
    return {
        "benchmark": "FIELD-EAST-CHINA-2025-EC01",
        "classification": "field_geometry_fixed_measured_flow_physics_reproduction",
        "source": {
            "paper": "Wang et al., Processes 13(8), 2459 (2025), DOI 10.3390/pr13082459",
            "field_data": "validation/public/field_east_china_2025/segment7.csv",
            "observation": "validation/public/field_east_china_2025/reference_observation.csv",
            "raw_field_pressures_publicly_available": False,
        },
        "api_version": version,
        "project": {
            "id": built["project"]["id"],
            "code": built["project"]["code"],
            "model_id": built["model"]["id"],
            "scenario_id": built["scenario"]["id"],
            "calculation_id": calculation["id"],
        },
        "persisted_resource_contract": built["resource_contract"],
        "source_checks": source,
        "adapter_assumptions": {
            "inlet_pressure_pa": ASSUMED_INLET_PRESSURE_PA,
            "inlet_pressure_is_field_measurement": False,
            "mawp_pa": ASSUMED_MAWP_PA,
            "mawp_is_segment_certified_value": False,
            "roughness_m": 0.0,
            "roughness_is_published_segment_measurement": False,
        },
        "calculation": {
            "status": calculation.get("status"),
            "engine_version": calculation.get("engine_version"),
            "input_hash": calculation.get("input_hash"),
            "result_status": result.get("status"),
            "feasible": result.get("feasible"),
            "min_pressure_pa": result.get("min_pressure_pa"),
            "max_pressure_pa": result.get("max_pressure_pa"),
            "violation_count": len(result.get("violations") or []),
            "warning_count": len(result.get("warnings") or []),
        },
        "execution_gate": gate,
        "comparison": comparison,
        "physics_reproduction_gate": physics_gate,
        "verdicts": {
            "physics_reproduction_verdict": physics_gate["status"],
            "physics_reproduction_scope": (
                "HydroLiquid reproduit à débit imposé les propriétés, géométrie, régime et "
                "perte Altshul calculée depuis les entrées publiques."
            ),
            "published_reynolds_reconciliation_verdict": (
                "PASS" if published_reynolds_reconciled else "NOT_RECONCILED"
            ),
            "published_reynolds_reconciliation_reason": (
                "Les données publiques D=273.1 mm, nu=4.72e-6 m2/s et Q=270 m3/h produisent "
                f"Re={source['physics_from_published_inputs']['reynolds']:.3f}, pas "
                f"Re={PUBLISHED_REYNOLDS:.0f}; aucune donnée n'est modifiée pour masquer cet écart."
            ),
            "field_data_comparison_verdict": "NOT_EVALUATED",
            "field_data_comparison_reason": "MEASURED_FLOW_USED_AS_INPUT",
            "predictive_validation_verdict": "NOT_EVALUATED",
            "predictive_validation_reason": "RAW_FIELD_PRESSURES_NOT_PUBLICLY_AVAILABLE",
            "certification": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email")
    parser.add_argument("--password")
    parser.add_argument("--access-token-env")
    parser.add_argument("--approver-email")
    parser.add_argument("--approver-password")
    parser.add_argument("--approver-access-token-env")
    parser.add_argument("--project-code", default=PROJECT_CODE_DEFAULT)
    parser.add_argument("--expected-git-sha")
    parser.add_argument("--output", type=Path, default=OUTPUT_DEFAULT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engineer = Client(args.base_url)
    approver = Client(args.base_url)
    authenticate(
        engineer,
        email=args.email,
        password=args.password,
        token_env=args.access_token_env,
    )
    authenticate(
        approver,
        email=args.approver_email,
        password=args.approver_password,
        token_env=args.approver_access_token_env,
    )
    report = run_benchmark(
        engineer,
        approver,
        project_code=args.project_code,
        expected_git_sha=args.expected_git_sha,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Preuve écrite dans {args.output}")
    return 0 if report["execution_gate"]["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
