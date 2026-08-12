from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest

from hydro_gas import export_gas_results_json


def _payload() -> dict[str, object]:
    return {
        "calculation_ref": "calc://gas/case-001",
        "model_version": "gas-model/0.1",
        "composition_source_ref": "lab://composition/sample-42",
        "property_method_ref": "coolprop://HEOS/methane",
        "generated_at": datetime(2026, 8, 12, 5, 30, tzinfo=UTC),
        "assumptions": {
            "pressure_basis": "absolute",
            "stationary_model": "mass-balance-foundation-only",
        },
        "results": {
            "linepack_mass_kg": 1234.5,
            "global_mass_residual_kg_s": 0.0,
        },
        "diagnostics": {
            "max_abs_node_residual_kg_s": 0.0,
            "stationary_pipe_pressure_law": "not_selected",
        },
        "source_refs": ["supplier://compressor/map-v3"],
    }


def test_gas_result_export_is_canonical_and_content_addressed() -> None:
    payload = _payload()
    artifact = export_gas_results_json(payload)

    reversed_payload = dict(reversed(tuple(payload.items())))
    second = export_gas_results_json(reversed_payload)

    assert artifact.media_type == "application/json"
    assert artifact.filename == "gas-results.json"
    assert artifact.content == second.content
    assert artifact.sha256 == second.sha256
    assert artifact.sha256 == hashlib.sha256(artifact.content).hexdigest()

    document = json.loads(artifact.content)
    assert document["export_version"] == "phase6-gas/1.0"
    assert document["results"]["linepack_mass_kg"] == pytest.approx(1234.5)
    assert document["diagnostics"]["stationary_pipe_pressure_law"] == "not_selected"
    assert document["generated_at"] == "2026-08-12T05:30:00+00:00"


def test_gas_result_export_requires_scientific_provenance() -> None:
    payload = _payload()
    del payload["property_method_ref"]

    with pytest.raises(ValueError, match="property_method_ref"):
        export_gas_results_json(payload)


def test_gas_result_export_rejects_blank_reference() -> None:
    payload = _payload()
    payload["composition_source_ref"] = "   "

    with pytest.raises(ValueError, match="composition_source_ref"):
        export_gas_results_json(payload)


def test_gas_result_export_rejects_naive_datetime() -> None:
    payload = _payload()
    payload["generated_at"] = datetime(2026, 8, 12, 5, 30)

    with pytest.raises(ValueError, match="timezone-aware"):
        export_gas_results_json(payload)


def test_gas_result_export_rejects_non_finite_json_values() -> None:
    payload = _payload()
    payload["results"] = {"linepack_mass_kg": float("nan")}

    with pytest.raises(ValueError):
        export_gas_results_json(payload)


def test_gas_result_export_requires_export_version() -> None:
    with pytest.raises(ValueError, match="version d'export"):
        export_gas_results_json(_payload(), export_version="  ")
