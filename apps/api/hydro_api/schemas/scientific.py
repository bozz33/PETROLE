"""Sous-schémas scientifiques typés exposés par l'API.

Ces contrats documentent, dans l'OpenAPI généré par FastAPI, les champs réellement
consommés par les moteurs (HydroLiquid Core, Tank & Transfer, Operations Optimizer).
Ils remplacent les ``dict[str, Any]`` opaques qui rendaient invisibles, sur
``/api/v1/docs``, les courbes de pompe, les propriétés de fluide, les conditions
aux limites, la configuration des stations et les options du solveur.

La conversion vers le paquet canonique du moteur reste assurée par
``hydro_domain.serialization`` (``pump_model_from_dict``, ``fluid_from_dict``,
``scenario_from_dict``, ``solver_options_from_dict``) : ce module ne fait que
documenter et valider tôt, sans dupliquer la logique scientifique.
"""

from __future__ import annotations

import itertools
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


def payload_to_dict(value: Any) -> dict[str, Any]:
    """Normalise un payload scientifique (typé ou libre) en dictionnaire.

    Les sous-schémas scientifiques documentent les champs réels consommés par
    les moteurs ; ils sont aplatis en plain dict avant persistance afin que le
    JSONB PostgreSQL et les assembleurs reçoivent toujours un dictionnaire.
    """

    if isinstance(value, BaseModel):
        return value.model_dump()
    return dict(value) if value else {}


#: Modèles de frottement disponibles (D-v2 § 5.3).
FrictionModelLiteral = Literal["colebrook_white", "haaland", "swamee_jain", "altshul"]

#: Montage des groupes de pompes d'une station (D07 § 6).
ArrangementLiteral = Literal["series", "parallel"]

#: Catégories de produits gérées par le MVP (D09 § 6).
FluidCategoryLiteral = Literal[
    "crude",
    "gasoline",
    "diesel",
    "kerosene",
    "fuel_oil_light",
    "fuel_oil_heavy",
    "condensate",
    "water",
    "custom",
]

#: Origine d'une valeur de propriété (D-v2 § 5.5).
PropertySourceLiteral = Literal[
    "laboratory",
    "internal_table",
    "correlation",
    "coolprop",
    "constant",
]

#: Statut qualité d'un point de propriété (D09 § 6).
PropertyQualityLiteral = Literal["measured", "approved", "estimated", "extrapolated"]

#: Schéma d'interpolation des courbes et tables.
InterpolationLiteral = Literal["linear", "pchip"]

#: Objectifs d'optimisation proposés au MVP (D-v2 § 4.10).
ObjectiveLiteral = Literal[
    "min_energy",
    "min_cost",
    "min_pump_count",
    "min_starts",
    "max_flow",
]

#: État d'un équipement dans un scénario (D09 § 4).
EquipmentStatusLiteral = Literal["available", "unavailable", "maintenance", "bypassed"]


class PumpCurveInput(BaseModel):
    """Courbe constructeur H(Q) et séries optionnelles η(Q), P(Q), NPSHr(Q)."""

    flows_m3_s: list[float] = Field(min_length=2, description="Débits de la courbe H(Q).")
    heads_m: list[float] = Field(min_length=2, description="Hauteurs de la courbe H(Q).")
    efficiencies: list[float] | None = Field(default=None, description="Rendements η(Q).")
    powers_w: list[float] | None = Field(default=None, description="Puissances P(Q) en watts.")
    npshr_m: list[float] | None = Field(
        default=None, description="NPSH requis (m) requis pour le contrôle C-003."
    )
    reference_speed_rpm: float | None = Field(
        default=None, ge=0, description="Vitesse de rotation de référence (rpm)."
    )
    interpolation: InterpolationLiteral = Field(
        default="pchip", description="Méthode d'interpolation de la courbe."
    )

    @model_validator(mode="after")
    def _consistent_lengths(self) -> PumpCurveInput:
        paired = {"efficiencies", "powers_w", "npshr_m"}
        for name in paired:
            value = getattr(self, name)
            if value is not None and len(value) != len(self.flows_m3_s):
                raise ValueError(f"La série '{name}' doit comporter {len(self.flows_m3_s)} points.")
        return self


