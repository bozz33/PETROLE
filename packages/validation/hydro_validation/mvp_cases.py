"""Cas de réception scientifique V-001 à V-020 du MVP.

Chaque cas traduit une exigence de la documentation MVP v2.0 en observations numériques
reproductibles. Les valeurs attendues proviennent soit d'une relation analytique, soit d'une
propriété de conservation, soit d'un événement physique explicitement attendu. Les cas
complètent les familles détaillées ``VAL-LIQ-*``, ``VAL-PMP-*`` et ``VAL-TNK-*`` du plan D10.
"""

from __future__ import annotations

import time

from hydro_domain import (
    CanonicalInput,
    ElevationProfile,
    EquipmentStatus,
    Fluid,
    Pipeline,
    PipeSegment,
    PumpCurve,
    PumpInstance,
    PumpModel,
    PumpOverride,
    PumpRole,
    Scenario,
    SolverOptions,
    StationOverride,
    StrappingTable,
    Tank,
    TankLevels,
    TransferStopReason,
    build_parallel_station,
    build_series_station,
)
from hydro_shared.codes import SimulationStatus, ViolationCode
from hydro_shared.diagnostics import SolverDiagnostics
from hydro_shared.errors import NotConvergedError
from hydro_shared.versioning import ENGINE_VERSION
from hydro_tanks import (
    TankTransferEngine,
    TransferRequest,
    constant_operating_point,
)
from hydro_validation.models import ValidationCase, ValidationObservation
from hydroliquid import (
    G,
    LongDistanceLiquidEngine,
    brent,
    friction_colebrook_white,
    friction_factor,
    friction_haaland,
    friction_head_loss_m,
    friction_swamee_jain,
    velocity_m_s,
)

PLAN_VERSION = "MVP-2.0"
REFERENCE_DENSITY_KG_M3 = 850.0
REFERENCE_KINEMATIC_VISCOSITY_M2_S = 6.0e-6
REFERENCE_VAPOR_PRESSURE_PA = 2_000.0
PRESSURE_TOLERANCE_REL = 2.0e-3
FLOW_TOLERANCE_REL = 1.0e-3
FRICTION_TOLERANCE_REL = 1.0e-3
VOLUME_TOLERANCE_REL = 1.0e-3


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
        actual=float(actual),
        expected=float(expected),
        unit=unit,
        absolute_tolerance=absolute,
        relative_tolerance=relative,
        detail=detail,
    )


def _fluid() -> Fluid:
    return Fluid(
        id="F-MVP",
        name="Liquide de référence MVP",
        density_kg_m3=REFERENCE_DENSITY_KG_M3,
        kinematic_viscosity_m2_s=REFERENCE_KINEMATIC_VISCOSITY_M2_S,
        vapor_pressure_pa=REFERENCE_VAPOR_PRESSURE_PA,
        data_source="Jeu de réception scientifique MVP v2.0",
    )


def _pump_model(*, identifier: str = "PMP-MVP", npshr_m: float = 4.0) -> PumpModel:
    curve = PumpCurve(
        [0.0, 0.1, 0.2, 0.35, 0.5, 0.7, 0.9],
        [240.0, 236.0, 229.0, 211.0, 188.0, 150.0, 100.0],
        efficiencies=[0.55, 0.66, 0.76, 0.83, 0.82, 0.74, 0.62],
        npshr_m=[npshr_m] * 7,
        reference_speed_rpm=3_000.0,
    )
    return PumpModel(
        id=identifier,
        name=identifier,
        curve=curve,
        motor_rated_power_w=5.0e6,
        npsh_margin_m=1.0,
        data_source="Courbe de réception scientifique MVP v2.0",
    )


def _pump(
    identifier: str,
    *,
    model: PumpModel | None = None,
    role: PumpRole = PumpRole.MAIN,
    running: bool | None = None,
) -> PumpInstance:
    return PumpInstance(
        id=identifier,
        model=model or _pump_model(),
        role=role,
        running=role.starts_by_default if running is None else running,
    )


