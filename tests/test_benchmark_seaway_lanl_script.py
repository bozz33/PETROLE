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


def test_allocation_reconstruite_retrouve_les_quatre_debits_lanl() -> None:
    module = load_script()

    flows = module.flow_by_pipe()

    assert flows[3] == pytest.approx(0.3567)
    assert flows[9] == pytest.approx(0.9644)
    assert flows[15] == pytest.approx(0.1389)
    assert flows[22] == pytest.approx(0.7178)


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

    assert module.SYNTHETIC_CONNECTOR_LENGTH_M == pytest.approx(0.001)
    assert module.EDGE_LAYOUT[0][4] is None
    physical = sum(length for _, length, _, _, source_pipe in module.EDGE_LAYOUT if source_pipe)
    assert physical == pytest.approx(969_030.0)
