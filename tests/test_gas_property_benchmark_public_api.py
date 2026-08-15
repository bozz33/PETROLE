import hydro_gas


REQUIRED_PROPERTY_BENCHMARK_EVIDENCE_SYMBOLS = (
    "COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_REF_PREFIX",
    "COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_SCHEMA_VERSION",
    "CoolPropGasPropertyBenchmarkEvidenceArtifact",
    "export_coolprop_gas_property_benchmark_evidence",
)


def test_property_benchmark_evidence_contracts_are_public() -> None:
    for symbol in REQUIRED_PROPERTY_BENCHMARK_EVIDENCE_SYMBOLS:
        assert hasattr(hydro_gas, symbol)
        assert symbol in hydro_gas.__all__


def test_gas_root_facade_has_no_duplicate_public_symbols() -> None:
    assert len(hydro_gas.__all__) == len(set(hydro_gas.__all__))
