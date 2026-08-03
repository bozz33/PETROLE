"""Moteur principal du MVP : oléoduc longue distance en régime permanent.

Principe de résolution
----------------------

Le pipeline est parcouru **de l'amont vers l'aval** en propageant la charge piézométrique
``H = z + p/(ρg)``. Entre deux abscisses ``x_k`` et ``x_{k+1}`` séparées de ``Δx`` :

.. math::

    H_{k+1} = H_k - i(Q)\\,\\Delta x - \\sum K \\frac{v|v|}{2g} + \\Delta H_{station}

où ``i(Q)`` est le gradient hydraulique de Darcy–Weisbach. À chaque station rencontrée, la
charge est augmentée de la hauteur fournie par le groupe de pompage au débit qui la traverse.

Deux régimes de calcul
----------------------

- **Débit imposé** (UC-05) : une seule marche suffit, la pression manquante à l'autre
  extrémité est le résultat.
- **Débit inconnu** (UC-06, cas V-006) : le débit est l'inconnue. Le résidu
  ``p_{aval,calculée}(Q) - p_{aval,imposée}`` est strictement décroissant en ``Q`` — les
  pertes croissent en ``Q²`` alors que la hauteur des pompes décroît —, ce qui garantit
  l'unicité de la racine et permet une résolution robuste par encadrement puis Brent.

Ce que le moteur ne fait pas
----------------------------

Il ne traite ni le régime transitoire, ni le multiphasique, ni le transport multiproduit, ni
la thermique. Une pression calculée sous la pression de vapeur invalide le modèle de conduite
pleine : elle est signalée comme violation critique C-002, sauf si le modèle de zone
gravitaire est explicitement sélectionné (D07 § 8).
"""

from __future__ import annotations

import time
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from itertools import pairwise

from hydro_domain.canonical import CanonicalInput
from hydro_domain.enums import EquipmentStatus, FrictionModel
from hydro_domain.geometry import PipeSegment
from hydro_domain.pipeline import Pipeline
from hydro_domain.pumps import PumpInstance
from hydro_domain.results import (
    EnergySummary,
    GravityZone,
    ProfilePointResult,
    PumpResult,
    SegmentResult,
    SimulationResult,
    StationResult,
)
from hydro_domain.scenario import Scenario, SolverOptions
from hydro_domain.stations import PumpStation
from hydro_shared.codes import SimulationStatus, ViolationCode, WarningCode
from hydro_shared.diagnostics import (
    Diagnostic,
    Location,
    Severity,
    SolverDiagnostics,
    ValidationReport,
    Violation,
)
from hydro_shared.errors import NoPhysicalSolutionError, NotConvergedError
from hydro_shared.versioning import engine_fingerprint
from hydroliquid import checks
from hydroliquid.engine import Explanation, ExplanationEntry, HydraulicEngine, register_engine
from hydroliquid.hydraulics import (
    G,
    friction_factor,
    is_transition_regime,
    pressure_to_head_m,
    reynolds,
    velocity_head_m,
    velocity_m_s,
)
from hydroliquid.properties import FluidPropertyProvider, FluidState
from hydroliquid.solvers import solve_monotonic

#: Débit maximal exploré par défaut lorsqu'aucune borne n'est configurée, en m³/s.
#: 10 m³/s ≈ 36 000 m³/h : au-delà de tout oléoduc terrestre existant, ce qui garantit que
#: l'encadrement couvre le domaine physique sans exploration inutile.
DEFAULT_MAX_FLOW_M3_S = 10.0
#: Débit d'amorçage de la recherche d'encadrement, en m³/s.
INITIAL_FLOW_GUESS_M3_S = 0.1
#: Débit minimal considéré comme non nul, en m³/s.
MINIMUM_FLOW_M3_S = 1e-9


@dataclass(slots=True)
class _StationPassage:
    """Trace du passage à une station, conservée pour construire le résultat."""

    station: PumpStation
    flow_m3_s: float
    suction_pressure_pa: float
    discharge_pressure_pa: float
    suction_head_m: float
    head_m: float
    hydraulic_power_w: float
    absorbed_power_w: float | None
    efficiency: float | None
    pump_flows: dict[str, float] = field(default_factory=dict)
    pump_evaluations: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class _MarchResult:
    """Sortie brute d'une marche amont → aval."""

    points: list[ProfilePointResult]
    stations: list[_StationPassage]
    outlet_pressure_pa: float
    gravity_clamped: bool = False


def _resolve_pipeline(pipeline: Pipeline, scenario: Scenario) -> Pipeline:
    """Applique les surcharges du scénario à la baseline, sans jamais la modifier.

    La baseline reste intacte (FR-SCN-001) : cette fonction produit une copie sur laquelle le
    calcul est mené, ce qui garantit qu'un scénario dégradé n'altère pas le modèle approuvé.
    """
    segments: list[PipeSegment] = []
    for segment in pipeline.segments:
        override = scenario.segment_override_for(segment.id)
        if override is None:
            segments.append(segment)
            continue
        updated = segment if override.status is None else segment.with_status(override.status)
        if override.additional_k is not None:
            from hydro_domain.geometry import Fitting

            extra = Fitting(
                id=f"{segment.id}-override",
                kind="perte additionnelle (scénario)",
                k_coefficient=override.additional_k,
                chainage_m=segment.end_chainage_m,
                label="Perte additionnelle imposée par le scénario",
            )
            updated = PipeSegment(
                id=updated.id,
                sequence=updated.sequence,
                length_m=updated.length_m,
                inner_diameter_m=updated.inner_diameter_m,
                roughness_m=updated.roughness_m,
                start_chainage_m=updated.start_chainage_m,
                outer_diameter_m=updated.outer_diameter_m,
                wall_thickness_m=updated.wall_thickness_m,
                material=updated.material,
                maop_pa=updated.maop_pa,
                minimum_pressure_pa=updated.minimum_pressure_pa,
                status=updated.status,
                fittings=(*updated.fittings, extra),
                label=updated.label,
            )
        segments.append(updated)

    stations: list[PumpStation] = []
    for station in pipeline.stations:
        updated_station = station
        station_override = scenario.station_override_for(station.id)
        if station_override is not None and station_override.status is not None:
            updated_station = updated_station.with_status(station_override.status)

        replacements: dict[str, PumpInstance] = {}
        for pump in station.pumps:
            pump_override = scenario.pump_override_for(pump.id)
            if pump_override is None:
                continue
            replacements[pump.id] = pump.with_state(
                status=pump_override.status,
                running=pump_override.running,
                speed_ratio=pump_override.speed_ratio,
            )
        if replacements:
            updated_station = updated_station.with_pumps(replacements)
        stations.append(updated_station)

    return pipeline.with_segments(segments).with_stations(stations)


