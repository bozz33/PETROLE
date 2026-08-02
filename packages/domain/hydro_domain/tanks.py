"""Réservoirs, tables de barémage et inventaire.

Le barémage (*strapping table*) est la relation hauteur → volume propre à chaque bac. Il est
la référence métrologique de l'exploitation : le volume n'est jamais recalculé à partir d'une
géométrie idéalisée lorsqu'une table existe (D-v2 § 4.6, FR-TNK-002).

Contrôles à la construction (règle DQ-004) : hauteurs strictement croissantes, volumes
strictement croissants, sinon ``ERR_TANK_TABLE_INVALID``. Une table non monotone n'est pas
inversible, et le produit ne doit pas prétendre convertir un volume en niveau.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from hydro_shared.errors import StrappingTableError

from hydro_domain.enums import EquipmentStatus, TankType
from hydro_domain.interpolation import ExtrapolationPolicy, MonotoneTable


class StrappingTable:
    """Table de barémage hauteur → volume, interpolable et inversible.

    L'interpolation est linéaire par morceaux : c'est la convention métrologique usuelle des
    tables de jaugeage, et elle garantit que l'inversion volume → hauteur est exacte aux
    points de la table.
    """

    __slots__ = ("_table",)

    def __init__(self, heights_m: Sequence[float], volumes_m3: Sequence[float]) -> None:
        table = MonotoneTable(
            heights_m,
            volumes_m3,
            extrapolation=ExtrapolationPolicy.FORBID,
            label="table de barémage",
            error_type=StrappingTableError,
        )
        if not table.is_invertible:
            raise StrappingTableError(
                "Les volumes d'une table de barémage doivent être strictement croissants ; "
                "une table non monotone n'est pas inversible.",
                volumes=list(volumes_m3),
            )
        if any(v < 0 for v in volumes_m3):
            raise StrappingTableError(
                "Les volumes d'une table de barémage ne peuvent pas être négatifs.",
                volumes=list(volumes_m3),
            )
        if any(h < 0 for h in heights_m):
            raise StrappingTableError(
                "Les hauteurs d'une table de barémage ne peuvent pas être négatives.",
                heights=list(heights_m),
            )
        self._table = table

    @classmethod
    def from_pairs(cls, pairs: Sequence[tuple[float, float]]) -> StrappingTable:
        """Construit la table depuis des couples ``(hauteur_m, volume_m3)``."""
        return cls([p[0] for p in pairs], [p[1] for p in pairs])

    @classmethod
    def from_vertical_cylinder(
        cls, diameter_m: float, height_m: float, points: int = 21
    ) -> StrappingTable:
        """Barémage théorique d'un bac cylindrique vertical, ``V = A·h``.

        Cette construction est destinée aux cas d'étude et aux tests analytiques
        (VAL-TNK-001). Elle ne remplace pas un barémage de jaugeage réel.
        """
        if diameter_m <= 0 or height_m <= 0:
            raise StrappingTableError(
                "Le diamètre et la hauteur d'un bac cylindrique doivent être strictement positifs.",
                diameter_m=diameter_m,
                height_m=height_m,
            )
        area = math.pi * diameter_m**2 / 4.0
        heights = [height_m * i / (points - 1) for i in range(points)]
        return cls(heights, [area * h for h in heights])

    @property
    def height_range_m(self) -> tuple[float, float]:
        return self._table.domain

    @property
    def volume_range_m3(self) -> tuple[float, float]:
        return (self._table.y[0], self._table.y[-1])

    @property
    def max_height_m(self) -> float:
        return self._table.domain[1]

    @property
    def max_volume_m3(self) -> float:
        return self._table.y[-1]

    @property
    def points(self) -> list[tuple[float, float]]:
        return list(zip(self._table.x, self._table.y, strict=True))

    def volume_at(self, height_m: float) -> float:
        """Volume correspondant à une hauteur. Hors table, lève une erreur explicite."""
        return self._table.evaluate(height_m).value

    def height_at(self, volume_m3: float) -> float:
        """Hauteur correspondant à un volume. Hors table, lève une erreur explicite."""
        return self._table.inverse(volume_m3).value

    def dvolume_dheight(self, height_m: float) -> float:
        """Dérivée ``dV/dh`` en m², utilisée pour l'évolution du niveau ``dh/dt`` (D07 § 9)."""
        return self._table.derivative(height_m)

    def as_dict(self) -> dict[str, Any]:
        return {"points": [{"height_m": h, "volume_m3": v} for h, v in self.points]}

    def __len__(self) -> int:
        return len(self._table)


