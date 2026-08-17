"""Propriétés gaz minimales fondées sur l'équation d'état de D07.

Ces fonctions servent de référence vérifiable pour le futur moteur gaz. Elles
n'implémentent ni une corrélation de facteur Z ni un solveur de réseau. Le
facteur de compressibilité doit provenir d'une méthode ou d'une bibliothèque
validée et rester traçable dans le scénario.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

UNIVERSAL_GAS_CONSTANT_J_MOL_K = 8.31446261815324


@dataclass(frozen=True, slots=True)
class GasState:
    """État thermodynamique minimal en unités SI."""

    pressure_pa: float
    temperature_k: float
    molar_mass_kg_mol: float
    compressibility_factor: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.pressure_pa) or self.pressure_pa <= 0:
            raise ValueError("La pression absolue du gaz doit être finie et positive.")
        if not math.isfinite(self.temperature_k) or self.temperature_k <= 0:
            raise ValueError("La température absolue du gaz doit être finie et positive.")
        if not math.isfinite(self.molar_mass_kg_mol) or self.molar_mass_kg_mol <= 0:
            raise ValueError("La masse molaire doit être finie et positive.")
        if not math.isfinite(self.compressibility_factor) or self.compressibility_factor <= 0:
            raise ValueError("Le facteur de compressibilité Z doit être fini et positif.")

    @property
    def density_kg_m3(self) -> float:
        """Masse volumique issue de ``p = Z ρ R_sp T``."""

        return gas_density_from_z(
            pressure_pa=self.pressure_pa,
            temperature_k=self.temperature_k,
            molar_mass_kg_mol=self.molar_mass_kg_mol,
            compressibility_factor=self.compressibility_factor,
        )


def gas_density_from_z(
    *,
    pressure_pa: float,
    temperature_k: float,
    molar_mass_kg_mol: float,
    compressibility_factor: float,
) -> float:
    """Calcule ρ à partir de p, T, masse molaire et Z, tous explicitement fournis."""

    state = (pressure_pa, temperature_k, molar_mass_kg_mol, compressibility_factor)
    if any(not math.isfinite(value) or value <= 0 for value in state):
        raise ValueError("p, T, masse molaire et Z doivent être finis et strictement positifs.")
    specific_gas_constant = UNIVERSAL_GAS_CONSTANT_J_MOL_K / molar_mass_kg_mol
    return pressure_pa / (compressibility_factor * specific_gas_constant * temperature_k)


def linepack_mass(
    *,
    densities_kg_m3: list[float],
    cross_section_areas_m2: list[float],
    cell_lengths_m: list[float],
) -> float:
    """Intègre la masse contenue dans des cellules de conduite.

    L'approximation discrète correspond à la forme intégrale ``∫ρ A dx`` de
    D07. Le choix des états p/T/Z par cellule appartient au futur solveur gaz.
    """

    if not densities_kg_m3:
        raise ValueError("Le calcul de line-pack exige au moins une cellule.")
    if not (len(densities_kg_m3) == len(cross_section_areas_m2) == len(cell_lengths_m)):
        raise ValueError("Les vecteurs densité, aire et longueur doivent avoir la même taille.")
    values = zip(densities_kg_m3, cross_section_areas_m2, cell_lengths_m, strict=True)
    contributions: list[float] = []
    for density, area, length in values:
        if any(not math.isfinite(value) or value <= 0 for value in (density, area, length)):
            raise ValueError("Densité, aire et longueur doivent être finies et positives.")
        contributions.append(density * area * length)
    return math.fsum(contributions)


__all__ = [
    "UNIVERSAL_GAS_CONSTANT_J_MOL_K",
    "GasState",
    "gas_density_from_z",
    "linepack_mass",
]