def _build_grid(pipeline: Pipeline, options: SolverOptions) -> list[float]:
    """Construit la grille de calcul le long du tracé.

    La grille contient obligatoirement : les extrémités de chaque tronçon, tous les points du
    profil levé, les chainages des stations, ceux des injections et ceux des accessoires. Le
    pas ``profile_step_m`` ne fait que **densifier** cette grille.

    Ce choix est important : un ré-échantillonnage à pas constant qui écraserait un sommet du
    relief masquerait le point de pression minimale, c'est-à-dire précisément l'endroit où le
    contrôle C-002 doit s'exercer.
    """
    chainages: set[float] = set()
    for segment in pipeline.segments:
        chainages.add(segment.start_chainage_m)
        chainages.add(segment.end_chainage_m)
        for fitting in segment.fittings:
            if fitting.chainage_m is not None:
                chainages.add(fitting.chainage_m)
    for point in pipeline.profile.points:
        if pipeline.start_chainage_m <= point.chainage_m <= pipeline.end_chainage_m:
            chainages.add(point.chainage_m)
    for station in pipeline.stations:
        chainages.add(station.chainage_m)
    for injection in pipeline.injections:
        chainages.add(injection.chainage_m)

    start, end = pipeline.start_chainage_m, pipeline.end_chainage_m
    step = options.profile_step_m
    current = start
    while current < end:
        chainages.add(current)
        current += step
    chainages.add(end)
    return sorted(c for c in chainages if start - 1e-9 <= c <= end + 1e-9)


