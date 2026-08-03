"""Cas analytiques rapides du plan de validation D10."""

from __future__ import annotations

import math

from hydro_domain import (
    CanonicalInput,
    ElevationProfile,
    Fluid,
    Pipeline,
    PipeSegment,
    PumpCurve,
    PumpInstance,
    PumpModel,
    Scenario,
    StrappingTable,
    Tank,
    TankLevels,
    build_parallel_station,
    build_series_station,
    fit_quadratic_head,
)
from hydro_shared.versioning import ENGINE_VERSION
from hydro_tanks import (
    TankTransferEngine,
    TransferBalanceInput,
    TransferRequest,
    VolumeMeasurement,
    compute_transfer_balance,
    constant_operating_point,
)
from hydro_validation.external_cases import EXTERNAL_CASES
from hydro_validation.models import ValidationCase, ValidationObservation
from hydro_validation.mvp_cases import MVP_CASES
from hydroliquid import (
    G,
    LongDistanceLiquidEngine,
    friction_colebrook_white,
    friction_head_loss_m,
    minor_head_loss_m,
    reynolds,
)

RELATIVE_PRESSURE_TOLERANCE = 2.0e-3
RELATIVE_FRICTION_TOLERANCE = 1.0e-3
RELATIVE_VOLUME_TOLERANCE = 1.0e-3


def _observation(
    name: str,
    actual: float,
    expected: float,
    *,
    unit: str = "",
    absolute: float = 0.0,
    relative: float = 0.0,
    detail: str | None = None,
) -> ValidationObservation:
    return ValidationObservation(
        name=name,
        actual=actual,
        expected=expected,
        unit=unit,
        absolute_tolerance=absolute,
        relative_tolerance=relative,
        detail=detail,
    )


def _liquid_001() -> tuple[ValidationObservation, ...]:
    density = 900.0
    dynamic_viscosity = 0.09
    kinematic_viscosity = dynamic_viscosity / density
    flow = 1.0e-5
    diameter = 0.05
    length = 100.0
    area = math.pi * diameter**2 / 4.0
    velocity = flow / area
    actual_reynolds = reynolds(velocity, diameter, kinematic_viscosity)
    expected_reynolds = velocity * diameter / kinematic_viscosity
    head_loss = friction_head_loss_m(
        flow,
        length,
        diameter,
        0.0,
        kinematic_viscosity,
    )
    actual_pressure_loss = density * G * head_loss
    expected_pressure_loss = 128.0 * dynamic_viscosity * length * flow / (math.pi * diameter**4)
    return (
        _observation(
            "Nombre de Reynolds",
            actual_reynolds,
            expected_reynolds,
            relative=RELATIVE_FRICTION_TOLERANCE,
        ),
        _observation(
            "Perte de pression",
            actual_pressure_loss,
            expected_pressure_loss,
            unit="Pa",
            relative=RELATIVE_PRESSURE_TOLERANCE,
        ),
    )


def _liquid_002() -> tuple[ValidationObservation, ...]:
    re = 1.0e6
    relative_roughness = 2.0e-4
    factor = friction_colebrook_white(re, relative_roughness)
    residual = 1.0 / math.sqrt(factor) + 2.0 * math.log10(
        relative_roughness / 3.7 + 2.51 / (re * math.sqrt(factor))
    )
    return (
        _observation(
            "Résidu de Colebrook-White",
            residual,
            0.0,
            absolute=1.0e-10,
        ),
    )


def _liquid_003() -> tuple[ValidationObservation, ...]:
    flow = 0.12
    viscosity = 6.0e-6
    first = friction_head_loss_m(flow, 12_000.0, 0.45, 4.5e-5, viscosity)
    second = friction_head_loss_m(flow, 8_000.0, 0.35, 4.5e-5, viscosity)
    combined = first + second
    independent_sum = 0.0
    for length, diameter in ((12_000.0, 0.45), (8_000.0, 0.35)):
        area = math.pi * diameter**2 / 4.0
        velocity = flow / area
        reynolds_number = velocity * diameter / viscosity
        friction_factor = friction_colebrook_white(
            reynolds_number,
            4.5e-5 / diameter,
        )
        independent_sum += friction_factor * length / diameter * velocity**2 / (2.0 * G)
    return (
        _observation(
            "Somme des pertes de deux tronçons",
            combined,
            independent_sum,
            unit="m",
            relative=RELATIVE_PRESSURE_TOLERANCE,
        ),
    )


