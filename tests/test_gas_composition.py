from __future__ import annotations

import pytest

from hydro_gas import GasComponentFraction, GasComposition


def test_gas_composition_computes_mixture_molar_mass_from_explicit_inputs() -> None:
    composition = GasComposition(
        source_ref="lab://gc/sample-2026-08-10",
        components=(
            GasComponentFraction("methane", 0.90, 0.016043),
            GasComponentFraction("ethane", 0.10, 0.030070),
        ),
    )
    assert composition.molar_mass_kg_mol == pytest.approx(0.0174457)


def test_gas_composition_rejects_non_normalized_fraction_sum() -> None:
    with pytest.raises(ValueError, match="somme des fractions molaires"):
        GasComposition(
            source_ref="lab://gc/invalid",
            components=(
                GasComponentFraction("methane", 0.80, 0.016043),
                GasComponentFraction("ethane", 0.10, 0.030070),
            ),
        )


def test_gas_composition_rejects_duplicate_component_names() -> None:
    with pytest.raises(ValueError, match="uniques"):
        GasComposition(
            source_ref="lab://gc/duplicate",
            components=(
                GasComponentFraction("methane", 0.50, 0.016043),
                GasComponentFraction("methane", 0.50, 0.016043),
            ),
        )