class PumpModelInput(BaseModel):
    """Modèle de pompe du catalogue technique consommé par le moteur liquide.

    Les champs ``id`` et ``name`` sont injectés par le service catalogue à partir
    du ``code`` et du ``name`` de la ressource : ils ne doivent pas être fournis
    dans ce payload.
    """

    curve: PumpCurveInput = Field(description="Courbe constructeur obligatoire.")
    manufacturer: str | None = None
    motor_rated_power_w: float | None = Field(
        default=None, ge=0, description="Puissance nominale du moteur (W) — contrôle C-007."
    )
    npsh_margin_m: float = Field(
        default=0.5, ge=0, description="Marge de NPSH (m) appliquée au contrôle C-003."
    )
    min_speed_ratio: float = Field(default=0.7, gt=0, description="Rapport de vitesse minimal.")
    max_speed_ratio: float = Field(default=1.0, gt=0, description="Rapport de vitesse maximal.")
    minimum_continuous_flow_m3_s: float | None = Field(
        default=None, ge=0, description="Débit minimum continu (MCSF)."
    )
    data_source: str | None = None


class PropertyPointInput(BaseModel):
    """Point d'une table température → propriété d'un fluide."""

    temperature_k: float = Field(gt=0)
    value: float
    pressure_pa: float = Field(default=101325.0, gt=0)
    uncertainty: float | None = Field(default=None, ge=0)
    method: str | None = None
    quality: PropertyQualityLiteral = "measured"


class PropertyTableInput(BaseModel):
    """Table monotone température → propriété, interpolée dans son domaine."""

    points: list[PropertyPointInput] = Field(
        min_length=2, description="Points à températures strictement croissantes."
    )
    source: PropertySourceLiteral = "internal_table"
    reference: str | None = None

    @model_validator(mode="after")
    def _increasing_temperatures(self) -> PropertyTableInput:
        temps = [point.temperature_k for point in self.points]
        if any(right <= left for left, right in itertools.pairwise(temps)):
            raise ValueError("Les températures de la table doivent être strictement croissantes.")
        return self


class FluidInput(BaseModel):
    """Produit liquide : propriétés et tables température → propriété.

    Au moins une source de masse volumique est obligatoire : ``density_kg_m3``
    scalaire ou ``density_table`` tabulée. Les champs ``id`` et ``name`` sont
    injectés par le service catalogue.
    """

    category: FluidCategoryLiteral = "custom"
    reference_temperature_k: float = Field(default=288.15, gt=0)
    reference_pressure_pa: float = Field(default=101325.0, gt=0)
    density_kg_m3: float | None = Field(default=None, ge=0)
    kinematic_viscosity_m2_s: float | None = Field(default=None, ge=0)
    vapor_pressure_pa: float | None = Field(default=None, ge=0)
    density_table: PropertyTableInput | None = None
    kinematic_viscosity_table: PropertyTableInput | None = None
    vapor_pressure_table: PropertyTableInput | None = None
    thermal_expansion_1_k: float | None = None
    coolprop_name: str | None = None
    data_source: str | None = None
    batch_reference: str | None = None

    @model_validator(mode="after")
    def _density_source_required(self) -> FluidInput:
        if self.density_kg_m3 is None and self.density_table is None:
            raise ValueError(
                "Au moins une source de masse volumique est obligatoire "
                "(density_kg_m3 ou density_table)."
            )
        return self


