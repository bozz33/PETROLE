"""Configuration documentaire d'une station de compression gaz.

D07 prévoit unités principales/secours, bypass, refroidisseurs et vannes. Ce
module décrit ces éléments et leurs références techniques ; il ne simule ni
commande, ni anti-surge, ni régulation et ne déduit aucune disponibilité.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CompressorUnitRole(StrEnum):
    MAIN = "main"
    STANDBY = "standby"


class StationValveRole(StrEnum):
    ISOLATION = "isolation"
    BYPASS = "bypass"
    RECYCLE = "recycle"
    CHECK = "check"
    CONTROL = "control"


@dataclass(frozen=True, slots=True)
class CompressorUnitConfiguration:
    """Unité compresseur liée à ses sources de performance/version."""

    unit_id: str
    role: CompressorUnitRole
    performance_map_ref: str
    operating_envelope_ref: str
    source_ref: str

    def __post_init__(self) -> None:
        values = (
            self.unit_id,
            self.performance_map_ref,
            self.operating_envelope_ref,
            self.source_ref,
        )
        if any(not value.strip() for value in values):
            raise ValueError("L'unité compresseur et toutes ses références sont obligatoires.")


@dataclass(frozen=True, slots=True)
class StationCoolerConfiguration:
    cooler_id: str
    source_ref: str

    def __post_init__(self) -> None:
        if not self.cooler_id.strip() or not self.source_ref.strip():
            raise ValueError("Le refroidisseur et sa provenance sont obligatoires.")


@dataclass(frozen=True, slots=True)
class StationValveConfiguration:
    valve_id: str
    role: StationValveRole
    source_ref: str

    def __post_init__(self) -> None:
        if not self.valve_id.strip() or not self.source_ref.strip():
            raise ValueError("La vanne et sa provenance sont obligatoires.")


@dataclass(frozen=True, slots=True)
class CompressorStationConfiguration:
    """Topologie documentaire minimale d'une station, sans logique de contrôle."""

    station_id: str
    source_ref: str
    units: tuple[CompressorUnitConfiguration, ...]
    coolers: tuple[StationCoolerConfiguration, ...] = ()
    valves: tuple[StationValveConfiguration, ...] = ()
    bypass_path_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.station_id.strip() or not self.source_ref.strip():
            raise ValueError("La station et sa provenance sont obligatoires.")
        if not self.units:
            raise ValueError("Une station de compression doit référencer au moins une unité.")
        if not any(unit.role is CompressorUnitRole.MAIN for unit in self.units):
            raise ValueError("Une station doit contenir au moins une unité principale.")

        component_ids = [unit.unit_id for unit in self.units]
        component_ids.extend(cooler.cooler_id for cooler in self.coolers)
        component_ids.extend(valve.valve_id for valve in self.valves)
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("Les identifiants d'équipements doivent être uniques dans la station.")
        if self.bypass_path_ref is not None and not self.bypass_path_ref.strip():
            raise ValueError("La référence du bypass ne peut pas être vide.")

    @property
    def main_unit_ids(self) -> tuple[str, ...]:
        return tuple(unit.unit_id for unit in self.units if unit.role is CompressorUnitRole.MAIN)

    @property
    def standby_unit_ids(self) -> tuple[str, ...]:
        return tuple(unit.unit_id for unit in self.units if unit.role is CompressorUnitRole.STANDBY)


__all__ = [
    "CompressorStationConfiguration",
    "CompressorUnitConfiguration",
    "CompressorUnitRole",
    "StationCoolerConfiguration",
    "StationValveConfiguration",
    "StationValveRole",
]
