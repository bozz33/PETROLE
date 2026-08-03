"""Fournisseurs de propriétés physiques et adaptateur CoolProp.

Le moteur ne consulte jamais directement une constante : il passe par un
:class:`PropertyProvider` qui trace la **source** de chaque valeur et signale toute
extrapolation (contrôle C-011, FR-FLD-004).

Hiérarchie appliquée (D-v2 § 5.5) :

1. valeur de laboratoire ou saisie par l'utilisateur ;
2. table interne température → propriété, dans son domaine ;
3. corrélation interne validée ;
4. CoolProp, pour les fluides que la bibliothèque couvre ;
5. valeur constante, acceptable sur une plage étroite seulement.

CoolProp ne représente pas automatiquement les pétroles bruts et les produits commerciaux :
l'adaptateur n'est utilisé que si le produit déclare explicitement un fluide CoolProp, et il
échoue de façon visible plutôt que de retourner une valeur approchée non tracée.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from hydro_domain.enums import PropertySource
from hydro_domain.fluid import Fluid, PropertyEvaluation


class PropertyProvider(Protocol):
    """Contrat commun à tous les fournisseurs de propriétés."""

    def density(self, temperature_k: float, pressure_pa: float) -> PropertyEvaluation: ...

    def kinematic_viscosity(
        self, temperature_k: float, pressure_pa: float
    ) -> PropertyEvaluation: ...

    def vapor_pressure(self, temperature_k: float) -> PropertyEvaluation: ...


@dataclass(frozen=True, slots=True)
class FluidState:
    """État thermodynamique résolu, utilisé tout au long d'une simulation.

    Les propriétés sont évaluées **une fois** à la température de calcul puis figées : le MVP
    traite un régime permanent isotherme (D-v2 § 5.1). Cette évaluation unique garantit que
    tous les tronçons partagent exactement les mêmes propriétés, condition d'un bilan
    d'énergie cohérent.
    """

    temperature_k: float
    pressure_pa: float
    density_kg_m3: float
    kinematic_viscosity_m2_s: float
    vapor_pressure_pa: float
    density_source: PropertySource
    viscosity_source: PropertySource
    vapor_pressure_source: PropertySource
    extrapolated: bool = False
    notes: tuple[str, ...] = ()

    @property
    def dynamic_viscosity_pa_s(self) -> float:
        """Viscosité dynamique ``μ = ρν``."""
        return self.density_kg_m3 * self.kinematic_viscosity_m2_s

    def as_dict(self) -> dict[str, object]:
        return {
            "temperature_k": self.temperature_k,
            "pressure_pa": self.pressure_pa,
            "density_kg_m3": self.density_kg_m3,
            "kinematic_viscosity_m2_s": self.kinematic_viscosity_m2_s,
            "dynamic_viscosity_pa_s": self.dynamic_viscosity_pa_s,
            "vapor_pressure_pa": self.vapor_pressure_pa,
            "density_source": self.density_source.value,
            "viscosity_source": self.viscosity_source.value,
            "vapor_pressure_source": self.vapor_pressure_source.value,
            "extrapolated": self.extrapolated,
            "notes": list(self.notes),
        }


class FluidPropertyProvider:
    """Fournisseur par défaut : la fiche produit, complétée par CoolProp si déclaré."""

    __slots__ = ("_coolprop", "_fluid")

    def __init__(self, fluid: Fluid, *, use_coolprop: bool | None = None) -> None:
        self._fluid = fluid
        enabled = fluid.coolprop_name is not None if use_coolprop is None else use_coolprop
        self._coolprop = (
            CoolPropAdapter(fluid.coolprop_name) if enabled and fluid.coolprop_name else None
        )

    @property
    def fluid(self) -> Fluid:
        return self._fluid

    def density(self, temperature_k: float, pressure_pa: float) -> PropertyEvaluation:
        if self._fluid.density_table is not None or self._fluid.density_kg_m3 is not None:
            return self._fluid.density(temperature_k)
        if self._coolprop is not None:
            return self._coolprop.density(temperature_k, pressure_pa)
        return self._fluid.density(temperature_k)

    def kinematic_viscosity(self, temperature_k: float, pressure_pa: float) -> PropertyEvaluation:
        if (
            self._fluid.kinematic_viscosity_table is not None
            or self._fluid.kinematic_viscosity_m2_s is not None
        ):
            return self._fluid.kinematic_viscosity(temperature_k)
        if self._coolprop is not None:
            return self._coolprop.kinematic_viscosity(temperature_k, pressure_pa)
        return self._fluid.kinematic_viscosity(temperature_k)

    def vapor_pressure(self, temperature_k: float) -> PropertyEvaluation:
        if self._fluid.has_vapor_pressure:
            return self._fluid.vapor_pressure(temperature_k)
        if self._coolprop is not None:
            return self._coolprop.vapor_pressure(temperature_k)
        return self._fluid.vapor_pressure(temperature_k)

    def resolve(self, temperature_k: float, pressure_pa: float) -> FluidState:
        """Évalue toutes les propriétés et construit l'état figé de la simulation."""
        density = self.density(temperature_k, pressure_pa)
        viscosity = self.kinematic_viscosity(temperature_k, pressure_pa)
        vapor = self.vapor_pressure(temperature_k)

        notes = tuple(
            note for note in (density.detail, viscosity.detail, vapor.detail) if note is not None
        )
        return FluidState(
            temperature_k=temperature_k,
            pressure_pa=pressure_pa,
            density_kg_m3=density.value,
            kinematic_viscosity_m2_s=viscosity.value,
            vapor_pressure_pa=vapor.value,
            density_source=density.source,
            viscosity_source=viscosity.source,
            vapor_pressure_source=vapor.source,
            extrapolated=density.extrapolated or viscosity.extrapolated or vapor.extrapolated,
            notes=notes,
        )