class SolverOptionsInput(BaseModel):
    """Paramètres numériques du solveur stationnaire (D-v2 § 5.6)."""

    friction_model: FrictionModelLiteral = "colebrook_white"
    pressure_tolerance_pa: float = Field(default=1.0, gt=0)
    flow_tolerance_m3_s: float = Field(default=1.0e-9, gt=0)
    mass_balance_tolerance: float = Field(default=1.0e-6, gt=0)
    max_iterations: int = Field(default=100, ge=1)
    profile_step_m: float = Field(default=1000.0, gt=0)
    store_iterations: bool = False
    use_quadratic_pump_fit: bool = False
    max_flow_m3_s: float | None = Field(default=None, gt=0)
    detect_gravity_zones: bool = True
    apply_gravity_model: bool = False
    min_velocity_m_s: float | None = Field(default=None, ge=0)
    max_velocity_m_s: float | None = Field(default=None, gt=0)


class PumpOverrideInput(BaseModel):
    """Surcharge d'une pompe dans un scénario (panne, secours, vitesse)."""

    pump_id: str = Field(min_length=1)
    status: EquipmentStatusLiteral | None = None
    running: bool | None = None
    speed_ratio: float | None = Field(default=None, gt=0)


class StationOverrideInput(BaseModel):
    """Surcharge d'une station dans un scénario (indisponibilité, bypass)."""

    station_id: str = Field(min_length=1)
    status: EquipmentStatusLiteral | None = None


class SegmentOverrideInput(BaseModel):
    """Surcharge d'un tronçon dans un scénario (filtre colmaté, vanne partielle)."""

    segment_id: str = Field(min_length=1)
    status: EquipmentStatusLiteral | None = None
    additional_k: float | None = Field(default=None, ge=0)


class ScenarioPayloadInput(BaseModel):
    """Conditions d'étude et surcharges d'un scénario de simulation.

    La cohérence des conditions aux limites (exactement deux indépendantes parmi
    débit imposé, pression et niveau de bac) est validée par le moteur au moment
    du calcul : elle n'est pas dupliquée ici afin de garder une seule source de
    vérité scientifique.
    """

    temperature_k: float | None = Field(default=None, gt=0)
    imposed_flow_m3_s: float | None = Field(default=None, gt=0)
    inlet_pressure_pa: float | None = Field(default=None, gt=0)
    outlet_pressure_pa: float | None = Field(default=None, gt=0)
    inlet_tank_level_m: float | None = Field(default=None, ge=0)
    outlet_tank_level_m: float | None = Field(default=None, ge=0)
    pump_overrides: list[PumpOverrideInput] = Field(default_factory=list)
    station_overrides: list[StationOverrideInput] = Field(default_factory=list)
    segment_overrides: list[SegmentOverrideInput] = Field(default_factory=list)
    solver: SolverOptionsInput = Field(default_factory=SolverOptionsInput)
    objective: ObjectiveLiteral | None = None
    energy_price_per_joule: float | None = Field(default=None, ge=0)


class StationConfigurationInput(BaseModel):
    """Configuration hydraulique d'un nœud station (payload de NetworkNode)."""

    arrangement: ArrangementLiteral = Field(
        default="series", description="Montage des groupes de pompes de la station."
    )
    suction_pressure_min_pa: float | None = Field(
        default=None, ge=0, description="Seuil bas de pression d'aspiration (Pa) — contrôle C-004."
    )
    discharge_pressure_max_pa: float | None = Field(
        default=None,
        ge=0,
        description="Seuil haut de pression de refoulement (Pa) — contrôle C-004.",
    )
    suction_line_k: float = Field(
        default=0.0, ge=0, description="Coefficient de perte de la ligne d'aspiration."
    )
    suction_line_diameter_m: float | None = Field(
        default=None,
        gt=0,
        description="Diamètre de la ligne d'aspiration — requis pour C-003 (NPSH).",
    )
    bypass_k: float = Field(default=0.0, ge=0, description="Coefficient de perte du bypass.")
    drive_efficiency: float = Field(
        default=1.0, gt=0, le=1.0, description="Rendement de l'entraînement (moteur/variateur)."
    )
    label: str | None = Field(default=None, max_length=200, description="Libellé d'affichage.")


class InjectionNodePayloadInput(BaseModel):
    """Payload d'un nœud d'injection (débit entrant positif)."""

    flow_m3_s: float = Field(gt=0, description="Débit injecté dans le réseau (m³/s).")


