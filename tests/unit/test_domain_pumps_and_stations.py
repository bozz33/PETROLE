"""Tests des pompes et des stations.

Couvre les cas de validation VAL-PMP-002 (ajustement H = a − b·Q²), VAL-PMP-003 (série),
VAL-PMP-004 (parallèle identique), VAL-PMP-005 (parallèle différent) et VAL-PMP-006
(vitesse variable).
"""

from __future__ import annotations

import pytest

from hydro_shared.errors import PumpCurveError

from hydro_domain.enums import EquipmentStatus, PumpArrangement, PumpRole
from hydro_domain.pumps import (
    G,
    PumpCurve,
    PumpInstance,
    PumpModel,
    absorbed_power_w,
    fit_quadratic_head,
    hydraulic_power_w,
)
from hydro_domain.stations import (
    PumpGroup,
    PumpStation,
    build_parallel_station,
    build_series_station,
    head_to_pressure_pa,
    pressure_to_head_m,
)

#: Courbe de référence : pompe de gros débit type oléoduc, points constructeur en m³/h.
_POINTS_M3H = [1000.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0, 7000.0]
_HEADS_NM8 = [298.0, 292.0, 284.0, 270.0, 252.0, 230.0, 205.0]


def courbe_nm8(**kwargs) -> PumpCurve:
    return PumpCurve([q / 3600.0 for q in _POINTS_M3H], _HEADS_NM8, **kwargs)


def modele(nom: str = "NM-8", **kwargs) -> PumpModel:
    return PumpModel(id=nom, name=nom, curve=courbe_nm8(), **kwargs)


def pompe(identifiant: str = "P1", **kwargs) -> PumpInstance:
    kwargs.setdefault("model", modele())
    return PumpInstance(id=identifiant, **kwargs)


class TestAjustementQuadratique:
    def test_reconstruit_une_parabole_exacte(self):
        """Sur des points exactement quadratiques, l'ajustement doit être exact."""
        a, b = 300.0, 150.0
        flows = [0.1, 0.3, 0.5, 0.7, 0.9]
        heads = [a - b * q * q for q in flows]
        fit = fit_quadratic_head(flows, heads)
        assert fit.a == pytest.approx(a, rel=1e-10)
        assert fit.b == pytest.approx(b, rel=1e-10)
        assert fit.rms_error_m == pytest.approx(0.0, abs=1e-9)

    def test_cas_vale_pmp_002_sur_courbe_constructeur(self):
        """VAL-PMP-002 : coefficients et erreur d'ajustement reproduits sur la courbe NM-8."""
        fit = courbe_nm8().quadratic_fit
        assert fit.point_count == 7
        # L'ajustement doit rester très proche des points constructeur.
        assert fit.rms_error_m < 2.0
        assert fit.max_error_m < 4.0
        # Hauteur à débit nul cohérente avec l'extrapolation de la courbe.
        assert 295.0 < fit.shutoff_head_m < 310.0

    def test_moins_de_trois_points_rejete(self):
        with pytest.raises(PumpCurveError, match="au moins trois points"):
            fit_quadratic_head([0.1, 0.2], [300.0, 290.0])

    def test_debits_identiques_rejetes(self):
        with pytest.raises(PumpCurveError, match="indétermin"):
            fit_quadratic_head([0.5, 0.5, 0.5], [300.0, 290.0, 280.0])

    def test_debit_maximal_theorique(self):
        fit = fit_quadratic_head([0.0, 1.0, 2.0], [400.0, 300.0, 0.0])
        assert fit.max_flow_m3_s > 0


