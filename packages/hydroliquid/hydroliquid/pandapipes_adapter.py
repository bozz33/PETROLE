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

import time
from importlib.util import find_spec

from hydro_domain.canonical import CanonicalInput
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
from hydroliquid.hydraulics import G, velocity_m_s

#: Vrai si pandapipes est disponible dans l'environnement.
PANDAPIPES_AVAILABLE = find_spec("pandapipes") is not None


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
    version = "0.1.0"

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
        active_stations = [s for s in pipeline.stations if s.is_in_service and s.active_pumps]
        if active_stations:
            reasons.append(
                f"{len(active_stations)} station(s) de pompage active(s) : le modèle de pompe de "
                f"pandapipes ne reproduit pas le partage de débit entre groupes série et "
                f"parallèle du moteur longue distance."
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

        import pandapipes as pp

        from hydroliquid.properties import FluidPropertyProvider

        pipeline = canonical_input.pipeline
        provider = FluidPropertyProvider(canonical_input.fluid)
        temperature = scenario.temperature_k or canonical_input.fluid.reference_temperature_k
        state = provider.resolve(temperature, scenario.inlet_pressure_pa)

        net = pp.create_empty_network(fluid="water")
        # Le fluide est redéfini par ses propriétés réelles : pandapipes travaille avec un
        # fluide nommé, mais accepte des propriétés constantes fournies explicitement.
        pp.create_constant_property(net, "density", state.density_kg_m3, overwrite=True)
        pp.create_constant_property(net, "viscosity", state.dynamic_viscosity_pa_s, overwrite=True)

        junctions: list[int] = []
        for index, chainage in enumerate(
            [pipeline.start_chainage_m] + [s.end_chainage_m for s in pipeline.segments]
        ):
            junctions.append(
                pp.create_junction(
                    net,
                    pn_bar=scenario.inlet_pressure_pa / 1e5,
                    tfluid_k=temperature,
                    height_m=pipeline.elevation_at(chainage),
                    name=f"J{index}",
                )
            )

        for index, segment in enumerate(pipeline.segments):
            pp.create_pipe_from_parameters(
                net,
                from_junction=junctions[index],
                to_junction=junctions[index + 1],
                length_km=segment.length_m / 1000.0,
                diameter_m=segment.inner_diameter_m,
                k_mm=segment.roughness_m * 1000.0,
                loss_coefficient=segment.total_fitting_k(),
                name=segment.label or segment.id,
            )

        pp.create_ext_grid(
            net, junction=junctions[0], p_bar=scenario.inlet_pressure_pa / 1e5, t_k=temperature
        )
        pp.create_sink(
            net,
            junction=junctions[-1],
            mdot_kg_per_s=scenario.imposed_flow_m3_s * state.density_kg_m3,
        )

        pp.pipeflow(net, friction_model="colebrook", mode="hydraulics")

        diagnostics.converged = bool(net.converged)
        diagnostics.iterations = 0
        diagnostics.residual = 0.0
        diagnostics.tolerance = scenario.solver.pressure_tolerance_pa
        diagnostics.elapsed_s = time.perf_counter() - started

        points: list[ProfilePointResult] = []
        segments_results: list[SegmentResult] = []
        for index, segment in enumerate(pipeline.segments):
            inlet_bar = float(net.res_junction.p_bar.iloc[junctions[index]])
            outlet_bar = float(net.res_junction.p_bar.iloc[junctions[index + 1]])
            velocity = velocity_m_s(scenario.imposed_flow_m3_s, segment.inner_diameter_m)
            head_loss = (inlet_bar - outlet_bar) * 1e5 / (state.density_kg_m3 * G)
            segments_results.append(
                SegmentResult(
                    segment_id=segment.id,
                    label=segment.label,
                    flow_m3_s=scenario.imposed_flow_m3_s,
                    velocity_m_s=velocity,
                    reynolds=float(net.res_pipe.reynolds.iloc[index]),
                    friction_factor=float(net.res_pipe.lambda_.iloc[index]),
                    friction_model="colebrook (pandapipes)",
                    friction_head_loss_m=head_loss,
                    minor_head_loss_m=0.0,
                    elevation_change_m=pipeline.profile.elevation_change(
                        segment.start_chainage_m, segment.end_chainage_m
                    ),
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
                    + inlet_bar * 1e5 / (state.density_kg_m3 * G),
                    flow_m3_s=scenario.imposed_flow_m3_s,
                    velocity_m_s=velocity,
                    below_vapor_pressure=inlet_bar * 1e5 <= state.vapor_pressure_pa,
                )
            )

        last = pipeline.segments[-1]
        outlet_bar = float(net.res_junction.p_bar.iloc[junctions[-1]])
        points.append(
            ProfilePointResult(
                chainage_m=last.end_chainage_m,
                elevation_m=pipeline.elevation_at(last.end_chainage_m),
                pressure_pa=outlet_bar * 1e5,
                hydraulic_grade_m=pipeline.elevation_at(last.end_chainage_m)
                + outlet_bar * 1e5 / (state.density_kg_m3 * G),
                flow_m3_s=scenario.imposed_flow_m3_s,
                velocity_m_s=velocity_m_s(scenario.imposed_flow_m3_s, last.inner_diameter_m),
                below_vapor_pressure=outlet_bar * 1e5 <= state.vapor_pressure_pa,
            )
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
                "engine_role": (
                    "Moteur secondaire de comparaison. Les résultats servent au benchmark du "
                    "moteur longue distance, pas à la production d'une note de calcul approuvée."
                ),
            },
            environment=engine_fingerprint(),
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