class OfftakeNodePayloadInput(BaseModel):
    """Payload d'un nœud de soutirage (débit sortant positif)."""

    flow_m3_s: float = Field(gt=0, description="Débit soutiré du réseau (m³/s).")


class TankNodePayloadInput(BaseModel):
    """Payload d'un nœud de raccordement de réservoir.

    Le nœud porte l'altitude du piquage ; ``tank_id`` désigne le réservoir
    réellement raccordé. Sans cette liaison, un transfert ne peut pas être
    rattaché de façon déterministe au réseau.
    """

    tank_id: uuid.UUID = Field(description="Réservoir raccordé à ce nœud.")
    connection_label: str | None = Field(
        default=None, max_length=200, description="Repère du piquage sur le bac."
    )


class TerminalNodePayloadInput(BaseModel):
    """Payload d'un nœud terminal (réservoir d'extrémité destination).

    Nœud de type ``terminal`` du réseau versionné ; payload généralement vide.
    """


class EdgeGeometryInput(BaseModel):
    """Compléments géométriques d'un tronçon (payload de NetworkEdge)."""

    outer_diameter_m: float | None = Field(default=None, gt=0)
    wall_thickness_m: float | None = Field(default=None, gt=0)
    minimum_pressure_pa: float | None = Field(
        default=None,
        ge=0,
        description="Pression minimale admissible sur le tronçon — contrôle C-002.",
    )


class PumpAssetInput(BaseModel):
    """Configuration d'exploitation d'une pompe posée sur un nœud (AssetInstance)."""

    running: bool | None = Field(default=None, description="Pompe en marche.")
    speed_ratio: float | None = Field(
        default=None, gt=0, description="Rapport de vitesse (variateur)."
    )


class ValveAssetInput(BaseModel):
    """Configuration d'une vanne ou d'un accessoire posé sur un tronçon."""

    chainage_m: float | None = Field(default=None, ge=0, description="Position le long du tronçon.")
    quantity: int = Field(default=1, ge=1)
    opening_ratio: float = Field(
        default=1.0, ge=0, le=1.0, description="Taux d'ouverture (0 = fermé, 1 = ouvert)."
    )


#: Types de vannes couramment rencontrés sur une ligne liquide (D09 § 6).
ValveTypeLiteral = Literal[
    "gate",
    "globe",
    "ball",
    "butterfly",
    "check",
    "control",
    "plug",
    "needle",
    "other",
]

#: Position de repli d'une vanne motorisée en cas de perte d'énergie.
FailPositionLiteral = Literal["fail_open", "fail_close", "fail_last", "not_applicable"]

#: Familles d'accessoires dont la perte singulière est prise en compte.
AccessoryTypeLiteral = Literal[
    "elbow",
    "tee",
    "reducer",
    "expander",
    "filter",
    "check_valve",
    "entrance",
    "exit",
    "custom",
]


class ValveInput(BaseModel):
    """Fiche d'une vanne du catalogue technique.

    Seul ``k_coefficient`` est consommé par le calcul hydraulique : les autres
    champs documentent l'équipement et servent aux rapports et à l'exploitation.
    """

    valve_type: ValveTypeLiteral = Field(
        default="gate", description="Type de vanne selon la nomenclature du dictionnaire."
    )
    nominal_diameter_m: float | None = Field(
        default=None, gt=0, description="Diamètre nominal (m)."
    )
    k_coefficient: float | None = Field(
        default=None,
        ge=0,
        description="Coefficient de perte singulière utilisé par le calcul hydraulique.",
    )
    cv: float | None = Field(default=None, ge=0, description="Coefficient de débit Cv (US).")
    kv: float | None = Field(default=None, ge=0, description="Coefficient de débit Kv (SI).")
    opening_ratio: float = Field(
        default=1.0, ge=0, le=1.0, description="Taux d'ouverture nominal (0 = fermé, 1 = ouvert)."
    )
    opening_time_s: float | None = Field(default=None, ge=0, description="Temps d'ouverture (s).")
    closing_time_s: float | None = Field(default=None, ge=0, description="Temps de fermeture (s).")
    fail_position: FailPositionLiteral = Field(
        default="not_applicable", description="Position de repli en cas de perte d'énergie."
    )
    pressure_class: str | None = Field(
        default=None, max_length=50, description="Classe de pression, par exemple ANSI 300."
    )
    manufacturer: str | None = Field(default=None, max_length=200)
    data_source: str | None = Field(default=None, max_length=10_000)