def _liquid_005() -> tuple[ValidationObservation, ...]:
    density = 850.0
    elevation_change = 120.0
    inlet_pressure = 3.0e6
    segment = PipeSegment(
        id="T1",
        sequence=1,
        length_m=1_000.0,
        inner_diameter_m=0.5,
        roughness_m=0.0,
    )
    pipeline = Pipeline(
        id="PL-ALT",
        name="Conduite altimétrique",
        segments=(segment,),
        profile=ElevationProfile.from_pairs([(0.0, 100.0), (1_000.0, 100.0 + elevation_change)]),
    )
    fluid = Fluid(
        id="F-ALT",
        name="Liquide de référence",
        density_kg_m3=density,
        kinematic_viscosity_m2_s=1.0e-5,
        vapor_pressure_pa=1_000.0,
    )
    scenario = Scenario(
        id="SC-ALT",
        name="Bernoulli statique",
        imposed_flow_m3_s=0.0,
        inlet_pressure_pa=inlet_pressure,
    )
    result = LongDistanceLiquidEngine().simulate(
        CanonicalInput(
            pipeline=pipeline,
            fluid=fluid,
            scenario=scenario,
            engine="long_distance_liquid",
            engine_version=ENGINE_VERSION,
        )
    )
    actual_outlet = result.profile[-1].pressure_pa
    expected_outlet = inlet_pressure - density * G * elevation_change
    return (
        _observation(
            "Pression aval par Bernoulli",
            actual_outlet,
            expected_outlet,
            unit="Pa absolus",
            relative=RELATIVE_PRESSURE_TOLERANCE,
        ),
    )


def _liquid_006() -> tuple[ValidationObservation, ...]:
    flow = 0.2
    diameter = 0.5
    total_k = 7.5
    area = math.pi * diameter**2 / 4.0
    velocity = flow / area
    expected = total_k * velocity**2 / (2.0 * G)
    actual = minor_head_loss_m(flow, diameter, total_k)
    return (
        _observation(
            "Perte singulière",
            actual,
            expected,
            unit="m",
            relative=RELATIVE_PRESSURE_TOLERANCE,
        ),
    )


def _pump_curve() -> PumpCurve:
    return PumpCurve(
        [0.0, 0.1, 0.2, 0.3],
        [120.0, 110.0, 80.0, 30.0],
        efficiencies=[0.60, 0.75, 0.80, 0.65],
        npshr_m=[2.0, 2.5, 3.5, 5.0],
    )


def _pump_002() -> tuple[ValidationObservation, ...]:
    flows = [0.0, 0.1, 0.2, 0.3]
    expected_a = 120.0
    expected_b = 1_000.0
    heads = [expected_a - expected_b * flow**2 for flow in flows]
    fit = fit_quadratic_head(flows, heads)
    return (
        _observation("Coefficient a", fit.a, expected_a, unit="m", relative=1.0e-12),
        _observation("Coefficient b", fit.b, expected_b, unit="s²/m⁵", relative=1.0e-12),
        _observation("Erreur RMS", fit.rms_error_m, 0.0, unit="m", absolute=1.0e-12),
    )


def _pump_003() -> tuple[ValidationObservation, ...]:
    model = PumpModel(id="M1", name="Pompe de référence", curve=_pump_curve())
    first = PumpInstance(id="P1", model=model)
    second = PumpInstance(id="P2", model=model)
    station = build_series_station("S1", "Station série", 0.0, 0.0, (first, second))
    flow = 0.15
    return (
        _observation(
            "Hauteur de deux pompes en série",
            station.combined_head(flow),
            2.0 * model.curve.head(flow),
            unit="m",
            relative=1.0e-12,
        ),
    )


def _pump_004() -> tuple[ValidationObservation, ...]:
    model = PumpModel(id="M1", name="Pompe de référence", curve=_pump_curve())
    station = build_parallel_station(
        "S1",
        "Station parallèle",
        0.0,
        0.0,
        (
            PumpInstance(id="P1", model=model),
            PumpInstance(id="P2", model=model),
        ),
    )
    total_flow = 0.2
    return (
        _observation(
            "Hauteur de deux pompes identiques en parallèle",
            station.combined_head(total_flow),
            model.curve.head(total_flow / 2.0),
            unit="m",
            relative=1.0e-8,
        ),
    )


