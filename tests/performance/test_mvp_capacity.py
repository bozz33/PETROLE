"""Essais de capacité et de durée annoncées pour le backend MVP.

Les seuils viennent de la documentation maître § 12.1. Ils sont volontairement exécutables
avec la campagne locale normale : une régression de complexité doit être détectée avant une
livraison, même lorsque l'intégration continue distante est indisponible.
"""

from __future__ import annotations

import copy
import math
import time
import tracemalloc
from datetime import UTC, datetime
from io import BytesIO

import pytest
from pypdf import PdfReader

from hydro_domain import (
    CanonicalInput,
    ElevationProfile,
    Fluid,
    FluidCategory,
    ObjectiveKind,
    Pipeline,
    PipeSegment,
    PumpCurve,
    PumpInstance,
    PumpModel,
    Scenario,
    SolverOptions,
    build_series_station,
)
from hydro_optimization import (
    CandidateEvaluation,
    ExhaustivePumpOptimizer,
    OptimizationConstraints,
    OptimizationRequest,
    OptimizationStatus,
)
from hydro_reporting import HydraulicReportData, build_hydraulic_calculation_pdf
from hydroliquid import LongDistanceLiquidEngine

pytestmark = pytest.mark.performance


def _capacity_input(segment_count: int, station_count: int = 50) -> CanonicalInput:
    """Construit un cas synthétique régulier sans masquer le coût des objets métier."""

    segment_length_m = 100.0
    total_length_m = segment_count * segment_length_m
    segments = tuple(
        PipeSegment(
            id=f"T{index:04d}",
            sequence=index,
            length_m=segment_length_m,
            inner_diameter_m=0.8,
            roughness_m=4.5e-5,
            start_chainage_m=(index - 1) * segment_length_m,
            maop_pa=10.0e6,
        )
        for index in range(1, segment_count + 1)
    )
    profile = ElevationProfile.from_pairs([(0.0, 100.0), (total_length_m, 120.0)])
    curve = PumpCurve(
        [0.05, 0.2, 0.5],
        [7.0, 6.0, 3.0],
        efficiencies=[0.70, 0.82, 0.75],
        npshr_m=[2.0, 3.0, 5.0],
    )
    pump_model = PumpModel(
        id="PMP-CAPACITE",
        name="Pompe du cas de capacité",
        curve=curve,
        motor_rated_power_w=2.0e6,
    )
    station_spacing_m = total_length_m / station_count
    stations = tuple(
        build_series_station(
            f"S{index:02d}",
            f"Station {index}",
            float(chainage_m),
            profile.elevation_at(float(chainage_m)),
            (PumpInstance(id=f"P{index:02d}", model=pump_model),),
        )
        for index, chainage_m in enumerate(
            (station_spacing_m * index for index in range(station_count)),
            start=1,
        )
    )
    pipeline = Pipeline(
        id="PL-CAPACITE-1000",
        name="Pipeline de capacité MVP",
        segments=segments,
        profile=profile,
        stations=stations,
    )
    fluid = Fluid(
        id="FL-CAPACITE",
        name="Fluide du cas de capacité",
        category=FluidCategory.CRUDE,
        density_kg_m3=875.0,
        kinematic_viscosity_m2_s=9.0e-6,
        vapor_pressure_pa=10_000.0,
    )
    scenario = Scenario(
        id="SC-CAPACITE-1000",
        name="Simulation de capacité MVP",
        imposed_flow_m3_s=0.2,
        inlet_pressure_pa=2.0e6,
        solver=SolverOptions(profile_step_m=1_000.0),
    )
    return CanonicalInput(
        pipeline=pipeline,
        fluid=fluid,
        scenario=scenario,
        engine="long_distance_liquid",
    )


def _stable_result_payload(result) -> dict:
    """Retire uniquement mesures temporelles et empreinte de machine non scientifiques."""

    payload = copy.deepcopy(result.as_dict())
    payload.pop("environment", None)
    diagnostics = payload.get("diagnostics", {})
    diagnostics.pop("elapsed_s", None)
    return payload


def test_pipeline_de_mille_troncons_et_cinquante_stations_sous_dix_secondes() -> None:
    """La taille maximale annoncée doit converger sous la cible d'une simulation standard."""
    canonical_input = _capacity_input(1_000)

    started = time.perf_counter()
    result = LongDistanceLiquidEngine().simulate(canonical_input)
    duration_s = time.perf_counter() - started

    assert result.status.has_results
    assert result.is_feasible
    assert len(result.segments) == 1_000
    assert len(result.stations) == 50
    assert len(result.profile) == 1_001
    assert result.diagnostics.residual <= result.diagnostics.tolerance
    assert duration_s < 10.0


@pytest.mark.qualification
@pytest.mark.slow
def test_p95_de_vingt_calculs_de_mille_troncons_reste_sous_dix_secondes() -> None:
    """NFR-PERF-001 exige un percentile 95, pas une mesure unique favorable."""

    canonical_input = _capacity_input(1_000)
    durations: list[float] = []
    engine = LongDistanceLiquidEngine()
    for _ in range(20):
        started = time.perf_counter()
        result = engine.simulate(canonical_input)
        durations.append(time.perf_counter() - started)
        assert result.status.has_results

    ordered = sorted(durations)
    p95_s = ordered[math.ceil(0.95 * len(ordered)) - 1]
    print(f"P95_1000_TRONCONS_S={p95_s:.6f}")
    assert p95_s < 10.0


