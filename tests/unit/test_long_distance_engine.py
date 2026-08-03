"""Cas de validation intégrés du moteur longue distance.

Les résultats sont comparés aux bilans analytiques de Darcy-Weisbach et aux conditions
aux limites imposées. Les tests couvrent les trois modes de résolution du moteur.
"""

from __future__ import annotations

import math

import pytest
from tests.factories import (
    ATMOSPHERE_PA,
    bac,
    brut_leger,
    entree_canonique,
    pipeline,
    profil_plat,
    scenario,
    segment,
    station_serie,
)

from hydro_domain import (
    ElevationProfile,
    InjectionPoint,
    Pipeline,
    PumpOverride,
    SegmentOverride,
    SolverOptions,
)
from hydro_shared.codes import SimulationStatus, ViolationCode, WarningCode
from hydroliquid import LongDistanceLiquidEngine
from hydroliquid.hydraulics import G, friction_head_loss_m


def test_marche_directe_reproduit_darcy_weisbach():
    conduit = pipeline(
        segments=(
            segment(
                longueur_m=10_000.0,
                diametre_m=0.5,
                maop_pa=10.0e6,
            ),
        ),
        profil=profil_plat(10_000.0, 100.0),
    )
    cas = scenario(
        imposed_flow_m3_s=0.1,
        inlet_pressure_pa=5.0e6,
        options=SolverOptions(profile_step_m=2_000.0),
    )
    fluid = brut_leger()
    result = LongDistanceLiquidEngine().simulate(
        entree_canonique(conduite=conduit, fluide=fluid, cas=cas)
    )

    expected_loss = friction_head_loss_m(
        0.1,
        10_000.0,
        0.5,
        4.5e-5,
        9.0e-6,
    )
    expected_outlet = 5.0e6 - 875.0 * G * expected_loss
    assert result.status.has_results
    assert result.flow_m3_s == pytest.approx(0.1)
    assert result.total_head_loss_m == pytest.approx(expected_loss, rel=1e-12)
    assert result.profile[-1].pressure_pa == pytest.approx(expected_outlet, rel=1e-12)
    assert result.segments[0].outlet_pressure_pa == pytest.approx(expected_outlet)
    assert result.diagnostics.method == "marche directe"
    assert result.diagnostics.iterations == 1
    assert result.diagnostics.mass_balance_ok
    assert result.input_hash


def test_debit_impose_et_pression_aval_resolvent_pression_amont():
    cas = scenario(
        imposed_flow_m3_s=0.1,
        outlet_pressure_pa=2.0e6,
        options=SolverOptions(
            profile_step_m=5_000.0,
            pressure_tolerance_pa=0.01,
            store_iterations=True,
        ),
    )
    result = LongDistanceLiquidEngine().simulate(
        entree_canonique(
            conduite=pipeline(
                segments=(segment(longueur_m=10_000.0),),
                profil=profil_plat(10_000.0),
            ),
            cas=cas,
        )
    )

    assert result.status.has_results
    assert result.profile[-1].pressure_pa == pytest.approx(2.0e6, abs=0.01)
    assert result.profile[0].pressure_pa > result.profile[-1].pressure_pa
    assert result.diagnostics.converged
    assert result.diagnostics.iterations >= 1


def test_debit_inconnu_resout_deux_pressions():
    cas = scenario(
        inlet_pressure_pa=5.0e6,
        outlet_pressure_pa=4.0e6,
        options=SolverOptions(
            profile_step_m=2_000.0,
            pressure_tolerance_pa=0.1,
            max_flow_m3_s=2.0,
        ),
    )
    result = LongDistanceLiquidEngine().simulate(
        entree_canonique(
            conduite=pipeline(
                segments=(segment(longueur_m=10_000.0),),
                profil=profil_plat(10_000.0),
            ),
            cas=cas,
        )
    )

    assert result.status.has_results
    assert 0.0 < result.flow_m3_s < 2.0
    assert result.profile[0].pressure_pa == pytest.approx(5.0e6)
    assert result.profile[-1].pressure_pa == pytest.approx(4.0e6, abs=0.1)
    assert result.diagnostics.converged


def test_probleme_sous_contraint_retourne_entree_invalide():
    cas = scenario(imposed_flow_m3_s=0.1)
    result = LongDistanceLiquidEngine().simulate(entree_canonique(cas=cas))

    assert result.status is SimulationStatus.INVALID_INPUT
    assert not result.profile
    assert result.violations
    assert any("sous-contraint" in violation.message for violation in result.violations)