def _segment(
    identifier: str,
    sequence: int,
    start_m: float,
    length_m: float,
    *,
    diameter_m: float = 0.6,
    maop_pa: float = 12.0e6,
) -> PipeSegment:
    return PipeSegment(
        id=identifier,
        sequence=sequence,
        start_chainage_m=start_m,
        length_m=length_m,
        inner_diameter_m=diameter_m,
        roughness_m=4.5e-5,
        maop_pa=maop_pa,
    )


def _pipeline(
    *,
    length_m: float = 10_000.0,
    diameter_m: float = 0.6,
    profile: ElevationProfile | None = None,
    stations=(),
    maop_pa: float = 12.0e6,
) -> Pipeline:
    return Pipeline(
        id="PL-MVP",
        name="Pipeline de réception MVP",
        segments=(_segment("T1", 1, 0.0, length_m, diameter_m=diameter_m, maop_pa=maop_pa),),
        profile=profile or ElevationProfile.from_pairs([(0.0, 100.0), (length_m, 100.0)]),
        stations=tuple(stations),
    )


def _scenario(
    identifier: str,
    *,
    imposed_flow_m3_s: float | None = None,
    inlet_pressure_pa: float | None = None,
    outlet_pressure_pa: float | None = None,
    pump_overrides: tuple[PumpOverride, ...] = (),
    station_overrides: tuple[StationOverride, ...] = (),
    max_flow_m3_s: float | None = 2.0,
    profile_step_m: float = 1_000.0,
) -> Scenario:
    return Scenario(
        id=identifier,
        name=identifier,
        imposed_flow_m3_s=imposed_flow_m3_s,
        inlet_pressure_pa=inlet_pressure_pa,
        outlet_pressure_pa=outlet_pressure_pa,
        pump_overrides=pump_overrides,
        station_overrides=station_overrides,
        solver=SolverOptions(
            pressure_tolerance_pa=0.1,
            flow_tolerance_m3_s=1.0e-9,
            max_flow_m3_s=max_flow_m3_s,
            profile_step_m=profile_step_m,
            max_velocity_m_s=5.0,
        ),
    )


def _simulate(pipeline: Pipeline, scenario: Scenario, fluid: Fluid | None = None):
    return LongDistanceLiquidEngine().simulate(
        CanonicalInput(
            pipeline=pipeline,
            fluid=fluid or _fluid(),
            scenario=scenario,
            engine="long_distance_liquid",
            engine_version=ENGINE_VERSION,
        )
    )


def _tank(identifier: str, level_m: float, *, fluid_id: str | None) -> Tank:
    table = StrappingTable.from_vertical_cylinder(10.0, 10.0, points=21)
    return Tank(
        id=identifier,
        name=f"Bac {identifier}",
        strapping=table,
        levels=TankLevels(
            minimum_m=1.0,
            low_m=1.5,
            normal_m=5.0,
            high_m=7.0,
            high_high_m=9.0,
        ),
        current_level_m=level_m,
        fluid_id=fluid_id,
        compatible_fluid_ids=("F-MVP",),
    )


def _v001() -> tuple[ValidationObservation, ...]:
    flow = 0.12
    fluid = _fluid()
    pipe = _pipeline(length_m=12_000.0)
    inlet_pressure = 5.0e6
    result = _simulate(
        pipe,
        _scenario("V-001", imposed_flow_m3_s=flow, inlet_pressure_pa=inlet_pressure),
        fluid,
    )
    expected_loss = friction_head_loss_m(
        flow,
        pipe.total_length_m,
        pipe.segments[0].inner_diameter_m,
        pipe.segments[0].roughness_m,
        REFERENCE_KINEMATIC_VISCOSITY_M2_S,
    )
    expected_outlet = inlet_pressure - REFERENCE_DENSITY_KG_M3 * G * expected_loss
    return (
        _observation(
            "Perte de charge horizontale",
            result.total_head_loss_m,
            expected_loss,
            unit="m",
            relative=PRESSURE_TOLERANCE_REL,
        ),
        _observation(
            "Pression de sortie",
            result.profile[-1].pressure_pa,
            expected_outlet,
            unit="Pa absolus",
            relative=PRESSURE_TOLERANCE_REL,
        ),
    )


