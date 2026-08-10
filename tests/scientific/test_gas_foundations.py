"""Références analytiques des premières fondations gaz de Phase 6."""

from __future__ import annotations

import pytest

from hydro_gas import GasState, gas_density_from_z, linepack_mass


def test_ideal_gas_reference_density_matches_closed_form() -> None:
    # Méthane de référence simplifié, Z=1 : ce test valide uniquement l'algèbre
    # de l'EOS, pas un modèle industriel de gaz naturel.
    density = gas_density_from_z(
        pressure_pa=101_325.0,
        temperature_k=288.15,
        molar_mass_kg_mol=0.016_04,
        compressibility_factor=1.0,
    )
    assert density == pytest.approx(0.67848, rel=2e-4)

    state = GasState(
        pressure_pa=101_325.0,
        temperature_k=288.15,
        molar_mass_kg_mol=0.016_04,
        compressibility_factor=1.0,
    )
    assert state.density_kg_m3 == pytest.approx(density)


def test_linepack_integrates_rho_area_dx_without_hidden_defaults() -> None:
    mass = linepack_mass(
        densities_kg_m3=[10.0, 12.0],
        cross_section_areas_m2=[0.5, 0.5],
        cell_lengths_m=[100.0, 200.0],
    )
    assert mass == pytest.approx(1_700.0)

    with pytest.raises(ValueError, match="même taille"):
        linepack_mass(
            densities_kg_m3=[10.0],
            cross_section_areas_m2=[0.5, 0.5],
            cell_lengths_m=[100.0],
        )
