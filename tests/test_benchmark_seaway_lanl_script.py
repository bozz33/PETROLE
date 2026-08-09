from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deployment/scripts/vps/benchmark_seaway_lanl.py"


def load_script():
    spec = importlib.util.spec_from_file_location("benchmark_seaway_lanl", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dataset_public_seaway_est_complet_et_equilibre() -> None:
    module = load_script()

    summary = module.check_source_dataset()

    assert summary["junction_count"] == 23
    assert summary["pipe_count"] == 13
    assert summary["pump_count"] == 9
    assert summary["producer_count"] == 3
    assert summary["consumer_count"] == 2
    assert summary["physical_pipe_length_m"] == pytest.approx(969_030.0)
    assert summary["allocation_balance_m3_s"] == pytest.approx(0.0, abs=1e-12)


def test_allocation_native_retrouve_les_quatre_debits_lanl() -> None:
    module = load_script()

    flows = module.flow_by_pipe()

    assert flows[3] == pytest.approx(0.356724281076506)
    assert flows[9] == pytest.approx(0.9644530624149225)
    assert flows[15] == pytest.approx(0.139)
    assert flows[22] == pytest.approx(0.7177994929483865)


def test_reference_native_verifie_la_sortie_lanl_et_sa_normalisation() -> None:
    module = load_script()

    reference = module.verify_native_reference()
    heads = module.reference_pressure_heads()

    assert reference["source_commit"] == "df35cd4999a1289710640a46882de7f665d4b32f"
    assert reference["termination_status"] == "LOCALLY_SOLVED"
    assert reference["objective"] == pytest.approx(-15.428061594560887)
    assert reference["base_head_m"] == pytest.approx(100.0)
    assert heads["N1"] == pytest.approx(190.0)
    assert heads["N23"] == pytest.approx(231.70397217522148)


def test_courbe_pompe_reproduit_la_loi_quadratique_lanl() -> None:
    module = load_script()
    curve = module.pump_curve()

    for flow, head, efficiency in zip(
        curve["flows_m3_s"], curve["heads_m"], curve["efficiencies"], strict=True
    ):
        assert head == pytest.approx(276.8 - 92.0 * flow**2)
        assert efficiency == pytest.approx(2.0 * 0.87 * flow - 0.87 * flow**2)


def test_adaptateur_ne_fait_pas_passer_la_mawp_synthetique_pour_une_donnee_terrain() -> None:
    module = load_script()

    assert module.ASSUMED_MAWP_PA == 10_000_000.0
    text = SCRIPT.read_text(encoding="utf-8")
    assert "ASSUMPTION non bloquante" in text
    assert '"mawp_is_real_pipeline_value": False' in text


def test_connecteur_source_station_est_negligeable_et_declare() -> None:
    module = load_script()

    assert pytest.approx(1.001) == module.SYNTHETIC_CONNECTOR_LENGTH_M
    assert module.SYNTHETIC_CONNECTOR_LENGTH_M > 1.0
    assert module.EDGE_LAYOUT[0][4] is None
    physical = sum(length for _, length, _, _, source_pipe in module.EDGE_LAYOUT if source_pipe)
    assert physical == pytest.approx(969_030.0)


def test_version_api_lit_le_sha_racine_et_refuse_un_candidat_different() -> None:
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


def test_porte_execution_refuse_non_convergence_et_violations() -> None:
    module = load_script()

    verdict = module.execution_gate(
        {"status": "SIM_NOT_CONVERGED"},
        {
            "status": "SIM_NOT_CONVERGED",
            "feasible": False,
            "violations": [{"code": "P_MIN"}],
            "warnings": [{"code": "WARN"}],
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


def test_porte_execution_accepte_uniquement_les_avertissements_deja_declares() -> None:
    module = load_script()

    verdict = module.execution_gate(
        {"status": "SIM_CONVERGED"},
        {
            "status": "SIM_CONVERGED",
            "feasible": True,
            "violations": [],
            "warnings": [{"code": "WARN_PROPERTY_DEFAULTED"}, {"code": "WARN_PUMP_OFF_BEP"}],
        },
    )

    assert verdict["passed"] is True
    assert verdict["status"] == "PASS_WITH_EXPECTED_WARNINGS"
    assert verdict["unexpected_warning_codes"] == []


def test_rejeu_change_le_code_projet_sans_dupliquer_le_catalogue() -> None:
    module = load_script()

    class ProjectsClient:
        def request(self, method, path, payload=None, **kwargs):
            assert (method, path) == (
                "GET",
                "/projects?include_archived=true&limit=200&offset=0",
            )
            return {
                "items": [
                    {"code": "BENCH-SEAWAY-LANL"},
                    {"code": "BENCH-SEAWAY-LANL-R2"},
                ]
            }

    assert module.next_project_code(ProjectsClient(), "BENCH-SEAWAY-LANL") == "BENCH-SEAWAY-LANL-R3"


def test_resume_adaptateur_distingue_conduites_physiques_et_connecteur() -> None:
    module = load_script()

    summary = module.adapted_topology_summary(
        {
            "nodes": [{"kind": "source"}, {"kind": "station"}],
            "assets": [{"code": "P1"}],
            "edges": [
                {"code": code, "length_m": length_m, "payload": {}}
                for code, length_m, _, _, _ in module.EDGE_LAYOUT
            ],
        }
    )

    assert summary["node_count"] == 2
    assert summary["asset_count"] == 1
    assert summary["physical_pipe_count"] == 13
    assert summary["physical_pipe_length_m"] == pytest.approx(969_030.0)
    assert summary["synthetic_connector_count"] == 1
    assert summary["synthetic_connector_length_m"] == pytest.approx(1.001)


def test_contrat_ressources_persistes_verifie_hierarchie_et_champs_api() -> None:
    module = load_script()
    topology = {
        "nodes": [
            {
                "code": code,
                "kind": kind,
                "elevation_m": elevation,
                "status": "available",
            }
            for code, _, elevation, _, kind in module.MODEL_LOCATIONS
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
            for code, length_m, from_code, to_code, _ in module.EDGE_LAYOUT
        ],
        "assets": [
            {
                "code": pump_id,
                "node_code": station_code,
                "role": "main",
                "status": "available",
                "catalog_code": "LANL-SEAWAY-PUMP",
            }
            for station_code, _, _, pump_ids, _ in module.MODEL_LOCATIONS
            for pump_id in pump_ids
        ],
    }

    contract = module.persisted_resource_contract(topology)

    assert contract["verified"] is True
    assert contract["node_count"] == 15
    assert contract["edge_count"] == 14
    assert contract["asset_count"] == 9
    assert contract["asset_parent_field"] == "node_code"