class TestPumpCurve:
    def test_interpolation_aux_points_constructeur(self):
        courbe = courbe_nm8()
        for q_m3h, h in zip(_POINTS_M3H, _HEADS_NM8, strict=True):
            assert courbe.head(q_m3h / 3600.0) == pytest.approx(h, rel=1e-9)

    def test_courbe_croissante_rejetee(self):
        """Une courbe H(Q) croissante rendrait le point de fonctionnement non unique."""
        with pytest.raises(PumpCurveError, match="strictement décroissante"):
            PumpCurve([0.1, 0.2, 0.3], [200.0, 250.0, 300.0])

    def test_hauteur_negative_rejetee(self):
        with pytest.raises(PumpCurveError, match="négatives"):
            PumpCurve([0.1, 0.2], [200.0, -10.0])

    def test_rendement_hors_fraction_rejete(self):
        with pytest.raises(PumpCurveError, match="fraction"):
            PumpCurve([0.1, 0.2], [200.0, 180.0], efficiencies=[72.0, 81.0])

    def test_extrapolation_signalee(self):
        """Contrôle C-006 : sortie du domaine constructeur signalée, jamais silencieuse."""
        courbe = courbe_nm8()
        evaluation = courbe.evaluate(9000.0 / 3600.0)
        assert evaluation.extrapolated
        assert evaluation.detail is not None
        assert "hors du domaine constructeur" in evaluation.detail

    def test_domaine_verifie(self):
        courbe = courbe_nm8()
        assert courbe.is_within_domain(3000.0 / 3600.0)
        assert not courbe.is_within_domain(9000.0 / 3600.0)

    def test_point_de_meilleur_rendement(self):
        courbe = courbe_nm8(efficiencies=[0.60, 0.70, 0.78, 0.83, 0.81, 0.75, 0.68])
        bep = courbe.best_efficiency_point()
        assert bep is not None
        assert bep[0] == pytest.approx(4000.0 / 3600.0)
        assert bep[1] == pytest.approx(0.83)

    def test_sans_rendement_pas_de_bep(self):
        assert courbe_nm8().best_efficiency_point() is None


class TestLoisDAffinite:
    def test_vale_pmp_006_hauteur_en_carre_de_la_vitesse(self):
        """VAL-PMP-006 : H varie comme s², Q comme s."""
        courbe = courbe_nm8()
        q0 = 4000.0 / 3600.0
        h0 = courbe.head(q0)
        s = 0.8
        h1 = courbe.head(q0 * s, speed_ratio=s)
        assert h1 == pytest.approx(h0 * s**2, rel=1e-9)

    def test_puissance_en_cube_de_la_vitesse(self):
        courbe = courbe_nm8(powers_w=[1.0e6 * x for x in (1.0, 1.4, 1.7, 1.9, 2.0, 2.05, 2.1)])
        q0 = 4000.0 / 3600.0
        p0 = courbe.evaluate(q0).power_w
        s = 0.9
        p1 = courbe.evaluate(q0 * s, speed_ratio=s).power_w
        assert p0 is not None and p1 is not None
        assert p1 == pytest.approx(p0 * s**3, rel=1e-9)

    def test_vitesse_tres_eloignee_signalee(self):
        evaluation = courbe_nm8().evaluate(2000.0 / 3600.0, speed_ratio=0.3)
        assert evaluation.detail is not None
        assert "lois d'affinité ne sont plus fiables" in evaluation.detail

    def test_vitesse_nulle_rejetee(self):
        with pytest.raises(PumpCurveError, match="strictement positif"):
            courbe_nm8().evaluate(0.5, speed_ratio=0.0)

    def test_vitesse_hors_bornes_constructeur_rejetee(self):
        with pytest.raises(PumpCurveError, match="bornes constructeur"):
            PumpInstance(id="P1", model=modele(min_speed_ratio=0.7), speed_ratio=0.5)


class TestPumpInstance:
    def test_pompe_indisponible_ne_fournit_rien(self):
        p = pompe(status=EquipmentStatus.UNAVAILABLE)
        assert not p.is_active
        assert p.head(1.0) == 0.0

    def test_pompe_arretee_ne_fournit_rien(self):
        assert pompe(running=False).head(1.0) == 0.0

    def test_pompe_de_secours_reste_disponible(self):
        """FR-PMP-004 : une pompe de secours n'est pas indisponible, elle est à l'arrêt."""
        p = pompe(role=PumpRole.STANDBY, running=False)
        assert p.status is EquipmentStatus.AVAILABLE
        assert not p.is_active
        assert p.with_state(running=True).is_active

    def test_role_secours_ne_demarre_pas_par_defaut(self):
        assert not PumpRole.STANDBY.starts_by_default
        assert PumpRole.MAIN.starts_by_default