@dataclass(frozen=True, slots=True)
class TankLevels:
    """Seuils d'exploitation d'un réservoir, en mètres (D-v2 § 4.6).

    Ordre attendu : ``minimum ≤ low < normal < high ≤ high_high``. Les seuils ``low`` et
    ``high`` déclenchent des avertissements ; ``minimum`` et ``high_high`` déclenchent les
    contrôles critiques C-008 et C-009.
    """

    minimum_m: float
    high_high_m: float
    low_m: float | None = None
    normal_m: float | None = None
    high_m: float | None = None

    def __post_init__(self) -> None:
        if self.minimum_m < 0:
            raise StrappingTableError(
                "Le niveau minimal ne peut pas être négatif.", minimum_m=self.minimum_m
            )
        if self.high_high_m <= self.minimum_m:
            raise StrappingTableError(
                "Le niveau très haut doit être supérieur au niveau minimal.",
                minimum_m=self.minimum_m,
                high_high_m=self.high_high_m,
            )
        ordered = [
            value
            for value in (self.minimum_m, self.low_m, self.normal_m, self.high_m, self.high_high_m)
            if value is not None
        ]
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if current < previous:
                raise StrappingTableError(
                    "Les seuils de niveau doivent être ordonnés : minimum ≤ bas ≤ normal ≤ haut "
                    "≤ très haut.",
                    levels=ordered,
                )

    @property
    def effective_high_m(self) -> float:
        """Seuil haut effectif : ``high`` s'il est défini, sinon ``high_high``."""
        return self.high_m if self.high_m is not None else self.high_high_m

    @property
    def effective_low_m(self) -> float:
        """Seuil bas effectif : ``low`` s'il est défini, sinon le niveau minimal."""
        return self.low_m if self.low_m is not None else self.minimum_m

    def as_dict(self) -> dict[str, Any]:
        return {
            "minimum_m": self.minimum_m,
            "low_m": self.low_m,
            "normal_m": self.normal_m,
            "high_m": self.high_m,
            "high_high_m": self.high_high_m,
        }


