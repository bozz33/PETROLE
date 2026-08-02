"""Unités, conversions et cohérence dimensionnelle.

Principe directeur ([ADR-005](../../../docs/adr/adr-005-si-interne.md)) : **le stockage et le
calcul utilisent exclusivement un système SI cohérent**. Les unités d'affichage sont converties
aux frontières de l'application, et la valeur d'origine ainsi que son unité sont conservées
(FR-GEN-003, D07 § 2).

Pint est utilisé aux frontières et dans les tests ; les types métier internes manipulent des
`float` en SI pour éviter le coût des quantités dans les boucles numériques (D-v2 § 9.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

import pint

from hydro_shared.errors import DimensionalityMismatchError, UnknownUnitError

#: Registre Pint unique du processus. `auto_reduce_dimensions` est laissé désactivé afin de
#: garder les unités telles que l'utilisateur les exprime avant conversion explicite.
UNIT_REGISTRY: Final[pint.UnitRegistry] = pint.UnitRegistry(
    autoconvert_offset_to_baseunit=True,
)
UNIT_REGISTRY.formatter.default_format = "~P"

# Alias métier absents ou ambigus dans Pint.
UNIT_REGISTRY.define("cSt = centistokes")
UNIT_REGISTRY.define("standard_cubic_metre = m ** 3 = Sm3")

Quantity = UNIT_REGISTRY.Quantity


class Dimension(StrEnum):
    """Grandeurs manipulées par la plateforme, avec leur unité interne SI (D-v2 § 9.3)."""

    LENGTH = "length"
    ELEVATION = "elevation"
    DIAMETER = "diameter"
    ROUGHNESS = "roughness"
    AREA = "area"
    VOLUME = "volume"
    MASS = "mass"
    PRESSURE = "pressure"
    HEAD = "head"
    VOLUMETRIC_FLOW = "volumetric_flow"
    MASS_FLOW = "mass_flow"
    VELOCITY = "velocity"
    DENSITY = "density"
    DYNAMIC_VISCOSITY = "dynamic_viscosity"
    KINEMATIC_VISCOSITY = "kinematic_viscosity"
    TEMPERATURE = "temperature"
    POWER = "power"
    ENERGY = "energy"
    TIME = "time"
    ROTATIONAL_SPEED = "rotational_speed"
    DIMENSIONLESS = "dimensionless"
    CURRENCY_PER_ENERGY = "currency_per_energy"


#: Unité interne canonique de chaque grandeur. Toute valeur stockée en base ou transmise au
#: noyau scientifique est exprimée dans ces unités.
SI_UNITS: Final[dict[Dimension, str]] = {
    Dimension.LENGTH: "m",
    Dimension.ELEVATION: "m",
    Dimension.DIAMETER: "m",
    Dimension.ROUGHNESS: "m",
    Dimension.AREA: "m ** 2",
    Dimension.VOLUME: "m ** 3",
    Dimension.MASS: "kg",
    Dimension.PRESSURE: "Pa",
    Dimension.HEAD: "m",
    Dimension.VOLUMETRIC_FLOW: "m ** 3 / s",
    Dimension.MASS_FLOW: "kg / s",
    Dimension.VELOCITY: "m / s",
    Dimension.DENSITY: "kg / m ** 3",
    Dimension.DYNAMIC_VISCOSITY: "Pa * s",
    Dimension.KINEMATIC_VISCOSITY: "m ** 2 / s",
    Dimension.TEMPERATURE: "K",
    Dimension.POWER: "W",
    Dimension.ENERGY: "J",
    Dimension.TIME: "s",
    Dimension.ROTATIONAL_SPEED: "1 / s",
    Dimension.DIMENSIONLESS: "dimensionless",
    Dimension.CURRENCY_PER_ENERGY: "1 / J",
}

#: Unités d'affichage usuelles proposées par l'interface (D-v2 § 9.3).
DISPLAY_UNITS: Final[dict[Dimension, tuple[str, ...]]] = {
    Dimension.LENGTH: ("m", "km", "mm"),
    Dimension.ELEVATION: ("m", "ft"),
    Dimension.DIAMETER: ("m", "mm", "inch"),
    Dimension.ROUGHNESS: ("m", "mm"),
    Dimension.VOLUME: ("m ** 3", "bbl", "L"),
    Dimension.PRESSURE: ("Pa", "bar", "MPa", "psi", "kPa"),
    Dimension.HEAD: ("m", "ft"),
    Dimension.VOLUMETRIC_FLOW: ("m ** 3 / s", "m ** 3 / hour", "bbl / hour", "L / s"),
    Dimension.MASS_FLOW: ("kg / s", "t / hour"),
    Dimension.VELOCITY: ("m / s",),
    Dimension.DENSITY: ("kg / m ** 3", "g / cm ** 3"),
    Dimension.DYNAMIC_VISCOSITY: ("Pa * s", "mPa * s", "cP"),
    Dimension.KINEMATIC_VISCOSITY: ("m ** 2 / s", "cSt", "mm ** 2 / s"),
    Dimension.TEMPERATURE: ("K", "degC", "degF"),
    Dimension.POWER: ("W", "kW", "MW"),
    Dimension.ENERGY: ("J", "kWh", "MWh"),
    Dimension.TIME: ("s", "minute", "hour", "day"),
}

# Cache des unités SI compilées : la conversion est appelée dans les boucles d'import.
_SI_UNIT_CACHE: dict[Dimension, Any] = {}


def si_unit_for(dimension: Dimension) -> str:
    """Retourne l'unité interne SI de la grandeur."""
    return SI_UNITS[dimension]


