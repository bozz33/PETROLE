from __future__ import annotations

import hydro_gas.stationary_equipment_api as mixed_api


def test_mixed_compressor_facade_exposes_governed_solver_and_evidence_contracts() -> None:
    assert mixed_api.ACTIVE_COMPRESSOR_PROBLEM_FAMILY_REF.startswith("problem-family://gas/")
    assert mixed_api.ACTIVE_COMPRESSOR_P2_NUMERICAL_REPRESENTATION_REF.startswith("numerics://gas/")
    assert mixed_api.MIXED_STATIONARY_GAS_EXPORT_VERSION.startswith("phase6-gas/")
    assert mixed_api.STATIONARY_EQUIPMENT_BENCHMARK_EVIDENCE_SCHEMA_VERSION.startswith("phase6/")

    required_symbols = (
        "StationaryActiveCompressorProblem",
        "StationaryActiveCompressorUnknownState",
        "ScipyActiveCompressorLeastSquaresTrfConfiguration",
        "solve_stationary_active_compressor_with_approved_inputs",
        "export_stationary_active_compressor_solve_result_json",
        "StationaryEquipmentBenchmarkBinding",
        "build_stationary_equipment_benchmark_observations",
        "export_stationary_equipment_benchmark_evidence",
    )
    for symbol in required_symbols:
        assert hasattr(mixed_api, symbol)
        assert symbol in mixed_api.__all__


def test_mixed_compressor_facade_has_no_duplicate_public_symbols() -> None:
    assert len(mixed_api.__all__) == len(set(mixed_api.__all__))
