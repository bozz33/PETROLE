from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deployment/scripts/vps/benchmark_east_china_2025.py"


def load_script():
    spec = importlib.util.spec_from_file_location("benchmark_east_china_2025", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_donnees_terrain_et_geometrie_publics_restent_tracables() -> None:
    module = load_script()

    source = module.source_checks()

    assert source["geometry"]["total_length_m"] == pytest.approx(40_078.0)
    assert source["published_observation"]["measured_flow_m3_h"] == pytest.approx(270.0)
    assert source["published_observation"]["published_calculated_flow_m3_h"] == pytest.approx(
        268.70
    )
    assert source["published_observation"]["published_reynolds"] == pytest.approx(76_918.0)


def test_reproduction_physique_n_efface_pas_ecart_reynolds_publie() -> None:
    module = load_script()

    source = module.source_checks()
    physics = source["physics_from_published_inputs"]

    assert physics["flow_m3_s"] == pytest.approx(0.075)
    assert physics["velocity_m_s"] == pytest.approx(1.280347865370652)
    assert physics["reynolds"] == pytest.approx(74_081.1444984587)
    assert source["published_reynolds_difference_percent"] == pytest.approx(-3.688155570271329)
    assert source["published_reynolds_reconciled"] is False
    assert physics["altshul_vs_leibenzon_percent"] == pytest.approx(-2.044986042993398)


def test_comparaison_lit_le_contrat_api_segments() -> None:
    module = load_script()
    source = module.source_checks()
    physics = source["physics_from_published_inputs"]
    result = {
        "segments": [
            {
                "reynolds": physics["reynolds"],
                "friction_head_loss_m": physics["altshul_loss_m"] / 2.0,
                "flow_m3_s": physics["flow_m3_s"],
            },
            {
                "reynolds": physics["reynolds"],
                "friction_head_loss_m": physics["altshul_loss_m"] / 2.0,
                "flow_m3_s": physics["flow_m3_s"],
            },
        ]
    }

    comparison = module.compare_result(result, source)

    assert comparison["engine_reynolds_error_percent"] == pytest.approx(0.0)
    assert comparison["engine_altshul_friction_error_percent"] == pytest.approx(0.0)
    assert comparison["published_reynolds_difference_percent"] == pytest.approx(-3.688155570271329)
    assert comparison["measured_flow_is_imposed_input"] is True
    assert module.physics_reproduction_gate(comparison)["status"] == "PASS"


def test_porte_physique_refuse_ecart_moteur_hors_tolerance() -> None:
    module = load_script()

    verdict = module.physics_reproduction_gate(
        {
            "engine_flow_error_percent": 0.0,
            "engine_reynolds_error_percent": 0.01,
            "engine_altshul_friction_error_percent": 0.0,
        }
    )

    assert verdict["status"] == "FAIL"
    assert verdict["failures"] == ["reynolds"]


def test_porte_execution_refuse_violations_et_avertissements_non_declares() -> None:
    module = load_script()

    verdict = module.execution_gate(
        {"status": "SIM_NOT_CONVERGED"},
        {
            "status": "SIM_NOT_CONVERGED",
            "feasible": False,
            "violations": [{"code": "P_MIN"}],
            "warnings": [{"code": "WARN_UNEXPECTED"}],
        },
    )

    assert verdict["status"] == "FAIL"
    assert set(verdict["failures"]) == {
        "calculation_status",
        "result_status",
        "feasible",
        "violations",
        "warning_codes",
    }


def test_porte_execution_accepte_uniquement_warning_propriete_attendu() -> None:
    module = load_script()

    verdict = module.execution_gate(
        {"status": "SIM_CONVERGED_WARN"},
        {
            "status": "SIM_CONVERGED_WARN",
            "feasible": True,
            "violations": [],
            "warnings": [{"code": "WARN_PROPERTY_DEFAULTED"}],
        },
    )

    assert verdict["passed"] is True
    assert verdict["status"] == "PASS_WITH_EXPECTED_WARNINGS"


def test_contrat_persistant_verifie_ressources_et_hierarchie() -> None:
    module = load_script()
    topology = {
        "nodes": [
            {"code": code, "kind": kind, "elevation_m": elevation, "status": "available"}
            for code, _, kind, elevation in module.NODES
        ],
        "edges": [
            {
                "code": code,
                "from_node_code": from_code,
                "to_node_code": to_code,
                "length_m": length_m,
                "inner_diameter_m": module.DIAMETER_M,
                "roughness_m": 0.0,
                "mawp_pa": module.ASSUMED_MAWP_PA,
                "status": "available",
                "profile": [{}, {}],
            }
            for code, from_code, to_code, length_m in module.EDGES
        ],
        "assets": [],
    }

    contract = module.persisted_resource_contract(topology)

    assert contract["verified"] is True
    assert contract["node_count"] == 3
    assert contract["edge_count"] == 2
    assert contract["asset_count"] == 0


def test_version_api_refuse_serveur_different() -> None:
    module = load_script()

    class ClientVersion:
        def request(self, method, path, payload=None, **kwargs):
            assert (method, path) == ("GET", "/version")
            return {"git_sha": "served"}

    with pytest.raises(module.BenchmarkError, match="pas le SHA attendu"):
        module.run_benchmark(
            ClientVersion(),
            ClientVersion(),
            project_code="AUDIT",
            expected_git_sha="candidate",
        )
