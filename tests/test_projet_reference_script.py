from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1] / "deployment" / "scripts" / "vps" / "projet_reference.py"
)


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("projet_reference", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_geometrie_reference_conserve_200_km_et_rapproche_la_premiere_station() -> None:
    module = load_script()
    lengths = [module.segment_length_m(index) for index in range(module.SEGMENT_COUNT)]

    assert sum(lengths) == pytest.approx(
        module.SEGMENT_COUNT * module.SEGMENT_LENGTH_M,
    )
    assert (
        lengths[: module.UPSTREAM_SEGMENT_COUNT]
        == [module.UPSTREAM_SEGMENT_LENGTH_M] * module.UPSTREAM_SEGMENT_COUNT
    )
    assert sum(lengths[: module.UPSTREAM_SEGMENT_COUNT]) == pytest.approx(2_000.0)
    assert lengths[module.UPSTREAM_SEGMENT_COUNT] == pytest.approx(
        module.DOWNSTREAM_SEGMENT_LENGTH_M,
    )


def test_geometrie_reference_refuse_un_indice_hors_trace() -> None:
    module = load_script()

    with pytest.raises(ValueError, match="hors limites"):
        module.segment_length_m(module.SEGMENT_COUNT)
