"""Composition gaz explicite pour le domaine gaz PETROLE.

Les fractions molaires et masses molaires sont fournies par une source
traçable. Aucune composition par défaut, pseudo-composant ou corrélation de
propriétés n'est injecté par ce module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GasComponentFraction:
    """Fraction molaire d'un composant et masse molaire associée."""

    component: str
    mole_fraction: float
    molar_mass_kg_mol: float

    def __post_init__(self) -> None:
        if not self.component.strip():
            raise ValueError("Le nom du composant gaz est obligatoire.")
        if (
            not math.isfinite(self.mole_fraction)
            or self.mole_fraction < 0
            or self.mole_fraction > 1
        ):
            raise ValueError("Une fraction molaire doit appartenir à [0, 1].")
        if not math.isfinite(self.molar_mass_kg_mol) or self.molar_mass_kg_mol <= 0:
            raise ValueError("La masse molaire d'un composant doit être finie et positive.")


@dataclass(frozen=True, slots=True)
class GasComposition:
    """Composition normalisée provenant d'une analyse ou d'un jeu de référence."""

    source_ref: str
    components: tuple[GasComponentFraction, ...]
    fraction_tolerance: float = 1e-9

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("La provenance de la composition gaz est obligatoire.")
        if not self.components:
            raise ValueError("La composition gaz doit contenir au moins un composant.")
        names = [component.component for component in self.components]
        if len(names) != len(set(names)):
            raise ValueError("Les composants d'une composition gaz doivent être uniques.")
        if not math.isfinite(self.fraction_tolerance) or self.fraction_tolerance < 0:
            raise ValueError("La tolérance de somme des fractions doit être finie et positive.")
        total = math.fsum(component.mole_fraction for component in self.components)
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=self.fraction_tolerance):
            raise ValueError(
                "La somme des fractions molaires doit être égale à 1 dans la tolérance."
            )

    @property
    def molar_mass_kg_mol(self) -> float:
        """M = Σ y_i M_i pour la composition molaire fournie."""

        return math.fsum(
            component.mole_fraction * component.molar_mass_kg_mol for component in self.components
        )


__all__ = ["GasComponentFraction", "GasComposition"]
