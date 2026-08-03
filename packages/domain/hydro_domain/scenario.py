"""Scénarios, conditions aux limites et options de solveur.

Un scénario référence un modèle et n'en stocke que les **différences** (D12 § 5) : états
d'équipement, vitesses, conditions aux limites et objectif. La baseline n'est jamais modifiée
(FR-SCN-001), ce qui garantit la filiation et la reproductibilité.

Le système doit vérifier que le problème est **suffisamment contraint** et détecter les
conditions contradictoires (D07 § 7). Pour un pipeline linéaire, exactement deux conditions
indépendantes sont nécessaires parmi : pression amont, pression aval, débit imposé, niveau de
bac amont, niveau de bac aval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hydro_domain.enums import (
    BoundaryKind,
    EquipmentStatus,
    FrictionModel,
    ObjectiveKind,
)
from hydro_shared.errors import BoundaryConditionError

#: Tolérance par défaut sur le résidu de pression, en pascals. Sur des pressions de plusieurs
#: mégapascals, 1 Pa correspond à un résidu relatif de l'ordre de 10⁻⁷ : très en deçà de la
#: précision des données d'entrée, tout en restant atteignable numériquement.
DEFAULT_PRESSURE_TOLERANCE_PA = 1.0
#: Tolérance sur l'inconnue débit du solveur, en m³/s.
DEFAULT_FLOW_TOLERANCE_M3_S = 1.0e-9
#: Tolérance par défaut sur le bilan de masse, en relatif (D10 § 3).
DEFAULT_MASS_BALANCE_TOLERANCE = 1e-6
#: Nombre maximal d'itérations par défaut.
DEFAULT_MAX_ITERATIONS = 100
#: Pas d'échantillonnage par défaut du profil de sortie, en mètres.
DEFAULT_PROFILE_STEP_M = 1000.0


@dataclass(frozen=True, slots=True)
class BoundaryCondition:
    """Condition imposée à une extrémité ou à un nœud du réseau."""

    kind: BoundaryKind
    value: float
    #: Nœud ou extrémité concerné : ``"inlet"``, ``"outlet"`` ou un identifiant de nœud.
    location: str = "inlet"
    label: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "value": self.value,
            "location": self.location,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class SolverOptions:
    """Paramètres numériques du calcul, enregistrés avec le résultat (NFR-SCI-001)."""

    friction_model: FrictionModel = FrictionModel.COLEBROOK_WHITE
    pressure_tolerance_pa: float = DEFAULT_PRESSURE_TOLERANCE_PA
    flow_tolerance_m3_s: float = DEFAULT_FLOW_TOLERANCE_M3_S
    mass_balance_tolerance: float = DEFAULT_MASS_BALANCE_TOLERANCE
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    profile_step_m: float = DEFAULT_PROFILE_STEP_M
    #: Journalise chaque itération du solveur ; volumineux, réservé au diagnostic.
    store_iterations: bool = False
    #: Utilise l'ajustement ``H = a − b·Q²`` au lieu de l'interpolation des points constructeur.
    use_quadratic_pump_fit: bool = False
    #: Borne supérieure de la recherche de débit, en m³/s. ``None`` : déterminée automatiquement.
    max_flow_m3_s: float | None = None
    #: Détecte et signale les zones susceptibles d'être gravitaires (modèle PHY-GRV-01).
    detect_gravity_zones: bool = True
    #: Applique le modèle de zone gravitaire au calcul lui-même, en bornant la charge à
    #: ``z + p_v/(ρg)`` dans les portions dépressurisées.
    #:
    #: **Désactivé par défaut.** Le modèle par défaut est celui d'une conduite pleine ; une
    #: pression calculée sous la pression de vapeur y est traitée comme une violation
    #: critique (contrôle C-002), ce qui est la posture prudente. L'activation de cette
    #: option sélectionne explicitement le modèle académique à surface libre décrit au
    #: D07 § 8, dont les hypothèses (interface gaz-liquide, régime stable, capacité de
    #: transport) doivent être vérifiées avant tout usage industriel.
    apply_gravity_model: bool = False
    #: Vitesses admissibles pour le contrôle C-005, en m/s.
    min_velocity_m_s: float | None = None
    max_velocity_m_s: float | None = 3.0

    def __post_init__(self) -> None:
        if self.pressure_tolerance_pa <= 0:
            raise BoundaryConditionError(
                "La tolérance de pression doit être strictement positive.",
                pressure_tolerance_pa=self.pressure_tolerance_pa,
            )
        if self.mass_balance_tolerance <= 0:
            raise BoundaryConditionError(
                "La tolérance de bilan de masse doit être strictement positive.",
                mass_balance_tolerance=self.mass_balance_tolerance,
            )
        if self.flow_tolerance_m3_s <= 0:
            raise BoundaryConditionError(
                "La tolérance de débit doit être strictement positive.",
                flow_tolerance_m3_s=self.flow_tolerance_m3_s,
            )
        if self.max_flow_m3_s is not None and self.max_flow_m3_s <= 0:
            raise BoundaryConditionError(
                "La borne maximale de débit doit être strictement positive.",
                max_flow_m3_s=self.max_flow_m3_s,
            )
        if self.max_iterations < 1:
            raise BoundaryConditionError(
                "Le nombre maximal d'itérations doit être au moins 1.",
                max_iterations=self.max_iterations,
            )
        if self.profile_step_m <= 0:
            raise BoundaryConditionError(
                "Le pas du profil de sortie doit être strictement positif.",
                profile_step_m=self.profile_step_m,
            )
        if (
            self.min_velocity_m_s is not None
            and self.max_velocity_m_s is not None
            and self.min_velocity_m_s >= self.max_velocity_m_s
        ):
            raise BoundaryConditionError(
                "La vitesse minimale doit être inférieure à la vitesse maximale.",
                min_velocity_m_s=self.min_velocity_m_s,
                max_velocity_m_s=self.max_velocity_m_s,
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "friction_model": self.friction_model.value,
            "pressure_tolerance_pa": self.pressure_tolerance_pa,
            "flow_tolerance_m3_s": self.flow_tolerance_m3_s,
            "mass_balance_tolerance": self.mass_balance_tolerance,
            "max_iterations": self.max_iterations,
            "profile_step_m": self.profile_step_m,
            "store_iterations": self.store_iterations,
            "use_quadratic_pump_fit": self.use_quadratic_pump_fit,
            "max_flow_m3_s": self.max_flow_m3_s,
            "detect_gravity_zones": self.detect_gravity_zones,
            "apply_gravity_model": self.apply_gravity_model,
            "min_velocity_m_s": self.min_velocity_m_s,
            "max_velocity_m_s": self.max_velocity_m_s,
        }


@dataclass(frozen=True, slots=True)
class PumpOverride:
    """Modification de l'état d'une pompe dans un scénario."""

    pump_id: str
    status: EquipmentStatus | None = None
    running: bool | None = None
    speed_ratio: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "pump_id": self.pump_id,
            "status": self.status.value if self.status else None,
            "running": self.running,
            "speed_ratio": self.speed_ratio,
        }


@dataclass(frozen=True, slots=True)
class StationOverride:
    """Modification de l'état d'une station dans un scénario."""

    station_id: str
    status: EquipmentStatus | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "station_id": self.station_id,
            "status": self.status.value if self.status else None,
        }


@dataclass(frozen=True, slots=True)
class SegmentOverride:
    """Modification de l'état d'un tronçon dans un scénario."""

    segment_id: str
    status: EquipmentStatus | None = None
    #: Coefficient de perte singulière additionnel, par exemple un filtre colmaté (§ 4.8).
    additional_k: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "status": self.status.value if self.status else None,
            "additional_k": self.additional_k,
        }


@dataclass(frozen=True, slots=True)
class Scenario:
    """Conditions d'exploitation d'un calcul (D-v2 § 4.8).

    Un scénario est identifié, filiable (``parent_id``) et entièrement décrit par ses
    surcharges et ses conditions aux limites. Deux scénarios partageant la même baseline et
    les mêmes surcharges produisent le même paquet d'entrée canonique et donc la même
    empreinte de calcul.
    """

    id: str
    name: str
    #: Température d'exploitation, en kelvins ; alimente l'évaluation des propriétés.
    temperature_k: float | None = None
    #: Débit imposé à l'entrée du pipeline, en m³/s. ``None`` : le débit est l'inconnue.
    imposed_flow_m3_s: float | None = None
    #: Pression absolue imposée à l'entrée, en pascals.
    inlet_pressure_pa: float | None = None
    #: Pression absolue imposée en sortie, en pascals.
    outlet_pressure_pa: float | None = None
    #: Niveau imposé au bac amont, en mètres.
    inlet_tank_level_m: float | None = None
    #: Niveau imposé au bac aval, en mètres.
    outlet_tank_level_m: float | None = None

    pump_overrides: tuple[PumpOverride, ...] = ()
    station_overrides: tuple[StationOverride, ...] = ()
    segment_overrides: tuple[SegmentOverride, ...] = ()

    solver: SolverOptions = field(default_factory=SolverOptions)
    objective: ObjectiveKind | None = None
    #: Tarif énergétique pour le chiffrage du scénario, en unité monétaire par joule.
    energy_price_per_joule: float | None = None
    parent_id: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ conditions

    @property
    def boundary_conditions(self) -> tuple[BoundaryCondition, ...]:
        """Conditions aux limites effectivement déclarées."""
        conditions: list[BoundaryCondition] = []
        if self.inlet_pressure_pa is not None:
            conditions.append(
                BoundaryCondition(BoundaryKind.PRESSURE, self.inlet_pressure_pa, "inlet")
            )
        if self.outlet_pressure_pa is not None:
            conditions.append(
                BoundaryCondition(BoundaryKind.PRESSURE, self.outlet_pressure_pa, "outlet")
            )
        if self.imposed_flow_m3_s is not None:
            conditions.append(BoundaryCondition(BoundaryKind.FLOW, self.imposed_flow_m3_s, "inlet"))
        if self.inlet_tank_level_m is not None:
            conditions.append(
                BoundaryCondition(BoundaryKind.TANK_LEVEL, self.inlet_tank_level_m, "inlet")
            )
        if self.outlet_tank_level_m is not None:
            conditions.append(
                BoundaryCondition(BoundaryKind.TANK_LEVEL, self.outlet_tank_level_m, "outlet")
            )
        return tuple(conditions)

    @property
    def solves_for_flow(self) -> bool:
        """Vrai si le débit est l'inconnue du problème (cas UC-06 : débit compatible)."""
        return self.imposed_flow_m3_s is None

    def validate_boundary_conditions(self) -> list[str]:
        """Vérifie que le problème est correctement contraint (D07 § 7).

        Pour un pipeline linéaire, il faut exactement une condition à chaque extrémité, ou une
        condition d'extrémité et un débit imposé. Les combinaisons redondantes sont rejetées :
        imposer simultanément la pression amont, la pression aval **et** le débit sur-contraint
        le problème, sauf à accepter qu'une des trois soit ignorée — ce que le produit ne fait
        jamais silencieusement (FR-GEN-005).
        """
        problems: list[str] = []

        inlet_specs = sum(
            1 for value in (self.inlet_pressure_pa, self.inlet_tank_level_m) if value is not None
        )
        outlet_specs = sum(
            1 for value in (self.outlet_pressure_pa, self.outlet_tank_level_m) if value is not None
        )

        if inlet_specs > 1:
            problems.append(
                "L'entrée est sur-contrainte : une pression et un niveau de bac sont imposés "
                "simultanément. Choisissez l'une des deux conditions."
            )
        if outlet_specs > 1:
            problems.append(
                "La sortie est sur-contrainte : une pression et un niveau de bac sont imposés "
                "simultanément. Choisissez l'une des deux conditions."
            )

        total = inlet_specs + outlet_specs + (0 if self.solves_for_flow else 1)
        if total < 2:
            problems.append(
                "Le problème est sous-contraint : deux conditions indépendantes sont nécessaires "
                "(pression ou niveau à chaque extrémité, ou une extrémité et un débit imposé). "
                f"{total} condition(s) déclarée(s)."
            )
        if total > 2:
            problems.append(
                "Le problème est sur-contraint : trois conditions ou plus sont imposées alors que "
                "deux suffisent. Retirez la condition redondante pour éviter une solution "
                "arbitraire."
            )

        if self.imposed_flow_m3_s is not None and self.imposed_flow_m3_s < 0:
            problems.append(
                "Le débit imposé est négatif : le sens d'écoulement doit être exprimé par "
                "l'orientation du pipeline, pas par le signe du débit."
            )
        for name, pressure in (
            ("d'entrée", self.inlet_pressure_pa),
            ("de sortie", self.outlet_pressure_pa),
        ):
            if pressure is not None and pressure <= 0:
                problems.append(
                    f"La pression {name} doit être strictement positive : les pressions sont "
                    f"exprimées en pascals absolus."
                )
        if self.temperature_k is not None and self.temperature_k <= 0:
            problems.append("La température doit être exprimée en kelvins et strictement positive.")

        return problems

    # ------------------------------------------------------------------ accès

    def pump_override_for(self, pump_id: str) -> PumpOverride | None:
        for override in self.pump_overrides:
            if override.pump_id == pump_id:
                return override
        return None

    def station_override_for(self, station_id: str) -> StationOverride | None:
        for override in self.station_overrides:
            if override.station_id == station_id:
                return override
        return None

    def segment_override_for(self, segment_id: str) -> SegmentOverride | None:
        for override in self.segment_overrides:
            if override.segment_id == segment_id:
                return override
        return None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "description": self.description,
            "temperature_k": self.temperature_k,
            "imposed_flow_m3_s": self.imposed_flow_m3_s,
            "inlet_pressure_pa": self.inlet_pressure_pa,
            "outlet_pressure_pa": self.outlet_pressure_pa,
            "inlet_tank_level_m": self.inlet_tank_level_m,
            "outlet_tank_level_m": self.outlet_tank_level_m,
            "pump_overrides": [o.as_dict() for o in self.pump_overrides],
            "station_overrides": [o.as_dict() for o in self.station_overrides],
            "segment_overrides": [o.as_dict() for o in self.segment_overrides],
            "solver": self.solver.as_dict(),
            "objective": self.objective.value if self.objective else None,
            "energy_price_per_joule": self.energy_price_per_joule,
        }