def _si_quantity(dimension: Dimension) -> Any:
    unit = _SI_UNIT_CACHE.get(dimension)
    if unit is None:
        unit = UNIT_REGISTRY.parse_expression(SI_UNITS[dimension])
        _SI_UNIT_CACHE[dimension] = unit
    return unit


def parse_unit(unit: str) -> Any:
    """Analyse une unité textuelle.

    Lève :class:`UnknownUnitError` (code ``ERR_UNIT_UNKNOWN``) si Pint ne la reconnaît pas.
    """
    try:
        return UNIT_REGISTRY.Unit(unit)
    except Exception as exc:  # pint lève plusieurs types selon l'entrée
        raise UnknownUnitError(unit) from exc


def to_si(value: float, unit: str, dimension: Dimension) -> float:
    """Convertit ``value`` exprimée en ``unit`` vers l'unité SI interne de ``dimension``.

    >>> to_si(1.0, "bar", Dimension.PRESSURE)
    100000.0
    >>> round(to_si(3600.0, "m ** 3 / hour", Dimension.VOLUMETRIC_FLOW), 6)
    1.0

    Lève :class:`UnknownUnitError` si l'unité est inconnue et
    :class:`DimensionalityMismatchError` si elle n'est pas compatible avec la grandeur.
    """
    quantity = Quantity(float(value), parse_unit(unit))
    target = _si_quantity(dimension)
    try:
        return float(quantity.to(target).magnitude)
    except pint.DimensionalityError as exc:
        raise DimensionalityMismatchError(
            unit=unit, dimension=dimension.value, expected=SI_UNITS[dimension]
        ) from exc


def from_si(value_si: float, unit: str, dimension: Dimension) -> float:
    """Convertit une valeur SI interne vers une unité d'affichage."""
    quantity = Quantity(float(value_si), _si_quantity(dimension))
    try:
        return float(quantity.to(parse_unit(unit)).magnitude)
    except pint.DimensionalityError as exc:
        raise DimensionalityMismatchError(
            unit=unit, dimension=dimension.value, expected=SI_UNITS[dimension]
        ) from exc


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Conversion directe entre deux unités compatibles."""
    quantity = Quantity(float(value), parse_unit(from_unit))
    try:
        return float(quantity.to(parse_unit(to_unit)).magnitude)
    except pint.DimensionalityError as exc:
        raise DimensionalityMismatchError(
            unit=from_unit, dimension="conversion", expected=to_unit
        ) from exc


def is_compatible(unit: str, dimension: Dimension) -> bool:
    """Indique si ``unit`` est dimensionnellement compatible avec ``dimension``."""
    try:
        to_si(1.0, unit, dimension)
    except (UnknownUnitError, DimensionalityMismatchError):
        return False
    return True


def format_si(value_si: float, dimension: Dimension, unit: str | None = None, digits: int = 4) -> str:
    """Formate une valeur SI pour l'affichage, unité toujours visible (NFR-UX-002)."""
    target = unit or SI_UNITS[dimension]
    displayed = from_si(value_si, target, dimension) if target != SI_UNITS[dimension] else value_si
    pretty = f"{UNIT_REGISTRY.Unit(target):~P}" if target != "dimensionless" else ""
    return f"{displayed:.{digits}g} {pretty}".strip()


@dataclass(frozen=True, slots=True)
class Measure:
    """Valeur physique conservant sa saisie d'origine.

    Le noyau scientifique consomme ``value_si`` ; l'interface et les rapports restituent
    ``original_value``/``original_unit`` afin qu'aucune conversion ne soit silencieuse
    (FR-GEN-003, D09 § 1).
    """

    value_si: float
    dimension: Dimension
    original_value: float
    original_unit: str

    @classmethod
    def of(cls, value: float, unit: str, dimension: Dimension) -> Measure:
        """Construit une mesure à partir d'une saisie utilisateur."""
        return cls(
            value_si=to_si(value, unit, dimension),
            dimension=dimension,
            original_value=float(value),
            original_unit=unit,
        )

    @classmethod
    def si(cls, value_si: float, dimension: Dimension) -> Measure:
        """Construit une mesure déjà exprimée en unité interne."""
        return cls(
            value_si=float(value_si),
            dimension=dimension,
            original_value=float(value_si),
            original_unit=SI_UNITS[dimension],
        )

    @property
    def si_unit(self) -> str:
        return SI_UNITS[self.dimension]

    def display(self, unit: str | None = None, digits: int = 4) -> str:
        return format_si(self.value_si, self.dimension, unit, digits)

    def to(self, unit: str) -> float:
        return from_si(self.value_si, unit, self.dimension)

    def as_dict(self) -> dict[str, Any]:
        return {
            "value_si": self.value_si,
            "unit_si": self.si_unit,
            "dimension": self.dimension.value,
            "original_value": self.original_value,
            "original_unit": self.original_unit,
        }
