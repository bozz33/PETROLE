"""Énumérations métier partagées par le noyau scientifique et la persistance.

Les valeurs sont des chaînes stables : elles apparaissent dans le paquet d'entrée canonique,
dans les empreintes de calcul et dans l'API. Elles ne doivent pas être renommées sans
procédure de dépréciation.
"""

from __future__ import annotations

from enum import StrEnum


class EquipmentStatus(StrEnum):
    """État d'un équipement dans un scénario (D09 § 4, D-v2 § 4.5)."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    MAINTENANCE = "maintenance"
    BYPASSED = "bypassed"

    @property
    def is_in_service(self) -> bool:
        return self is EquipmentStatus.AVAILABLE


class PumpRole(StrEnum):
    """Rôle d'une pompe dans sa station (FR-PMP-004)."""

    MAIN = "main"
    STANDBY = "standby"
    BOOSTER = "booster"

    @property
    def starts_by_default(self) -> bool:
        """Une pompe de secours ne démarre que si un scénario l'active explicitement."""
        return self is not PumpRole.STANDBY


class PumpArrangement(StrEnum):
    """Montage des pompes d'une station (D07 § 6)."""

    #: Les charges s'additionnent au même débit.
    SERIES = "series"
    #: Les débits s'additionnent à la même charge.
    PARALLEL = "parallel"


class NodeType(StrEnum):
    """Types de nœuds du graphe hydraulique (D09 § 4)."""

    SOURCE = "source"
    SINK = "sink"
    JUNCTION = "junction"
    STATION = "station"
    TANK = "tank"
    BOUNDARY = "boundary"


class EdgeType(StrEnum):
    """Types d'arêtes du graphe hydraulique."""

    PIPE = "pipe"
    PUMP = "pump"
    VALVE = "valve"
    FITTING_GROUP = "fitting_group"


class FluidCategory(StrEnum):
    """Catégories de produits gérées par le MVP (D09 § 6, D-v2 § 4.3)."""

    CRUDE = "crude"
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    KEROSENE = "kerosene"
    FUEL_OIL_LIGHT = "fuel_oil_light"
    FUEL_OIL_HEAVY = "fuel_oil_heavy"
    CONDENSATE = "condensate"
    WATER = "water"
    CUSTOM = "custom"


class PropertySource(StrEnum):
    """Origine d'une valeur de propriété, toujours tracée (D-v2 § 5.5)."""

    #: Valeur saisie ou issue d'un rapport de laboratoire : source prioritaire.
    LABORATORY = "laboratory"
    #: Table interne température → propriété, interpolée dans son domaine.
    INTERNAL_TABLE = "internal_table"
    #: Corrélation paramétrique interne validée.
    CORRELATION = "correlation"
    #: Bibliothèque CoolProp, pour les fluides qu'elle couvre.
    COOLPROP = "coolprop"
    #: Valeur constante : acceptable sur une plage étroite, signalée sinon.
    CONSTANT = "constant"


class PropertyQuality(StrEnum):
    """Statut qualité d'un point de propriété (D09 § 6)."""

    MEASURED = "measured"
    APPROVED = "approved"
    ESTIMATED = "estimated"
    EXTRAPOLATED = "extrapolated"


class FrictionModel(StrEnum):
    """Corrélations de facteur de frottement disponibles (D-v2 § 5.3, FR-LIQ-009).

    Toutes sont sélectionnables par scénario, ce qui permet l'analyse de sensibilité
    demandée au § 5.3 sans modifier le code du solveur.
    """

    #: Colebrook–White résolu implicitement : référence du MVP.
    COLEBROOK_WHITE = "colebrook_white"
    #: Approximation explicite de Haaland (1983).
    HAALAND = "haaland"
    #: Approximation explicite de Swamee–Jain (1976).
    SWAMEE_JAIN = "swamee_jain"
    #: Corrélation d'Altshul, utilisée par le support académique fourni ; conservée pour
    #: reproduire le cas de référence de 460 km (D10 § 5).
    ALTSHUL = "altshul"


class BoundaryKind(StrEnum):
    """Nature d'une condition aux limites (D07 § 7)."""

    PRESSURE = "pressure"
    FLOW = "flow"
    TANK_LEVEL = "tank_level"


class TankType(StrEnum):
    """Types de réservoirs du MVP (D09 § 7, D-v2 § 4.6)."""

    VERTICAL_FIXED_ROOF = "vertical_fixed_roof"
    FLOATING_ROOF = "floating_roof"
    HORIZONTAL = "horizontal"
    SPHERE = "sphere"
    CUSTOM = "custom"


class ObjectiveKind(StrEnum):
    """Objectifs d'optimisation proposés au MVP (D-v2 § 4.10)."""

    MIN_ENERGY = "min_energy"
    MIN_COST = "min_cost"
    MIN_PUMP_COUNT = "min_pump_count"
    MIN_STARTS = "min_starts"
    MAX_FLOW = "max_flow"


class TransferStopReason(StrEnum):
    """Cause d'arrêt d'un transfert bac-à-bac (D-v2 § 4.7)."""

    TARGET_VOLUME_REACHED = "target_volume_reached"
    TARGET_LEVEL_REACHED = "target_level_reached"
    SOURCE_LOW_LEVEL = "source_low_level"
    DESTINATION_HIGH_LEVEL = "destination_high_level"
    DURATION_REACHED = "duration_reached"
    HYDRAULIC_CONSTRAINT = "hydraulic_constraint"
    NOT_FEASIBLE = "not_feasible"