def _v002() -> tuple[ValidationObservation, ...]:
    fluid = _fluid()
    inlet_pressure = 3.0e6
    observations: list[ValidationObservation] = []
    for label, end_elevation in (("montée", 220.0), ("descente", -20.0)):
        profile = ElevationProfile.from_pairs([(0.0, 100.0), (1_000.0, end_elevation)])
        result = _simulate(
            _pipeline(length_m=1_000.0, profile=profile),
            _scenario(
                f"V-002-{label}",
                imposed_flow_m3_s=0.0,
                inlet_pressure_pa=inlet_pressure,
            ),
            fluid,
        )
        expected = inlet_pressure - REFERENCE_DENSITY_KG_M3 * G * (end_elevation - 100.0)
        observations.append(
            _observation(
                f"Pression aval en {label}",
                result.profile[-1].pressure_pa,
                expected,
                unit="Pa absolus",
                relative=PRESSURE_TOLERANCE_REL,
            )
        )
    return tuple(observations)


def _v003() -> tuple[ValidationObservation, ...]:
    re = 1_200.0
    return (
        _observation(
            "Facteur de frottement laminaire",
            friction_factor(re, 1.0e-4),
            64.0 / re,
            relative=FRICTION_TOLERANCE_REL,
        ),
    )


def _v004() -> tuple[ValidationObservation, ...]:
    re = 1.0e6
    relative_roughness = 2.0e-4
    reference = friction_colebrook_white(re, relative_roughness)
    haaland_error = abs(friction_haaland(re, relative_roughness) - reference) / reference
    swamee_error = abs(friction_swamee_jain(re, relative_roughness) - reference) / reference
    return (
        _observation("Écart relatif Haaland/Colebrook", haaland_error, 0.0, absolute=0.02),
        _observation(
            "Écart relatif Swamee-Jain/Colebrook",
            swamee_error,
            0.0,
            absolute=0.03,
        ),
    )


def _v005() -> tuple[ValidationObservation, ...]:
    flow = 0.18
    result = _simulate(
        _pipeline(length_m=25_000.0),
        _scenario("V-005", imposed_flow_m3_s=flow, inlet_pressure_pa=6.0e6),
    )
    return (
        _observation("Débit imposé conservé", result.flow_m3_s, flow, unit="m³/s", absolute=1e-12),
        _observation(
            "Débit constant sur le profil",
            max(abs(point.flow_m3_s - flow) for point in result.profile),
            0.0,
            unit="m³/s",
            absolute=1e-12,
        ),
    )


def _v006() -> tuple[ValidationObservation, ...]:
    fluid = _fluid()
    pipe = _pipeline(length_m=18_000.0)
    expected_flow = 0.14
    expected_loss = friction_head_loss_m(
        expected_flow,
        pipe.total_length_m,
        pipe.segments[0].inner_diameter_m,
        pipe.segments[0].roughness_m,
        REFERENCE_KINEMATIC_VISCOSITY_M2_S,
    )
    inlet_pressure = 6.0e6
    outlet_pressure = inlet_pressure - REFERENCE_DENSITY_KG_M3 * G * expected_loss
    result = _simulate(
        pipe,
        _scenario(
            "V-006",
            inlet_pressure_pa=inlet_pressure,
            outlet_pressure_pa=outlet_pressure,
            max_flow_m3_s=1.0,
        ),
        fluid,
    )
    return (
        _observation(
            "Débit résolu entre deux pressions",
            result.flow_m3_s,
            expected_flow,
            unit="m³/s",
            relative=FLOW_TOLERANCE_REL,
        ),
        _observation(
            "Résidu de pression",
            result.diagnostics.residual,
            0.0,
            unit="Pa",
            absolute=0.1,
        ),
    )


