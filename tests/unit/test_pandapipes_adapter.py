"""Preuve de concept du moteur secondaire pandapipes (POC-OS-04).

Ces essais vérifient la traduction vers l'API pandapipes réellement supportée, la cohérence
avec HydroLiquid Core sur les cas communs et le refus explicite des modèles que l'adaptateur
ne représente pas fidèlement.
"""

from __future__ import annotations

import pytest
from tests.factories import (
    accessoire,
    entree_canonique,
    pipeline,
    profil_incline,
    profil_plat,
    scenario,
    segment,
    station_serie,
)

from hydro_domain import (
    CanonicalInput,
    ElevationProfile,
    FrictionModel,
    InjectionPoint,
    SolverOptions,
)
from hydro_shared.codes import SimulationStatus
from hydro_shared.errors import UnsupportedCaseError
from hydroliquid.long_distance import LongDistanceLiquidEngine
from hydroliquid.pandapipes_adapter import PandapipesEngine

pytest.importorskip("pandapipes", minversion="0.14")


def test_conduite_horizontale_coherente_avec_le_moteur_principal() -> None:
    """Pression, frottement et pertes singulières doivent rester comparables."""
    troncon = segment(
        longueur_m=10_000.0,
        diametre_m=0.5,
        fittings=(accessoire(k=1.7),),
    )
    entree = entree_canonique(
        conduite=pipeline(segments=(troncon,), profil=profil_plat(10_000.0)),
        cas=scenario(imposed_flow_m3_s=0.2, inlet_pressure_pa=5.0e6),
        moteur="pandapipes",
    )

    comparaison = PandapipesEngine().simulate(entree)
    reference = LongDistanceLiquidEngine().simulate(entree)

    assert comparaison.profile[-1].pressure_pa == pytest.approx(
        reference.profile[-1].pressure_pa, rel=2.0e-4
    )
    assert comparaison.segments[0].friction_factor == pytest.approx(
        reference.segments[0].friction_factor, rel=2.0e-3
    )
    assert comparaison.segments[0].friction_head_loss_m == pytest.approx(
        reference.segments[0].friction_head_loss_m, rel=2.0e-3
    )
    assert comparaison.segments[0].minor_head_loss_m == pytest.approx(
        reference.segments[0].minor_head_loss_m, rel=1.0e-3
    )
    assert comparaison.diagnostics.residual <= comparaison.diagnostics.tolerance
    assert comparaison.diagnostics.mass_balance_ok

    # Une comparaison convergée reste non approuvable : elle n'exécute pas C-001 à C-012.
    assert comparaison.is_feasible
    assert not comparaison.is_approvable
    assert comparaison.summary()["approval_permitted"] is False
    assert comparaison.summary()["approval_block_reason"]
    assert not PandapipesEngine().explain(comparaison).approvable


def test_denivele_reste_distinct_de_la_perte_de_charge() -> None:
    """La hauteur statique ne doit jamais être publiée comme perte par frottement."""
    troncon = segment(longueur_m=10_000.0, diametre_m=0.5)
    entree = entree_canonique(
        conduite=pipeline(
            segments=(troncon,),
            profil=profil_incline(10_000.0, altitude_depart_m=100.0, denivele_m=50.0),
        ),
        cas=scenario(imposed_flow_m3_s=0.2, inlet_pressure_pa=5.0e6),
        moteur="pandapipes",
    )

    comparaison = PandapipesEngine().simulate(entree)
    reference = LongDistanceLiquidEngine().simulate(entree)
    resultat_troncon = comparaison.segments[0]

    assert comparaison.profile[-1].pressure_pa == pytest.approx(
        reference.profile[-1].pressure_pa, rel=2.0e-4
    )
    assert resultat_troncon.elevation_change_m == 50.0
    assert resultat_troncon.friction_head_loss_m == pytest.approx(
        reference.segments[0].friction_head_loss_m, rel=2.0e-3
    )
    assert resultat_troncon.total_head_loss_m < resultat_troncon.elevation_change_m
    assert comparaison.diagnostics.residual <= comparaison.diagnostics.tolerance


@pytest.mark.parametrize(
    ("entree", "motif"),
    [
        (
            entree_canonique(
                conduite=pipeline(
                    profil=ElevationProfile.from_pairs(
                        [(0.0, 100.0), (25_000.0, 180.0), (50_000.0, 100.0)]
                    )
                )
            ),
            "point(s) altimétrique(s) intérieur(s)",
        ),
        (
            entree_canonique(
                conduite=pipeline(stations=(station_serie(),)),
            ),
            "station(s) de pompage déclarée(s)",
        ),
        (
            entree_canonique(
                conduite=pipeline(
                    injections=(InjectionPoint("INJ-1", 10_000.0, 0.01),),
                )
            ),
            "Injections ou soutirages intermédiaires",
        ),
        (
            entree_canonique(
                cas=scenario(
                    imposed_flow_m3_s=0.2,
                    inlet_pressure_pa=5.0e6,
                    options=SolverOptions(friction_model=FrictionModel.HAALAND),
                )
            ),
            "n'est pas Colebrook–White",
        ),
    ],
)
def test_cas_non_traduits_refuses_explicitement(entree: CanonicalInput, motif: str) -> None:
    moteur = PandapipesEngine()

    assert not moteur.supports(entree)
    with pytest.raises(UnsupportedCaseError) as erreur:
        moteur.simulate(entree)
    assert motif in str(erreur.value)


def test_debit_et_pression_amont_sont_obligatoires() -> None:
    moteur = PandapipesEngine()
    entree = entree_canonique(
        cas=scenario(inlet_pressure_pa=5.0e6, outlet_pressure_pa=4.0e6),
        moteur="pandapipes",
    )

    with pytest.raises(UnsupportedCaseError, match="débit imposé et une pression amont"):
        moteur.simulate(entree)


def test_conditions_surcontraintes_refusees_avant_calcul() -> None:
    entree = entree_canonique(
        cas=scenario(
            imposed_flow_m3_s=0.2,
            inlet_pressure_pa=5.0e6,
            outlet_pressure_pa=4.0e6,
        ),
        moteur="pandapipes",
    )

    resultat = PandapipesEngine().simulate(entree)

    assert resultat.status is SimulationStatus.INVALID_INPUT
    assert not resultat.profile
    assert any("sur-contraint" in violation.message for violation in resultat.violations)
    assert not resultat.is_approvable


def test_non_convergence_devient_un_resultat_structure() -> None:
    entree = entree_canonique(
        cas=scenario(
            imposed_flow_m3_s=0.2,
            inlet_pressure_pa=5.0e6,
            options=SolverOptions(max_iterations=1),
        ),
        moteur="pandapipes",
    )

    resultat = PandapipesEngine().simulate(entree)

    assert resultat.status is SimulationStatus.NOT_CONVERGED
    assert resultat.diagnostics.iterations == 1
    assert resultat.violations[0].check_id == "C-010"
    assert not resultat.is_approvable