def test_conditions_physiquement_impossibles_retournent_un_statut():
    cas = scenario(
        inlet_pressure_pa=1.0e5,
        outlet_pressure_pa=5.0e6,
        options=SolverOptions(max_flow_m3_s=1.0),
    )
    result = LongDistanceLiquidEngine().simulate(entree_canonique(cas=cas))

    assert result.status is SimulationStatus.NO_PHYSICAL_SOLUTION
    assert not result.profile
    assert result.violations[0].code is ViolationCode.RESIDUAL_ABOVE_TOLERANCE
    assert result.diagnostics.messages


def test_conditions_de_bacs_resolvent_le_debit_gravitaire():
    origin = bac(
        identifiant="B-AMONT",
        diametre_m=20.0,
        hauteur_m=12.0,
        niveau_m=8.0,
        altitude_m=0.0,
    )
    destination = bac(
        identifiant="B-AVAL",
        diametre_m=20.0,
        hauteur_m=12.0,
        niveau_m=2.0,
        altitude_m=0.0,
    )
    conduit = pipeline(
        segments=(segment(longueur_m=1_000.0, diametre_m=0.5),),
        profil=profil_plat(1_000.0, 0.0),
        origin_tank=origin,
        destination_tank=destination,
    )
    cas = scenario(
        inlet_tank_level_m=8.0,
        outlet_tank_level_m=2.0,
        options=SolverOptions(
            profile_step_m=100.0,
            pressure_tolerance_pa=0.1,
            max_flow_m3_s=1.0,
        ),
    )
    result = LongDistanceLiquidEngine().simulate(entree_canonique(conduite=conduit, cas=cas))

    assert result.status.has_results
    assert result.flow_m3_s > 0
    assert result.profile[0].pressure_pa == pytest.approx(ATMOSPHERE_PA + 875.0 * G * 8.0)
    assert result.profile[-1].pressure_pa == pytest.approx(
        ATMOSPHERE_PA + 875.0 * G * 2.0,
        abs=0.1,
    )
    assert any("Aucune pompe" in warning.message for warning in result.warnings)


def test_station_serie_augmente_charge_et_calcule_energie():
    station = station_serie(
        identifiant="S1",
        chainage_m=0.0,
        altitude_m=100.0,
        nombre_de_pompes=2,
    )
    conduit = pipeline(
        segments=(segment(longueur_m=10_000.0),),
        profil=profil_plat(10_000.0, 100.0),
        stations=(station,),
    )
    cas = scenario(imposed_flow_m3_s=0.4, inlet_pressure_pa=1.0e6)
    engine = LongDistanceLiquidEngine()
    result = engine.simulate(entree_canonique(conduite=conduit, cas=cas))

    assert result.status.has_results
    assert len(result.stations) == 1
    assert result.stations[0].active_pump_count == 2
    assert result.stations[0].head_m > 0
    assert result.stations[0].discharge_pressure_pa > 1.0e6
    assert len(result.stations[0].pumps) == 2
    assert result.energy is not None
    assert result.energy.total_absorbed_power_w is not None
    assert result.energy.total_absorbed_power_w > 0
    explanation = engine.explain(result)
    assert explanation.assumptions
    assert explanation.methods
    assert "Scénario" in explanation.summary


def test_surcharge_pompe_ne_modifie_pas_baseline():
    station = station_serie(
        identifiant="S1",
        chainage_m=0.0,
        altitude_m=100.0,
        nombre_de_pompes=2,
    )
    conduit = pipeline(
        segments=(segment(longueur_m=5_000.0),),
        profil=profil_plat(5_000.0, 100.0),
        stations=(station,),
    )
    baseline = scenario(imposed_flow_m3_s=0.4, inlet_pressure_pa=1.0e6)
    degraded = scenario(
        imposed_flow_m3_s=0.4,
        inlet_pressure_pa=1.0e6,
        pump_overrides=(PumpOverride(pump_id="S1-P2", running=False),),
    )
    engine = LongDistanceLiquidEngine()
    normal = engine.simulate(entree_canonique(conduite=conduit, cas=baseline))
    reduced = engine.simulate(entree_canonique(conduite=conduit, cas=degraded))

    assert normal.stations[0].active_pump_count == 2
    assert reduced.stations[0].active_pump_count == 1
    assert reduced.stations[0].head_m < normal.stations[0].head_m
    assert station.active_pumps[1].is_active