class TestStationSerie:
    def test_vale_pmp_003_hauteurs_cumulees(self):
        """VAL-PMP-003 : deux pompes identiques en série doublent la hauteur au même débit."""
        q = 4000.0 / 3600.0
        une = build_series_station("S1", "Station 1", 0.0, 100.0, (pompe("P1"),))
        deux = build_series_station("S1", "Station 1", 0.0, 100.0, (pompe("P1"), pompe("P2")))
        assert deux.combined_head(q) == pytest.approx(2.0 * une.combined_head(q), rel=1e-12)

    def test_toutes_les_pompes_voient_le_debit_total(self):
        q = 4000.0 / 3600.0
        station = build_series_station("S1", "S", 0.0, 0.0, (pompe("P1"), pompe("P2")))
        distribution = station.flow_distribution(q)
        assert distribution == {"P1": pytest.approx(q), "P2": pytest.approx(q)}

    def test_pompe_indisponible_retiree_du_cumul(self):
        q = 4000.0 / 3600.0
        station = build_series_station(
            "S1", "S", 0.0, 0.0, (pompe("P1"), pompe("P2", status=EquipmentStatus.UNAVAILABLE))
        )
        seule = build_series_station("S1", "S", 0.0, 0.0, (pompe("P1"),))
        assert station.combined_head(q) == pytest.approx(seule.combined_head(q))

    def test_station_bypassee_ne_fournit_rien(self):
        """Scénario obligatoire « Bypass » : le fluide contourne la station."""
        station = build_series_station("S1", "S", 0.0, 0.0, (pompe("P1"),)).with_status(
            EquipmentStatus.BYPASSED
        )
        assert station.combined_head(1.0) == 0.0
        evaluation = station.evaluate(1.0, density_kg_m3=850.0)
        assert evaluation.active_pump_count == 0
        assert evaluation.detail == "Station bypassée."


class TestStationParallele:
    def test_vale_pmp_004_debit_double_a_hauteur_donnee(self):
        """VAL-PMP-004 : deux pompes identiques en parallèle doublent le débit à hauteur donnée."""
        une = build_parallel_station("S1", "S", 0.0, 0.0, (pompe("P1"),))
        deux = build_parallel_station("S1", "S", 0.0, 0.0, (pompe("P1"), pompe("P2")))
        q = 4000.0 / 3600.0
        hauteur_une = une.combined_head(q)
        hauteur_deux = deux.combined_head(2.0 * q)
        assert hauteur_deux == pytest.approx(hauteur_une, rel=1e-6)

    def test_partage_egal_entre_pompes_identiques(self):
        station = build_parallel_station("S1", "S", 0.0, 0.0, (pompe("P1"), pompe("P2")))
        q_total = 6000.0 / 3600.0
        distribution = station.flow_distribution(q_total)
        assert distribution["P1"] == pytest.approx(q_total / 2.0, rel=1e-6)
        assert distribution["P2"] == pytest.approx(q_total / 2.0, rel=1e-6)

    def test_conservation_du_debit_total(self):
        """Contrôle C-001 : la somme des débits de branche restitue exactement le total."""
        forte = PumpModel(id="forte", name="forte", curve=courbe_nm8())
        faible = PumpModel(
            id="faible",
            name="faible",
            curve=PumpCurve([q / 3600.0 for q in _POINTS_M3H], [h * 0.7 for h in _HEADS_NM8]),
        )
        station = build_parallel_station(
            "S1",
            "S",
            0.0,
            0.0,
            (PumpInstance(id="P1", model=forte), PumpInstance(id="P2", model=faible)),
        )
        q_total = 5000.0 / 3600.0
        distribution = station.flow_distribution(q_total)
        assert sum(distribution.values()) == pytest.approx(q_total, rel=1e-12)

    def test_vale_pmp_005_partage_inegal_entre_pompes_differentes(self):
        """VAL-PMP-005 : la pompe la plus forte prend la plus grande part du débit."""
        forte = PumpModel(id="forte", name="forte", curve=courbe_nm8())
        faible = PumpModel(
            id="faible",
            name="faible",
            curve=PumpCurve([q / 3600.0 for q in _POINTS_M3H], [h * 0.7 for h in _HEADS_NM8]),
        )
        station = build_parallel_station(
            "S1",
            "S",
            0.0,
            0.0,
            (PumpInstance(id="P1", model=forte), PumpInstance(id="P2", model=faible)),
        )
        distribution = station.flow_distribution(5000.0 / 3600.0)
        assert distribution["P1"] > distribution["P2"]