def _v007() -> tuple[ValidationObservation, ...]:
    fluid = _fluid()
    flow = 0.2
    model = _pump_model(identifier="PMP-V007")
    station = build_series_station(
        "S-V007", "Station V-007", 0.0, 100.0, (_pump("P-V007", model=model),)
    )
    pipe = _pipeline(length_m=20_000.0, stations=(station,))
    inlet_pressure = 1.0e6
    friction_loss = friction_head_loss_m(
        flow,
        pipe.total_length_m,
        pipe.segments[0].inner_diameter_m,
        pipe.segments[0].roughness_m,
        REFERENCE_KINEMATIC_VISCOSITY_M2_S,
    )
    outlet_pressure = inlet_pressure + REFERENCE_DENSITY_KG_M3 * G * (
        station.combined_head(flow) - friction_loss
    )
    result = _simulate(
        pipe,
        _scenario(
            "V-007",
            inlet_pressure_pa=inlet_pressure,
            outlet_pressure_pa=outlet_pressure,
            max_flow_m3_s=0.9,
        ),
        fluid,
    )
    return (
        _observation(
            "Débit au point pompe-réseau",
            result.flow_m3_s,
            flow,
            unit="m³/s",
            relative=FLOW_TOLERANCE_REL,
        ),
        _observation(
            "Hauteur de la pompe au point d'exploitation",
            result.stations[0].head_m,
            model.curve.head(flow),
            unit="m",
            relative=PRESSURE_TOLERANCE_REL,
        ),
    )


def _v008() -> tuple[ValidationObservation, ...]:
    model = _pump_model(identifier="PMP-V008")
    first = _pump("P1", model=model)
    second = _pump("P2", model=model)
    station = build_series_station("S-V008", "Station série", 0.0, 0.0, (first, second))
    flow = 0.25
    return (
        _observation(
            "Hauteur de deux pompes en série",
            station.combined_head(flow),
            2.0 * model.curve.head(flow),
            unit="m",
            relative=1.0e-12,
        ),
    )


def _v009() -> tuple[ValidationObservation, ...]:
    model = _pump_model(identifier="PMP-V009")
    station = build_parallel_station(
        "S-V009",
        "Station parallèle",
        0.0,
        0.0,
        (_pump("P1", model=model), _pump("P2", model=model)),
    )
    total_flow = 0.4
    distribution = station.flow_distribution(total_flow)
    return (
        _observation(
            "Hauteur commune en parallèle",
            station.combined_head(total_flow),
            model.curve.head(total_flow / 2.0),
            unit="m",
            relative=1.0e-8,
        ),
        _observation(
            "Conservation du débit parallèle",
            sum(distribution.values()),
            total_flow,
            unit="m³/s",
            absolute=1.0e-12,
        ),
    )


def _v010() -> tuple[ValidationObservation, ...]:
    fluid = _fluid()
    model = _pump_model(identifier="PMP-V010")
    flow = 0.35
    stations = tuple(
        build_series_station(
            f"S{index}",
            f"Station {index}",
            chainage,
            100.0,
            (_pump(f"S{index}-P1", model=model),),
        )
        for index, chainage in enumerate((0.0, 50_000.0, 100_000.0), start=1)
    )
    pipe = _pipeline(length_m=150_000.0, stations=stations)
    result = _simulate(
        pipe,
        _scenario(
            "V-010",
            imposed_flow_m3_s=flow,
            inlet_pressure_pa=1.5e6,
            profile_step_m=5_000.0,
        ),
        fluid,
    )
    expected_differential = REFERENCE_DENSITY_KG_M3 * G * model.curve.head(flow)
    return (
        _observation("Nombre de stations évaluées", len(result.stations), 3.0),
        _observation(
            "Écart maximal des pressions différentielles",
            max(
                abs(station.differential_pressure_pa - expected_differential)
                for station in result.stations
            ),
            0.0,
            unit="Pa",
            absolute=1.0,
        ),
    )


def _v011() -> tuple[ValidationObservation, ...]:
    model = _pump_model(identifier="PMP-V011", npshr_m=20.0)
    station = build_series_station(
        "S-V011",
        "Station NPSH",
        0.0,
        100.0,
        (_pump("P-V011", model=model),),
        suction_line_diameter_m=0.4,
        suction_line_k=2.0,
    )
    result = _simulate(
        _pipeline(length_m=1_000.0, stations=(station,)),
        _scenario("V-011", imposed_flow_m3_s=0.1, inlet_pressure_pa=100_000.0),
    )
    pump = result.stations[0].pumps[0]
    return (
        _observation(
            "Violation de cavitation détectée",
            any(violation.code is ViolationCode.CAVITATION for violation in result.violations),
            1.0,
        ),
        _observation(
            "Marge NPSH défavorable",
            1.0 if pump.npsh_margin_m is not None and pump.npsh_margin_m < 0.0 else 0.0,
            1.0,
        ),
    )


