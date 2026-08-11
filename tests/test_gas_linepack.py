from __future__ import annotations

import pytest

from hydro_gas import GasLinepackCell, GasState, compute_segmented_linepack


def _state(pressure_pa: float) -> GasState:
    return GasState(
        pressure_pa=pressure_pa,
        temperature_k=288.15,
        molar_mass_kg_mol=0.018,
        compressibility_factor=0.95,
    )


def test_segmented_linepack_preserves_cell_contributions_and_sources() -> None:
    cells = (
        GasLinepackCell(
            cell_id="C-001",
            length_m=1_000.0,
            cross_section_area_m2=0.5,
            state=_state(5_000_000.0),
            state_source_ref="calc://gas/state/1",
        ),
        GasLinepackCell(
            cell_id="C-002",
            length_m=500.0,
            cross_section_area_m2=0.5,
            state=_state(4_000_000.0),
            state_source_ref="calc://gas/state/2",
        ),
    )

    result = compute_segmented_linepack(cells)

    assert result.total_volume_m3 == pytest.approx(750.0)
    assert result.total_mass_kg == pytest.approx(sum(result.cell_masses_kg))
    assert result.cell_ids == ("C-001", "C-002")
    assert result.source_refs == ("calc://gas/state/1", "calc://gas/state/2")


def test_segmented_linepack_rejects_duplicate_cell_ids() -> None:
    cell = GasLinepackCell(
        cell_id="C-001",
        length_m=1_000.0,
        cross_section_area_m2=0.5,
        state=_state(5_000_000.0),
        state_source_ref="calc://gas/state/1",
    )

    with pytest.raises(ValueError, match="identifiant unique"):
        compute_segmented_linepack((cell, cell))
