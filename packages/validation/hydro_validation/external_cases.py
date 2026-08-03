"""Benchmarks externes reproductibles du moteur liquide.

Les valeurs de référence ne proviennent pas des équations internes de HydroLiquid. Elles sont
issues de réseaux distribués avec pandapipes 0.14.0 et du rapport officiel de validation DWSIM
du 3 mai 2026. Les données complètes de provenance sont conservées dans
``datasets/reference_cases/external_benchmarks_v1.json``.

Le premier cas STANET se situe dans la zone de transition hydraulique. STANET y applique
directement Prandtl-Colebrook, tandis que HydroLiquid interpole entre les régimes laminaire et
turbulent. Ce cas est donc classé comme écart de modèle expliqué au sens D10 § 12, avec une
tolérance spécifique visible dans le dossier de preuve. Il ne doit pas être présenté comme une
égalité entre modèles.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial

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
    SolverOptions,
)
from hydro_domain.pumps import absorbed_power_w, hydraulic_power_w
from hydro_validation.models import ValidationCase, ValidationObservation
from hydroliquid import G, LongDistanceLiquidEngine


@dataclass(frozen=True, slots=True)
class ExternalPipeReference:
    """Entrées minimales d'un réseau externe à conduite unique."""

    identifier: str
    reference_system: str
    temperature_k: float
    density_kg_m3: float
    dynamic_viscosity_pa_s: float
    length_m: float
    diameter_m: float
    roughness_m: float
    mass_flow_kg_s: float
    inlet_pressure_bar: float
    outlet_pressure_bar: float
    relative_tolerance: float
    detail: str | None = None

    @property
    def flow_m3_s(self) -> float:
        return self.mass_flow_kg_s / self.density_kg_m3

    @property
    def reference_pressure_drop_pa(self) -> float:
        return abs(self.inlet_pressure_bar - self.outlet_pressure_bar) * 1.0e5


PANDAPIPES_REFERENCES: tuple[ExternalPipeReference, ...] = (
    ExternalPipeReference(
        "EXT-PP-STANET-01",
        "STANET, réseau pandapipes water_one_pipe1, Prandtl-Colebrook",
        283.15,
        1_000.0,
        1.793e-3,
        2_000.0,
        0.075,
        1.0e-4,
        0.277777777777778,
        5.0,
        4.9755,
        0.30,
        (
            "Écart de modèle B : Re≈2630. STANET applique Prandtl-Colebrook turbulent ; "
            "HydroLiquid interpole entre les régimes laminaire et turbulent."
        ),
    ),
    ExternalPipeReference(
        "EXT-PP-OM-01",
        "OpenModelica, réseau pandapipes water_one_pipe1, Prandtl-Colebrook",
        293.15,
        998.2060924679472,
        1.001605325647912e-3,
        2_000.0,
        0.075,
        1.0e-4,
        1.3821,
        5.0,
        4.636695205386038,
        0.002,
    ),
    ExternalPipeReference(
        "EXT-PP-STANET-02",
        "STANET, réseau pandapipes water_one_pipe2, Prandtl-Colebrook",
        283.15,
        1_000.0,
        1.793e-3,
        10_000.0,
        0.075,
        1.0e-4,
        1.325277777777778,
        5.0,
        3.1228,
        0.002,
    ),
    ExternalPipeReference(
        "EXT-PP-OM-02",
        "OpenModelica, réseau pandapipes water_one_pipe2, Prandtl-Colebrook",
        293.15,
        998.2060924679472,
        1.001605325647912e-3,
        10_000.0,
        0.075,
        1.0e-4,
        1.325,
        5.0,
        3.318369155192938,
        0.002,
    ),
    ExternalPipeReference(
        "EXT-PP-STANET-03",
        "STANET, réseau pandapipes water_one_pipe3, Prandtl-Colebrook",
        283.15,
        1_000.0,
        1.793e-3,
        3_000.0,
        0.075,
        1.0e-4,
        0.555555555555556,
        7.0,
        6.8787,
        0.002,
    ),
    ExternalPipeReference(
        "EXT-PP-OM-03",
        "OpenModelica, réseau pandapipes water_one_pipe3, Prandtl-Colebrook",
        293.15,
        998.2060924679472,
        1.001605325647912e-3,
        3_000.0,
        0.075,
        1.0e-4,
        0.56,
        7.0,
        6.893021940086651,
        0.002,
    ),
)


