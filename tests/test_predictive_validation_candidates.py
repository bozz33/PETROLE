from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "validation/public/predictive_candidates.json"


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_campagne_ne_se_ferme_pas_sans_trois_validations_predictives() -> None:
    registry = load_registry()

    assert registry["campaign"] == "PUBLIC-VALIDATION-02"
    assert registry["strict_closure_required_independent_predictive_cases"] == 3
    completed = [
        candidate
        for candidate in registry["candidates"]
        if candidate["predictive_validation_verdict"] == "PASS"
    ]
    assert registry["strict_predictive_cases_completed"] == len(completed)
    assert len(completed) < 3
    assert registry["status"] != "CLOSED"
    assert registry["certification"] is False


def test_aucun_candidat_bloque_n_est_promu_en_pass_predictif() -> None:
    registry = load_registry()

    for candidate in registry["candidates"]:
        if candidate["eligibility_status"].startswith("BLOCKED") or candidate[
            "eligibility_status"
        ] == "SUPPORTING_ONLY":
            assert candidate["blockers"]
            assert candidate["predictive_validation_verdict"] == "NOT_EVALUATED"


def test_registre_contient_les_trois_dependances_industrielles_prioritaires() -> None:
    registry = load_registry()
    by_id = {candidate["id"]: candidate for candidate in registry["candidates"]}

    assert by_id["FIELD-BN1-2022"]["class"] == "industrial_crude_pipeline"
    assert by_id["FIELD-GUANGDONG-NO1-2021"]["geometry_complete"] is True
    assert by_id["FIELD-GUANGDONG-NO1-2021"]["fluid_properties_complete"] is True
    assert by_id["FIELD-QINGTIE-2022"]["current_engine_scope"] is False


def test_un_pass_predictif_futur_exige_donnees_et_scope_complets() -> None:
    registry = load_registry()

    for candidate in registry["candidates"]:
        if candidate["predictive_validation_verdict"] != "PASS":
            continue
        assert candidate["measured_truth_available"] is True
        assert candidate["raw_pressures_available"] is True
        assert candidate["geometry_complete"] is True
        assert candidate["fluid_properties_complete"] is True
        assert candidate["current_engine_scope"] is True
        assert not candidate["blockers"]
