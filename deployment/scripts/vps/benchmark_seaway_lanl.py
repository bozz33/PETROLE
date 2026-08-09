#!/usr/bin/env python3
"""Construit et rejoue le benchmark public complet Seaway/LANL dans PETROLE.

Le script n'utilise que l'API publique. Il transforme le cas machine-readable
`case_seaway.m` de PetroleumModels.jl vers le modèle linéaire normalisé de
PETROLE, exécute HydroLiquid et produit une preuve JSON comparative.

Nature de la preuve : **rejeu hydraulique de formulation distincte**. Le cas
LANL est synthétisé à partir d'un système réel et de données publiques ; il ne
remplace pas des mesures SCADA industrielles confidentielles. Les quatre débits
publiés servent ici à fixer les conditions limites : ils ne constituent donc
pas, à eux seuls, une validation indépendante de PETROLE.

Deux transformations sont explicitement assumées :

1. les pompes LANL sont des arêtes de longueur nulle, alors que PETROLE place
   les pompes sur des nœuds station. Les extrémités de chaque pompe ont la même
   altitude dans le cas LANL ; elles sont donc regroupées à un même chainage.
   À l'origine, un connecteur hydraulique synthétique de 1 mm sépare le nœud
   source de la première station, car PETROLE distingue ces deux rôles ;
2. le cas LANL ne fournit pas de MAWP de conduite. PETROLE exige ce champ pour
   un tronçon : 10 MPa est utilisé comme **ASSUMPTION non bloquante**, jamais
   comme donnée du vrai Seaway.

Exemple :

    python deployment/scripts/vps/benchmark_seaway_lanl.py \
      --base-url https://petrole.distesage.com/api/v1 \
      --email "$RECETTE_ENGINEER_EMAIL" --password "$RECETTE_ENGINEER_PASSWORD" \
      --approver-email "$RECETTE_APPROVER_EMAIL" \
      --approver-password "$RECETTE_APPROVER_PASSWORD"

Pour l'automatisation VPS, les deux comptes peuvent aussi être injectés sous
forme de jetons courts :

    ... --access-token-env BENCH_ENGINEER_TOKEN \
        --approver-access-token-env BENCH_APPROVER_TOKEN
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
DATA_DIR = ROOT / "validation/public/seaway_lanl"
PROJECT_CODE_DEFAULT = "BENCH-SEAWAY-LANL"
OUTPUT_DEFAULT = ROOT / "var/validation-vps/benchmark-seaway-lanl.json"

RHO_KG_M3 = 827.0
NU_M2_S = 4.9e-6
LANL_G = 9.8
PETROLE_G = 9.80665
DIAMETER_M = 0.75
BETA = 0.0246
LEIBENZON_M = 0.25
SYNTHETIC_CONNECTOR_LENGTH_M = 0.001
ASSUMED_MAWP_PA = 10_000_000.0
SOURCE_PRESSURE_HEAD_M = 190.0
INLET_FLOW_M3_S = 0.3567

# Allocation reconstruite par bilan de masse à partir des quatre débits publiés
# dans le test officiel PetroleumModels.jl/test/opf.jl.
INJECTION_N9_M3_S = 0.6077
OFFTAKE_N15_M3_S = 0.8255
INJECTION_N18_M3_S = 0.5789
TERMINAL_FLOW_M3_S = 0.7178

# Point de fonctionnement transformé, pré-enregistré dans
# reference_operating_point.csv. Il est dérivé des équations LANL sous allocation
# fixe, contraintes de charge/pompe/rendement, puis minimisation du coût de pompage.
PUMP_SPEED_RATIOS = {
    "P1": 0.80534824,
    "P2": 0.80534824,
    "P4": 0.80534824,
    "P7": 0.80534824,
    "P10": 1.04550752,
    "P12": 1.04547034,
    "P13": 1.04546422,
    "P19": 0.97734783,
    "P21": 0.83155304,
}

# Les nœuds de pompe de longueur nulle du modèle LANL sont regroupés :
# (code PETROLE, nom, altitude, pompes sur ce chainage, type spécial éventuel).
# Les longueurs réelles restent celles des 13 conduites LANL.
MODEL_LOCATIONS = [
    ("SRC-N1", "Injection amont N1", 273.0, [], "source"),
    ("ST-N3", "Station N1-N3 — P1 + P2", 273.0, ["P1", "P2"], "station"),
    ("ST-N5", "Station N4-N5 — P4", 293.0, ["P4"], "station"),
    ("JN-N6", "Jonction N6", 201.0, [], "junction"),
    ("ST-N8", "Station N7-N8 — P7", 266.0, ["P7"], "station"),
    ("INJ-N9", "Injection N9", 180.0, [], "injection"),
    ("ST-N11", "Station N10-N11 — P10", 153.0, ["P10"], "station"),
    ("ST-N14", "Station N12-N14 — P12 + P13", 146.0, ["P12", "P13"], "station"),
    ("OFF-N15", "Soutirage N15", 107.0, [], "offtake"),
    ("JN-N16", "Jonction N16", 106.0, [], "junction"),
    ("JN-N17", "Jonction N17", 92.0, [], "junction"),
    ("INJ-N18", "Injection N18", 92.0, [], "injection"),
    ("ST-N20", "Station N19-N20 — P19", 202.0, ["P19"], "station"),
    ("ST-N22", "Station N21-N22 — P21", 95.0, ["P21"], "station"),
    ("TERM-N23", "Terminal N23", 2.0, [], "terminal"),
]

# Arêtes PETROLE dans l'ordre. Le premier connecteur est synthétique et déclaré.
EDGE_LAYOUT = [
    ("X-CONN", SYNTHETIC_CONNECTOR_LENGTH_M, "SRC-N1", "ST-N3", None),
    ("L3", 154_000.0, "ST-N3", "ST-N5", 3),
    ("L5", 3_800.0, "ST-N5", "JN-N6", 5),
    ("L6", 132_000.0, "JN-N6", "ST-N8", 6),
    ("L8", 106_300.0, "ST-N8", "INJ-N9", 8),
    ("L9", 36_000.0, "INJ-N9", "ST-N11", 9),
    ("L11", 165_000.0, "ST-N11", "ST-N14", 11),
    ("L14", 2_940.0, "ST-N14", "OFF-N15", 14),
    ("L15", 870.0, "OFF-N15", "JN-N16", 15),
    ("L16", 83_200.0, "JN-N16", "JN-N17", 16),
    ("L17", 10_700.0, "JN-N17", "INJ-N18", 17),
    ("L18", 87_000.0, "INJ-N18", "ST-N20", 18),
    ("L20", 173_600.0, "ST-N20", "ST-N22", 20),
    ("L22", 13_620.0, "ST-N22", "TERM-N23", 22),
]

REFERENCE_FLOW_BY_PIPE = {3: 0.3567, 9: 0.9644, 15: 0.1389, 22: 0.7178}

# Portes définies avant toute exécution. Elles qualifient seulement la bonne
# exécution du rejeu dans PETROLE ; elles ne confèrent pas de verdict de
# validation externe, car le point de fonctionnement et les charges de
# référence sont dérivés des mêmes sorties LANL.
ACCEPTED_CALCULATION_STATUSES = frozenset({"SIM_CONVERGED"})
MAXIMUM_VIOLATION_COUNT = 0
MAXIMUM_WARNING_COUNT = 0
EXECUTION_GATE = {
    "accepted_statuses": sorted(ACCEPTED_CALCULATION_STATUSES),
    "require_feasible": True,
    "maximum_violation_count": MAXIMUM_VIOLATION_COUNT,
    "maximum_warning_count": MAXIMUM_WARNING_COUNT,
}


class BenchmarkError(RuntimeError):
    """Erreur explicite de préparation ou d'exécution du benchmark."""


