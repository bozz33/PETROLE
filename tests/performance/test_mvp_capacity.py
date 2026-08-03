"""Essais de capacité et de durée annoncées pour le backend MVP.

Les seuils viennent de la documentation maître § 12.1. Ils sont volontairement exécutables
avec la campagne locale normale : une régression de complexité doit être détectée avant une
livraison, même lorsque l'intégration continue distante est indisponible.
"""

from __future__ import annotations

import time

import pytest

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
from hydroliquid import LongDistanceLiquidEngine

pytestmark = pytest.mark.performance


def test_pipeline_de_mille_troncons_et_cinquante_stations_sous_dix_secondes() -> None:
    """La taille maximale annoncée doit converger sous la cible d'une simulation standard."""
    segment_count = 1_000
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
    stations = tuple(
        build_series_station(
            f"S{index:02d}",
            f"Station {index}",
            float(chainage_m),
            profile.elevation_at(float(chainage_m)),
            (PumpInstance(id=f"P{index:02d}", model=pump_model),),
        )
        for index, chainage_m in enumerate(range(0, 100_000, 2_000), start=1)
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
    canonical_input = CanonicalInput(
        pipeline=pipeline,
        fluid=fluid,
        scenario=scenario,
        engine="long_distance_liquid",
    )

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
