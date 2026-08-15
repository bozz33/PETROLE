from __future__ import annotations

import hydro_gas.stationary_equipment_api as mixed_api


def test_mixed_compressor_facade_exposes_governed_solver_and_evidence_contracts() -> None:
    assert mixed_api.ACTIVE_COMPRESSOR_PROBLEM_FAMILY_REF.startswith("problem-family://gas/")
    assert mixed_api.ACTIVE_COMPRESSOR_P2_NUMERICAL_REPRESENTATION_REF.startswith("numerics://gas/")
    assert mixed_api.MIXED_STATIONARY_GAS_EXPORT_VERSION.startswith("phase6-gas/")
    assert mixed_api.STATIONARY_EQUIPMENT_BENCHMARK_EVIDENCE_SCHEMA_VERSION.startswith("phase6/")

    required_symbols = (
        "CoolPropCompressorFluidDefinition",
        "StationaryActiveCompressorProblem",
        "StationaryActiveCompressorResultTables",
        "StationaryActiveCompressorThermodynamicAssessment",
        "StationaryActiveCompressorUnknownState",
        "StationaryCompressorStationThermodynamicSummary",
        "ScipyActiveCompressorLeastSquaresTrfConfiguration",
        "aggregate_stationary_compressor_thermodynamics",
        "build_stationary_active_compressor_result_tables",
        "build_stationary_equipment_benchmark_observations",
        "evaluate_stationary_active_compressor_thermodynamics",
        "export_stationary_active_compressor_solve_result_json",
        "export_stationary_equipment_benchmark_evidence",
        "solve_stationary_active_compressor_with_approved_inputs",
        "StationaryEquipmentBenchmarkBinding",
    )
    for symbol in required_symbols:
        assert hasattr(mixed_api, symbol)
        assert symbol in mixed_api.__all__


def test_mixed_compressor_facade_has_no_duplicate_public_symbols() -> None:
    assert len(mixed_api.__all__) == len(set(mixed_api.__all__))