class _Marcher:
    """Propagation de la charge le long du tracé pour un débit donné."""

    __slots__ = (
        "_fittings_by_chainage",
        "_injections_at_grid",
        "_segments_at_grid",
        "_stations_at_grid",
        "grid",
        "options",
        "pipeline",
        "state",
    )

    def __init__(
        self, pipeline: Pipeline, state: FluidState, options: SolverOptions, grid: list[float]
    ) -> None:
        self.pipeline = pipeline
        self.state = state
        self.options = options
        self.grid = grid
        # Les accessoires sans chainage explicite sont rattachés à la fin de leur tronçon :
        # leur position exacte est inconnue, mais leur perte doit être comptée une fois et
        # une seule.
        self._fittings_by_chainage: dict[float, float] = {}
        for segment in pipeline.segments:
            for fitting in segment.fittings:
                position = (
                    fitting.chainage_m if fitting.chainage_m is not None else segment.end_chainage_m
                )
                self._fittings_by_chainage[position] = (
                    self._fittings_by_chainage.get(position, 0.0) + fitting.effective_k()
                )

        # Une marche utilise une grille immuable. Résoudre la géométrie, les stations et les
        # injections une fois ici évite de balayer tous les tronçons à chaque point de profil.
        # Sans ce cache, un réseau de n tronçons échantillonné à n points dégrade la marche en
        # O(n²), alors que la topologie du MVP est une chaîne ordonnée (D11 § 4.4).
        self._segments_at_grid = self._segments_for_grid(pipeline, grid)
        self._stations_at_grid = tuple(pipeline.station_at(chainage) for chainage in grid)
        self._injections_at_grid = tuple(
            sum(
                injection.flow_m3_s
                for injection in pipeline.injections
                if injection.is_active and abs(injection.chainage_m - chainage) < 1e-6
            )
            for chainage in grid
        )

    @staticmethod
    def _segments_for_grid(pipeline: Pipeline, grid: list[float]) -> tuple[PipeSegment, ...]:
        """Associe chaque point de grille à son tronçon gouvernant en temps logarithmique.

        Aux frontières, la convention reste exactement celle de :meth:`_segment_for` : le
        tronçon aval gouverne l'intervalle suivant et le dernier point appartient au tronçon
        amont. Les contrôles topologiques garantissent une chaîne continue ; le repli conserve
        néanmoins le comportement défensif historique pour une entrée invalide.
        """

        segments = pipeline.segments
        starts = tuple(segment.start_chainage_m for segment in segments)
        last_grid_index = len(grid) - 1
        resolved: list[PipeSegment] = []

        for index, chainage in enumerate(grid):
            forward = index < last_grid_index
            segment_index = (
                bisect_right(starts, chainage) - 1 if forward else bisect_left(starts, chainage) - 1
            )
            if 0 <= segment_index < len(segments):
                candidate = segments[segment_index]
                if (
                    candidate.start_chainage_m <= chainage < candidate.end_chainage_m
                    if forward
                    else candidate.start_chainage_m < chainage <= candidate.end_chainage_m
                ):
                    resolved.append(candidate)
                    continue

            resolved.append(
                segments[-1] if chainage >= segments[-1].start_chainage_m else segments[0]
            )

        return tuple(resolved)

    def march(self, inlet_flow_m3_s: float, inlet_pressure_pa: float) -> _MarchResult:
        """Parcourt le pipeline et retourne le profil hydraulique complet."""
        rho = self.state.density_kg_m3
        nu = self.state.kinematic_viscosity_m2_s
        pv = self.state.vapor_pressure_pa
        model = self.options.friction_model

        points: list[ProfilePointResult] = []
        passages: list[_StationPassage] = []
        gravity_clamped = False

        elevation = self.pipeline.elevation_at(self.grid[0])
        head = elevation + pressure_to_head_m(inlet_pressure_pa, rho)
        flow = inlet_flow_m3_s

        for index, chainage in enumerate(self.grid):
            elevation = self.pipeline.elevation_at(chainage)

            # 1. Injection ou soutirage au point courant : il modifie le débit aval.
            flow += self._injections_at_grid[index]

            # 2. Perte singulière ponctuelle.
            segment = self._segments_at_grid[index]
            k_total = self._fittings_by_chainage.get(chainage, 0.0)
            if k_total:
                velocity = velocity_m_s(flow, segment.inner_diameter_m)
                head -= k_total * velocity * abs(velocity) / (2.0 * G)

            # 3. Station : la charge augmente de la hauteur fournie.
            station = self._stations_at_grid[index]
            if station is not None:
                suction_head = head
                suction_pressure = (suction_head - elevation) * rho * G
                if station.is_bypassed and station.bypass_k:
                    velocity = velocity_m_s(flow, segment.inner_diameter_m)
                    head -= station.bypass_k * velocity * abs(velocity) / (2.0 * G)
                evaluation = station.evaluate(flow, rho)
                head += evaluation.head_m
                discharge_pressure = (head - elevation) * rho * G
                passages.append(
                    _StationPassage(
                        station=station,
                        flow_m3_s=flow,
                        suction_pressure_pa=suction_pressure,
                        discharge_pressure_pa=discharge_pressure,
                        suction_head_m=suction_head,
                        head_m=evaluation.head_m,
                        hydraulic_power_w=evaluation.hydraulic_power_w,
                        absorbed_power_w=evaluation.absorbed_power_w,
                        efficiency=evaluation.efficiency,
                        pump_flows=dict(evaluation.flow_per_pump_m3_s),
                        pump_evaluations=dict(evaluation.pump_evaluations),
                    )
                )

            # 4. Modèle de zone gravitaire, si explicitement sélectionné.
            minimum_head = elevation + pressure_to_head_m(pv, rho)
            if self.options.apply_gravity_model and head < minimum_head:
                head = minimum_head
                gravity_clamped = True

            pressure = (head - elevation) * rho * G
            velocity = velocity_m_s(flow, segment.inner_diameter_m)
            points.append(
                ProfilePointResult(
                    chainage_m=chainage,
                    elevation_m=elevation,
                    pressure_pa=pressure,
                    hydraulic_grade_m=head,
                    flow_m3_s=flow,
                    velocity_m_s=velocity,
                    below_vapor_pressure=pressure <= pv,
                )
            )

            # 5. Perte linéaire jusqu'au point suivant.
            if index < len(self.grid) - 1:
                dx = self.grid[index + 1] - chainage
                if dx > 0.0:
                    re = reynolds(velocity, segment.inner_diameter_m, nu)
                    lam = friction_factor(re, segment.relative_roughness, model)
                    gradient = lam / segment.inner_diameter_m * velocity * abs(velocity) / (2.0 * G)
                    head -= gradient * dx

        return _MarchResult(
            points=points,
            stations=passages,
            outlet_pressure_pa=points[-1].pressure_pa,
            gravity_clamped=gravity_clamped,
        )

    def _segment_for(self, chainage: float, *, forward: bool) -> PipeSegment:
        """Tronçon gouvernant le calcul au point donné.

        Aux frontières entre deux tronçons, le tronçon **aval** est retenu lorsqu'on s'apprête
        à parcourir l'intervalle suivant : la perte de charge sur ``[x_k ; x_{k+1}]`` doit
        utiliser la géométrie de l'intervalle, pas celle du tronçon qui vient de s'achever.
        """
        segments = self.pipeline.segments
        for segment in segments:
            if forward:
                if segment.start_chainage_m <= chainage < segment.end_chainage_m:
                    return segment
            elif segment.start_chainage_m < chainage <= segment.end_chainage_m:
                return segment
        return segments[-1] if chainage >= segments[-1].start_chainage_m else segments[0]