def _v012() -> tuple[ValidationObservation, ...]:
    result = _simulate(
        _pipeline(length_m=1_000.0, maop_pa=2.0e6),
        _scenario("V-012", imposed_flow_m3_s=0.1, inlet_pressure_pa=5.0e6),
    )
    pressure_violations = [
        violation
        for violation in result.violations
        if violation.code is ViolationCode.PRESSURE_HIGH
    ]
    return (
        _observation("Surpression détectée", bool(pressure_violations), 1.0),
        _observation(
            "Marge MAOP négative",
            1.0 if result.segments[0].maop_margin_pa < 0.0 else 0.0,
            1.0,
        ),
    )


def _v013() -> tuple[ValidationObservation, ...]:
    fluid = _fluid()
    model = _pump_model(identifier="PMP-V013")
    station = build_series_station(
        "S-V013",
        "Station avec bypass",
        0.0,
        100.0,
        (_pump("P-V013", model=model),),
        bypass_k=8.0,
    )
    pipe = _pipeline(length_m=5_000.0, stations=(station,))
    flow = 0.2
    normal = _simulate(
        pipe,
        _scenario("V-013-N", imposed_flow_m3_s=flow, inlet_pressure_pa=2.0e6),
        fluid,
    )
    bypass = _simulate(
        pipe,
        _scenario(
            "V-013-B",
            imposed_flow_m3_s=flow,
            inlet_pressure_pa=2.0e6,
            station_overrides=(
                StationOverride(station_id=station.id, status=EquipmentStatus.BYPASSED),
            ),
        ),
        fluid,
    )
    velocity = velocity_m_s(flow, pipe.segments[0].inner_diameter_m)
    expected_difference = (
        REFERENCE_DENSITY_KG_M3
        * G
        * (station.combined_head(flow) + station.bypass_k * velocity**2 / (2.0 * G))
    )
    actual_difference = normal.profile[-1].pressure_pa - bypass.profile[-1].pressure_pa
    return (
        _observation("Station reconnue bypassée", bypass.stations[0].bypassed, 1.0),
        _observation(
            "Effet hydraulique du bypass",
            actual_difference,
            expected_difference,
            unit="Pa",
            relative=PRESSURE_TOLERANCE_REL,
        ),
    )


def _v014() -> tuple[ValidationObservation, ...]:
    model = _pump_model(identifier="PMP-V014")
    station = build_series_station(
        "S-V014",
        "Station avec secours",
        0.0,
        100.0,
        (
            _pump("P-MAIN", model=model, role=PumpRole.MAIN),
            _pump("P-SEC", model=model, role=PumpRole.STANDBY),
        ),
    )
    pipe = _pipeline(length_m=5_000.0, stations=(station,))
    base = _simulate(
        pipe,
        _scenario("V-014-N", imposed_flow_m3_s=0.2, inlet_pressure_pa=2.0e6),
    )
    replacement = _simulate(
        pipe,
        _scenario(
            "V-014-S",
            imposed_flow_m3_s=0.2,
            inlet_pressure_pa=2.0e6,
            pump_overrides=(
                PumpOverride(pump_id="P-MAIN", running=False),
                PumpOverride(pump_id="P-SEC", running=True),
            ),
        ),
    )
    standby = next(pump for pump in replacement.stations[0].pumps if pump.pump_id == "P-SEC")
    return (
        _observation(
            "Une pompe active après substitution", replacement.stations[0].active_pump_count, 1.0
        ),
        _observation("Pompe de secours démarrée", standby.running, 1.0),
        _observation(
            "Pression aval conservée avec pompe identique",
            replacement.profile[-1].pressure_pa,
            base.profile[-1].pressure_pa,
            unit="Pa absolus",
            relative=PRESSURE_TOLERANCE_REL,
        ),
    )