class MaterialInput(BaseModel):
    """Fiche d'un matériau de conduite du catalogue technique.

    ``roughness_m`` alimente le calcul de perte de charge et ``mawp_pa`` le
    contrôle de pression maximale ; les autres champs sont documentaires.
    """

    roughness_m: float | None = Field(
        default=None, ge=0, description="Rugosité absolue utilisée par le modèle de frottement."
    )
    mawp_pa: float | None = Field(
        default=None, ge=0, description="Pression maximale admissible en service (Pa)."
    )
    material_family: str | None = Field(
        default=None, max_length=120, description="Famille, par exemple acier au carbone."
    )
    specification: str | None = Field(
        default=None, max_length=120, description="Spécification, par exemple API 5L."
    )
    grade: str | None = Field(default=None, max_length=60, description="Grade, par exemple X52.")
    smys_pa: float | None = Field(
        default=None, ge=0, description="Limite d'élasticité minimale spécifiée (Pa)."
    )
    ultimate_strength_pa: float | None = Field(
        default=None, ge=0, description="Résistance ultime à la traction (Pa)."
    )
    density_kg_m3: float | None = Field(default=None, ge=0)
    outer_diameter_m: float | None = Field(default=None, gt=0)
    wall_thickness_m: float | None = Field(default=None, gt=0)
    corrosion_allowance_m: float | None = Field(default=None, ge=0)
    design_temperature_k: float | None = Field(default=None, gt=0)
    standard_reference: str | None = Field(
        default=None,
        max_length=200,
        description="Référence normative documentaire ; n'établit aucune conformité.",
    )
    data_source: str | None = Field(default=None, max_length=10_000)


class AccessoryInput(BaseModel):
    """Fiche d'un accessoire de ligne du catalogue technique.

    ``k_coefficient`` est la seule grandeur consommée par le calcul hydraulique.
    """

    accessory_type: AccessoryTypeLiteral = Field(default="elbow")
    k_coefficient: float | None = Field(
        default=None, ge=0, description="Coefficient de perte singulière."
    )
    nominal_diameter_m: float | None = Field(default=None, gt=0)
    equivalent_length_m: float | None = Field(
        default=None, ge=0, description="Longueur équivalente, si la source l'exprime ainsi."
    )
    manufacturer: str | None = Field(default=None, max_length=200)
    data_source: str | None = Field(default=None, max_length=10_000)


__all__ = [
    "AccessoryInput",
    "AccessoryTypeLiteral",
    "ArrangementLiteral",
    "EdgeGeometryInput",
    "EquipmentStatusLiteral",
    "FailPositionLiteral",
    "FluidCategoryLiteral",
    "FluidInput",
    "FrictionModelLiteral",
    "InjectionNodePayloadInput",
    "InterpolationLiteral",
    "MaterialInput",
    "ObjectiveLiteral",
    "OfftakeNodePayloadInput",
    "PropertyPointInput",
    "PropertyQualityLiteral",
    "PropertySourceLiteral",
    "PropertyTableInput",
    "PumpAssetInput",
    "PumpCurveInput",
    "PumpModelInput",
    "PumpOverrideInput",
    "ScenarioPayloadInput",
    "SegmentOverrideInput",
    "SolverOptionsInput",
    "StationConfigurationInput",
    "StationOverrideInput",
    "TankNodePayloadInput",
    "TerminalNodePayloadInput",
    "ValveAssetInput",
    "ValveInput",
    "ValveTypeLiteral",
    "payload_to_dict",
]