class Client:
    """Client HTTP minimal sans dépendance tierce."""

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
        token = self.request("POST", "/auth/login", {"email": email, "password": password})
        self.token = str(token["access_token"])


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
        value = os.environ.get(token_env)
        if not value:
            raise BenchmarkError(f"La variable {token_env!r} est absente ou vide.")
        client.token = value
        return
    if not email or not password:
        raise BenchmarkError("Fournissez email/password ou un jeton court via --*-token-env.")
    client.login(email, password)


def page(client: Client, path: str) -> list[dict[str, Any]]:
    response = client.request("GET", path)
    return list(response.get("items", []))


def load_csv(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / name
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def pump_curve() -> dict[str, Any]:
    """Échantillonne exactement les lois nominales LANL sur le domaine utile."""

    flows = [round(0.30 + 0.05 * index, 10) for index in range(19)]  # 0.30 → 1.20
    heads = [276.8 - 92.0 * q * q for q in flows]
    efficiencies = [2.0 * 0.87 * q - 0.87 * q * q for q in flows]
    return {
        "flows_m3_s": flows,
        "heads_m": heads,
        "efficiencies": efficiencies,
        "reference_speed_rpm": 3000.0,
        "interpolation": "pchip",
    }


def leibenzon_loss_m(flow_m3_s: float, length_m: float) -> float:
    return (
        1.02
        * BETA
        * flow_m3_s ** (2.0 - LEIBENZON_M)
        * NU_M2_S**LEIBENZON_M
        / DIAMETER_M ** (5.0 - LEIBENZON_M)
        * length_m
    )


def lanl_pump_head_m(flow_m3_s: float, speed_ratio: float) -> float:
    return 276.8 * speed_ratio * speed_ratio - 92.0 * flow_m3_s * flow_m3_s


def flow_by_pipe() -> dict[int, float]:
    """Débit de chaque conduite physique sous l'allocation de référence."""

    values: dict[int, float] = {}
    current = INLET_FLOW_M3_S
    for _, _, _, _, source_pipe_id in EDGE_LAYOUT:
        if source_pipe_id is None:
            continue
        if source_pipe_id == 9:
            current += INJECTION_N9_M3_S
        if source_pipe_id == 15:
            current -= OFFTAKE_N15_M3_S
        if source_pipe_id == 18:
            current += INJECTION_N18_M3_S
        values[source_pipe_id] = current
    return values


def reference_pressure_heads() -> dict[str, float]:
    rows = load_csv("reference_operating_point.csv")
    return {row["id"]: float(row["value"]) for row in rows if row["kind"] == "pressure_head"}


def check_source_dataset() -> dict[str, Any]:
    junctions = load_csv("junctions.csv")
    pipes = load_csv("pipes.csv")
    pumps = load_csv("pumps.csv")
    producers = load_csv("producers.csv")
    consumers = load_csv("consumers.csv")
    if len(junctions) != 23 or len(pipes) != 13 or len(pumps) != 9:
        raise BenchmarkError("Le jeu Seaway LANL n'a pas la cardinalité attendue 23/13/9.")
    total_length_m = sum(float(row["length_m"]) for row in pipes)
    if abs(total_length_m - 969_030.0) > 1e-6:
        raise BenchmarkError(f"Longueur LANL inattendue : {total_length_m} m.")
    if len(producers) != 3 or len(consumers) != 2:
        raise BenchmarkError("Le jeu doit contenir 3 producteurs et 2 consommateurs.")
    balance = INLET_FLOW_M3_S + INJECTION_N9_M3_S + INJECTION_N18_M3_S
    balance -= OFFTAKE_N15_M3_S + TERMINAL_FLOW_M3_S
    if abs(balance) > 1e-12:
        raise BenchmarkError(f"Allocation reconstruite non équilibrée : {balance} m3/s.")
    return {
        "junction_count": len(junctions),
        "pipe_count": len(pipes),
        "pump_count": len(pumps),
        "producer_count": len(producers),
        "consumer_count": len(consumers),
        "physical_pipe_length_m": total_length_m,
        "allocation_balance_m3_s": balance,
    }


def next_project_code(engineer: Client, requested_code: str) -> str:
    """Évite qu'un rejeu laisse le benchmark bloqué par un code déjà utilisé."""

    projects = page(engineer, "/projects?include_archived=true&limit=200&offset=0")
    codes = {str(project.get("code", "")) for project in projects}
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
    """Réutilise une version approuvée plutôt que de dupliquer le catalogue.

    Les codes de catalogue sont uniques par organisation et famille. Cette
    fonction rend un rejeu résilient après une interruption partielle, sans
    contourner l'approbation métier de l'API.
    """

    items = page(
        engineer,
        f"/catalog/{collection}?organization_id={organization_id}&limit=500&offset=0",
    )
    matches = [item for item in items if item.get("code") == payload["code"]]
    if matches:
        item = max(matches, key=lambda value: int(value.get("version_number", 0)))
        if item.get("status") != "approved":
            item = approver.request("POST", f"/catalog/items/{item['id']}/approve")
        return item
    item = engineer.request("POST", f"/catalog/{collection}", payload)
    return approver.request("POST", f"/catalog/items/{item['id']}/approve")


def execution_gate(calculation: dict[str, Any], result_payload: dict[str, Any]) -> dict[str, Any]:
    """Évalue explicitement le rejeu avant toute interprétation scientifique.

    Un JSON de calcul non vide ne signifie pas qu'un cas est physiquement
    réalisable. Cette porte est volontairement stricte pour qu'un avertissement,
    une violation ou une non-convergence ne soit jamais présenté comme un
    benchmark réussi.
    """

    calculation_status = str(calculation.get("status") or "")
    result_status = str(result_payload.get("status") or calculation_status)
    violation_count = len(result_payload.get("violations") or [])
    warning_count = len(result_payload.get("warnings") or [])
    checks = {
        "calculation_status": calculation_status in ACCEPTED_CALCULATION_STATUSES,
        "result_status": result_status in ACCEPTED_CALCULATION_STATUSES,
        "feasible": bool(result_payload.get("feasible")),
        "violations": violation_count <= MAXIMUM_VIOLATION_COUNT,
        "warnings": warning_count <= MAXIMUM_WARNING_COUNT,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "status": "PASS" if not failures else "FAIL",
        "criteria": EXECUTION_GATE,
        "checks": checks,
        "calculation_status": calculation_status,
        "result_status": result_status,
        "feasible": bool(result_payload.get("feasible")),
        "violation_count": violation_count,
        "warning_count": warning_count,
        "failures": failures,
    }


def create_catalog(
    engineer: Client,
    approver: Client,
    organization_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    fluid = create_or_reuse_catalog_item(
        engineer,
        approver,
        collection="fluids",
        organization_id=organization_id,
        payload={
            "organization_id": organization_id,
            "code": "LANL-SEAWAY-CRUDE",
            "name": "Crude oil — LANL Seaway benchmark",
            "source": "Khlebnikova et al. 2021 / PetroleumModels.jl case_seaway.m",
            "payload": {
                "category": "crude",
                "reference_temperature_k": 288.15,
                "reference_pressure_pa": 101325.0,
                "density_kg_m3": RHO_KG_M3,
                "kinematic_viscosity_m2_s": NU_M2_S,
                "data_source": (
                    "PUBLIC source: LANL PetroleumModels.jl case_seaway.m; "
                    "rho=827 kg/m3, nu=4.9e-6 m2/s."
                ),
            },
        },
    )

    pump = create_or_reuse_catalog_item(
        engineer,
        approver,
        collection="pumps",
        organization_id=organization_id,
        payload={
            "organization_id": organization_id,
            "code": "LANL-SEAWAY-PUMP",
            "name": "Variable-speed pump — LANL Seaway",
            "source": "Khlebnikova et al. 2021, eq. 17 and case_seaway.m",
            "payload": {
                "curve": pump_curve(),
                "manufacturer": "Benchmark model — no real manufacturer claimed",
                "min_speed_ratio": 0.8,
                "max_speed_ratio": 1.2,
                "data_source": (
                    "H=276.8-92 Q^2 at 3000 rpm; eta_nom=0.87, Q_nom=1 m3/s. "
                    "No manufacturer NPSHr is available in the public case."
                ),
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
            "code": "LANL-SEAWAY-PIPE-ASSUMPTION",
            "name": "Conduite benchmark — MAWP non publiée",
            "source": (
                "Diameter from case_seaway.m. MAWP=10 MPa is an adapter ASSUMPTION, "
                "not a property of the real Seaway system."
            ),
            "payload": {
                "roughness_m": 0.0,
                "mawp_pa": ASSUMED_MAWP_PA,
                "material_family": "Benchmark — unspecified",
                "specification": "Not published in LANL benchmark",
            },
        },
    )
    return fluid, pump, material


def node_payload(code: str, kind: str) -> dict[str, Any]:
    if kind == "station":
        pump_count = 2 if code in {"ST-N3", "ST-N14"} else 1
        return {
            "arrangement": "series",
            "drive_efficiency": 0.966 * 0.95,
            "label": f"{pump_count} pompe(s) LANL en série",
        }
    if kind == "injection":
        return {"flow_m3_s": INJECTION_N9_M3_S if code == "INJ-N9" else INJECTION_N18_M3_S}
    if kind == "offtake":
        return {"flow_m3_s": OFFTAKE_N15_M3_S}
    return {}


def build_model(
    engineer: Client,
    approver: Client,
    organization_id: str,
    project_code: str,
) -> dict[str, Any]:
    resolved_project_code = next_project_code(engineer, project_code)
    project = engineer.request(
        "POST",
        "/projects",
        {
            "organization_id": organization_id,
            "name": "Benchmark public — Seaway LANL",
            "code": resolved_project_code,
            "description": (
                "Cas complet de pétrole brut provenant de PetroleumModels.jl. "
                "Cross-solver benchmark, pas données SCADA du vrai Seaway."
            ),
            "project_type": "liquid_pipeline",
            "country_code": "US",
        },
    )
    fluid, pump, material = create_catalog(engineer, approver, organization_id)
    model = engineer.request(
        "POST",
        f"/projects/{project['id']}/models",
        {
            "name": "Seaway LANL — allocation de référence",
            "payload": {
                "units": {"system": "SI"},
                "fluid_catalog_item_id": fluid["id"],
                "network_name": "Seaway crude pipeline test system — transformed",
                "validation_source": "LANL PetroleumModels.jl / AIChE Journal 2021",
            },
        },
    )
    model_id = model["id"]

    nodes: dict[str, dict[str, Any]] = {}
    pumps_by_station: dict[str, list[str]] = {}
    for code, name, elevation, pump_ids, kind in MODEL_LOCATIONS:
        node = engineer.request(
            "POST",
            f"/models/{model_id}/nodes",
            {
                "code": code,
                "name": name,
                "kind": kind,
                "elevation_m": elevation,
                "status": "available",
                "payload": node_payload(code, kind),
            },
        )
        nodes[code] = node
        if pump_ids:
            pumps_by_station[code] = pump_ids

    for sequence, (edge_code, length_m, start_code, end_code, source_pipe_id) in enumerate(
        EDGE_LAYOUT, start=1
    ):
        start = nodes[start_code]
        end = nodes[end_code]
        engineer.request(
            "POST",
            f"/models/{model_id}/edges",
            {
                "from_node_id": start["id"],
                "to_node_id": end["id"],
                "material_catalog_item_id": material["id"],
                "code": edge_code,
                "name": (
                    "Connecteur source-station — ASSUMPTION"
                    if source_pipe_id is None
                    else f"LANL pipe {source_pipe_id}"
                ),
                "sequence": sequence,
                "length_m": length_m,
                "inner_diameter_m": DIAMETER_M,
                "roughness_m": 0.0,
                "mawp_pa": ASSUMED_MAWP_PA,
                "status": "available",
                "profile": [
                    {"chainage_m": 0.0, "elevation_m": start["elevation_m"]},
                    {"chainage_m": length_m, "elevation_m": end["elevation_m"]},
                ],
                "fittings": [],
                "payload": {
                    "source_pipe_id": source_pipe_id,
                    "provenance": "ASSUMPTION" if source_pipe_id is None else "LANL",
                },
            },
        )

    for station_code, pump_ids in pumps_by_station.items():
        for pump_id in pump_ids:
            engineer.request(
                "POST",
                f"/models/{model_id}/assets",
                {
                    "catalog_item_id": pump["id"],
                    "node_id": nodes[station_code]["id"],
                    "code": pump_id,
                    "name": f"LANL {pump_id}",
                    "role": "main",
                    "status": "available",
                    "payload": {
                        "running": True,
                        "speed_ratio": PUMP_SPEED_RATIOS[pump_id],
                    },
                },
            )

    validation = engineer.request("POST", f"/models/{model_id}/validate")
    if not validation.get("valid"):
        raise BenchmarkError(f"Le réseau PETROLE transformé n'est pas valide : {validation}")

    scenario = engineer.request(
        "POST",
        f"/models/{model_id}/scenarios",
        {
            "name": "Allocation LANL de référence — point transformé",
            "description": (
                "Débits officiels LANL reconstruits par bilan de masse ; vitesses de pompe "
                "dérivées et déclarées dans reference_operating_point.csv."
            ),
            "payload": {
                "temperature_k": 288.15,
                "imposed_flow_m3_s": INLET_FLOW_M3_S,
                "inlet_pressure_pa": SOURCE_PRESSURE_HEAD_M * RHO_KG_M3 * PETROLE_G,
                "outlet_pressure_pa": None,
                "inlet_tank_level_m": None,
                "outlet_tank_level_m": None,
                "pump_overrides": [
                    {
                        "pump_id": pump_id,
                        "status": "available",
                        "running": True,
                        "speed_ratio": ratio,
                    }
                    for pump_id, ratio in PUMP_SPEED_RATIOS.items()
                ],
                "station_overrides": [],
                "segment_overrides": [],
                "solver": {
                    "friction_model": "altshul",
                    "pressure_tolerance_pa": 1.0,
                    "flow_tolerance_m3_s": 1e-9,
                    "mass_balance_tolerance": 1e-7,
                    "max_iterations": 100,
                    "profile_step_m": 5_000.0,
                    "store_iterations": False,
                    "use_quadratic_pump_fit": True,
                    "max_flow_m3_s": 2.0,
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
        "validation": validation,
    }


def wait_calculation(client: Client, calculation: dict[str, Any]) -> dict[str, Any]:
    current = calculation
    deadline = time.monotonic() + 300.0
    while time.monotonic() < deadline:
        status = str(current.get("status", ""))
        if "QUEUED" not in status and "RUNNING" not in status:
            return current
        time.sleep(1.0)
        current = client.request("GET", f"/calculations/{calculation['id']}")
    raise BenchmarkError("Le calcul Seaway n'a pas terminé en 300 s.")


def closest_profile_point(profile: list[dict[str, Any]], chainage_m: float) -> dict[str, Any]:
    if not profile:
        raise BenchmarkError("Le résultat ne contient aucun profil hydraulique.")
    return min(profile, key=lambda item: abs(float(item["chainage_m"]) - chainage_m))


def chainages() -> dict[str, float]:
    result: dict[str, float] = {"SRC-N1": 0.0}
    current = 0.0
    for _, length_m, _, end_code, _ in EDGE_LAYOUT:
        current += length_m
        result[end_code] = current
    return result


def lanl_checkpoint_map() -> dict[str, str]:
    # Après une station, PETROLE expose la charge après toutes les pompes du nœud.
    return {
        "SRC-N1": "N1",
        "ST-N3": "N3",
        "ST-N5": "N5",
        "JN-N6": "N6",
        "ST-N8": "N8",
        "INJ-N9": "N9",
        "ST-N11": "N11",
        "ST-N14": "N14",
        "OFF-N15": "N15",
        "JN-N16": "N16",
        "JN-N17": "N17",
        "INJ-N18": "N18",
        "ST-N20": "N20",
        "ST-N22": "N22",
        "TERM-N23": "N23",
    }


def compare_result(result_payload: dict[str, Any]) -> dict[str, Any]:
    profile = list(result_payload.get("profile") or [])
    locations = chainages()

    # Débits officiels utilisés par le test LANL. Ils ne sont pas tous saisis
    # directement : N9/N15/N18 changent le débit via les injections/soutirages.
    flow_checks = {
        "pipe_3": (locations["ST-N3"], REFERENCE_FLOW_BY_PIPE[3]),
        "pipe_9": (locations["INJ-N9"], REFERENCE_FLOW_BY_PIPE[9]),
        "pipe_15": (locations["OFF-N15"], REFERENCE_FLOW_BY_PIPE[15]),
        "pipe_22": (locations["INJ-N18"], REFERENCE_FLOW_BY_PIPE[22]),
    }
    flow_rows: list[dict[str, Any]] = []
    for label, (position, expected) in flow_checks.items():
        point = closest_profile_point(profile, position)
        actual = float(point["flow_m3_s"])
        flow_rows.append(
            {
                "reference": label,
                "chainage_m": position,
                "expected_m3_s": expected,
                "petrole_m3_s": actual,
                "absolute_error_m3_s": actual - expected,
                "relative_error_percent": 100.0 * (actual - expected) / expected,
            }
        )

    expected_heads = reference_pressure_heads()
    head_rows: list[dict[str, Any]] = []
    for petrole_code, lanl_code in lanl_checkpoint_map().items():
        point = closest_profile_point(profile, locations[petrole_code])
        petrole_pressure_head = float(point["pressure_pa"]) / (RHO_KG_M3 * PETROLE_G)
        expected = expected_heads[lanl_code]
        head_rows.append(
            {
                "petrole_node": petrole_code,
                "lanl_node": lanl_code,
                "chainage_m": locations[petrole_code],
                "lanl_pressure_head_m": expected,
                "petrole_pressure_head_m": petrole_pressure_head,
                "difference_m": petrole_pressure_head - expected,
            }
        )

    # Comparaison de formulation sur chaque conduite : LANL Leibenzon contre
    # PETROLE Altshul lisse. L'écart n'est pas calibré après observation.
    source_flows = flow_by_pipe()
    pipe_rows = []
    for _, length_m, _, _, source_pipe_id in EDGE_LAYOUT:
        if source_pipe_id is None:
            continue
        q = source_flows[source_pipe_id]
        expected_loss = leibenzon_loss_m(q, length_m)
        # Forme PETROLE d'Altshul, réécrite ici uniquement pour publier la
        # différence théorique de modèle avant de regarder le résultat réseau.
        area = math.pi * DIAMETER_M**2 / 4.0
        velocity = q / area
        reynolds = velocity * DIAMETER_M / NU_M2_S
        friction_factor = 0.11 * (68.0 / reynolds) ** 0.25
        petrole_formula_loss = (
            friction_factor * (length_m / DIAMETER_M) * velocity * velocity / (2.0 * PETROLE_G)
        )
        pipe_rows.append(
            {
                "lanl_pipe_id": source_pipe_id,
                "flow_m3_s": q,
                "length_m": length_m,
                "lanl_leibenzon_loss_m": expected_loss,
                "petrole_altshul_formula_loss_m": petrole_formula_loss,
                "formula_difference_percent": 100.0
                * (petrole_formula_loss - expected_loss)
                / expected_loss,
            }
        )

    return {
        "flow_checks": flow_rows,
        "pressure_head_checkpoints": head_rows,
        "pipe_formula_comparison": pipe_rows,
        "max_abs_flow_relative_error_percent": max(
            abs(float(row["relative_error_percent"])) for row in flow_rows
        ),
        "max_abs_pressure_head_difference_m": max(
            abs(float(row["difference_m"])) for row in head_rows
        ),
        "max_abs_pipe_formula_difference_percent": max(
            abs(float(row["formula_difference_percent"])) for row in pipe_rows
        ),
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
            f"Le benchmark attend l'instance mono-exploitant ; organisations={len(organizations)}."
        )
    organization_id = str(organizations[0]["id"])
    source = check_source_dataset()
    built = build_model(engineer, approver, organization_id, project_code)

    calculation = engineer.request(
        "POST",
        f"/scenarios/{built['scenario']['id']}/calculations",
        {"engine": "long_distance_liquid"},
        idempotency_key=f"benchmark-seaway-{uuid.uuid4()}",
    )
    calculation = wait_calculation(engineer, calculation)
    result = engineer.request("GET", f"/calculations/{calculation['id']}/results")
    result_payload = result.get("result") or {}
    if not result_payload:
        raise BenchmarkError(f"Le calcul ne contient aucun résultat : {result}")

    replay_gate = execution_gate(calculation, result_payload)
    comparison = compare_result(result_payload) if replay_gate["status"] == "PASS" else None
    return {
        "benchmark": "PUBLIC-SEAWAY-LANL-01",
        "classification": "complete_pipeline_cross_formulation_replay",
        "source": {
            "paper": "Khlebnikova et al., AIChE Journal 2021, DOI 10.1002/aic.17124",
            "machine_data": "lanl-ansi/PetroleumModels.jl test/data/case_seaway.m",
            "source_model_is_synthesized": True,
        },
        "adapter_assumptions": {
            "synthetic_source_station_connector_m": SYNTHETIC_CONNECTOR_LENGTH_M,
            "mawp_pa": ASSUMED_MAWP_PA,
            "mawp_is_real_pipeline_value": False,
            "friction_mapping": "LANL Leibenzon smooth ↔ PETROLE Altshul epsilon=0",
            "pump_edge_mapping": "zero-length LANL pump edges collapsed onto PETROLE station nodes",
        },
        "api_version": version,
        "project": {
            "id": built["project"]["id"],
            "code": built["project"]["code"],
            "model_id": built["model"]["id"],
            "scenario_id": built["scenario"]["id"],
            "calculation_id": calculation["id"],
        },
        "source_dataset": source,
        "calculation": {
            "status": calculation.get("status"),
            "engine_version": calculation.get("engine_version"),
            "input_hash": calculation.get("input_hash"),
            "result_status": result_payload.get("status"),
            "feasible": result_payload.get("feasible"),
            "min_pressure_pa": result_payload.get("min_pressure_pa"),
            "max_pressure_pa": result_payload.get("max_pressure_pa"),
            "total_power_w": result_payload.get("total_power_w"),
            "violation_count": len(result_payload.get("violations") or []),
            "warning_count": len(result_payload.get("warnings") or []),
        },
        "execution_gate": replay_gate,
        "comparison": comparison,
        "interpretation": {
            "flow_reference_is_official_lanl_test_output": True,
            "pressure_head_reference_is_derived_from_lanl_equations": True,
            "independent_validation_verdict": "NOT_EVALUATED",
            "independent_validation_reason": (
                "Les débits LANL servent à reconstruire les injections/soutirages et les "
                "charges/vitesses du fichier reference_operating_point.csv sont DERIVED. "
                "Une validation cross-solver indépendante exige une sortie native et figée "
                "de PetroleumModels.jl (pressions nodales, vitesses, puissances)."
            ),
            "field_validation": False,
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
    return 0 if report["execution_gate"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