def _v015() -> tuple[ValidationObservation, ...]:
    request = TransferRequest(
        source=_tank("SOURCE-V015", 8.0, fluid_id="F-MVP"),
        destination=_tank("DEST-V015", 2.0, fluid_id=None),
        fluid_id="F-MVP",
        requested_flow_m3_s=0.1,
        target_volume_m3=100.0,
        time_step_s=137.0,
        loss_fraction=0.01,
    )
    result = TankTransferEngine().simulate(request, constant_operating_point(0.1))
    return (
        _observation(
            "Volume soutiré",
            result.withdrawn_volume_m3,
            100.0,
            unit="m³",
            relative=VOLUME_TOLERANCE_REL,
        ),
        _observation(
            "Volume reçu", result.received_volume_m3, 99.0, unit="m³", relative=VOLUME_TOLERANCE_REL
        ),
        _observation("Durée", result.duration_s, 1_000.0, unit="s", relative=VOLUME_TOLERANCE_REL),
        _observation(
            "Résidu de bilan", result.balance_residual_m3, 0.0, unit="m³", absolute=1.0e-8
        ),
    )


def _v016() -> tuple[ValidationObservation, ...]:
    source = _tank("SOURCE-V016", 1.2, fluid_id="F-MVP")
    destination = _tank("DEST-V016", 2.0, fluid_id=None)
    request = TransferRequest(
        source=source,
        destination=destination,
        fluid_id="F-MVP",
        requested_flow_m3_s=0.001,
        target_duration_s=100.0,
        time_step_s=100.0,
    )
    result = TankTransferEngine().simulate(request, constant_operating_point(1.0))
    return (
        _observation(
            "Arrêt au niveau bas source",
            result.stop_reason is TransferStopReason.SOURCE_LOW_LEVEL,
            1.0,
        ),
        _observation(
            "Niveau final source",
            result.source_final.current_level_m,
            source.levels.minimum_m,
            unit="m",
            absolute=1.0e-10,
        ),
    )


def _v017() -> tuple[ValidationObservation, ...]:
    source = _tank("SOURCE-V017", 8.0, fluid_id="F-MVP")
    destination = _tank("DEST-V017", 8.8, fluid_id=None)
    request = TransferRequest(
        source=source,
        destination=destination,
        fluid_id="F-MVP",
        requested_flow_m3_s=0.001,
        target_duration_s=100.0,
        time_step_s=100.0,
    )
    result = TankTransferEngine().simulate(request, constant_operating_point(1.0))
    return (
        _observation(
            "Arrêt au niveau haut destination",
            result.stop_reason is TransferStopReason.DESTINATION_HIGH_LEVEL,
            1.0,
        ),
        _observation(
            "Niveau final destination",
            result.destination_final.current_level_m,
            destination.levels.high_high_m,
            unit="m",
            absolute=1.0e-10,
        ),
    )


def _v018() -> tuple[ValidationObservation, ...]:
    result = _simulate(
        _pipeline(),
        _scenario(
            "V-018",
            inlet_pressure_pa=1.0e5,
            outlet_pressure_pa=5.0e6,
            max_flow_m3_s=0.5,
        ),
    )
    return (
        _observation(
            "Statut absence de solution physique",
            result.status is SimulationStatus.NO_PHYSICAL_SOLUTION,
            1.0,
        ),
        _observation("Profil absent", len(result.profile), 0.0),
    )


def _v019() -> tuple[ValidationObservation, ...]:
    diagnostics = SolverDiagnostics()
    caught = False
    try:
        brent(
            lambda value: value**3 - 2.0,
            0.0,
            2.0,
            tolerance=1.0e-15,
            variable_tolerance=1.0e-15,
            max_iterations=1,
            diagnostics=diagnostics,
            log_iterations=True,
        )
    except NotConvergedError:
        caught = True
    return (
        _observation("Non-convergence explicite", caught, 1.0),
        _observation("Itérations conservées", diagnostics.iterations, 1.0),
        _observation(
            "Résidu final supérieur à la tolérance",
            1.0 if diagnostics.residual > 1.0e-15 else 0.0,
            1.0,
        ),
    )