@pytest.mark.qualification
def test_dix_repetitions_produisent_un_resultat_scientifique_identique() -> None:
    """NFR-SCI-002 et D05 § 12 imposent dix répétitions déterministes."""

    canonical_input = _capacity_input(100, station_count=5)
    payloads = [
        _stable_result_payload(LongDistanceLiquidEngine().simulate(canonical_input))
        for _ in range(10)
    ]
    assert all(payload == payloads[0] for payload in payloads[1:])


@pytest.mark.qualification
@pytest.mark.slow
def test_reseau_de_dix_mille_troncons_mesure_temps_et_memoire() -> None:
    """D18 § 8 demande une mesure à 10 000 tronçons, sans seuil contractuel propre."""

    canonical_input = _capacity_input(10_000)
    tracemalloc.start()
    started = time.perf_counter()
    result = LongDistanceLiquidEngine().simulate(canonical_input)
    duration_s = time.perf_counter() - started
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"DUREE_10000_TRONCONS_S={duration_s:.6f}")
    print(f"MEMOIRE_10000_TRONCONS_MIO={peak_bytes / 1024**2:.3f}")
    assert result.status.has_results
    assert len(result.segments) == 10_000
    assert duration_s < 120.0
    assert peak_bytes < 1_500 * 1024**2


@pytest.mark.qualification
def test_cent_configurations_simples_sous_cent_vingt_secondes() -> None:
    """NFR-PERF-002 mesure cent simulations distinctes, pas deux résultats persistés."""

    base = _capacity_input(100, station_count=5)
    started = time.perf_counter()
    results = []
    for index in range(100):
        flow_m3_s = 0.05 + index * 0.001
        scenario = Scenario(
            id=f"SC-CONFIG-{index:03d}",
            name=f"Configuration {index}",
            imposed_flow_m3_s=flow_m3_s,
            inlet_pressure_pa=2.0e6,
            solver=SolverOptions(profile_step_m=1_000.0),
        )
        results.append(
            LongDistanceLiquidEngine().simulate(
                CanonicalInput(
                    pipeline=base.pipeline,
                    fluid=base.fluid,
                    scenario=scenario,
                    engine="long_distance_liquid",
                )
            )
        )
    duration_s = time.perf_counter() - started

    print(f"DUREE_100_CONFIGURATIONS_S={duration_s:.6f}")
    assert all(result.status.has_results for result in results)
    assert duration_s < 120.0


@pytest.mark.qualification
@pytest.mark.slow
def test_rapport_de_mille_troncons_reste_exploitable() -> None:
    """D18 § 8 exige de mesurer un rapport volumineux, sa durée et sa taille."""

    canonical_input = _capacity_input(1_000)
    result = LongDistanceLiquidEngine().simulate(canonical_input)
    data = HydraulicReportData(
        report_id="00000000-0000-0000-0000-000000001000",
        calculation_id="00000000-0000-0000-0000-000000002000",
        project_name="Qualification de capacité",
        project_code="QUAL-1000",
        model_name="Réseau de mille tronçons",
        model_version=1,
        scenario_name="Débit nominal",
        generated_at=datetime(2026, 8, 3, tzinfo=UTC),
        input_payload=canonical_input.as_dict(),
        result_payload=result.as_dict(),
    )

    started = time.perf_counter()
    content = build_hydraulic_calculation_pdf(data)
    duration_s = time.perf_counter() - started
    reader = PdfReader(BytesIO(content))

    print(f"DUREE_RAPPORT_1000_TRONCONS_S={duration_s:.6f}")
    print(f"TAILLE_RAPPORT_1000_TRONCONS_OCTETS={len(content)}")
    print(f"PAGES_RAPPORT_1000_TRONCONS={len(reader.pages)}")
    assert content.startswith(b"%PDF-")
    assert len(reader.pages) >= 10
    assert duration_s < 60.0
    assert len(content) < 25_000_000


def test_optimisation_bornee_de_65535_configurations_sous_cinq_minutes() -> None:
    """L'optimiseur initial doit terminer un espace discret borné et prouver l'optimum."""
    pump_ids = tuple(f"P{index}" for index in range(1, 9))
    request = OptimizationRequest(
        pump_ids=pump_ids,
        speed_options=(0.8, 0.9, 1.0),
        objective=ObjectiveKind.MIN_ENERGY,
        constraints=OptimizationConstraints(minimum_flow_m3_s=0.8),
        maximum_configurations=100_000,
    )

    def evaluate(configuration) -> CandidateEvaluation:
        total_speed = sum(ratio for _, ratio in configuration.speed_ratios)
        return CandidateEvaluation(
            flow_m3_s=0.15 * total_speed,
            energy_kwh=10.0 * total_speed,
            minimum_pressure_pa=2.0e5,
            maximum_pressure_pa=5.0e6,
        )

    started = time.perf_counter()
    result = ExhaustivePumpOptimizer().optimize(request, evaluate)
    duration_s = time.perf_counter() - started

    assert result.status is OptimizationStatus.OPTIMAL
    assert result.complete
    assert result.generated_count == 65_535
    assert result.evaluated_count == 65_535
    assert result.optimality_gap == 0.0
    assert duration_s < 300.0
