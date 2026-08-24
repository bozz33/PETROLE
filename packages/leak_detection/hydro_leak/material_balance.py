"""Bilan matière compensé sans seuil de fuite implicite.

Cette brique calcule un résidu massique et son incertitude combinée. Elle ne
convertit pas le résidu en alarme : les seuils et règles de décision doivent
être pré-enregistrés avec l'opérateur et validés sur données indépendantes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MaterialBalanceWindow:
    """Masses intégrées sur une fenêtre synchronisée, en kg."""

    inlet_mass_kg: float
    outlet_mass_kg: float
    inventory_change_kg: float
    inlet_standard_uncertainty_kg: float = 0.0
    outlet_standard_uncertainty_kg: float = 0.0
    inventory_standard_uncertainty_kg: float = 0.0

    def __post_init__(self) -> None:
        masses = (self.inlet_mass_kg, self.outlet_mass_kg, self.inventory_change_kg)
        if any(not math.isfinite(value) for value in masses):
            raise ValueError("Les masses du bilan doivent être finies.")
        uncertainties = (
            self.inlet_standard_uncertainty_kg,
            self.outlet_standard_uncertainty_kg,
            self.inventory_standard_uncertainty_kg,
        )
        if any(not math.isfinite(value) or value < 0 for value in uncertainties):
            raise ValueError("Les incertitudes-types doivent être finies et positives ou nulles.")


@dataclass(frozen=True, slots=True)
class MaterialBalanceResult:
    """Résultat descriptif utilisable par un détecteur futur."""

    residual_kg: float
    combined_standard_uncertainty_kg: float
    normalized_residual: float | None


def compute_material_balance(window: MaterialBalanceWindow) -> MaterialBalanceResult:
    """Calcule entrée - sortie - variation d'inventaire et l'incertitude RSS."""

    residual = window.inlet_mass_kg - window.outlet_mass_kg - window.inventory_change_kg
    combined_uncertainty = math.sqrt(
        window.inlet_standard_uncertainty_kg**2
        + window.outlet_standard_uncertainty_kg**2
        + window.inventory_standard_uncertainty_kg**2
    )
    normalized = residual / combined_uncertainty if combined_uncertainty > 0 else None
    return MaterialBalanceResult(
        residual_kg=residual,
        combined_standard_uncertainty_kg=combined_uncertainty,
        normalized_residual=normalized,
    )


__all__ = ["MaterialBalanceResult", "MaterialBalanceWindow", "compute_material_balance"]