def _v020() -> tuple[ValidationObservation, ...]:
    fluid = _fluid()
    model = _pump_model(identifier="PMP-V020")
    segments = (
        _segment("T1", 1, 0.0, 150_000.0, diameter_m=0.8),
        _segment("T2", 2, 150_000.0, 150_000.0, diameter_m=0.8),
        _segment("T3", 3, 300_000.0, 160_000.0, diameter_m=0.8),
    )
    profile = ElevationProfile.from_kilometre_pairs(
        [
            (0.0, 100.0),
            (40.0, 180.0),
            (90.0, 125.0),
            (150.0, 210.0),
            (205.0, 140.0),
            (260.0, 230.0),
            (320.0, 155.0),
            (380.0, 205.0),
            (430.0, 130.0),
            (460.0, 115.0),
        ]
    )
    stations = tuple(
        build_series_station(
            f"S{index}",
            f"Station {index}",
            chainage,
            profile.elevation_at(chainage),
            (_pump(f"S{index}-P1", model=model),),
        )
        for index, chainage in enumerate((0.0, 150_000.0, 300_000.0), start=1)
    )
    pipeline = Pipeline(
        id="PL-460",
        name="Benchmark académique de 460 km",
        segments=segments,
        profile=profile,
        stations=stations,
    )
    started = time.perf_counter()
    result = _simulate(
        pipeline,
        _scenario(
            "V-020",
            imposed_flow_m3_s=0.5,
            inlet_pressure_pa=2.0e6,
            profile_step_m=2_000.0,
        ),
        fluid,
    )
    duration = time.perf_counter() - started
    return (
        _observation("Calcul convergé", result.status.has_results, 1.0),
        _observation("Résultat physiquement réalisable", result.is_feasible, 1.0),
        _observation("Longueur calculée", pipeline.total_length_m, 460_000.0, unit="m"),
        _observation("Stations évaluées", len(result.stations), 3.0),
        _observation(
            "Résidu de masse", result.diagnostics.mass_balance_residual, 0.0, absolute=1.0e-9
        ),
        _observation(
            "Durée de calcul sous la cible MVP",
            duration,
            0.0,
            unit="s",
            absolute=10.0,
        ),
    )


MVP_CASES: tuple[ValidationCase, ...] = tuple(
    ValidationCase(
        f"V-{index:03d}",
        title,
        category,
        f"Documentation MVP v2.0 § 13.2, plan {PLAN_VERSION} ; {reference}",
        executor,
    )
    for index, title, category, reference, executor in (
        (1, "Conduite horizontale simple", "liquide", "Darcy-Weisbach", _v001),
        (2, "Dénivelé positif et négatif", "liquide", "Bernoulli statique", _v002),
        (3, "Régime laminaire", "liquide", "lambda = 64/Re", _v003),
        (4, "Régime turbulent", "liquide", "Colebrook, Haaland et Swamee-Jain", _v004),
        (5, "Débit imposé", "réseau", "Conservation du débit", _v005),
        (6, "Pressions imposées", "réseau", "Darcy-Weisbach et recherche de racine", _v006),
        (7, "Pompe unique", "pompe", "Intersection pompe-réseau", _v007),
        (8, "Pompes en série", "pompe", "Addition des hauteurs", _v008),
        (9, "Pompes en parallèle", "pompe", "Addition et conservation des débits", _v009),
        (10, "Stations multiples", "réseau", "Bilan de charge par station", _v010),
        (11, "NPSH insuffisant", "pompe", "Marge NPSHa - NPSHr", _v011),
        (12, "Surpression", "contrôle", "Contrôle C-004 et MAOP", _v012),
        (13, "Station bypassée", "scénario", "Équation d'énergie du bypass", _v013),
        (14, "Pompe de secours", "scénario", "Substitution à performance identique", _v014),
        (15, "Transfert bac-à-bac", "transfert", "Bilan volumique discret", _v015),
        (16, "Bac presque vide", "transfert", "Événement niveau minimal", _v016),
        (17, "Bac presque plein", "transfert", "Événement niveau très haut", _v017),
        (18, "Absence de solution", "numérique", "Encadrement physique borné", _v018),
        (19, "Non-convergence forcée", "numérique", "Brent à itérations limitées", _v019),
        (20, "Grande longueur et profil complexe", "performance", "Benchmark de 460 km", _v020),
    )
)


__all__ = ["MVP_CASES", "PLAN_VERSION"]