@lru_cache(maxsize=1)
def _coolprop_module():
    """Charge CoolProp à la demande : l'import est coûteux et n'est pas toujours nécessaire."""
    from CoolProp.CoolProp import PropsSI

    return PropsSI


class CoolPropAdapter:
    """Adaptateur vers CoolProp pour les fluides que la bibliothèque couvre.

    L'adaptateur **n'invente rien** : si CoolProp ne connaît pas le fluide ou ne peut pas
    évaluer une propriété dans les conditions demandées, l'erreur est propagée telle quelle.
    Une valeur approchée non tracée serait plus dangereuse qu'une absence de valeur.
    """

    __slots__ = ("fluid_name",)

    def __init__(self, fluid_name: str) -> None:
        self.fluid_name = fluid_name

    def density(self, temperature_k: float, pressure_pa: float) -> PropertyEvaluation:
        props = _coolprop_module()
        value = float(props("D", "T", temperature_k, "P", pressure_pa, self.fluid_name))
        return PropertyEvaluation(
            value=value,
            source=PropertySource.COOLPROP,
            detail=f"CoolProp, fluide « {self.fluid_name} ».",
        )

    def dynamic_viscosity(self, temperature_k: float, pressure_pa: float) -> PropertyEvaluation:
        props = _coolprop_module()
        value = float(props("V", "T", temperature_k, "P", pressure_pa, self.fluid_name))
        return PropertyEvaluation(
            value=value,
            source=PropertySource.COOLPROP,
            detail=f"CoolProp, fluide « {self.fluid_name} ».",
        )

    def kinematic_viscosity(self, temperature_k: float, pressure_pa: float) -> PropertyEvaluation:
        mu = self.dynamic_viscosity(temperature_k, pressure_pa)
        rho = self.density(temperature_k, pressure_pa)
        return PropertyEvaluation(
            value=mu.value / rho.value,
            source=PropertySource.COOLPROP,
            detail=f"CoolProp, ν = μ/ρ pour « {self.fluid_name} ».",
        )

    def vapor_pressure(self, temperature_k: float) -> PropertyEvaluation:
        props = _coolprop_module()
        value = float(props("P", "T", temperature_k, "Q", 0, self.fluid_name))
        return PropertyEvaluation(
            value=value,
            source=PropertySource.COOLPROP,
            detail=f"CoolProp, pression de saturation de « {self.fluid_name} ».",
        )
