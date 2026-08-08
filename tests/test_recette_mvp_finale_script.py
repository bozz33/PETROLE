from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "deployment"
    / "scripts"
    / "vps"
    / "recette_mvp_finale.py"
)


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("recette_mvp_finale", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClient:
    def __init__(self, responses: dict[tuple[str, str], Any]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, Any]] = []

    def request(
        self,
        method: str,
        path: str,
        payload: Any = None,
        **_: Any,
    ) -> Any:
        self.calls.append((method, path, payload))
        key = (method, path)
        if key not in self.responses:
            raise AssertionError(f"Appel inattendu : {key}")
        response = self.responses[key]
        return response(payload) if callable(response) else response


def test_latest_model_choisit_la_version_la_plus_recente() -> None:
    module = load_script()
    models = [
        {"id": "v1", "version_number": 1},
        {"id": "v3", "version_number": 3},
        {"id": "v2", "version_number": 2},
    ]
    assert module.latest_model(models)["id"] == "v3"


def test_tank_node_retrouve_le_raccordement_par_identifiant_metier() -> None:
    module = load_script()
    nodes = [
        {"id": "n1", "kind": "junction", "payload": {}},
        {"id": "n2", "kind": "tank", "payload": {"tank_id": "tank-02"}},
    ]
    assert module.tank_node(nodes, "tank-02")["id"] == "n2"


def test_scenario_impossible_force_pression_vapeur_et_pompes_indisponibles() -> None:
    module = load_script()
    model_id = "model-1"
    nominal = {
        "id": "scenario-nominal",
        "payload": {
            "inlet_pressure_pa": 600_000.0,
            "imposed_flow_m3_s": 0.25,
            "pump_overrides": [],
        },
    }
    assets = [
        {"code": "P-001", "role": "main"},
        {"code": "P-002", "role": "standby"},
        {"code": "V-001", "role": "isolation"},
    ]

    def create(payload: dict[str, Any]) -> dict[str, Any]:
        assert payload["name"] == module.IMPOSSIBLE_SCENARIO_NAME
        assert payload["parent_id"] == nominal["id"]
        scientific = payload["payload"]
        assert scientific["inlet_pressure_pa"] == 4_000.0
        assert scientific["imposed_flow_m3_s"] == 0.25
        assert {item["pump_id"] for item in scientific["pump_overrides"]} == {
            "P-001",
            "P-002",
        }
        assert all(item["status"] == "unavailable" for item in scientific["pump_overrides"])
        return {"id": "scenario-impossible", **payload}

    client = FakeClient(
        {
            ("GET", f"/models/{model_id}/scenarios?limit=200&offset=0"): {
                "items": [],
            },
            ("POST", f"/models/{model_id}/scenarios"): create,
        }
    )
    created = module.ensure_impossible_scenario(client, model_id, nominal, assets)
    assert created["id"] == "scenario-impossible"


def test_compare_builds_refuse_deux_sha_differents() -> None:
    module = load_script()
    primary = FakeClient(
        {
            ("GET", "/version"): {
                "application_version": "0.2.0",
                "git_sha": "aaaa",
                "ref": "main",
                "build_date": "2026-08-08T00:00:00Z",
                "scientific_engine_version": "hydroliquid-0.1.0",
                "database_migration_version": "9f3b6e0d5c17",
            }
        }
    )
    secondary = FakeClient(
        {
            ("GET", "/version"): {
                "application_version": "0.2.0",
                "git_sha": "bbbb",
                "ref": "main",
                "build_date": "2026-08-08T00:00:00Z",
                "scientific_engine_version": "hydroliquid-0.1.0",
                "database_migration_version": "9f3b6e0d5c17",
            }
        }
    )
    with pytest.raises(module.AcceptanceError, match="même build"):
        module.compare_builds(primary, secondary)


def test_render_markdown_rappelle_la_porte_humaine() -> None:
    module = load_script()
    summary = {
        "executed_at": "2026-08-08T08:00:00+00:00",
        "base_url": "https://example/api/v1",
        "project": {"code": "REF-MVP-01"},
        "model": {"id": "model-1"},
        "counts": {"nodes": 101, "edges": 100, "assets": 15, "tanks": 10},
        "network_validation": {"errors": 0, "warnings": 0},
        "gates": {
            "impossible_scenario": {"status": "SIM_PHYSICAL_LIMIT"},
            "imports": {
                "profile": {"accepted_count": 3},
                "pump_curve": {"accepted_count": 4},
                "strapping": {"accepted_count": 3},
                "fluid_properties": {"accepted_count": 3},
            },
            "transfer": {
                "received_volume_m3": 100.0,
                "sample_count": 5,
                "balance_residual_m3": 0.0,
            },
            "optimization": {"solver": "enumeration", "status": "completed"},
            "same_build": {"status": "passed"},
        },
    }
    markdown = module.render_markdown(summary)
    assert "5e scénario non réalisable" in markdown
    assert "Porte humaine restante" in markdown
    assert "ingénieur extérieur" in markdown