def _run_pipe_reference(reference: ExternalPipeReference) -> tuple[ValidationObservation, ...]:
    """Rejoue un réseau tiers dans le moteur principal HydroLiquid."""

    pipeline = Pipeline(
        id=f"PL-{reference.identifier}",
        name=reference.reference_system,
        segments=(
            PipeSegment(
                id="T1",
                sequence=1,
                length_m=reference.length_m,
                inner_diameter_m=reference.diameter_m,
                roughness_m=reference.roughness_m,
                start_chainage_m=0.0,
            ),
        ),
        profile=ElevationProfile.from_pairs([(0.0, 0.0), (reference.length_m, 0.0)]),
    )
    fluid = Fluid(
        id=f"FL-{reference.identifier}",
        name="Eau du cas de référence externe",
        reference_temperature_k=reference.temperature_k,
        density_kg_m3=reference.density_kg_m3,
        kinematic_viscosity_m2_s=(reference.dynamic_viscosity_pa_s / reference.density_kg_m3),
        vapor_pressure_pa=2_000.0,
        data_source=reference.reference_system,
    )
    scenario = Scenario(
        id=f"SC-{reference.identifier}",
        name=reference.identifier,
        imposed_flow_m3_s=reference.flow_m3_s,
        inlet_pressure_pa=reference.inlet_pressure_bar * 1.0e5,
        solver=SolverOptions(
            pressure_tolerance_pa=0.1,
            profile_step_m=reference.length_m,
        ),
    )
    result = LongDistanceLiquidEngine().simulate(
        CanonicalInput(
            pipeline=pipeline,
            fluid=fluid,
            scenario=scenario,
            engine="long_distance_liquid",
        )
    )
    pressure_drop_pa = result.total_head_loss_m * reference.density_kg_m3 * G
    return (
        ValidationObservation(
            name="Perte de pression HydroLiquid comparée à la référence externe",
            actual=pressure_drop_pa,
            expected=reference.reference_pressure_drop_pa,
            unit="Pa",
            relative_tolerance=reference.relative_tolerance,
            detail=reference.detail,
        ),
    )


def _dwsim_pump_u03() -> tuple[ValidationObservation, ...]:
    """Reproduit le cas U03 du rapport officiel de validation DWSIM."""

    density_kg_m3 = 997.0
    mass_flow_kg_s = 1.0
    pressure_increase_pa = 1.0e6
    efficiency = 0.75
    flow_m3_s = mass_flow_kg_s / density_kg_m3
    head_m = pressure_increase_pa / (density_kg_m3 * G)
    curve = PumpCurve(
        [0.0, flow_m3_s, 2.0 * flow_m3_s],
        [1.10 * head_m, head_m, 0.75 * head_m],
        efficiencies=[0.70, efficiency, 0.72],
    )
    pump = PumpInstance(
        id="P-DWSIM-U03",
        model=PumpModel(
            id="PM-DWSIM-U03",
            name="Pompe du cas DWSIM U03",
            curve=curve,
            data_source="DWSIM Validation Report, U03, 3 mai 2026",
        ),
    )
    evaluation = pump.evaluate(flow_m3_s)
    if evaluation.efficiency is None:
        raise RuntimeError("Le rendement du point de référence DWSIM est indisponible.")
    power_w = absorbed_power_w(
        hydraulic_power_w(flow_m3_s, evaluation.head_m, density_kg_m3),
        evaluation.efficiency,
    )
    return (
        ValidationObservation(
            name="Augmentation de pression",
            actual=density_kg_m3 * G * evaluation.head_m,
            expected=pressure_increase_pa,
            unit="Pa",
            relative_tolerance=1.0e-3,
        ),
        ValidationObservation(
            name="Puissance absorbée",
            actual=power_w,
            expected=1_337.345,
            unit="W",
            relative_tolerance=0.05,
            detail="Référence DWSIM U03 : eau 1 kg/s, ΔP=10 bar, rendement 75 %.",
        ),
    )


EXTERNAL_CASES: tuple[ValidationCase, ...] = (
    *(
        ValidationCase(
            reference.identifier,
            f"Réseau tiers {reference.reference_system}",
            "benchmark externe",
            reference.reference_system,
            partial(_run_pipe_reference, reference),
        )
        for reference in PANDAPIPES_REFERENCES
    ),
    ValidationCase(
        "EXT-DWSIM-U03",
        "Pompe eau, débit massique 1 kg/s et élévation de pression 10 bar",
        "benchmark externe",
        "DWSIM Validation Report 2026-05-03, cas U03",
        _dwsim_pump_u03,
    ),
)


__all__ = ["EXTERNAL_CASES", "PANDAPIPES_REFERENCES", "ExternalPipeReference"]
