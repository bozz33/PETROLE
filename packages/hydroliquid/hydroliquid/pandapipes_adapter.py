"""Adaptateur pandapipes : moteur secondaire de comparaison.

Décision DEC-ENGINE-002 : *pandapipes est intégré par adaptateur après preuve de concept ; il
ne devient ni une dépendance unique, ni une dépendance irréversible.*

La documentation officielle de pandapipes le présente d'abord comme un programme de calcul de
réseaux de gaz et de chauffage urbain. Il possède bien des composants de conduite, de pompe et
de compresseur, mais son domaine n'est pas celui de l'oléoduc longue distance avec profil
altimétrique détaillé, stations multiples et pompes de secours.

Rôle exact dans le MVP (D-v2 § 2 « Deux moteurs liquides derrière une interface commune ») :

- topologie nœuds-branches et réseaux ramifiés simples ;
- certains calculs stationnaires compatibles ;
- **comparaison croisée et benchmark** du moteur principal sur les cas génériques.

L'adaptateur refuse explicitement les cas qu'il ne sait pas représenter fidèlement plutôt que
de produire un résultat approché : une comparaison sur un cas mal traduit serait plus
trompeuse qu'une absence de comparaison.
"""

from __future__ import annotations

import math
import time
from importlib.util import find_spec

from hydro_domain.canonical import CanonicalInput
from hydro_domain.enums import FrictionModel
from hydro_domain.results import (
    ProfilePointResult,
    SegmentResult,
    SimulationResult,
)
from hydro_shared.codes import SimulationStatus, ViolationCode, WarningCode
from hydro_shared.diagnostics import (
    Diagnostic,
    Severity,
    SolverDiagnostics,
    ValidationReport,
    Violation,
)
from hydro_shared.errors import UnsupportedCaseError
from hydro_shared.versioning import engine_fingerprint
from hydroliquid.engine import Explanation, ExplanationEntry, HydraulicEngine, register_engine
from hydroliquid.hydraulics import velocity_m_s

#: Vrai si pandapipes est disponible dans l'environnement.
PANDAPIPES_AVAILABLE = find_spec("pandapipes") is not None
#: Valeur codée par pandapipes 0.14 pour reconstruire exactement son bilan de charge.
PANDAPIPES_GRAVITY_M_S2 = 9.81


