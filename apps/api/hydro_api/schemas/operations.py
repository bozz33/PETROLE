"""Contrats des réservoirs, transferts, comparaisons et optimisations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrappingPointInput(BaseModel):
    height_m: float = Field(ge=0)
    volume_m3: float = Field(ge=0)


class TankLevelsInput(BaseModel):
    minimum_m: float = Field(ge=0)
    low_m: float | None = Field(default=None, ge=0)
    normal_m: float | None = Field(default=None, ge=0)
    high_m: float | None = Field(default=None, ge=0)
    high_high_m: float = Field(gt=0)


class TankCreate(BaseModel):
    organization_id: uuid.UUID
    site_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=50)
    tank_type: Literal[
        "vertical_fixed_roof",
        "floating_roof",
        "horizontal",
        "sphere",
        "custom",
    ] = "vertical_fixed_roof"
    elevation_m: float = 0.0
    current_level_m: float = Field(ge=0)
    fluid_id: str | None = Field(default=None, max_length=100)
    compatible_fluid_ids: list[str] = Field(default_factory=list, max_length=100)
    status: Literal["available", "unavailable", "maintenance", "bypassed"] = "available"
    dead_volume_m3: float = Field(default=0.0, ge=0)
    levels: TankLevelsInput
    strapping: list[StrappingPointInput] = Field(min_length=2, max_length=20_000)

    @model_validator(mode="after")
    def validate_identifiers(self) -> TankCreate:
        self.code = self.code.strip().upper()
        if self.fluid_id is not None:
            self.fluid_id = self.fluid_id.strip()
        self.compatible_fluid_ids = sorted(
            {identifier.strip() for identifier in self.compatible_fluid_ids if identifier.strip()}
        )
        return self


class TankUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    current_level_m: float | None = Field(default=None, ge=0)
    fluid_id: str | None = Field(default=None, max_length=100)
    compatible_fluid_ids: list[str] | None = Field(default=None, max_length=100)
    status: Literal["available", "unavailable", "maintenance", "bypassed"] | None = None


class TankRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    site_id: uuid.UUID | None
    name: str
    code: str
    tank_type: str
    elevation_m: float
    current_level_m: float
    current_volume_m3: float
    nominal_capacity_m3: float
    available_capacity_m3: float
    pumpable_volume_m3: float
    fluid_id: str | None
    compatible_fluid_ids: list[str]
    status: str
    dead_volume_m3: float
    levels: dict[str, float | None]
    strapping: list[dict[str, float]]
    created_at: datetime
    updated_at: datetime


class TransferHydraulicContext(BaseModel):
    """Chemin hydraulique et groupe de pompage d'un transfert.

    Le chemin est explicitement désigné : le MVP ne cherche pas de route
    automatique lorsque plusieurs sont possibles, afin que la simulation reste
    reproductible.
    """

    model_version_id: uuid.UUID
    scenario_id: uuid.UUID
    source_node_id: uuid.UUID = Field(description="Nœud raccordant le bac source.")
    destination_node_id: uuid.UUID = Field(description="Nœud raccordant le bac destination.")
    path_edge_ids: list[uuid.UUID] = Field(
        min_length=1,
        max_length=5_000,
        description="Tronçons orientés du chemin, du nœud source au nœud destination.",
    )
    pump_asset_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=500,
        description="Pompes en marche pendant le transfert ; toutes celles du chemin si vide.",
    )
    level_step_m: float = Field(
        default=0.05,
        gt=0,
        description=(
            "Variation de niveau au-delà de laquelle le point de fonctionnement est "
            "recalculé. Évite un calcul hydraulique complet à chaque pas de temps."
        ),
    )
    maximum_evaluations: int = Field(
        default=2_000,
        ge=1,
        le=100_000,
        description="Garde-fou sur le nombre de calculs hydrauliques d'un transfert.",
    )


class TransferCreate(BaseModel):
    """Demande de transfert entre deux bacs.

    Sans ``scenario_id``, le débit demandé est imposé : le module se comporte
    comme une simulation de volumes et de niveaux. Avec ``scenario_id``, le
    débit est déterminé à chaque pas par HydroLiquid à partir des niveaux
    courants, du chemin hydraulique et des pompes retenues.
    """

    source_tank_id: uuid.UUID
    destination_tank_id: uuid.UUID
    fluid_id: str = Field(min_length=1, max_length=100)
    requested_flow_m3_s: float = Field(gt=0)
    hydraulic_context: TransferHydraulicContext | None = Field(
        default=None,
        description=(
            "Chemin hydraulique et groupe de pompage. Absent, le débit demandé est "
            "imposé et le comportement historique est conservé."
        ),
    )
    target_volume_m3: float | None = Field(default=None, gt=0)
    target_destination_level_m: float | None = Field(default=None, gt=0)
    target_duration_s: float | None = Field(default=None, gt=0)
    time_step_s: float = Field(default=60.0, gt=0)
    maximum_duration_s: float = Field(default=31_536_000.0, gt=0)
    maximum_flow_m3_s: float | None = Field(default=None, gt=0)
    loss_fraction: float = Field(default=0.0, ge=0, lt=1)
    discharge_pressure_pa: float | None = Field(default=None, ge=0)
    absorbed_power_w: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def reject_computed_inputs(self) -> TransferCreate:
        """Interdit de saisir ce que HydroLiquid doit calculer.

        Accepter une pression de refoulement ou une puissance absorbée alors que
        le réseau les détermine ferait coexister deux valeurs contradictoires
        dans le même résultat.
        """

        if self.hydraulic_context is None:
            return self
        if self.discharge_pressure_pa is not None or self.absorbed_power_w is not None:
            raise ValueError(
                "En couplage hydraulique, la pression de refoulement et la puissance "
                "absorbée sont calculées par le moteur : elles ne peuvent pas être fournies."
            )
        return self

    @model_validator(mode="after")
    def validate_objective(self) -> TransferCreate:
        objectives = (
            self.target_volume_m3,
            self.target_destination_level_m,
            self.target_duration_s,
        )
        if sum(value is not None for value in objectives) != 1:
            raise ValueError("Un seul objectif de transfert doit être renseigné.")
        return self


class TransferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    source_tank_id: uuid.UUID
    destination_tank_id: uuid.UUID
    status: str
    input_hash: str
    input_payload: dict[str, Any]
    result_payload: dict[str, Any]
    balance_payload: dict[str, Any] | None
    created_at: datetime
    started_at: datetime
    finished_at: datetime


class VolumeMeasurementInput(BaseModel):
    value_m3: float
    standard_uncertainty_m3: float = Field(default=0.0, ge=0)
    label: str | None = Field(default=None, max_length=200)


class TransferBalanceCreate(BaseModel):
    source_opening: VolumeMeasurementInput
    source_closing: VolumeMeasurementInput
    destination_opening: VolumeMeasurementInput
    destination_closing: VolumeMeasurementInput
    metered_volume: VolumeMeasurementInput
    accounted_losses: VolumeMeasurementInput = VolumeMeasurementInput(
        value_m3=0.0,
        label="Pertes comptabilisées",
    )
    coverage_factor: float = Field(default=2.0, gt=0)
    absolute_tolerance_m3: float = Field(default=0.0, ge=0)
    relative_tolerance: float = Field(default=0.001, ge=0)


class TransferBalanceRead(BaseModel):
    source_withdrawal_m3: float
    destination_receipt_m3: float
    metered_volume_m3: float
    system_imbalance_m3: float
    meter_source_difference_m3: float
    meter_destination_difference_m3: float
    combined_standard_uncertainty_m3: float
    expanded_uncertainty_m3: float
    acceptance_limit_m3: float
    relative_imbalance: float | None
    within_tolerance: bool


class ComparisonCreate(BaseModel):
    calculation_ids: list[uuid.UUID] = Field(min_length=2, max_length=20)

    @model_validator(mode="after")
    def validate_unique_calculations(self) -> ComparisonCreate:
        if len(set(self.calculation_ids)) != len(self.calculation_ids):
            raise ValueError("Chaque calcul ne peut apparaître qu'une fois.")
        return self


class ComparisonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    calculation_ids: list[str]
    content_hash: str
    result_payload: dict[str, Any]
    created_at: datetime


class OptimizationConstraintsInput(BaseModel):
    minimum_flow_m3_s: float | None = Field(default=None, ge=0)
    maximum_flow_m3_s: float | None = Field(default=None, ge=0)
    minimum_pressure_pa: float | None = Field(default=None, ge=0)
    maximum_pressure_pa: float | None = Field(default=None, ge=0)
    maximum_active_pumps: int | None = Field(default=None, ge=0)
    required_pump_ids: list[str] = Field(default_factory=list)
    forbidden_pump_ids: list[str] = Field(default_factory=list)
    allow_violations: bool = False


class OptimizationCreate(BaseModel):
    objective: Literal[
        "min_energy",
        "min_cost",
        "min_pump_count",
        "min_starts",
        "max_flow",
    ] = "min_energy"
    pump_ids: list[str] | None = None
    speed_options: list[float] = Field(default_factory=lambda: [1.0], min_length=1, max_length=10)
    reference_duration_s: float = Field(default=3_600.0, gt=0)
    energy_price_per_kwh: float | None = Field(default=None, ge=0)
    constraints: OptimizationConstraintsInput = Field(default_factory=OptimizationConstraintsInput)
    maximum_configurations: int = Field(default=100_000, ge=1, le=1_000_000)
    maximum_evaluations: int | None = Field(default=None, ge=1, le=1_000_000)


class OptimizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    scenario_id: uuid.UUID
    status: str
    input_hash: str
    input_payload: dict[str, Any]
    result_payload: dict[str, Any]
    engine_version: str
    created_at: datetime
    started_at: datetime
    finished_at: datetime


__all__ = [
    "ComparisonCreate",
    "ComparisonRead",
    "OptimizationCreate",
    "OptimizationRead",
    "StrappingPointInput",
    "TankCreate",
    "TankLevelsInput",
    "TankRead",
    "TankUpdate",
    "TransferBalanceCreate",
    "TransferBalanceRead",
    "TransferCreate",
    "TransferRead",
    "VolumeMeasurementInput",
]
