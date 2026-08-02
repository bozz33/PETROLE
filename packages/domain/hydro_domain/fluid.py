"""Produits et propriétés physiques.

Hiérarchie des sources (D-v2 § 5.5) : les données de laboratoire et de l'opérateur sont
**prioritaires** ; les tables internes s'appliquent dans leur domaine ; CoolProp couvre les
fluides qu'il connaît ; une valeur constante n'est acceptable que sur une plage étroite.

Toute évaluation hors du domaine tabulé produit un avertissement `WARN_EXTRAPOLATION`
(contrôle C-011, FR-FLD-004) : le résultat reste disponible mais n'est jamais silencieux.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hydro_shared.errors import FluidPropertyError
from hydro_shared.units import Dimension, Measure

from hydro_domain.enums import FluidCategory, PropertyQuality, PropertySource
from hydro_domain.interpolation import MonotoneTable

#: Température de référence usuelle des fiches produit (15 °C).
REFERENCE_TEMPERATURE_K = 288.15
#: Pression atmosphérique normale.
STANDARD_PRESSURE_PA = 101_325.0


@dataclass(frozen=True, slots=True)
class PropertyPoint:
    """Point de propriété mesuré ou calculé, avec sa traçabilité complète (D09 § 6)."""

    temperature_k: float
    value: float
    pressure_pa: float = STANDARD_PRESSURE_PA
    uncertainty: float | None = None
    method: str | None = None
    quality: PropertyQuality = PropertyQuality.MEASURED

    def as_dict(self) -> dict[str, Any]:
        return {
            "temperature_k": self.temperature_k,
            "pressure_pa": self.pressure_pa,
            "value": self.value,
            "uncertainty": self.uncertainty,
            "method": self.method,
            "quality": self.quality.value,
        }


@dataclass(frozen=True, slots=True)
class PropertyEvaluation:
    """Résultat d'une évaluation de propriété : valeur **et** conditions de son obtention.

    Le couple ``(value, extrapolated)`` est ce qui permet au moteur d'émettre C-011 sans
    inspecter l'implémentation du fournisseur.
    """

    value: float
    source: PropertySource
    extrapolated: bool = False
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "source": self.source.value,
            "extrapolated": self.extrapolated,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class PropertyTable:
    """Table température → propriété, interpolée linéairement dans son domaine.

    L'extrapolation est autorisée mais **toujours signalée** ; elle est linéaire à partir des
    deux points extrêmes, ce qui reste prévisible et borné.
    """

    points: tuple[PropertyPoint, ...]
    source: PropertySource = PropertySource.INTERNAL_TABLE
    reference: str | None = None

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise FluidPropertyError(
                "Une table de propriété exige au moins deux points.",
                point_count=len(self.points),
            )
        temperatures = [p.temperature_k for p in self.points]
        if any(b <= a for a, b in zip(temperatures, temperatures[1:], strict=False)):
            raise FluidPropertyError(
                "Les températures d'une table de propriété doivent être strictement croissantes.",
                temperatures=temperatures,
            )

    @property
    def temperature_range_k(self) -> tuple[float, float]:
        return (self.points[0].temperature_k, self.points[-1].temperature_k)

    def evaluate(self, temperature_k: float) -> PropertyEvaluation:
        lo, hi = self.temperature_range_k
        extrapolated = temperature_k < lo or temperature_k > hi
        xs = [p.temperature_k for p in self.points]
        ys = [p.value for p in self.points]
        value = _linear_interpolate_extrapolate(xs, ys, temperature_k)
        detail = None
        if extrapolated:
            detail = (
                f"Température {temperature_k:.2f} K hors du domaine tabulé "
                f"[{lo:.2f} K ; {hi:.2f} K]."
            )
        return PropertyEvaluation(
            value=value, source=self.source, extrapolated=extrapolated, detail=detail
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.value,
            "reference": self.reference,
            "points": [p.as_dict() for p in self.points],
        }


def _linear_interpolate_extrapolate(xs: list[float], ys: list[float], x: float) -> float:
    """Interpolation linéaire avec prolongement linéaire aux extrémités."""
    if x <= xs[0]:
        if len(xs) == 1:
            return ys[0]
        slope = (ys[1] - ys[0]) / (xs[1] - xs[0])
        return ys[0] + slope * (x - xs[0])
    if x >= xs[-1]:
        slope = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
        return ys[-1] + slope * (x - xs[-1])
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]  # pragma: no cover - inatteignable, bornes déjà traitées


@dataclass(frozen=True, slots=True)
class Fluid:
    """Fiche produit : identification, conditions de référence, propriétés et traçabilité.

    Le MVP traite un liquide newtonien monophasé (D-v2 § 5.1). Un produit non newtonien ou
    proche du point d'écoulement exige un modèle rhéologique spécifique, hors périmètre.

    Les propriétés minimales sont la masse volumique, la viscosité cinématique et la pression
    de vapeur (FR-FLD-001). Chacune peut être fournie soit par une constante, soit par une
    table, la table étant prioritaire lorsqu'elle existe.
    """

    id: str
    name: str
    category: FluidCategory = FluidCategory.CUSTOM

    # Conditions de référence de la fiche.
    reference_temperature_k: float = REFERENCE_TEMPERATURE_K
    reference_pressure_pa: float = STANDARD_PRESSURE_PA

    # Valeurs constantes (utilisées si aucune table n'est fournie).
    density_kg_m3: float | None = None
    kinematic_viscosity_m2_s: float | None = None
    vapor_pressure_pa: float | None = None

    # Tables température → propriété (prioritaires sur les constantes).
    density_table: PropertyTable | None = None
    kinematic_viscosity_table: PropertyTable | None = None
    vapor_pressure_table: PropertyTable | None = None

    #: Coefficient de dilatation volumique, utilisé si seule une masse volumique de
    #: référence est connue : ρ(T) = ρ_ref / (1 + β (T − T_ref)).
    thermal_expansion_1_k: float | None = None

    #: Nom du fluide CoolProp lorsqu'il est applicable (FR-FLD-005).
    coolprop_name: str | None = None

    # Traçabilité (D09 § 6).
    data_source: str | None = None
    batch_reference: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.density_table is None and self.density_kg_m3 is None and self.coolprop_name is None:
            raise FluidPropertyError(
                "Le produit doit fournir une masse volumique constante, une table ou un fluide "
                "CoolProp.",
                fluid=self.name,
            )
        if self.density_kg_m3 is not None and self.density_kg_m3 <= 0:
            raise FluidPropertyError(
                "La masse volumique doit être strictement positive.",
                fluid=self.name,
                density_kg_m3=self.density_kg_m3,
            )
        if self.kinematic_viscosity_m2_s is not None and self.kinematic_viscosity_m2_s <= 0:
            raise FluidPropertyError(
                "La viscosité cinématique doit être strictement positive.",
                fluid=self.name,
                kinematic_viscosity_m2_s=self.kinematic_viscosity_m2_s,
            )
        if self.vapor_pressure_pa is not None and self.vapor_pressure_pa < 0:
            raise FluidPropertyError(
                "La pression de vapeur ne peut pas être négative.",
                fluid=self.name,
                vapor_pressure_pa=self.vapor_pressure_pa,
            )

    # ------------------------------------------------------------------ propriétés

    def density(self, temperature_k: float | None = None) -> PropertyEvaluation:
        """Masse volumique ρ(T) en kg/m³."""
        t = self.reference_temperature_k if temperature_k is None else temperature_k
        if self.density_table is not None:
            return self.density_table.evaluate(t)
        if self.density_kg_m3 is not None:
            if self.thermal_expansion_1_k is not None:
                delta = t - self.reference_temperature_k
                value = self.density_kg_m3 / (1.0 + self.thermal_expansion_1_k * delta)
                return PropertyEvaluation(
                    value=value,
                    source=PropertySource.CORRELATION,
                    detail="Dilatation volumique linéaire à partir de la masse volumique de référence.",
                )
            return PropertyEvaluation(
                value=self.density_kg_m3,
                source=PropertySource.CONSTANT,
                detail="Masse volumique constante ; vérifier la plage de température.",
            )
        raise FluidPropertyError(
            "Masse volumique indisponible sans fournisseur externe.", fluid=self.name
        )

    def kinematic_viscosity(self, temperature_k: float | None = None) -> PropertyEvaluation:
        """Viscosité cinématique ν(T) en m²/s."""
        t = self.reference_temperature_k if temperature_k is None else temperature_k
        if self.kinematic_viscosity_table is not None:
            return self.kinematic_viscosity_table.evaluate(t)
        if self.kinematic_viscosity_m2_s is not None:
            return PropertyEvaluation(
                value=self.kinematic_viscosity_m2_s,
                source=PropertySource.CONSTANT,
                detail="Viscosité constante ; la dépendance en température est ignorée.",
            )
        raise FluidPropertyError(
            "Viscosité cinématique indisponible sans fournisseur externe.", fluid=self.name
        )

    def dynamic_viscosity(self, temperature_k: float | None = None) -> PropertyEvaluation:
        """Viscosité dynamique μ = ρν en Pa·s (D07 § 2)."""
        nu = self.kinematic_viscosity(temperature_k)
        rho = self.density(temperature_k)
        return PropertyEvaluation(
            value=nu.value * rho.value,
            source=nu.source,
            extrapolated=nu.extrapolated or rho.extrapolated,
            detail="μ = ρ·ν",
        )

    def vapor_pressure(self, temperature_k: float | None = None) -> PropertyEvaluation:
        """Pression de vapeur p_v(T) en Pa absolus, utilisée pour C-002 et C-003."""
        t = self.reference_temperature_k if temperature_k is None else temperature_k
        if self.vapor_pressure_table is not None:
            return self.vapor_pressure_table.evaluate(t)
        if self.vapor_pressure_pa is not None:
            return PropertyEvaluation(
                value=self.vapor_pressure_pa,
                source=PropertySource.CONSTANT,
                detail="Pression de vapeur constante.",
            )
        # Sans donnée, on ne devine pas : la valeur nulle est la plus conservatrice pour la
        # détection de dépression, mais l'absence est signalée par le moteur.
        return PropertyEvaluation(
            value=0.0,
            source=PropertySource.CONSTANT,
            detail="Pression de vapeur non renseignée ; contrôle de cavitation non concluant.",
        )

    @property
    def has_vapor_pressure(self) -> bool:
        return self.vapor_pressure_pa is not None or self.vapor_pressure_table is not None

    def measures(self, temperature_k: float | None = None) -> dict[str, Measure]:
        """Propriétés évaluées, exprimées comme mesures affichables."""
        t = self.reference_temperature_k if temperature_k is None else temperature_k
        return {
            "density": Measure.si(self.density(t).value, Dimension.DENSITY),
            "kinematic_viscosity": Measure.si(
                self.kinematic_viscosity(t).value, Dimension.KINEMATIC_VISCOSITY
            ),
            "dynamic_viscosity": Measure.si(
                self.dynamic_viscosity(t).value, Dimension.DYNAMIC_VISCOSITY
            ),
            "vapor_pressure": Measure.si(self.vapor_pressure(t).value, Dimension.PRESSURE),
            "temperature": Measure.si(t, Dimension.TEMPERATURE),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "reference_temperature_k": self.reference_temperature_k,
            "reference_pressure_pa": self.reference_pressure_pa,
            "density_kg_m3": self.density_kg_m3,
            "kinematic_viscosity_m2_s": self.kinematic_viscosity_m2_s,
            "vapor_pressure_pa": self.vapor_pressure_pa,
            "thermal_expansion_1_k": self.thermal_expansion_1_k,
            "coolprop_name": self.coolprop_name,
            "density_table": self.density_table.as_dict() if self.density_table else None,
            "kinematic_viscosity_table": (
                self.kinematic_viscosity_table.as_dict()
                if self.kinematic_viscosity_table
                else None
            ),
            "vapor_pressure_table": (
                self.vapor_pressure_table.as_dict() if self.vapor_pressure_table else None
            ),
            "data_source": self.data_source,
            "batch_reference": self.batch_reference,
        }


__all__ = [
    "REFERENCE_TEMPERATURE_K",
    "STANDARD_PRESSURE_PA",
    "Fluid",
    "MonotoneTable",
    "PropertyEvaluation",
    "PropertyPoint",
    "PropertyTable",
]