@register_engine
class PandapipesEngine(HydraulicEngine):
    """Adaptateur vers pandapipes pour les cas génériques compatibles.

    Cas **non couverts**, refusés explicitement :

    - présence de stations de pompage à plusieurs groupes série/parallèle, dont le partage de
      débit n'a pas d'équivalent direct dans le modèle de pompe de pandapipes ;
    - modèle de zone gravitaire, qui suppose une conduite non entièrement pressurisée ;
    - injections et soutirages intermédiaires le long d'un tronçon.
    """

    name = "pandapipes"
    version = "0.2.0"

    _APPROVAL_BLOCK_REASON = (
        "Moteur secondaire de comparaison : les contrôles scientifiques obligatoires "
        "C-001 à C-012 ne sont pas tous exécutés."
    )

    # ------------------------------------------------------------------ compatibilité

    def supports(self, canonical_input: CanonicalInput) -> bool:
        return not self._incompatibilities(canonical_input)

    @staticmethod
    def _incompatibilities(canonical_input: CanonicalInput) -> list[str]:
        """Motifs pour lesquels le cas ne peut pas être traduit fidèlement."""
        reasons: list[str] = []
        pipeline = canonical_input.pipeline

        if not PANDAPIPES_AVAILABLE:
            reasons.append(
                "La bibliothèque pandapipes n'est pas installée dans cet environnement "
                "(extra « pandapipes »)."
            )
        if pipeline.stations:
            reasons.append(
                f"{len(pipeline.stations)} station(s) de pompage déclarée(s) : l'adaptateur de "
                "comparaison ne traduit actuellement aucune station, y compris contournée "
                "ou hors service."
            )
        if any(i.is_active for i in pipeline.injections):
            reasons.append(
                "Injections ou soutirages intermédiaires déclarés : la topologie devrait être "
                "redécoupée, ce qui modifierait la comparaison."
            )
        if canonical_input.scenario.solver.apply_gravity_model:
            reasons.append(
                "Le modèle de zone gravitaire est activé : pandapipes calcule une conduite "
                "entièrement pressurisée."
            )
        if canonical_input.scenario.solver.friction_model is not FrictionModel.COLEBROOK_WHITE:
            reasons.append(
                "Le modèle de frottement demandé n'est pas Colebrook–White, seul modèle "
                "traduit par l'adaptateur pandapipes."
            )
        unavailable_segments = [
            segment.id for segment in pipeline.segments if not segment.is_in_service
        ]
        if unavailable_segments:
            reasons.append(
                "Tronçon(s) hors service non représentable(s) dans une chaîne en écoulement : "
                + ", ".join(unavailable_segments)
                + "."
            )
        closed_segments = [
            segment.id
            for segment in pipeline.segments
            if not math.isfinite(segment.total_fitting_k())
        ]
        if closed_segments:
            reasons.append(
                "Accessoire fermé sur le(s) tronçon(s) "
                + ", ".join(closed_segments)
                + " : aucun écoulement imposé ne peut le traverser."
            )
        scenario = canonical_input.scenario
        if scenario.pump_overrides or scenario.station_overrides or scenario.segment_overrides:
            reasons.append(
                "Des surcharges d'équipement sont déclarées dans le scénario ; elles ne sont "
                "pas traduites par l'adaptateur de comparaison."
            )

        boundaries = [pipeline.start_chainage_m] + [
            segment.end_chainage_m for segment in pipeline.segments
        ]
        internal_profile_points = [
            point.chainage_m
            for point in pipeline.profile.points
            if not any(
                math.isclose(point.chainage_m, boundary, abs_tol=1e-6) for boundary in boundaries
            )
        ]
        if internal_profile_points:
            reasons.append(
                f"{len(internal_profile_points)} point(s) altimétrique(s) intérieur(s) à un "
                "tronçon : le réseau doit être redécoupé à ces chainages avant comparaison."
            )
        return reasons

    # ------------------------------------------------------------------ interface

    def validate(self, canonical_input: CanonicalInput) -> ValidationReport:
        report = ValidationReport()
        for problem in canonical_input.validate():
            report.add_error(
                Violation(
                    code=ViolationCode.RESIDUAL_ABOVE_TOLERANCE,
                    severity=Severity.CRITICAL,
                    message=problem,
                )
            )
        for reason in self._incompatibilities(canonical_input):
            report.add_warning(
                Diagnostic(
                    code=WarningCode.RULE_NOT_IMPLEMENTED,
                    message=f"Cas non couvert par l'adaptateur pandapipes : {reason}",
                )
            )
        return report

    def simulate(self, canonical_input: CanonicalInput) -> SimulationResult:
        """Traduit le cas en réseau pandapipes, le résout et reconstruit un résultat commun."""
        started = time.perf_counter()
        diagnostics = SolverDiagnostics(method="pandapipes")

        reasons = self._incompatibilities(canonical_input)
        if reasons:
            raise UnsupportedCaseError(
                "L'adaptateur pandapipes ne couvre pas ce cas : " + " ".join(reasons),
                reasons=reasons,
                engine=self.name,
            )

        scenario = canonical_input.scenario
        if scenario.imposed_flow_m3_s is None or scenario.inlet_pressure_pa is None:
            raise UnsupportedCaseError(
                "L'adaptateur pandapipes exige un débit imposé et une pression amont : la "
                "recherche de débit compatible relève du moteur longue distance.",
                engine=self.name,
            )

        validation = self.validate(canonical_input)
        if not validation.is_valid:
            diagnostics.tolerance = scenario.solver.pressure_tolerance_pa
            diagnostics.elapsed_s = time.perf_counter() - started
            return SimulationResult(
                status=SimulationStatus.INVALID_INPUT,
                scenario_id=scenario.id,
                engine=self.name,
                engine_version=f"{self.name}-{self.version}",
                input_hash=canonical_input.fingerprint,
                violations=tuple(validation.errors),
                warnings=tuple(validation.warnings),
                diagnostics=diagnostics,
                environment=engine_fingerprint(),
                approval_permitted=False,
                approval_block_reason=self._APPROVAL_BLOCK_REASON,
            )

        import pandapipes as pp
        from pandapipes.component_models.component_toolbox import p_correction_height_air
        from pandapipes.pf.pipeflow_setup import PipeflowNotConverged

        from hydroliquid.properties import FluidPropertyProvider

        pipeline = canonical_input.pipeline
        provider = FluidPropertyProvider(canonical_input.fluid)
        temperature = scenario.temperature_k or canonical_input.fluid.reference_temperature_k
        state = provider.resolve(temperature, scenario.inlet_pressure_pa)

        net = pp.create_empty_network(fluid="water")
        # Le fluide est redéfini par ses propriétés réelles : pandapipes travaille avec un
        # fluide nommé, mais accepte des propriétés constantes fournies explicitement.
        pp.create_constant_property(
            net,
            "density",
            state.density_kg_m3,
            overwrite=True,
            warn_on_duplicates=False,
        )
        pp.create_constant_property(
            net,
            "viscosity",
            state.dynamic_viscosity_pa_s,
            overwrite=True,
            warn_on_duplicates=False,
        )

        junctions: list[int] = []
        ambient_pressures_bar: list[float] = []
        for index, chainage in enumerate(
            [pipeline.start_chainage_m] + [s.end_chainage_m for s in pipeline.segments]
        ):
            elevation = pipeline.elevation_at(chainage)
            ambient_pressures_bar.append(float(p_correction_height_air(elevation)))
            junctions.append(
                pp.create_junction(
                    net,
                    pn_bar=scenario.inlet_pressure_pa / 1e5,
                    tfluid_k=temperature,
                    height_m=elevation,
                    name=f"J{index}",
                )
            )

        pipe_ids: list[int] = []
        for index, segment in enumerate(pipeline.segments):
            pipe_ids.append(
                pp.create_pipe_from_parameters(
                    net,
                    from_junction=junctions[index],
                    to_junction=junctions[index + 1],
                    length_km=segment.length_m / 1000.0,
                    inner_diameter_mm=segment.inner_diameter_m * 1000.0,
                    k_mm=segment.roughness_m * 1000.0,
                    loss_coefficient=segment.total_fitting_k(),
                    name=segment.label or segment.id,
                )
            )

        pp.create_ext_grid(
            net,
            junction=junctions[0],
            # pandapipes exprime ``p_bar`` relativement à la pression atmosphérique locale,
            # tandis que le contrat HydroLiquid impose une pression absolue.
            p_bar=scenario.inlet_pressure_pa / 1e5 - ambient_pressures_bar[0],
            t_k=temperature,
        )
        pp.create_sink(
            net,
            junction=junctions[-1],
            mdot_kg_per_s=scenario.imposed_flow_m3_s * state.density_kg_m3,
        )

        try:
            pp.pipeflow(
                net,
                friction_model="colebrook",
                mode="hydraulics",
                tol_p=scenario.solver.pressure_tolerance_pa / 1e5,
                tol_m=max(
                    scenario.solver.mass_balance_tolerance
                    * state.density_kg_m3
                    * abs(scenario.imposed_flow_m3_s),
                    1e-12,
                ),
                max_iter_hyd=scenario.solver.max_iterations,
            )
        except PipeflowNotConverged as error:
            internal_results = net.get("_internal_results", {})
            diagnostics.iterations = int(
                internal_results.get("iterations_hydraulics", scenario.solver.max_iterations)
            )
            diagnostics.residual = float("inf")
            diagnostics.tolerance = scenario.solver.pressure_tolerance_pa
            diagnostics.elapsed_s = time.perf_counter() - started
            diagnostics.note(f"Échec de convergence pandapipes : {error}")
            return SimulationResult(
                status=SimulationStatus.NOT_CONVERGED,
                scenario_id=scenario.id,
                engine=self.name,
                engine_version=f"{self.name}-{self.version}",
                input_hash=canonical_input.fingerprint,
                flow_m3_s=scenario.imposed_flow_m3_s,
                violations=(
                    Violation(
                        code=ViolationCode.RESIDUAL_ABOVE_TOLERANCE,
                        severity=Severity.CRITICAL,
                        message=(
                            "pandapipes n'a pas convergé dans le nombre maximal "
                            "d'itérations autorisé."
                        ),
                        check_id="C-010",
                        recommendation=(
                            "Vérifier les conditions aux limites, augmenter le nombre maximal "
                            "d'itérations ou utiliser le moteur principal."
                        ),
                    ),
                ),
                diagnostics=diagnostics,
                environment=engine_fingerprint(),
                approval_permitted=False,
                approval_block_reason=self._APPROVAL_BLOCK_REASON,
            )

        internal_results = net.get("_internal_results", {})
        diagnostics.iterations = int(internal_results.get("iterations_hydraulics", 0))
        diagnostics.tolerance = scenario.solver.pressure_tolerance_pa

        points: list[ProfilePointResult] = []
        segments_results: list[SegmentResult] = []
        pressure_balance_residuals_pa: list[float] = []
        relative_flow_residuals: list[float] = []
        for index, segment in enumerate(pipeline.segments):
            pipe_id = pipe_ids[index]
            inlet_bar = (
                float(net.res_junction.at[junctions[index], "p_bar"]) + ambient_pressures_bar[index]
            )
            outlet_bar = (
                float(net.res_junction.at[junctions[index + 1], "p_bar"])
                + ambient_pressures_bar[index + 1]
            )
            velocity = velocity_m_s(scenario.imposed_flow_m3_s, segment.inner_diameter_m)
            friction_factor = float(net.res_pipe.at[pipe_id, "lambda"])
            friction_loss = (
                friction_factor
                * (segment.length_m / segment.inner_diameter_m)
                * velocity
                * abs(velocity)
                / (2.0 * PANDAPIPES_GRAVITY_M_S2)
            )
            minor_loss = (
                segment.total_fitting_k()
                * velocity
                * abs(velocity)
                / (2.0 * PANDAPIPES_GRAVITY_M_S2)
            )
            elevation_change = pipeline.profile.elevation_change(
                segment.start_chainage_m, segment.end_chainage_m
            )
            pressure_head_change = (
                (inlet_bar - outlet_bar) * 1e5 / (state.density_kg_m3 * PANDAPIPES_GRAVITY_M_S2)
            )
            pressure_balance_residuals_pa.append(
                abs(pressure_head_change - elevation_change - friction_loss - minor_loss)
                * state.density_kg_m3
                * PANDAPIPES_GRAVITY_M_S2
            )
            calculated_flow = float(net.res_pipe.at[pipe_id, "vdot_m3_per_s"])
            relative_flow_residuals.append(
                abs(calculated_flow - scenario.imposed_flow_m3_s)
                / max(abs(scenario.imposed_flow_m3_s), 1e-12)
            )
            segments_results.append(
                SegmentResult(
                    segment_id=segment.id,
                    label=segment.label,
                    flow_m3_s=scenario.imposed_flow_m3_s,
                    velocity_m_s=velocity,
                    reynolds=float(net.res_pipe.at[pipe_id, "reynolds"]),
                    friction_factor=friction_factor,
                    friction_model="colebrook (pandapipes)",
                    friction_head_loss_m=friction_loss,
                    minor_head_loss_m=minor_loss,
                    elevation_change_m=elevation_change,
                    inlet_pressure_pa=inlet_bar * 1e5,
                    outlet_pressure_pa=outlet_bar * 1e5,
                    min_pressure_pa=min(inlet_bar, outlet_bar) * 1e5,
                    max_pressure_pa=max(inlet_bar, outlet_bar) * 1e5,
                    maop_margin_pa=(
                        None
                        if segment.maop_pa is None
                        else segment.maop_pa - max(inlet_bar, outlet_bar) * 1e5
                    ),
                )
            )
            points.append(
                ProfilePointResult(
                    chainage_m=segment.start_chainage_m,
                    elevation_m=pipeline.elevation_at(segment.start_chainage_m),
                    pressure_pa=inlet_bar * 1e5,
                    hydraulic_grade_m=pipeline.elevation_at(segment.start_chainage_m)
                    + inlet_bar * 1e5 / (state.density_kg_m3 * PANDAPIPES_GRAVITY_M_S2),
                    flow_m3_s=scenario.imposed_flow_m3_s,
                    velocity_m_s=velocity,
                    below_vapor_pressure=inlet_bar * 1e5 <= state.vapor_pressure_pa,
                )
            )

        last = pipeline.segments[-1]
        outlet_bar = float(net.res_junction.at[junctions[-1], "p_bar"]) + ambient_pressures_bar[-1]
        points.append(
            ProfilePointResult(
                chainage_m=last.end_chainage_m,
                elevation_m=pipeline.elevation_at(last.end_chainage_m),
                pressure_pa=outlet_bar * 1e5,
                hydraulic_grade_m=pipeline.elevation_at(last.end_chainage_m)
                + outlet_bar * 1e5 / (state.density_kg_m3 * PANDAPIPES_GRAVITY_M_S2),
                flow_m3_s=scenario.imposed_flow_m3_s,
                velocity_m_s=velocity_m_s(scenario.imposed_flow_m3_s, last.inner_diameter_m),
                below_vapor_pressure=outlet_bar * 1e5 <= state.vapor_pressure_pa,
            )
        )

        diagnostics.residual = max(pressure_balance_residuals_pa, default=0.0)
        diagnostics.mass_balance_residual = max(relative_flow_residuals, default=0.0)
        diagnostics.mass_balance_tolerance = scenario.solver.mass_balance_tolerance
        diagnostics.converged = (
            bool(net.converged)
            and diagnostics.residual <= diagnostics.tolerance
            and diagnostics.mass_balance_ok
        )
        diagnostics.elapsed_s = time.perf_counter() - started
        diagnostics.note(
            "Le résidu publié est l'écart maximal du bilan de charge reconstruit, en pascals."
        )

        pressures = [p.pressure_pa for p in points]
        return SimulationResult(
            status=(
                SimulationStatus.CONVERGED
                if diagnostics.converged
                else SimulationStatus.NOT_CONVERGED
            ),
            scenario_id=scenario.id,
            engine=self.name,
            engine_version=f"{self.name}-{self.version}",
            input_hash=canonical_input.fingerprint,
            flow_m3_s=scenario.imposed_flow_m3_s,
            min_pressure_pa=min(pressures),
            max_pressure_pa=max(pressures),
            total_head_loss_m=sum(s.total_head_loss_m for s in segments_results),
            segments=tuple(segments_results),
            profile=tuple(points),
            diagnostics=diagnostics,
            assumptions={
                "fluid_state": state.as_dict(),
                "friction_model": "colebrook (pandapipes)",
                "gravity_m_s2": PANDAPIPES_GRAVITY_M_S2,
                "pressure_convention": (
                    "Les pressions relatives de pandapipes sont converties en pressions "
                    "absolues à l'altitude de chaque nœud."
                ),
                "engine_role": (
                    "Moteur secondaire de comparaison. Les résultats servent au benchmark du "
                    "moteur longue distance, pas à la production d'une note de calcul approuvée."
                ),
            },
            environment=engine_fingerprint(),
            approval_permitted=False,
            approval_block_reason=self._APPROVAL_BLOCK_REASON,
        )

    def explain(self, result: SimulationResult) -> Explanation:
        return Explanation(
            summary=(
                f"Résultat de comparaison pandapipes : débit {result.flow_m3_s * 3600:.0f} m³/h, "
                f"perte de charge totale {result.total_head_loss_m:.2f} m."
            ),
            feasible=result.is_feasible,
            approvable=False,
            methods=(
                ExplanationEntry(
                    title="Moteur secondaire",
                    detail=(
                        "Calcul réalisé par pandapipes avec le modèle de frottement de Colebrook. "
                        "Ce moteur sert à la comparaison croisée du moteur principal."
                    ),
                    reference="DEC-ENGINE-002",
                ),
            ),
            limitations=(
                ExplanationEntry(
                    title="Non approuvable",
                    detail=(
                        "Un résultat produit par l'adaptateur de comparaison n'est jamais "
                        "approuvable : il n'exécute pas les contrôles obligatoires C-001 à C-012 "
                        "du moteur principal."
                    ),
                    reference="ADR-003",
                ),
            ),
        )
