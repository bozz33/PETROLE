#!/usr/bin/env python3
"""Construit et rejoue le benchmark public complet Seaway/LANL dans PETROLE.

Le script n'utilise que l'API publique. Il transforme le cas machine-readable
`case_seaway.m` de PetroleumModels.jl vers le modèle linéaire normalisé de
PETROLE, exécute HydroLiquid et produit une preuve JSON comparative.

Nature de la preuve : **comparaison cross-solver à point imposé**. Le cas LANL
est synthétisé à partir d'un système réel et de données publiques ; il ne
remplace pas des mesures SCADA industrielles confidentielles. Une sortie OPF
native, figée et versionnée de PetroleumModels.jl fournit les débits, vitesses
et charges de comparaison. PETROLE rejoue ce point : c'est une vérification
cross-solver, non une validation prédictive indépendante.

Deux transformations sont explicitement assumées :

1. les pompes LANL sont des arêtes de longueur nulle, alors que PETROLE place
   les pompes sur des nœuds station. Les extrémités de chaque pompe ont la même
   altitude dans le cas LANL ; elles sont donc regroupées à un même chainage.
   À l'origine, un connecteur hydraulique synthétique de 1,001 m sépare le
   nœud source de la première station, car PETROLE distingue ces deux rôles.
   Cette longueur dépasse strictement la tolérance de recherche des stations
   (1 m) afin qu'une station ne soit jamais appliquée deux fois ;
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
import hashlib
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
NATIVE_REFERENCE_FILE = DATA_DIR / "native_opf_output.json"
PROJECT_CODE_DEFAULT = "BENCH-SEAWAY-LANL"
OUTPUT_DEFAULT = ROOT / "var/validation-vps/benchmark-seaway-lanl.json"

RHO_KG_M3 = 827.0
NU_M2_S = 4.9e-6
LANL_G = 9.8
PETROLE_G = 9.80665
DIAMETER_M = 0.75
BETA = 0.0246
LEIBENZON_M = 0.25
# Le moteur associe une station à un chainage avec une tolérance de 1 m.
# Une longueur strictement supérieure évite que ST-N3 soit rencontrée à 0 m et
# 1 mm. La correction reste négligeable (1,001 m / 969,03 km ≈ 1 ppm).
SYNTHETIC_CONNECTOR_LENGTH_M = 1.001
ASSUMED_MAWP_PA = 10_000_000.0
SOURCE_PRESSURE_HEAD_M = 190.0
# Sortie native enregistrée de PetroleumModels.jl, pas les valeurs arrondies du
# test officiel. Ces conditions limites et vitesses rendent le rejeu PETROLE
# exactement comparable au point de fonctionnement OPF LANL archivé.
INLET_FLOW_M3_S = 0.356724281076506
INJECTION_N9_M3_S = 0.6077287813384165
OFFTAKE_N15_M3_S = 0.8254530724072793
INJECTION_N18_M3_S = 0.5787995029407432
TERMINAL_FLOW_M3_S = 0.7177994929483865

# Vitesses de la sortie native, divisées par la vitesse nominale LANL de 50 r/s.
# `native_opf_output.json` et `reference_operating_point.csv` les rendent
# auditables et `check_source_dataset()` détecte toute divergence.
PUMP_SPEED_RATIOS = {
    "P1": 0.8054030514534964,
    "P2": 0.8054030514534964,
    "P4": 0.8054030477643892,
    "P7": 0.805403053511389,
    "P10": 1.0455237371209432,
    "P12": 1.0455237912205992,
    "P13": 1.0455237912205992,
    "P19": 0.9773477079236766,
    "P21": 0.8315529073354597,
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

REFERENCE_FLOW_BY_PIPE = {
    3: 0.356724281076506,
    9: 0.9644530624149225,
    15: 0.139,
    22: 0.7177994929483865,
}

# Portes définies avant toute exécution. Elles qualifient seulement la bonne
# exécution du rejeu dans PETROLE ; elles ne confèrent pas de validation
# prédictive : le point de fonctionnement est fourni par la sortie OPF LANL.
ACCEPTED_CALCULATION_STATUSES = frozenset({"SIM_CONVERGED", "SIM_CONVERGED_WARN"})
MAXIMUM_VIOLATION_COUNT = 0
EXPECTED_WARNING_CODES = frozenset({"WARN_PROPERTY_DEFAULTED", "WARN_PUMP_OFF_BEP"})
EXECUTION_GATE = {
    "accepted_statuses": sorted(ACCEPTED_CALCULATION_STATUSES),
    "require_feasible": True,
    "maximum_violation_count": MAXIMUM_VIOLATION_COUNT,
    "expected_warning_codes": sorted(EXPECTED_WARNING_CODES),
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


def operating_point_values(kind: str) -> dict[str, float]:
    """Charge les valeurs numériques de la référence native enregistrée."""

    return {
        row["id"]: float(row["value"])
        for row in load_csv("reference_operating_point.csv")
        if row["kind"] == kind
    }


def native_opf_reference() -> dict[str, Any]:
    """Lit et contrôle la sortie native, compacte et figée, de LANL.

    Le solveur LANL expose ici les charges `h` en unités de base (bien que le
    drapeau de la structure de sortie indique SI). Le cas source définit
    `base_head=100 m` et le nœud contraint N1 sort à 1.9 : la conversion vers
    les mètres est donc explicite, vérifiable et jamais implicite.
    """

    raw = NATIVE_REFERENCE_FILE.read_bytes()
    record = json.loads(raw)
    provenance = record.get("provenance") or {}
    solution = record.get("solution") or {}
    base_head_m = float(solution.get("base_head") or 0.0)
    if base_head_m != 100.0:
        raise BenchmarkError(f"base_head LANL inattendu : {base_head_m} m.")
    junctions = dict(solution.get("junction") or {})
    if abs(float(junctions.get("1", {}).get("h", math.nan)) * base_head_m - 190.0) > 1e-9:
        raise BenchmarkError(
            "La normalisation de charge LANL ne retrouve pas le nœud contraint N1."
        )

    heads_m = {
        f"N{junction_id}": float(item["h"]) * base_head_m for junction_id, item in junctions.items()
    }
    pumps = dict(solution.get("pump") or {})
    pump_source_ids = {
        "P1": "1",
        "P2": "2",
        "P4": "4",
        "P7": "7",
        "P10": "10",
        "P12": "12",
        "P13": "13",
        "P19": "19",
        "P21": "21",
    }
    pump_ratios = {
        code: float(pumps[source_id]["w"]) / 50.0 for code, source_id in pump_source_ids.items()
    }
    pipe_flows = {
        int(pipe_id): float(item["q_pipe"])
        for pipe_id, item in dict(solution.get("pipe") or {}).items()
    }
    producer_source_nodes = {"1": "N1", "2": "N9", "3": "N18"}
    return {
        "record_sha256": hashlib.sha256(raw).hexdigest(),
        "source_commit": provenance.get("source_commit"),
        "termination_status": record.get("termination_status"),
        "objective": float(record["objective"]),
        "base_head_m": base_head_m,
        "pressure_heads_m": heads_m,
        "pump_speed_ratios": pump_ratios,
        "pipe_flows_m3_s": pipe_flows,
        "producer_flows_m3_s": {
            producer_source_nodes[producer_id]: float(item["qg"])
            for producer_id, item in dict(solution.get("producer") or {}).items()
        },
        "consumer_flows_m3_s": {
            "N15": float(solution["consumer"]["1"]["ql"]),
            "N23": float(solution["consumer"]["2"]["ql"]),
        },
    }


def verify_native_reference() -> dict[str, Any]:
    """Empêche toute dérive entre l'artefact LANL, le CSV et l'adaptateur."""

    reference = native_opf_reference()
    if reference["source_commit"] != "df35cd4999a1289710640a46882de7f665d4b32f":
        raise BenchmarkError("La révision LANL de la référence native est inattendue.")
    if reference["termination_status"] not in {"LOCALLY_SOLVED", "OPTIMAL"}:
        raise BenchmarkError("La référence native LANL n'est pas une solution exploitable.")

    for code, expected in PUMP_SPEED_RATIOS.items():
        actual = float(reference["pump_speed_ratios"][code])
        if abs(actual - expected) > 1e-12:
            raise BenchmarkError(f"Vitesse native incohérente pour {code}: {actual} != {expected}.")
    for pipe_id, expected in REFERENCE_FLOW_BY_PIPE.items():
        actual = float(reference["pipe_flows_m3_s"][pipe_id])
        if abs(actual - expected) > 1e-12:
            raise BenchmarkError(
                f"Débit natif incohérent pour pipe {pipe_id}: {actual} != {expected}."
            )
    expected_boundary_flows = {
        "N1": INLET_FLOW_M3_S,
        "N9": INJECTION_N9_M3_S,
        "N18": INJECTION_N18_M3_S,
    }
    for node, expected in expected_boundary_flows.items():
        actual = float(reference["producer_flows_m3_s"][node])
        if abs(actual - expected) > 1e-12:
            raise BenchmarkError(
                f"Injection native incohérente pour {node}: {actual} != {expected}."
            )
    expected_withdrawals = {"N15": OFFTAKE_N15_M3_S, "N23": TERMINAL_FLOW_M3_S}
    for node, expected in expected_withdrawals.items():
        actual = float(reference["consumer_flows_m3_s"][node])
        if abs(actual - expected) > 1e-12:
            raise BenchmarkError(f"Soutirage natif incohérent pour {node}: {actual} != {expected}.")

    csv_heads = operating_point_values("pressure_head")
    for node, expected in reference["pressure_heads_m"].items():
        if abs(csv_heads[node] - expected) > 1e-9:
            raise BenchmarkError(
                f"Charge LANL incohérente pour {node}: {csv_heads[node]} != {expected}."
            )
    csv_ratios = operating_point_values("pump_speed_ratio")
    for code, expected in PUMP_SPEED_RATIOS.items():
        if abs(csv_ratios[code] - expected) > 1e-12:
            raise BenchmarkError(
                f"Vitesse CSV incohérente pour {code}: {csv_ratios[code]} != {expected}."
            )

    return {
        "source_commit": reference["source_commit"],
        "record_sha256": reference["record_sha256"],
        "termination_status": reference["termination_status"],
        "objective": reference["objective"],
        "base_head_m": reference["base_head_m"],
    }


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
    return operating_point_values("pressure_head")


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
    native_reference = verify_native_reference()
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
        "native_opf_reference": native_reference,
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
    warnings = list(result_payload.get("warnings") or [])
    warning_codes = [str(item.get("code") or "") for item in warnings]
    unexpected_warning_codes = sorted(set(warning_codes) - EXPECTED_WARNING_CODES)
    checks = {
        "calculation_status": calculation_status in ACCEPTED_CALCULATION_STATUSES,
        "result_status": result_status in ACCEPTED_CALCULATION_STATUSES,
        "feasible": bool(result_payload.get("feasible")),
        "violations": violation_count <= MAXIMUM_VIOLATION_COUNT,
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
        "criteria": EXECUTION_GATE,
        "checks": checks,
        "calculation_status": calculation_status,
        "result_status": result_status,
        "feasible": bool(result_payload.get("feasible")),
        "violation_count": violation_count,
        "warning_count": len(warnings),
        "warning_codes": warning_codes,
        "unexpected_warning_codes": unexpected_warning_codes,
        "failures": failures,
    }


def adapted_topology_summary(topology: dict[str, Any]) -> dict[str, Any]:
    """Distingue les cardinalités LANL de la représentation PETROLE.

    Les nœuds de pompe LANL sont reliés par des arêtes de longueur nulle. Ils
    sont condensés en stations PETROLE : l'adaptateur ne doit donc jamais
    laisser entendre que les 23 jonctions source existent telles quelles dans
    le modèle persisté.
    """

    nodes = list(topology.get("nodes") or [])
    edges = list(topology.get("edges") or [])
    assets = list(topology.get("assets") or [])
    # L'API expose le sous-ensemble validé de `payload` pour une arête et ne
    # conserve donc pas la clé d'adaptateur `source_pipe_id`. Les codes L3…L22
    # sont au contraire un contrat métier persistant, contrôlé ci-dessous.
    physical_codes = {
        edge_code
        for edge_code, _, _, _, source_pipe_id in EDGE_LAYOUT
        if source_pipe_id is not None
    }
    connector_codes = {
        edge_code for edge_code, _, _, _, source_pipe_id in EDGE_LAYOUT if source_pipe_id is None
    }
    physical_edges = [edge for edge in edges if edge.get("code") in physical_codes]
    connector_edges = [edge for edge in edges if edge.get("code") in connector_codes]
    persisted_codes = [str(edge.get("code") or "") for edge in edges]
    if set(persisted_codes) != physical_codes | connector_codes or len(persisted_codes) != len(
        set(persisted_codes)
    ):
        raise BenchmarkError(
            "Les codes d'arêtes persistés ne correspondent pas à l'adaptateur Seaway."
        )
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "asset_count": len(assets),
        "physical_pipe_count": len(physical_edges),
        "physical_pipe_length_m": sum(float(edge["length_m"]) for edge in physical_edges),
        "synthetic_connector_count": len(connector_edges),
        "synthetic_connector_length_m": sum(float(edge["length_m"]) for edge in connector_edges),
        "edge_codes": persisted_codes,
        "node_kind_counts": {
            kind: sum(1 for node in nodes if node.get("kind") == kind)
            for kind in sorted({str(node.get("kind")) for node in nodes})
        },
    }


def persisted_resource_contract(topology: dict[str, Any]) -> dict[str, Any]:
    """Contrôle les ressources réellement renvoyées par l'API publique.

    Le benchmark ne suppose pas que les champs envoyés au POST survivent tous :
    il vérifie leur représentation persistée avant de calculer. Cela verrouille
    la hiérarchie modèle → nœud/arête → équipement attendue par HydroLiquid.
    """

    nodes = {str(node.get("code")): node for node in list(topology.get("nodes") or [])}
    edges = {str(edge.get("code")): edge for edge in list(topology.get("edges") or [])}
    assets = {str(asset.get("code")): asset for asset in list(topology.get("assets") or [])}
    expected_nodes: dict[str, tuple[str, float]] = {
        code: (kind, elevation) for code, _, elevation, _, kind in MODEL_LOCATIONS
    }
    if set(nodes) != set(expected_nodes):
        raise BenchmarkError("Les nœuds persistés ne correspondent pas à la topologie Seaway.")
    for code, node_expected in expected_nodes.items():
        node = nodes[code]
        expected_kind, expected_elevation_m = node_expected
        if node.get("kind") != expected_kind:
            raise BenchmarkError(f"Type persistant inattendu pour le nœud {code}.")
        if abs(float(node["elevation_m"]) - expected_elevation_m) > 1e-9:
            raise BenchmarkError(f"Altitude persistante inattendue pour le nœud {code}.")
        if node.get("status") != "available":
            raise BenchmarkError(f"Statut persistant inattendu pour le nœud {code}.")

    expected_edges: dict[str, tuple[float, str, str]] = {
        code: (length_m, from_code, to_code)
        for code, length_m, from_code, to_code, _ in EDGE_LAYOUT
    }
    if set(edges) != set(expected_edges):
        raise BenchmarkError("Les arêtes persistées ne correspondent pas à la topologie Seaway.")
    for code, edge_expected in expected_edges.items():
        edge = edges[code]
        expected_length_m, expected_from_code, expected_to_code = edge_expected
        required_fields = {
            "from_node_code",
            "to_node_code",
            "length_m",
            "inner_diameter_m",
            "roughness_m",
            "mawp_pa",
            "status",
            "profile",
        }
        missing = required_fields - set(edge)
        if missing:
            raise BenchmarkError(f"Champs d'arête absents pour {code}: {sorted(missing)}.")
        if edge["from_node_code"] != expected_from_code or edge["to_node_code"] != expected_to_code:
            raise BenchmarkError(f"Hiérarchie d'arête inattendue pour {code}.")
        if abs(float(edge["length_m"]) - expected_length_m) > 1e-9:
            raise BenchmarkError(f"Longueur persistante inattendue pour l'arête {code}.")
        if abs(float(edge["inner_diameter_m"]) - DIAMETER_M) > 1e-12:
            raise BenchmarkError(f"Diamètre persistant inattendu pour l'arête {code}.")
        if abs(float(edge["roughness_m"])) > 1e-12 or float(edge["mawp_pa"]) != ASSUMED_MAWP_PA:
            raise BenchmarkError(f"Paramètres persistants inattendus pour l'arête {code}.")
        if edge["status"] != "available" or len(list(edge["profile"])) != 2:
            raise BenchmarkError(f"Profil ou statut persistant inattendu pour l'arête {code}.")

    expected_assets = {
        pump_id: station_code
        for station_code, _, _, pump_ids, _ in MODEL_LOCATIONS
        for pump_id in pump_ids
    }
    if set(assets) != set(expected_assets):
        raise BenchmarkError("Les équipements persistés ne correspondent pas aux neuf pompes LANL.")
    for code, expected_node_code in expected_assets.items():
        asset = assets[code]
        if asset.get("node_code") != expected_node_code:
            raise BenchmarkError(f"Rattachement hiérarchique inattendu pour la pompe {code}.")
        if asset.get("role") != "main" or asset.get("status") != "available":
            raise BenchmarkError(f"Rôle ou statut persistant inattendu pour la pompe {code}.")
        if asset.get("catalog_code") != "LANL-SEAWAY-PUMP":
            raise BenchmarkError(f"Catalogue persistant inattendu pour la pompe {code}.")

    return {
        "verified": True,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "asset_count": len(assets),
        "required_edge_fields": sorted(
            {
                "from_node_code",
                "to_node_code",
                "length_m",
                "inner_diameter_m",
                "roughness_m",
                "mawp_pa",
                "status",
                "profile",
            }
        ),
        "asset_parent_field": "node_code",
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
    topology = engineer.request("GET", f"/models/{model_id}/topology")
    topology_summary = adapted_topology_summary(topology)
    resource_contract = persisted_resource_contract(topology)
    if topology_summary["physical_pipe_count"] != 13:
        raise BenchmarkError("L'adaptateur PETROLE doit conserver les 13 conduites physiques LANL.")
    if abs(topology_summary["physical_pipe_length_m"] - 969_030.0) > 1e-6:
        raise BenchmarkError("La longueur physique LANL a été altérée par l'adaptateur PETROLE.")

    scenario = engineer.request(
        "POST",
        f"/models/{model_id}/scenarios",
        {
            "name": "Allocation LANL de référence — point transformé",
            "description": (
                "Conditions limites et vitesses provenant de l'OPF native LANL, "
                "figée dans reference_operating_point.csv."
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
        "topology": topology_summary,
        "resource_contract": resource_contract,
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

    # Débits issus de l'OPF native LANL. Ils ne sont pas tous saisis directement
    # dans PETROLE : N9/N15/N18 changent le débit via les injections/soutirages.
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

    cumulative_formula_head_difference_m = sum(
        float(row["lanl_leibenzon_loss_m"]) - float(row["petrole_altshul_formula_loss_m"])
        for row in pipe_rows
    )
    terminal_pressure_head_difference_m = float(head_rows[-1]["difference_m"])
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
        "cumulative_formula_head_difference_m": cumulative_formula_head_difference_m,
        "terminal_pressure_head_difference_m": terminal_pressure_head_difference_m,
        "terminal_head_difference_unexplained_by_friction_m": (
            terminal_pressure_head_difference_m - cumulative_formula_head_difference_m
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
    comparison = compare_result(result_payload) if replay_gate["passed"] else None
    return {
        "benchmark": "PUBLIC-SEAWAY-LANL-01",
        "classification": "complete_pipeline_cross_solver_fixed_operating_point",
        "source": {
            "paper": "Khlebnikova et al., AIChE Journal 2021, DOI 10.1002/aic.17124",
            "machine_data": "lanl-ansi/PetroleumModels.jl test/data/case_seaway.m",
            "source_model_is_synthesized": True,
            "native_opf_record": "validation/public/seaway_lanl/native_opf_output.json",
            "native_opf_source_commit": source["native_opf_reference"]["source_commit"],
            "native_opf_record_sha256": source["native_opf_reference"]["record_sha256"],
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
        "adapted_petrole_model": built["topology"],
        "persisted_resource_contract": built["resource_contract"],
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
            "native_opf_reference_available": True,
            "cross_solver_comparison_verdict": "COMPARISON_COMPLETE",
            "cross_solver_comparison_scope": (
                "Débits, vitesses et charges proviennent d'une sortie native et versionnée "
                "de PetroleumModels.jl ; PETROLE rejoue ce point avec Altshul alors que LANL "
                "emploie Leibenzon. L'écart est publié, sans calibration a posteriori."
            ),
            "predictive_validation_verdict": "NOT_EVALUATED",
            "predictive_validation_reason": (
                "Les conditions limites et vitesses de pompe sont imposées depuis la sortie "
                "LANL. Ce rejeu ne prédit donc pas une sortie LANL inconnue, et le modèle "
                "source reste synthétisé plutôt que mesuré par SCADA terrain."
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
    return 0 if report["execution_gate"]["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