@register_engine
class LongDistanceLiquidEngine(HydraulicEngine):
    """Moteur liquide longue distance : oléoducs multi-stations en régime permanent."""

    name = "long_distance_liquid"
    version = "0.1.0"

    # ------------------------------------------------------------------ validation

    def validate(self, canonical_input: CanonicalInput) -> ValidationReport:
        """Contrôle des entrées avant tout calcul (FR-MOD-008, D07 § 7)."""
        report = ValidationReport()

        for problem in canonical_input.validate():
            report.add_error(
                Violation(
                    code=ViolationCode.RESIDUAL_ABOVE_TOLERANCE,
                    severity=Severity.CRITICAL,
                    message=problem,
                    location=Location(
                        object_type="pipeline", object_id=canonical_input.pipeline.id
                    ),
                )
            )

        pipeline = canonical_input.pipeline
        scenario = canonical_input.scenario

        active_stations = [s for s in pipeline.stations if s.is_in_service and s.active_pumps]
        if not active_stations and scenario.solves_for_flow:
            report.add_warning(
                Diagnostic(
                    code=WarningCode.NEAR_LIMIT,
                    message=(
                        "Aucune pompe n'est en service : l'écoulement ne peut être que gravitaire. "
                        "Vérifiez que c'est bien le scénario voulu."
                    ),
                )
            )

        if not canonical_input.fluid.has_vapor_pressure:
            report.add_warning(
                Diagnostic(
                    code=WarningCode.PROPERTY_DEFAULTED,
                    message=(
                        "La pression de vapeur du produit n'est pas renseignée : les contrôles de "
                        "dépression (C-002) et de cavitation (C-003) ne pourront pas conclure."
                    ),
                )
            )

        if scenario.solver.apply_gravity_model:
            report.add_warning(
                Diagnostic(
                    code=WarningCode.GRAVITY_FLOW_SUSPECTED,
                    message=(
                        "Le modèle de zone gravitaire est explicitement activé. Ses hypothèses "
                        "(conduite non entièrement pressurisée, interface gaz-liquide, régime "
                        "stable) doivent être vérifiées avant tout usage industriel."
                    ),
                )
            )

        return report

    def supports(self, canonical_input: CanonicalInput) -> bool:
        """Le moteur couvre toute topologie linéaire, y compris avec injections."""
        return bool(canonical_input.pipeline.segments)

    # ------------------------------------------------------------------ simulation

    def simulate(self, canonical_input: CanonicalInput) -> SimulationResult:
        """Exécute la simulation et retourne un résultat immuable et explicable."""
        started = time.perf_counter()
        scenario = canonical_input.scenario
        options = scenario.solver
        diagnostics = SolverDiagnostics(tolerance=options.pressure_tolerance_pa)

        validation = self.validate(canonical_input)
        if not validation.is_valid:
            return self._failed_result(
                canonical_input,
                SimulationStatus.INVALID_INPUT,
                diagnostics,
                tuple(validation.errors),
                tuple(validation.warnings),
                started,
            )

        pipeline = _resolve_pipeline(canonical_input.pipeline, scenario)
        provider = FluidPropertyProvider(canonical_input.fluid)
        temperature = scenario.temperature_k or canonical_input.fluid.reference_temperature_k
        reference_pressure = (
            scenario.inlet_pressure_pa or canonical_input.fluid.reference_pressure_pa
        )
        state = provider.resolve(temperature, reference_pressure)

        grid = _build_grid(pipeline, options)
        marcher = _Marcher(pipeline, state, options, grid)

        try:
            flow, inlet_pressure, march = self._solve_operating_point(
                pipeline, marcher, scenario, state, diagnostics
            )
        except NoPhysicalSolutionError as exc:
            diagnostics.method = "bracket"
            diagnostics.note(exc.message)
            return self._failed_result(
                canonical_input,
                SimulationStatus.NO_PHYSICAL_SOLUTION,
                diagnostics,
                (
                    Violation(
                        code=ViolationCode.RESIDUAL_ABOVE_TOLERANCE,
                        severity=Severity.CRITICAL,
                        message=exc.message,
                        check_id="C-010",
                        recommendation=(
                            "Aucune configuration ne satisfait les conditions imposées. Réduisez "
                            "le débit demandé, ajoutez de la capacité de pompage ou relâchez une "
                            "condition aux limites."
                        ),
                    ),
                ),
                tuple(validation.warnings),
                started,
            )
        except NotConvergedError as exc:
            diagnostics.note(exc.message)
            return self._failed_result(
                canonical_input,
                SimulationStatus.NOT_CONVERGED,
                diagnostics,
                (
                    Violation(
                        code=ViolationCode.RESIDUAL_ABOVE_TOLERANCE,
                        severity=Severity.CRITICAL,
                        message=exc.message,
                        value=exc.residual,
                        limit=options.pressure_tolerance_pa,
                        check_id="C-010",
                    ),
                ),
                tuple(validation.warnings),
                started,
            )

        result = self._build_result(
            canonical_input,
            pipeline,
            state,
            march,
            flow,
            inlet_pressure,
            diagnostics,
            tuple(validation.warnings),
            started,
        )
        return result

    def _solve_operating_point(
        self,
        pipeline: Pipeline,
        marcher: _Marcher,
        scenario: Scenario,
        state: FluidState,
        diagnostics: SolverDiagnostics,
    ) -> tuple[float, float, _MarchResult]:
        """Détermine le couple (débit, pression amont) satisfaisant les conditions aux limites."""
        options = scenario.solver
        rho = state.density_kg_m3

        inlet_pressure = self._inlet_pressure(pipeline, scenario, rho)
        outlet_pressure_target = self._outlet_pressure(pipeline, scenario, rho)

        # Cas 1 — débit imposé et pression amont connue : une seule marche.
        if scenario.imposed_flow_m3_s is not None and inlet_pressure is not None:
            march = marcher.march(scenario.imposed_flow_m3_s, inlet_pressure)
            diagnostics.method = "marche directe"
            diagnostics.converged = True
            diagnostics.iterations = 1
            diagnostics.residual = 0.0
            return scenario.imposed_flow_m3_s, inlet_pressure, march

        # Cas 2 — débit imposé et pression aval connue : on résout la pression amont.
        if scenario.imposed_flow_m3_s is not None and outlet_pressure_target is not None:
            flow = scenario.imposed_flow_m3_s

            def residual_pressure(candidate_inlet: float) -> float:
                return (
                    marcher.march(flow, candidate_inlet).outlet_pressure_pa - outlet_pressure_target
                )

            root = solve_monotonic(
                residual_pressure,
                lower=1.0,
                upper=max(outlet_pressure_target * 2.0, 1.0e6),
                tolerance=options.pressure_tolerance_pa,
                variable_tolerance=options.pressure_tolerance_pa,
                max_iterations=options.max_iterations,
                diagnostics=diagnostics,
                log_iterations=options.store_iterations,
            )
            return flow, root.root, marcher.march(flow, root.root)

        # Cas 3 — débit inconnu : deux conditions d'extrémité, recherche du débit compatible.
        if inlet_pressure is None or outlet_pressure_target is None:
            raise NoPhysicalSolutionError(
                "Le problème n'est pas correctement contraint : le débit est inconnu et les deux "
                "conditions d'extrémité ne sont pas disponibles.",
                inlet_known=inlet_pressure is not None,
                outlet_known=outlet_pressure_target is not None,
            )

        def residual_flow(candidate_flow: float) -> float:
            return (
                marcher.march(candidate_flow, inlet_pressure).outlet_pressure_pa
                - outlet_pressure_target
            )

        upper = options.max_flow_m3_s or DEFAULT_MAX_FLOW_M3_S
        root = solve_monotonic(
            residual_flow,
            lower=MINIMUM_FLOW_M3_S,
            upper=min(INITIAL_FLOW_GUESS_M3_S, upper),
            tolerance=options.pressure_tolerance_pa,
            variable_tolerance=options.flow_tolerance_m3_s,
            hard_upper=options.max_flow_m3_s,
            max_iterations=options.max_iterations,
            diagnostics=diagnostics,
            log_iterations=options.store_iterations,
        )
        return root.root, inlet_pressure, marcher.march(root.root, inlet_pressure)

    @staticmethod
    def _inlet_pressure(pipeline: Pipeline, scenario: Scenario, rho: float) -> float | None:
        """Pression absolue à l'entrée, déduite d'une consigne ou d'un niveau de bac."""
        if scenario.inlet_pressure_pa is not None:
            return scenario.inlet_pressure_pa
        if scenario.inlet_tank_level_m is not None and pipeline.origin_tank is not None:
            tank = pipeline.origin_tank
            surface = tank.elevation_m + scenario.inlet_tank_level_m
            static = (surface - pipeline.elevation_at(pipeline.start_chainage_m)) * rho * G
            from hydro_domain.fluid import STANDARD_PRESSURE_PA

            return STANDARD_PRESSURE_PA + static
        return None

    @staticmethod
    def _outlet_pressure(pipeline: Pipeline, scenario: Scenario, rho: float) -> float | None:
        """Pression absolue en sortie, déduite d'une consigne ou d'un niveau de bac."""
        if scenario.outlet_pressure_pa is not None:
            return scenario.outlet_pressure_pa
        if scenario.outlet_tank_level_m is not None and pipeline.destination_tank is not None:
            tank = pipeline.destination_tank
            surface = tank.elevation_m + scenario.outlet_tank_level_m
            static = (surface - pipeline.elevation_at(pipeline.end_chainage_m)) * rho * G
            from hydro_domain.fluid import STANDARD_PRESSURE_PA

            return STANDARD_PRESSURE_PA + static
        return None

    # ------------------------------------------------------------------ résultat

    def _build_result(
        self,
        canonical_input: CanonicalInput,
        pipeline: Pipeline,
        state: FluidState,
        march: _MarchResult,
        flow: float,
        inlet_pressure: float,
        diagnostics: SolverDiagnostics,
        base_warnings: tuple[Diagnostic, ...],
        started: float,
    ) -> SimulationResult:
        options = canonical_input.scenario.solver
        rho = state.density_kg_m3
        points = march.points

        segment_results = self._segment_results(pipeline, state, points, options.friction_model)
        station_results, pump_results = self._station_results(march, state)
        gravity_zones = self._gravity_zones(points) if options.detect_gravity_zones else ()

        outcome = checks.CheckOutcome()
        outcome.extend(
            checks.check_mass_balance(
                inlet_flow_m3_s=flow,
                outlet_flow_m3_s=points[-1].flow_m3_s,
                net_injection_m3_s=pipeline.net_injection_m3_s,
                tolerance=options.mass_balance_tolerance,
            )
        )
        outcome.extend(
            checks.check_vapor_pressure(
                points,
                state.vapor_pressure_pa,
                gravity_model_applied=options.apply_gravity_model,
                vapor_pressure_known=canonical_input.fluid.has_vapor_pressure,
            )
        )
        outcome.extend(
            checks.check_npsh(
                pump_results,
                {
                    pump.id: pump.model.npsh_margin_m
                    for station in pipeline.stations
                    for pump in station.pumps
                },
            )
        )
        outcome.extend(checks.check_maximum_pressure(points, list(pipeline.segments)))
        outcome.extend(checks.check_velocity(points, options))
        outcome.extend(
            checks.check_pump_curve_domain(
                pump_results,
                {
                    pump.id: pump.model.minimum_continuous_flow_m3_s
                    for station in pipeline.stations
                    for pump in station.pumps
                    if pump.model.minimum_continuous_flow_m3_s is not None
                },
            )
        )
        outcome.extend(
            checks.check_motor_power(
                pump_results,
                {
                    pump.id: pump.model.motor_rated_power_w
                    for station in pipeline.stations
                    for pump in station.pumps
                    if pump.model.motor_rated_power_w is not None
                },
            )
        )
        outcome.extend(
            checks.check_station_pressures(
                station_results,
                {
                    station.id: {
                        "suction_min": station.suction_pressure_min_pa,
                        "discharge_max": station.discharge_pressure_max_pa,
                    }
                    for station in pipeline.stations
                },
            )
        )
        outcome.extend(checks.check_property_extrapolation(state.notes, state.extrapolated))

        mass_reference = max(abs(flow), 1e-12)
        diagnostics.mass_balance_residual = (
            points[-1].flow_m3_s - (flow + pipeline.net_injection_m3_s)
        ) / mass_reference
        diagnostics.mass_balance_tolerance = options.mass_balance_tolerance
        outcome.extend(
            checks.check_convergence(
                diagnostics.converged,
                diagnostics.residual,
                diagnostics.tolerance,
                diagnostics.iterations,
            )
        )

        if any(
            is_transition_regime(
                reynolds(
                    velocity_m_s(flow, segment.inner_diameter_m),
                    segment.inner_diameter_m,
                    state.kinematic_viscosity_m2_s,
                )
            )
            for segment in pipeline.segments
        ):
            outcome.warnings.append(
                Diagnostic(
                    code=WarningCode.TRANSITION_REGIME,
                    message=(
                        "Au moins un tronçon fonctionne en régime de transition (2 000 ≤ Re < "
                        "4 000). Le facteur de frottement y résulte d'une interpolation "
                        "conventionnelle entre les régimes laminaire et turbulent."
                    ),
                )
            )
        if diagnostics.fallback_used:
            outcome.warnings.append(
                Diagnostic(
                    code=WarningCode.SOLVER_FALLBACK,
                    message=(
                        "Le solveur a basculé sur une méthode de repli : "
                        + " ".join(diagnostics.messages)
                    ),
                )
            )

        violations = tuple(outcome.violations)
        warnings = (*base_warnings, *outcome.warnings)
        status = (
            SimulationStatus.CONVERGED_WARN
            if warnings or violations
            else SimulationStatus.CONVERGED
        )
        diagnostics.elapsed_s = time.perf_counter() - started

        energy = self._energy_summary(station_results, flow, canonical_input.scenario)
        pressures = [p.pressure_pa for p in points]

        return SimulationResult(
            status=status,
            scenario_id=canonical_input.scenario.id,
            engine=self.name,
            engine_version=f"{self.name}-{self.version}",
            input_hash=canonical_input.fingerprint,
            flow_m3_s=flow,
            min_pressure_pa=min(pressures),
            max_pressure_pa=max(pressures),
            total_head_loss_m=sum(s.total_head_loss_m for s in segment_results),
            segments=tuple(segment_results),
            stations=tuple(station_results),
            profile=tuple(points),
            gravity_zones=gravity_zones,
            energy=energy,
            violations=violations,
            warnings=tuple(warnings),
            diagnostics=diagnostics,
            assumptions={
                "fluid_state": state.as_dict(),
                "friction_model": options.friction_model.value,
                "gravity_model_applied": options.apply_gravity_model,
                "inlet_pressure_pa": inlet_pressure,
                "grid_points": len(points),
                "checks": outcome.as_dict(),
                "conventions": {
                    "pressure": "pascals absolus",
                    "head": "H = z + p/(ρg), hauteur cinétique omise sur les tronçons",
                    "npsh": "NPSHa = (p_aspiration − p_vapeur)/(ρg) + v²/(2g)",
                    "gravity_constant_m_s2": G,
                    "density_kg_m3": rho,
                },
            },
            environment=engine_fingerprint(),
        )

    def _segment_results(
        self,
        pipeline: Pipeline,
        state: FluidState,
        points: list[ProfilePointResult],
        model: FrictionModel,
    ) -> list[SegmentResult]:
        results: list[SegmentResult] = []
        chainages = [point.chainage_m for point in points]
        for segment in pipeline.segments:
            # Le profil est ordonné par chainage. Une recherche par dichotomie conserve les
            # extrémités partagées entre tronçons, sans reconstruire le profil complet pour
            # chaque segment (ce qui était quadratique sur les grands réseaux).
            start_index = bisect_left(chainages, segment.start_chainage_m - 1e-9)
            end_index = bisect_right(chainages, segment.end_chainage_m + 1e-9)
            inside = points[start_index:end_index]
            if not inside:
                continue
            weighted_length = 0.0
            weighted_flow = 0.0
            friction_loss = 0.0
            for left, right in pairwise(inside):
                dx = right.chainage_m - left.chainage_m
                if dx <= 0.0:
                    continue
                weighted_length += dx
                weighted_flow += left.flow_m3_s * dx
                interval_velocity = velocity_m_s(left.flow_m3_s, segment.inner_diameter_m)
                interval_re = reynolds(
                    interval_velocity,
                    segment.inner_diameter_m,
                    state.kinematic_viscosity_m2_s,
                )
                interval_lambda = friction_factor(
                    interval_re,
                    segment.relative_roughness,
                    model,
                )
                friction_loss += (
                    interval_lambda
                    * (dx / segment.inner_diameter_m)
                    * interval_velocity
                    * abs(interval_velocity)
                    / (2.0 * G)
                )
            flow = weighted_flow / weighted_length if weighted_length > 0.0 else inside[0].flow_m3_s
            velocity = velocity_m_s(flow, segment.inner_diameter_m)
            re = reynolds(velocity, segment.inner_diameter_m, state.kinematic_viscosity_m2_s)
            lam = friction_factor(re, segment.relative_roughness, model)
            flow_by_chainage = {point.chainage_m: point.flow_m3_s for point in inside}
            minor_loss = 0.0
            for fitting in segment.fittings:
                fitting_chainage = (
                    fitting.chainage_m if fitting.chainage_m is not None else segment.end_chainage_m
                )
                fitting_flow = flow_by_chainage.get(fitting_chainage, flow)
                fitting_k = fitting.effective_k()
                if fitting_k in (0.0, float("inf")):
                    continue
                fitting_velocity = velocity_m_s(fitting_flow, segment.inner_diameter_m)
                minor_loss += fitting_k * fitting_velocity * abs(fitting_velocity) / (2.0 * G)
            pressures = [p.pressure_pa for p in inside]
            results.append(
                SegmentResult(
                    segment_id=segment.id,
                    label=segment.label,
                    flow_m3_s=flow,
                    velocity_m_s=velocity,
                    reynolds=re,
                    friction_factor=lam,
                    friction_model=model.value,
                    friction_head_loss_m=friction_loss,
                    minor_head_loss_m=minor_loss,
                    elevation_change_m=pipeline.profile.elevation_change(
                        segment.start_chainage_m, segment.end_chainage_m
                    ),
                    inlet_pressure_pa=inside[0].pressure_pa,
                    outlet_pressure_pa=inside[-1].pressure_pa,
                    min_pressure_pa=min(pressures),
                    max_pressure_pa=max(pressures),
                    maop_margin_pa=(
                        None if segment.maop_pa is None else segment.maop_pa - max(pressures)
                    ),
                )
            )
        return results

    def _station_results(
        self, march: _MarchResult, state: FluidState
    ) -> tuple[list[StationResult], list[PumpResult]]:
        stations: list[StationResult] = []
        all_pumps: list[PumpResult] = []
        rho = state.density_kg_m3

        for passage in march.stations:
            station = passage.station
            pump_results: list[PumpResult] = []
            for pump in station.pumps:
                pump_flow = passage.pump_flows.get(pump.id, 0.0)
                evaluation = passage.pump_evaluations.get(pump.id)
                npshr = getattr(evaluation, "npshr_m", None) if evaluation else None
                efficiency = getattr(evaluation, "efficiency", None) if evaluation else None
                head = getattr(evaluation, "head_m", 0.0) if evaluation else 0.0
                within = not getattr(evaluation, "extrapolated", False) if evaluation else True

                # Le NPSH disponible se calcule à la bride d'aspiration : la pression
                # d'aspiration de la station, diminuée des pertes de son collecteur.
                npsha = None
                if pump.is_active and station.suction_line_diameter_m is not None:
                    velocity = velocity_m_s(
                        passage.flow_m3_s,
                        station.suction_line_diameter_m,
                    )
                    suction_pressure = passage.suction_pressure_pa
                    if station.suction_line_k:
                        suction_pressure -= (
                            station.suction_line_k * rho * velocity * abs(velocity) / 2.0
                        )
                    npsha = station.npsh_available_m(
                        suction_pressure_pa=suction_pressure,
                        vapor_pressure_pa=state.vapor_pressure_pa,
                        density_kg_m3=rho,
                        velocity_head_m=velocity_head_m(velocity),
                    )

                margin = None
                if npsha is not None and npshr is not None:
                    margin = npsha - npshr - pump.model.npsh_margin_m

                bep = pump.model.curve.best_efficiency_point()
                off_bep = None
                if bep is not None and bep[0] > 0 and pump.is_active:
                    off_bep = abs(pump_flow - bep[0]) / bep[0]

                hydraulic = rho * G * pump_flow * head if pump.is_active else 0.0
                absorbed = None
                if evaluation is not None:
                    power = getattr(evaluation, "power_w", None)
                    if power is not None:
                        absorbed = power / station.drive_efficiency
                    elif efficiency:
                        absorbed = hydraulic / efficiency / station.drive_efficiency

                pump_result = PumpResult(
                    pump_id=pump.id,
                    label=pump.display_name,
                    station_id=station.id,
                    running=pump.is_active,
                    flow_m3_s=pump_flow,
                    head_m=head if pump.is_active else 0.0,
                    speed_ratio=pump.speed_ratio,
                    efficiency=efficiency,
                    hydraulic_power_w=hydraulic,
                    absorbed_power_w=absorbed,
                    npsh_required_m=npshr,
                    npsh_available_m=npsha,
                    npsh_margin_m=margin,
                    within_curve_domain=within,
                    off_bep_ratio=off_bep,
                )
                pump_results.append(pump_result)
                all_pumps.append(pump_result)

            stations.append(
                StationResult(
                    station_id=station.id,
                    name=station.display_name,
                    chainage_m=station.chainage_m,
                    elevation_m=station.elevation_m,
                    in_service=station.is_in_service,
                    bypassed=station.is_bypassed,
                    flow_m3_s=passage.flow_m3_s,
                    suction_pressure_pa=passage.suction_pressure_pa,
                    discharge_pressure_pa=passage.discharge_pressure_pa,
                    head_m=passage.head_m,
                    hydraulic_power_w=passage.hydraulic_power_w,
                    absorbed_power_w=passage.absorbed_power_w,
                    efficiency=passage.efficiency,
                    active_pump_count=len(station.active_pumps),
                    pumps=tuple(pump_results),
                )
            )
        return stations, all_pumps

    @staticmethod
    def _gravity_zones(points: list[ProfilePointResult]) -> tuple[GravityZone, ...]:
        """Regroupe les points dépressurisés en zones contiguës."""
        zones: list[GravityZone] = []
        start: float | None = None
        previous: float | None = None
        for point in points:
            if point.below_vapor_pressure:
                if start is None:
                    start = point.chainage_m
                previous = point.chainage_m
            elif start is not None:
                zones.append(GravityZone(start_chainage_m=start, end_chainage_m=previous or start))
                start, previous = None, None
        if start is not None:
            zones.append(GravityZone(start_chainage_m=start, end_chainage_m=previous or start))
        return tuple(zones)

    @staticmethod
    def _energy_summary(
        stations: list[StationResult], flow: float, scenario: Scenario
    ) -> EnergySummary:
        hydraulic = sum(s.hydraulic_power_w for s in stations)
        absorbed_values = [s.absorbed_power_w for s in stations if s.absorbed_power_w is not None]
        absorbed = (
            sum(absorbed_values) if len(absorbed_values) == len(stations) and stations else None
        )

        duration = 3600.0
        energy = absorbed * duration if absorbed is not None else None
        cost = (
            energy * scenario.energy_price_per_joule
            if energy is not None and scenario.energy_price_per_joule is not None
            else None
        )
        specific = absorbed / flow if absorbed is not None and flow > 0 else None

        return EnergySummary(
            total_hydraulic_power_w=hydraulic,
            total_absorbed_power_w=absorbed,
            energy_j=energy,
            duration_s=duration,
            cost=cost,
            specific_energy_j_m3=specific,
        )

    def _failed_result(
        self,
        canonical_input: CanonicalInput,
        status: SimulationStatus,
        diagnostics: SolverDiagnostics,
        violations: tuple[Violation, ...],
        warnings: tuple[Diagnostic, ...],
        started: float,
    ) -> SimulationResult:
        """Résultat d'échec : jamais vide, toujours porteur d'un diagnostic exploitable."""
        diagnostics.elapsed_s = time.perf_counter() - started
        return SimulationResult(
            status=status,
            scenario_id=canonical_input.scenario.id,
            engine=self.name,
            engine_version=f"{self.name}-{self.version}",
            input_hash=canonical_input.fingerprint,
            violations=violations,
            warnings=warnings,
            diagnostics=diagnostics,
            environment=engine_fingerprint(),
        )

    # ------------------------------------------------------------------ explication

    def explain(self, result: SimulationResult) -> Explanation:
        """Explication structurée du résultat (D-v2 § 12.2)."""
        assumptions: list[ExplanationEntry] = []
        fluid_state = result.assumptions.get("fluid_state", {})
        if fluid_state:
            assumptions.append(
                ExplanationEntry(
                    title="Propriétés du produit",
                    detail=(
                        f"Masse volumique {fluid_state.get('density_kg_m3', 0):.1f} kg/m³ et "
                        f"viscosité cinématique "
                        f"{fluid_state.get('kinematic_viscosity_m2_s', 0) * 1e6:.2f} cSt évaluées à "
                        f"{fluid_state.get('temperature_k', 0) - 273.15:.1f} °C, puis figées pour "
                        f"toute la simulation (régime permanent isotherme)."
                    ),
                    reference="D07 § 3",
                    values=dict(fluid_state),
                )
            )
        conventions = result.assumptions.get("conventions", {})
        if conventions:
            assumptions.append(
                ExplanationEntry(
                    title="Conventions de calcul",
                    detail=(
                        "Pressions en pascals absolus ; charge piézométrique H = z + p/(ρg) ; "
                        "hauteur cinétique omise sur les tronçons de diamètre constant et "
                        "réintroduite pour le NPSH disponible."
                    ),
                    reference="D07 § 2",
                    values=dict(conventions),
                )
            )

        residual_text = (
            "non disponible"
            if result.diagnostics.residual is None
            else f"{result.diagnostics.residual:.3g}"
        )
        tolerance_text = (
            "non disponible"
            if result.diagnostics.tolerance is None
            else f"{result.diagnostics.tolerance:.3g}"
        )
        methods = [
            ExplanationEntry(
                title="Facteur de frottement",
                detail=(
                    f"Corrélation « {result.assumptions.get('friction_model', 'inconnue')} », "
                    f"avec λ = 64/Re en régime laminaire et interpolation continue et signalée "
                    f"dans la zone de transition 2 000 ≤ Re < 4 000."
                ),
                reference="D07 § 5",
            ),
            ExplanationEntry(
                title="Résolution",
                detail=(
                    f"Méthode « {result.diagnostics.method} », {result.diagnostics.iterations} "
                    f"itération(s), résidu final {residual_text} pour une "
                    f"tolérance de {tolerance_text}."
                ),
                reference="D07 § 7",
                values=result.diagnostics.as_dict(),
            ),
        ]

        findings = [
            ExplanationEntry(
                title=violation.message,
                detail=violation.recommendation or "Aucune recommandation automatique disponible.",
                reference=violation.check_id,
                values={
                    "valeur": violation.value,
                    "limite": violation.limit,
                    "écart": violation.deviation,
                    "localisation": violation.location.describe(),
                },
            )
            for violation in result.violations
        ]
        findings.extend(
            ExplanationEntry(
                title=warning.message,
                detail="Avertissement : le résultat reste disponible mais doit être examiné.",
                reference=warning.code.value,
            )
            for warning in result.warnings
        )

        limitations = [
            ExplanationEntry(
                title="Périmètre du moteur",
                detail=(
                    "Écoulement monophasique liquide, conduite pleine, régime permanent et "
                    "isotherme. Ni transitoire, ni multiproduit, ni thermique."
                ),
                reference="Documentation v2.0 § 1.2",
            )
        ]
        skipped = result.assumptions.get("checks", {}).get("skipped", {})
        limitations.extend(
            ExplanationEntry(
                title=f"Contrôle {check_id} non effectué",
                detail=reason,
                reference=check_id,
            )
            for check_id, reason in skipped.items()
        )

        if result.is_approvable:
            summary = (
                f"Scénario réalisable : débit {result.flow_m3_s * 3600:.0f} m³/h, pression comprise "
                f"entre {(result.min_pressure_pa or 0) / 1e5:.2f} et "
                f"{(result.max_pressure_pa or 0) / 1e5:.2f} bar, aucune violation critique."
            )
        elif result.status.has_results:
            summary = (
                f"Scénario calculé mais non approuvable : {len(result.critical_violations)} "
                f"violation(s) critique(s) détectée(s)."
            )
        else:
            summary = f"Aucun résultat exploitable : statut {result.status.value}."

        return Explanation(
            summary=summary,
            feasible=result.is_feasible,
            approvable=result.is_approvable,
            assumptions=tuple(assumptions),
            methods=tuple(methods),
            findings=tuple(findings),
            limitations=tuple(limitations),
        )


__all__ = ["EquipmentStatus", "LongDistanceLiquidEngine"]