def test_surcharge_perte_singuliere_abaisse_pression_aval():
    conduit = pipeline(
        segments=(segment(longueur_m=2_000.0),),
        profil=profil_plat(2_000.0),
    )
    baseline = scenario(imposed_flow_m3_s=0.2, inlet_pressure_pa=5.0e6)
    obstructed = scenario(
        imposed_flow_m3_s=0.2,
        inlet_pressure_pa=5.0e6,
        segment_overrides=(SegmentOverride(segment_id="T1", additional_k=20.0),),
    )
    engine = LongDistanceLiquidEngine()
    reference = engine.simulate(entree_canonique(conduite=conduit, cas=baseline))
    modified = engine.simulate(entree_canonique(conduite=conduit, cas=obstructed))

    assert modified.profile[-1].pressure_pa < reference.profile[-1].pressure_pa
    assert modified.segments[0].minor_head_loss_m > 0
    assert conduit.segments[0].fittings == ()


def test_injection_intermediaire_conserve_la_masse():
    conduit = Pipeline(
        id="PL-INJ",
        name="Pipeline avec injection",
        segments=(segment(longueur_m=2_000.0),),
        profile=profil_plat(2_000.0),
        injections=(InjectionPoint(id="INJ-1", chainage_m=1_000.0, flow_m3_s=0.05),),
    )
    cas = scenario(
        imposed_flow_m3_s=0.1,
        inlet_pressure_pa=5.0e6,
        options=SolverOptions(profile_step_m=500.0),
    )
    result = LongDistanceLiquidEngine().simulate(entree_canonique(conduite=conduit, cas=cas))

    assert result.status.has_results
    assert result.profile[0].flow_m3_s == pytest.approx(0.1)
    assert result.profile[-1].flow_m3_s == pytest.approx(0.15)
    assert result.diagnostics.mass_balance_residual == pytest.approx(0.0, abs=1e-12)
    assert not any(violation.code is ViolationCode.MASS_BALANCE for violation in result.violations)


def test_depression_detectee_et_mode_gravitaire_explicite():
    profile = ElevationProfile.from_pairs([(0.0, 0.0), (500.0, 200.0), (1_000.0, 0.0)])
    conduit = pipeline(
        segments=(segment(longueur_m=1_000.0),),
        profil=profile,
    )
    conservative = scenario(
        imposed_flow_m3_s=0.01,
        inlet_pressure_pa=150_000.0,
        options=SolverOptions(profile_step_m=500.0),
    )
    gravity = scenario(
        imposed_flow_m3_s=0.01,
        inlet_pressure_pa=150_000.0,
        options=SolverOptions(
            profile_step_m=500.0,
            apply_gravity_model=True,
        ),
    )
    engine = LongDistanceLiquidEngine()
    conservative_result = engine.simulate(entree_canonique(conduite=conduit, cas=conservative))
    gravity_result = engine.simulate(entree_canonique(conduite=conduit, cas=gravity))

    assert conservative_result.gravity_zones
    assert any(
        violation.code is ViolationCode.PRESSURE_BELOW_VAPOR
        for violation in conservative_result.violations
    )
    assert gravity_result.gravity_zones
    assert min(point.pressure_pa for point in gravity_result.profile) == pytest.approx(10_000.0)
    assert any(
        warning.code is WarningCode.GRAVITY_FLOW_SUSPECTED for warning in gravity_result.warnings
    )


def test_regime_de_transition_est_signale():
    diameter = 0.5
    nu = 9.0e-6
    velocity = 3_000.0 * nu / diameter
    flow = velocity * math.pi * diameter**2 / 4.0
    conduit = pipeline(
        segments=(segment(longueur_m=100.0, diametre_m=diameter),),
        profil=profil_plat(100.0),
    )
    cas = scenario(
        imposed_flow_m3_s=flow,
        inlet_pressure_pa=1.0e6,
        options=SolverOptions(profile_step_m=50.0),
    )

    result = LongDistanceLiquidEngine().simulate(entree_canonique(conduite=conduit, cas=cas))

    assert any(warning.code is WarningCode.TRANSITION_REGIME for warning in result.warnings)
