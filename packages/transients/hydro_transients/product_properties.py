"""Propriétés thermophysiques tabulées pour les lots multiproduits.

D07 privilégie les tables laboratoire/opérateur pour les produits réels. Cette
brique effectue uniquement une interpolation linéaire entre points fournis et
refuse toute extrapolation silencieuse hors du domaine de température.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise


@dataclass(frozen=True, slots=True)
class TemperaturePropertyPoint:
    """Valeur d'une propriété à une température absolue donnée."""

    temperature_k: float
    value: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.temperature_k) or self.temperature_k <= 0:
            raise ValueError("La température tabulée doit être finie et strictement positive.")
        if not math.isfinite(self.value):
            raise ValueError("La valeur de propriété tabulée doit être finie.")


@dataclass(frozen=True, slots=True)
class TemperaturePropertyTable:
    """Table 1D versionnée et traçable d'une propriété fonction de T."""

    property_name: str
    unit: str
    source_ref: str
    version: str
    points: tuple[TemperaturePropertyPoint, ...]

    def __post_init__(self) -> None:
        required = (self.property_name, self.unit, self.source_ref, self.version)
        if any(not value.strip() for value in required):
            raise ValueError("Nom, unité, provenance et version de table sont obligatoires.")
        if len(self.points) < 2:
            raise ValueError("Une table interpolée exige au moins deux points.")
        temperatures = [point.temperature_k for point in self.points]
        if temperatures != sorted(temperatures) or len(set(temperatures)) != len(temperatures):
            raise ValueError("Les températures de table doivent être strictement croissantes.")

    @property
    def minimum_temperature_k(self) -> float:
        return self.points[0].temperature_k

    @property
    def maximum_temperature_k(self) -> float:
        return self.points[-1].temperature_k

    def interpolate(self, temperature_k: float) -> float:
        """Interpole dans le domaine publié et refuse toute extrapolation."""

        if not math.isfinite(temperature_k) or temperature_k <= 0:
            raise ValueError("La température demandée doit être finie et strictement positive.")
        if temperature_k < self.minimum_temperature_k or temperature_k > self.maximum_temperature_k:
            raise ValueError(
                f"Température hors domaine de la table {self.property_name}: "
                f"[{self.minimum_temperature_k}, {self.maximum_temperature_k}] K."
            )
        for left, right in pairwise(self.points):
            if math.isclose(temperature_k, left.temperature_k, rel_tol=0.0, abs_tol=1e-12):
                return left.value
            if left.temperature_k <= temperature_k <= right.temperature_k:
                if math.isclose(temperature_k, right.temperature_k, rel_tol=0.0, abs_tol=1e-12):
                    return right.value
                fraction = (temperature_k - left.temperature_k) / (
                    right.temperature_k - left.temperature_k
                )
                return left.value + fraction * (right.value - left.value)
        raise RuntimeError("La température n'a pas pu être encadrée dans la table.")


@dataclass(frozen=True, slots=True)
class ProductPropertyTables:
    """Tables minimales retenues par D07 pour un produit pétrolier réel."""

    product_ref: str
    density: TemperaturePropertyTable
    kinematic_viscosity: TemperaturePropertyTable
    vapor_pressure: TemperaturePropertyTable

    def __post_init__(self) -> None:
        if not self.product_ref.strip():
            raise ValueError("La référence produit est obligatoire.")
        expected = (
            (self.density, "density", "kg/m^3"),
            (self.kinematic_viscosity, "kinematic_viscosity", "m^2/s"),
            (self.vapor_pressure, "vapor_pressure", "Pa"),
        )
        for table, property_name, unit in expected:
            if table.property_name != property_name or table.unit != unit:
                raise ValueError(
                    f"La table {property_name} doit utiliser le nom {property_name} et l'unité {unit}."
                )

    def at_temperature(self, temperature_k: float) -> dict[str, float]:
        """Évalue les trois propriétés sans masquer les domaines différents."""

        return {
            "density_kg_m3": self.density.interpolate(temperature_k),
            "kinematic_viscosity_m2_s": self.kinematic_viscosity.interpolate(temperature_k),
            "vapor_pressure_pa": self.vapor_pressure.interpolate(temperature_k),
        }


__all__ = [
    "ProductPropertyTables",
    "TemperaturePropertyPoint",
    "TemperaturePropertyTable",
]
