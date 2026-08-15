import importlib


REQUIRED_PROPERTY_BENCHMARK_EVIDENCE_SYMBOLS = (
    "COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_REF_PREFIX",
    "COOLPROP_GAS_PROPERTY_BENCHMARK_EVIDENCE_SCHEMA_VERSION",
    "CoolPropGasPropertyBenchmarkEvidenceArtifact",
    "export_coolprop_gas_property_benchmark_evidence",
)


def test_property_benchmark_evidence_contracts_are_public() -> None:
    gas_api = importlib.import_module("hydro_gas")
    public_symbols = getattr(gas_api, "__all__")
    for symbol in REQUIRED_PROPERTY_BENCHMARK_EVIDENCE_SYMBOLS:
        assert hasattr(gas_api, symbol)
        assert symbol in public_symbols


def test_gas_root_facade_has_no_duplicate_public_symbols() -> None:
    gas_api = importlib.import_module("hydro_gas")
    public_symbols = getattr(gas_api, "__all__")
    assert len(public_symbols) == len(set(public_symbols))