def _pump_006() -> tuple[ValidationObservation, ...]:
    curve = _pump_curve()
    reference_flow = 0.12
    speed_ratio = 0.8
    reference_head = curve.head(reference_flow)
    scaled_head = curve.head(reference_flow * speed_ratio, speed_ratio=speed_ratio)
    return (
        _observation(
            "Loi d'affinité sur la hauteur",
            scaled_head,
            reference_head * speed_ratio**2,
            unit="m",
            relative=1.0e-12,
        ),
    )


def _pump_007() -> tuple[ValidationObservation, ...]:
    model = PumpModel(id="M1", name="Pompe NPSH", curve=_pump_curve())
    station = build_series_station(
        "S1",
        "Station NPSH",
        0.0,
        0.0,
        (PumpInstance(id="P1", model=model),),
    )
    suction_pressure = 300_000.0
    vapor_pressure = 10_000.0
    density = 900.0
    velocity_head = 0.25
    expected = (suction_pressure - vapor_pressure) / (density * G) + velocity_head
    return (
        _observation(
            "NPSH disponible",
            station.npsh_available_m(
                suction_pressure,
                vapor_pressure,
                density,
                velocity_head,
            ),
            expected,
            unit="m",
            relative=1.0e-12,
        ),
    )


def _tank(identifier: str, *, level_m: float, fluid_id: str | None) -> Tank:
    strapping = StrappingTable.from_vertical_cylinder(10.0, 12.0, points=13)
    return Tank(
        id=identifier,
        name=f"Bac {identifier}",
        strapping=strapping,
        levels=TankLevels(
            minimum_m=0.5,
            low_m=1.0,
            normal_m=6.0,
            high_m=10.0,
            high_high_m=11.0,
        ),
        current_level_m=level_m,
        fluid_id=fluid_id,
    )


def _tank_001() -> tuple[ValidationObservation, ...]:
    diameter = 10.0
    level = 4.0
    table = StrappingTable.from_vertical_cylinder(diameter, 12.0)
    expected = math.pi * diameter**2 / 4.0 * level
    return (
        _observation(
            "Volume d'un bac cylindrique",
            table.volume_at(level),
            expected,
            unit="m³",
            relative=RELATIVE_VOLUME_TOLERANCE,
        ),
    )


def _tank_003() -> tuple[ValidationObservation, ...]:
    table = StrappingTable.from_pairs([(0.0, 0.0), (2.0, 100.0), (5.0, 400.0), (8.0, 1_000.0)])
    level = 3.5
    volume = table.volume_at(level)
    return (
        _observation(
            "Inversion d'un barémage non linéaire",
            table.height_at(volume),
            level,
            unit="m",
            absolute=1.0e-12,
        ),
    )


def _tank_004() -> tuple[ValidationObservation, ...]:
    source = _tank("SOURCE", level_m=8.0, fluid_id="F1")
    destination = _tank("DEST", level_m=2.0, fluid_id=None)
    request = TransferRequest(
        source=source,
        destination=destination,
        fluid_id="F1",
        requested_flow_m3_s=0.1,
        target_volume_m3=100.0,
        time_step_s=73.0,
    )
    result = TankTransferEngine().simulate(
        request,
        constant_operating_point(0.1, absorbed_power_w=20_000.0),
    )
    return (
        _observation(
            "Durée de transfert",
            result.duration_s,
            1_000.0,
            unit="s",
            relative=RELATIVE_VOLUME_TOLERANCE,
        ),
        _observation(
            "Volume soutiré",
            result.withdrawn_volume_m3,
            100.0,
            unit="m³",
            relative=RELATIVE_VOLUME_TOLERANCE,
        ),
        _observation(
            "Résidu volumique",
            result.balance_residual_m3,
            0.0,
            unit="m³",
            absolute=1.0e-8,
        ),
    )


