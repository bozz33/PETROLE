"""Line-pack segmenté à partir d'états gaz explicitement fournis.

Cette brique n'est pas un solveur de conduite. Elle transforme des états p/T/Z
provenant d'un calcul ou d'une mesure traçable en inventaire massique par
segment, conformément à l'intégrale discrète ``∫ρ A dx`` déjà définie dans D07.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_gas.properties import GasState


@dataclass(frozen=True, slots=True)
class GasLinepackCell:
    """Cellule de conduite avec état thermodynamique et provenance explicites."""

    cell_id: str
    length_m: float
    cross_section_area_m2: float
    state: GasState
    state_source_ref: str

    def __post_init__(self) -> None:
        if not self.cell_id.strip() or not self.state_source_ref.strip():
            raise ValueError("Identifiant de cellule et provenance d'état sont obligatoires.")
        if not math.isfinite(self.length_m) or self.length_m <= 0:
            raise ValueError("La longueur de cellule doit être finie et strictement positive.")
        if not math.isfinite(self.cross_section_area_m2) or self.cross_section_area_m2 <= 0:
            raise ValueError("L'aire de cellule doit être finie et strictement positive.")

    @property
    def volume_m3(self) -> float:
        return self.cross_section_area_m2 * self.length_m

    @property
    def mass_kg(self) -> float:
        return self.state.density_kg_m3 * self.volume_m3


@dataclass(frozen=True, slots=True)
class GasLinepackResult:
    """Inventaire massique et contributions sans hypothèse de profil cachée."""

    total_mass_kg: float
    total_volume_m3: float
    cell_masses_kg: tuple[float, ...]
    cell_ids: tuple[str, ...]
    source_refs: tuple[str, ...]


def compute_segmented_linepack(cells: tuple[GasLinepackCell, ...]) -> GasLinepackResult:
    """Agrège le line-pack sans interpoler ni extrapoler les états fournis."""

    if not cells:
        raise ValueError("Le line-pack segmenté exige au moins une cellule.")
    cell_ids = tuple(cell.cell_id for cell in cells)
    if len(cell_ids) != len(set(cell_ids)):
        raise ValueError("Chaque cellule de line-pack doit avoir un identifiant unique.")

    masses = tuple(cell.mass_kg for cell in cells)
    volumes = tuple(cell.volume_m3 for cell in cells)
    return GasLinepackResult(
        total_mass_kg=math.fsum(masses),
        total_volume_m3=math.fsum(volumes),
        cell_masses_kg=masses,
        cell_ids=cell_ids,
        source_refs=tuple(cell.state_source_ref for cell in cells),
    )


__all__ = ["GasLinepackCell", "GasLinepackResult", "compute_segmented_linepack"]