@dataclass(frozen=True, slots=True)
class Tank:
    """Réservoir de stockage avec son barémage et ses seuils d'exploitation.

    ``current_level_m`` est l'état à l'instant initial d'une simulation de transfert ; il est
    surchargeable par scénario sans modifier la fiche du bac.
    """

    id: str
    name: str
    strapping: StrappingTable
    levels: TankLevels
    tank_type: TankType = TankType.VERTICAL_FIXED_ROOF
    elevation_m: float = 0.0
    current_level_m: float = 0.0
    fluid_id: str | None = None
    compatible_fluid_ids: tuple[str, ...] = ()
    status: EquipmentStatus = EquipmentStatus.AVAILABLE
    #: Volume mort non soutirable, en m³.
    dead_volume_m3: float = 0.0
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        table_max = self.strapping.max_height_m
        if self.levels.high_high_m > table_max + 1e-9:
            raise StrappingTableError(
                f"Bac {self.name} : le niveau très haut ({self.levels.high_high_m} m) dépasse la "
                f"hauteur maximale du barémage ({table_max} m).",
                tank_id=self.id,
            )
        low, high = self.strapping.height_range_m
        if not low - 1e-9 <= self.current_level_m <= high + 1e-9:
            raise StrappingTableError(
                f"Bac {self.name} : le niveau courant ({self.current_level_m} m) sort du domaine "
                f"du barémage [{low} ; {high}] m.",
                tank_id=self.id,
            )
        if self.dead_volume_m3 < 0:
            raise StrappingTableError(
                f"Bac {self.name} : le volume mort ne peut pas être négatif.", tank_id=self.id
            )

    # ------------------------------------------------------------------ volumes

    @property
    def display_name(self) -> str:
        return self.label or self.name

    @property
    def nominal_capacity_m3(self) -> float:
        """Capacité nominale : volume au sommet du barémage."""
        return self.strapping.max_volume_m3

    @property
    def current_volume_m3(self) -> float:
        return self.strapping.volume_at(self.current_level_m)

    @property
    def minimum_volume_m3(self) -> float:
        return self.strapping.volume_at(self.levels.minimum_m)

    @property
    def high_high_volume_m3(self) -> float:
        return self.strapping.volume_at(self.levels.high_high_m)

    @property
    def usable_volume_m3(self) -> float:
        """Volume utile entre le niveau minimal et le niveau très haut."""
        return self.high_high_volume_m3 - self.minimum_volume_m3

    @property
    def available_capacity_m3(self) -> float:
        """Capacité de réception restante avant le niveau très haut."""
        return max(self.high_high_volume_m3 - self.current_volume_m3, 0.0)

    @property
    def pumpable_volume_m3(self) -> float:
        """Volume soutirable avant d'atteindre le niveau minimal."""
        return max(self.current_volume_m3 - self.minimum_volume_m3 - self.dead_volume_m3, 0.0)

    @property
    def is_available(self) -> bool:
        return self.status is EquipmentStatus.AVAILABLE

    def liquid_surface_elevation_m(self, level_m: float | None = None) -> float:
        """Cote absolue de la surface libre : altitude du fond plus hauteur de liquide."""
        return self.elevation_m + (self.current_level_m if level_m is None else level_m)

    def mass_kg(self, density_kg_m3: float, level_m: float | None = None) -> float:
        """Masse stockée pour une masse volumique donnée."""
        volume = (
            self.current_volume_m3 if level_m is None else self.strapping.volume_at(level_m)
        )
        return volume * density_kg_m3

    def accepts_fluid(self, fluid_id: str) -> bool:
        """Compatibilité produit (FR-TNK-005, contrôle ``VIOL_TANK_PRODUCT_INCOMPATIBLE``).

        Un bac vide sans produit affecté accepte tout produit compatible. Un bac contenant
        déjà un produit n'accepte que ce produit, sauf si le bac déclare explicitement une
        liste de compatibilité.
        """
        if self.compatible_fluid_ids:
            return fluid_id in self.compatible_fluid_ids
        if self.fluid_id is None:
            return True
        return fluid_id == self.fluid_id

    def with_level(self, level_m: float) -> Tank:
        """Copie du bac à un autre niveau, sans modifier sa fiche."""
        return Tank(
            id=self.id,
            name=self.name,
            strapping=self.strapping,
            levels=self.levels,
            tank_type=self.tank_type,
            elevation_m=self.elevation_m,
            current_level_m=level_m,
            fluid_id=self.fluid_id,
            compatible_fluid_ids=self.compatible_fluid_ids,
            status=self.status,
            dead_volume_m3=self.dead_volume_m3,
            label=self.label,
            metadata=self.metadata,
        )

    def with_volume(self, volume_m3: float) -> Tank:
        """Copie du bac contenant le volume indiqué."""
        return self.with_level(self.strapping.height_at(volume_m3))

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "label": self.label,
            "tank_type": self.tank_type.value,
            "elevation_m": self.elevation_m,
            "current_level_m": self.current_level_m,
            "current_volume_m3": self.current_volume_m3,
            "nominal_capacity_m3": self.nominal_capacity_m3,
            "dead_volume_m3": self.dead_volume_m3,
            "fluid_id": self.fluid_id,
            "compatible_fluid_ids": list(self.compatible_fluid_ids),
            "status": self.status.value,
            "levels": self.levels.as_dict(),
            "strapping": self.strapping.as_dict(),
        }