class TestPuissances:
    def test_puissance_hydraulique(self):
        """P_h = ρ g Q H (D07 § 6)."""
        assert hydraulic_power_w(1.0, 100.0, 850.0) == pytest.approx(850.0 * G * 100.0)

    def test_puissance_absorbee(self):
        assert absorbed_power_w(1.0e6, 0.8) == pytest.approx(1.25e6)

    def test_rendement_nul_rejete(self):
        """Une division silencieuse produirait une puissance infinie mal interprétée par C-007."""
        with pytest.raises(PumpCurveError, match="strictement positif"):
            absorbed_power_w(1.0e6, 0.0)

    def test_evaluation_station_avec_rendement(self):
        courbe = courbe_nm8(efficiencies=[0.60, 0.70, 0.78, 0.83, 0.81, 0.75, 0.68])
        m = PumpModel(id="M", name="M", curve=courbe)
        station = build_series_station("S1", "S", 0.0, 0.0, (PumpInstance(id="P1", model=m),))
        q = 4000.0 / 3600.0
        evaluation = station.evaluate(q, density_kg_m3=850.0)
        assert evaluation.absorbed_power_w is not None
        assert evaluation.absorbed_power_w > evaluation.hydraulic_power_w
        assert evaluation.efficiency == pytest.approx(0.83, rel=1e-6)

    def test_puissance_absorbee_inconnue_signalee(self):
        """Sans courbe P(Q) ni rendement, la puissance n'est pas devinée."""
        station = build_series_station("S1", "S", 0.0, 0.0, (pompe("P1"),))
        evaluation = station.evaluate(1.0, density_kg_m3=850.0)
        assert evaluation.absorbed_power_w is None
        assert evaluation.detail is not None
        assert "Puissance absorbée indisponible" in evaluation.detail

    def test_rendement_d_entrainement_pris_en_compte(self):
        courbe = courbe_nm8(efficiencies=[0.60, 0.70, 0.78, 0.83, 0.81, 0.75, 0.68])
        m = PumpModel(id="M", name="M", curve=courbe)
        pompes = (PumpInstance(id="P1", model=m),)
        sans = build_series_station("S1", "S", 0.0, 0.0, pompes)
        avec = build_series_station("S1", "S", 0.0, 0.0, pompes, drive_efficiency=0.95)
        q = 4000.0 / 3600.0
        a = sans.evaluate(q, 850.0).absorbed_power_w
        b = avec.evaluate(q, 850.0).absorbed_power_w
        assert a is not None and b is not None
        assert b == pytest.approx(a / 0.95)


class TestNPSH:
    def test_npsh_disponible(self):
        """NPSHa = (p_asp − p_v)/(ρg) + v²/2g (D07 § 6)."""
        station = build_series_station("S1", "S", 0.0, 0.0, (pompe("P1"),))
        rho = 850.0
        npsha = station.npsh_available_m(
            suction_pressure_pa=3.0e5, vapor_pressure_pa=1.0e4, density_kg_m3=rho
        )
        assert npsha == pytest.approx((3.0e5 - 1.0e4) / (rho * G))

    def test_hauteur_cinetique_ajoutee(self):
        station = build_series_station("S1", "S", 0.0, 0.0, (pompe("P1"),))
        sans = station.npsh_available_m(3.0e5, 1.0e4, 850.0)
        avec = station.npsh_available_m(3.0e5, 1.0e4, 850.0, velocity_head_m=0.5)
        assert avec == pytest.approx(sans + 0.5)


class TestConversions:
    def test_pression_hauteur_aller_retour(self):
        rho = 850.0
        assert pressure_to_head_m(head_to_pressure_pa(100.0, rho), rho) == pytest.approx(100.0)


class TestCoherenceStation:
    def test_identifiants_de_pompe_dupliques_rejetes(self):
        with pytest.raises(Exception, match="dupliqués"):
            PumpStation(
                id="S1",
                name="S",
                chainage_m=0.0,
                elevation_m=0.0,
                groups=(PumpGroup(id="G1", pumps=(pompe("P1"), pompe("P1"))),),
            )

    def test_limites_de_pression_incoherentes_rejetees(self):
        with pytest.raises(Exception, match="supérieure"):
            PumpStation(
                id="S1",
                name="S",
                chainage_m=0.0,
                elevation_m=0.0,
                suction_pressure_min_pa=5.0e6,
                discharge_pressure_max_pa=3.0e6,
            )

    def test_montage_par_defaut_serie(self):
        station = PumpStation(id="S1", name="S", chainage_m=0.0, elevation_m=0.0)
        assert station.arrangement is PumpArrangement.SERIES
        assert station.combined_head(1.0) == 0.0
