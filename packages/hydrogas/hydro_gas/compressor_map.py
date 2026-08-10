"""Interpolation traçable de cartes compresseur fournisseur.

Le module ne génère aucune carte synthétique et n'extrapole jamais hors du
domaine fourni. Les points doivent provenir d'une source versionnée et validée
pour le projet concerné.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompressorMapPoint:
    """Point d'une ligne de vitesse d'une carte compresseur."""

    mass_flow_kg_s: float
    pressure_ratio: float
    isentropic_efficiency: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.mass_flow_kg_s) or self.mass_flow_kg_s <= 0:
            raise ValueError("Le débit massique de carte doit être fini et positif.")
        if not math.isfinite(self.pressure_ratio) or self.pressure_ratio <= 0:
            raise ValueError("Le rapport de pression doit être fini et positif.")
        if (
            not math.isfinite(self.isentropic_efficiency)
            or self.isentropic_efficiency <= 0
            or self.isentropic_efficiency > 1
        ):
            raise ValueError("Le rendement isentropique doit appartenir à ]0, 1].")


@dataclass(frozen=True, slots=True)
class CompressorSpeedLine:
    """Ligne de vitesse avec points ordonnés en débit massique croissant."""

    speed_rpm: float
    points: tuple[CompressorMapPoint, ...]

    def __post_init__(self) -> None:
        if not math.isfinite(self.speed_rpm) or self.speed_rpm <= 0:
            raise ValueError("La vitesse compresseur doit être finie et positive.")
        if len(self.points) < 2:
            raise ValueError("Une ligne de vitesse exige au moins deux points de carte.")
        flows = [point.mass_flow_kg_s for point in self.points]
        if flows != sorted(flows) or len(set(flows)) != len(flows):
            raise ValueError("Les points d'une ligne doivent avoir des débits strictement croissants.")


@dataclass(frozen=True, slots=True)
class CompressorMap:
    """Carte fournisseur versionnée sans hypothèse de similitude cachée."""

    source_ref: str
    version: str
    speed_lines: tuple[CompressorSpeedLine, ...]

    def __post_init__(self) -> None:
        if not self.source_ref.strip() or not self.version.strip():
            raise ValueError("La provenance et la version de la carte sont obligatoires.")
        if not self.speed_lines:
            raise ValueError("La carte compresseur doit contenir au moins une ligne de vitesse.")
        speeds = [line.speed_rpm for line in self.speed_lines]
        if speeds != sorted(speeds) or len(set(speeds)) != len(speeds):
            raise ValueError("Les lignes de vitesse doivent être strictement croissantes.")


@dataclass(frozen=True, slots=True)
class CompressorOperatingPoint:
    """Point interpolé à l'intérieur du domaine fourni."""

    speed_rpm: float
    mass_flow_kg_s: float
    pressure_ratio: float
    isentropic_efficiency: float
    source_ref: str
    map_version: str


def _interpolate_line(
    line: CompressorSpeedLine,
    mass_flow_kg_s: float,
) -> tuple[float, float]:
    points = line.points
    if mass_flow_kg_s < points[0].mass_flow_kg_s or mass_flow_kg_s > points[-1].mass_flow_kg_s:
        raise ValueError("Le débit demandé est hors du domaine de la ligne de vitesse.")
    for left, right in zip(points, points[1:], strict=True):
        if left.mass_flow_kg_s <= mass_flow_kg_s <= right.mass_flow_kg_s:
            fraction = (mass_flow_kg_s - left.mass_flow_kg_s) / (
                right.mass_flow_kg_s - left.mass_flow_kg_s
            )
            pressure_ratio = left.pressure_ratio + fraction * (
                right.pressure_ratio - left.pressure_ratio
            )
            efficiency = left.isentropic_efficiency + fraction * (
                right.isentropic_efficiency - left.isentropic_efficiency
            )
            return pressure_ratio, efficiency
    raise RuntimeError("Le point de carte n'a pas pu être encadré.")


def interpolate_compressor_map(
    compressor_map: CompressorMap,
    *,
    speed_rpm: float,
    mass_flow_kg_s: float,
) -> CompressorOperatingPoint:
    """Interpôle débit puis vitesse, sans aucune extrapolation hors carte."""

    if not math.isfinite(speed_rpm) or speed_rpm <= 0:
        raise ValueError("La vitesse demandée doit être finie et positive.")
    if not math.isfinite(mass_flow_kg_s) or mass_flow_kg_s <= 0:
        raise ValueError("Le débit demandé doit être fini et positif.")

    lines = compressor_map.speed_lines
    if speed_rpm < lines[0].speed_rpm or speed_rpm > lines[-1].speed_rpm:
        raise ValueError("La vitesse demandée est hors du domaine de la carte compresseur.")

    if len(lines) == 1:
        if not math.isclose(speed_rpm, lines[0].speed_rpm, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("Une carte à une seule ligne n'autorise aucune interpolation en vitesse.")
        pressure_ratio, efficiency = _interpolate_line(lines[0], mass_flow_kg_s)
    else:
        bracket: tuple[CompressorSpeedLine, CompressorSpeedLine] | None = None
        for lower, upper in zip(lines, lines[1:], strict=True):
            if lower.speed_rpm <= speed_rpm <= upper.speed_rpm:
                bracket = lower, upper
                break
        if bracket is None:
            raise RuntimeError("La vitesse n'a pas pu être encadrée par la carte.")
        lower, upper = bracket
        lower_pressure, lower_efficiency = _interpolate_line(lower, mass_flow_kg_s)
        upper_pressure, upper_efficiency = _interpolate_line(upper, mass_flow_kg_s)
        speed_fraction = (speed_rpm - lower.speed_rpm) / (upper.speed_rpm - lower.speed_rpm)
        pressure_ratio = lower_pressure + speed_fraction * (upper_pressure - lower_pressure)
        efficiency = lower_efficiency + speed_fraction * (upper_efficiency - lower_efficiency)

    return CompressorOperatingPoint(
        speed_rpm=speed_rpm,
        mass_flow_kg_s=mass_flow_kg_s,
        pressure_ratio=pressure_ratio,
        isentropic_efficiency=efficiency,
        source_ref=compressor_map.source_ref,
        map_version=compressor_map.version,
    )


__all__ = [
    "CompressorMap",
    "CompressorMapPoint",
    "CompressorOperatingPoint",
    "CompressorSpeedLine",
    "interpolate_compressor_map",
]