def _tank_008() -> tuple[ValidationObservation, ...]:
    data = TransferBalanceInput(
        source_opening=VolumeMeasurement(1_000.0, 0.5),
        source_closing=VolumeMeasurement(600.0, 0.5),
        destination_opening=VolumeMeasurement(200.0, 0.4),
        destination_closing=VolumeMeasurement(599.0, 0.4),
        metered_volume=VolumeMeasurement(399.5, 0.2),
        accounted_losses=VolumeMeasurement(0.5, 0.1),
        coverage_factor=2.0,
    )
    result = compute_transfer_balance(data)
    expected_uncertainty = math.sqrt(0.5**2 + 0.5**2 + 0.4**2 + 0.4**2 + 0.1**2)
    return (
        _observation(
            "Écart système",
            result.system_imbalance_m3,
            0.5,
            unit="m³",
            absolute=1.0e-12,
        ),
        _observation(
            "Incertitude-type combinée",
            result.combined_standard_uncertainty_m3,
            expected_uncertainty,
            unit="m³",
            relative=1.0e-12,
        ),
        _observation(
            "Incertitude élargie",
            result.expanded_uncertainty_m3,
            2.0 * expected_uncertainty,
            unit="m³",
            relative=1.0e-12,
        ),
    )


DETAILED_CASES: tuple[ValidationCase, ...] = (
    ValidationCase(
        "VAL-LIQ-001",
        "Conduite horizontale laminaire",
        "liquide",
        "Hagen-Poiseuille et lambda = 64/Re",
        _liquid_001,
    ),
    ValidationCase(
        "VAL-LIQ-002",
        "Conduite turbulente unique",
        "liquide",
        "Équation implicite de Colebrook-White",
        _liquid_002,
    ),
    ValidationCase(
        "VAL-LIQ-003",
        "Deux diamètres en série",
        "liquide",
        "Additivité de Darcy-Weisbach",
        _liquid_003,
    ),
    ValidationCase(
        "VAL-LIQ-005",
        "Différence d'altitude sans pompe",
        "liquide",
        "Équation de Bernoulli statique",
        _liquid_005,
    ),
    ValidationCase(
        "VAL-LIQ-006",
        "Pertes singulières",
        "liquide",
        "Somme K fois v²/(2g)",
        _liquid_006,
    ),
    ValidationCase(
        "VAL-PMP-002",
        "Ajustement quadratique de pompe",
        "pompe",
        "Régression exacte H = a - bQ²",
        _pump_002,
    ),
    ValidationCase(
        "VAL-PMP-003",
        "Deux pompes identiques en série",
        "pompe",
        "Addition des hauteurs au même débit",
        _pump_003,
    ),
    ValidationCase(
        "VAL-PMP-004",
        "Deux pompes identiques en parallèle",
        "pompe",
        "Addition des débits à hauteur commune",
        _pump_004,
    ),
    ValidationCase(
        "VAL-PMP-006",
        "Variation de vitesse",
        "pompe",
        "Lois d'affinité des pompes centrifuges",
        _pump_006,
    ),
    ValidationCase(
        "VAL-PMP-007",
        "NPSH disponible",
        "pompe",
        "NPSHa = (p aspiration - p vapeur)/(rho g) + v²/(2g)",
        _pump_007,
    ),
    ValidationCase(
        "VAL-TNK-001",
        "Bac cylindrique",
        "réservoir",
        "Volume V = A h",
        _tank_001,
    ),
    ValidationCase(
        "VAL-TNK-003",
        "Barémage non linéaire",
        "réservoir",
        "Inversion exacte h(V)",
        _tank_003,
    ),
    ValidationCase(
        "VAL-TNK-004",
        "Transfert à niveaux variables",
        "transfert",
        "Bilan dynamique et événement terminal interpolé",
        _tank_004,
    ),
    ValidationCase(
        "VAL-TNK-008",
        "Bilan matière avec incertitudes",
        "transfert",
        "Propagation quadratique d'incertitudes indépendantes",
        _tank_008,
    ),
)

CASES: tuple[ValidationCase, ...] = (*MVP_CASES, *DETAILED_CASES, *EXTERNAL_CASES)


def validation_cases() -> tuple[ValidationCase, ...]:
    """Retourne le registre ordonné et immuable des cas rapides."""

    return CASES


__all__ = ["CASES", "DETAILED_CASES", "validation_cases"]
