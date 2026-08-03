"""Tests de l'hydraulique de base.

Chaque corrélation est confrontée soit à une solution analytique, soit à la bibliothèque
``fluids``, qui sert de seconde implémentation indépendante (D10 § 11 : « fluids/SciPy —
fonctions de base et racines »).
"""

from __future__ import annotations

import itertools
import math

import pytest

from hydro_domain.enums import FrictionModel
from hydroliquid.hydraulics import (
    LAMINAR_LIMIT_RE,
    TURBULENT_LIMIT_RE,
    G,
    flow_area_m2,
    flow_regime,
    friction_altshul,
    friction_colebrook_white,
    friction_factor,
    friction_haaland,
    friction_head_loss_m,
    friction_laminar,
    friction_swamee_jain,
    head_to_pressure_pa,
    hydraulic_gradient,
    is_transition_regime,
    minor_head_loss_m,
    pressure_to_head_m,
    reynolds,
    total_head_m,
    velocity_head_m,
    velocity_m_s,
)


class TestGrandeursDeBase:
    def test_section(self):
        assert flow_area_m2(1.0) == pytest.approx(math.pi / 4.0)

    def test_vitesse(self):
        """v = 4Q/(πD²)."""
        assert velocity_m_s(1.0, 1.0) == pytest.approx(4.0 / math.pi)

    def test_reynolds(self):
        assert reynolds(2.0, 0.5, 1e-6) == pytest.approx(1.0e6)

    def test_reynolds_independant_du_sens(self):
        """Le régime ne dépend pas du sens de circulation."""
        assert reynolds(-2.0, 0.5, 1e-6) == reynolds(2.0, 0.5, 1e-6)

    def test_viscosite_nulle_rejetee(self):
        with pytest.raises(ValueError, match="strictement positive"):
            reynolds(1.0, 0.5, 0.0)

    def test_hauteur_cinetique(self):
        assert velocity_head_m(2.0) == pytest.approx(4.0 / (2 * G))

    def test_conversion_pression_charge(self):
        rho = 850.0
        assert pressure_to_head_m(head_to_pressure_pa(50.0, rho), rho) == pytest.approx(50.0)

    def test_charge_totale(self):
        assert total_head_m(1.0e5, 100.0, 1000.0) == pytest.approx(100.0 + 1.0e5 / (1000.0 * G))


class TestRegimeLaminaire:
    def test_loi_lambda_64_sur_re(self):
        """Cas V-003 et VAL-LIQ-001 : λ = 64/Re en régime laminaire."""
        for re in (100.0, 500.0, 1500.0, 1999.0):
            assert friction_factor(re, 1e-4) == pytest.approx(64.0 / re, rel=1e-12)

    def test_hagen_poiseuille(self):
        """VAL-LIQ-001 : la perte laminaire doit coïncider avec Hagen–Poiseuille.

        Hagen–Poiseuille : Δp = 128 μ L Q / (π D⁴). Darcy–Weisbach avec λ = 64/Re doit
        redonner exactement cette expression : les deux formulations sont équivalentes en
        régime laminaire, ce test le vérifie sur des valeurs numériques.
        """
        diameter, length, nu, rho = 0.05, 100.0, 1e-4, 900.0
        flow = 1e-4  # m³/s
        mu = rho * nu

        hf = friction_head_loss_m(flow, length, diameter, 1e-6, nu)
        delta_p_darcy = hf * rho * G
        delta_p_poiseuille = 128.0 * mu * length * flow / (math.pi * diameter**4)

        re = reynolds(velocity_m_s(flow, diameter), diameter, nu)
        assert re < LAMINAR_LIMIT_RE, "le cas doit rester laminaire"
        assert delta_p_darcy == pytest.approx(delta_p_poiseuille, rel=1e-10)

    def test_debit_nul_perte_nulle(self):
        assert friction_laminar(0.0) == 0.0
        assert friction_head_loss_m(0.0, 1000.0, 0.5, 4.5e-5, 1e-6) == 0.0


class TestColebrookWhite:
    @pytest.mark.parametrize("re", [4000.0, 1e4, 1e5, 1e6, 1e7, 1e8])
    @pytest.mark.parametrize("relative_roughness", [1e-6, 1e-5, 1e-4, 1e-3, 1e-2])
    def test_satisfait_l_equation_implicite(self, re, relative_roughness):
        """La solution doit annuler le résidu de l'équation de Colebrook–White."""
        lam = friction_colebrook_white(re, relative_roughness)
        residual = 1.0 / math.sqrt(lam) + 2.0 * math.log10(
            relative_roughness / 3.7 + 2.51 / (re * math.sqrt(lam))
        )
        assert residual == pytest.approx(0.0, abs=1e-10)

    @pytest.mark.parametrize("re", [1e4, 1e5, 1e6, 1e7])
    @pytest.mark.parametrize("relative_roughness", [1e-5, 1e-4, 1e-3])
    def test_accord_avec_la_bibliotheque_fluids(self, re, relative_roughness):
        """Seconde implémentation indépendante : la bibliothèque ``fluids`` (D10 § 11)."""
        from fluids.friction import Colebrook

        assert friction_colebrook_white(re, relative_roughness) == pytest.approx(
            Colebrook(re, relative_roughness), rel=1e-8
        )

    def test_tolerance_atteinte_ou_erreur_explicite(self):
        """Le produit ne retourne jamais un facteur de frottement non convergé."""
        with pytest.raises(RuntimeError, match="n'a pas convergé"):
            friction_colebrook_white(1e6, 1e-4, tolerance=0.0, max_iterations=2)


class TestApproximationsExplicites:
    @pytest.mark.parametrize("re", [1e4, 1e5, 1e6, 1e7])
    @pytest.mark.parametrize("relative_roughness", [1e-5, 1e-4, 1e-3])
    def test_haaland_proche_de_colebrook(self, re, relative_roughness):
        """Écart annoncé de Haaland à Colebrook : inférieur à 2 % sur le domaine usuel."""
        reference = friction_colebrook_white(re, relative_roughness)
        assert friction_haaland(re, relative_roughness) == pytest.approx(reference, rel=0.02)

    @pytest.mark.parametrize("re", [1e4, 1e5, 1e6, 1e7])
    @pytest.mark.parametrize("relative_roughness", [1e-5, 1e-4, 1e-3])
    def test_swamee_jain_proche_de_colebrook(self, re, relative_roughness):
        reference = friction_colebrook_white(re, relative_roughness)
        assert friction_swamee_jain(re, relative_roughness) == pytest.approx(reference, rel=0.03)

    def test_altshul_reste_du_meme_ordre(self):
        """Altshul est conservée pour reproduire le cas académique, pas comme référence."""
        reference = friction_colebrook_white(5e4, 4e-4)
        assert friction_altshul(5e4, 4e-4) == pytest.approx(reference, rel=0.15)


class TestTransition:
    def test_continuite_aux_bornes(self):
        """La continuité de λ(Re) est indispensable à la convergence du solveur."""
        eps_d = 1e-4
        gauche = friction_factor(LAMINAR_LIMIT_RE - 1e-6, eps_d)
        droite = friction_factor(LAMINAR_LIMIT_RE + 1e-6, eps_d)
        assert gauche == pytest.approx(droite, rel=1e-6)

        avant = friction_factor(TURBULENT_LIMIT_RE - 1e-6, eps_d)
        apres = friction_factor(TURBULENT_LIMIT_RE + 1e-6, eps_d)
        assert avant == pytest.approx(apres, rel=1e-6)

    def test_monotonie_et_encadrement_dans_la_zone(self):
        """L'interpolation reste monotone et bornée par les deux régimes encadrants.

        Le passage du laminaire au turbulent s'accompagne d'une **hausse** du facteur de
        frottement : à ε/D = 10⁻⁴, λ passe de 64/2000 = 0,032 à environ 0,040. La valeur
        interpolée ne doit donc jamais sortir de cet encadrement, ni osciller.
        """
        eps_d = 1e-4
        borne_basse = friction_laminar(LAMINAR_LIMIT_RE)
        borne_haute = friction_colebrook_white(TURBULENT_LIMIT_RE, eps_d)
        assert borne_haute > borne_basse

        valeurs = [friction_factor(re, eps_d) for re in range(2000, 4001, 100)]
        assert all(b >= a - 1e-12 for a, b in itertools.pairwise(valeurs))
        assert all(borne_basse - 1e-12 <= v <= borne_haute + 1e-12 for v in valeurs)

    def test_zone_signalee(self):
        assert is_transition_regime(3000.0)
        assert not is_transition_regime(1000.0)
        assert not is_transition_regime(5000.0)

    def test_libelles_de_regime(self):
        assert flow_regime(1000.0) == "laminaire"
        assert flow_regime(3000.0) == "transition"
        assert flow_regime(50000.0) == "turbulent"

    def test_altshul_non_interpolee(self):
        """Altshul est continue par construction : elle s'applique dès Re = 2 000."""
        valeur = friction_factor(3000.0, 1e-4, FrictionModel.ALTSHUL)
        assert valeur == pytest.approx(friction_altshul(3000.0, 1e-4))


class TestPertes:
    def test_darcy_weisbach(self):
        """VAL-LIQ-002 : h_f = λ (L/D) v²/(2g)."""
        flow, length, diameter, roughness, nu = 0.2, 1000.0, 0.5, 4.5e-5, 1e-6
        v = velocity_m_s(flow, diameter)
        lam = friction_factor(reynolds(v, diameter, nu), roughness / diameter)
        attendu = lam * (length / diameter) * v * v / (2 * G)
        assert friction_head_loss_m(flow, length, diameter, roughness, nu) == pytest.approx(attendu)

    def test_signe_suit_le_debit(self):
        """La perte s'oppose toujours à l'écoulement, quel que soit son sens."""
        amont = friction_head_loss_m(0.2, 1000.0, 0.5, 4.5e-5, 1e-6)
        aval = friction_head_loss_m(-0.2, 1000.0, 0.5, 4.5e-5, 1e-6)
        assert amont > 0
        assert aval == pytest.approx(-amont)

    def test_perte_quadratique_en_debit(self):
        """À λ quasi constant, doubler le débit quadruple approximativement la perte."""
        simple = friction_head_loss_m(0.2, 1000.0, 0.5, 4.5e-5, 1e-6)
        double = friction_head_loss_m(0.4, 1000.0, 0.5, 4.5e-5, 1e-6)
        assert 3.7 < double / simple < 4.0

    def test_pertes_singulieres(self):
        """VAL-LIQ-006 : h_m = ΣK v²/(2g)."""
        v = velocity_m_s(0.2, 0.5)
        assert minor_head_loss_m(0.2, 0.5, 2.5) == pytest.approx(2.5 * v * v / (2 * G))

    def test_k_nul(self):
        assert minor_head_loss_m(0.2, 0.5, 0.0) == 0.0

    def test_accessoire_ferme_bloque_l_ecoulement(self):
        assert math.isinf(minor_head_loss_m(0.2, 0.5, math.inf))
        assert minor_head_loss_m(0.0, 0.5, math.inf) == 0.0

    def test_gradient_hydraulique(self):
        """Le gradient est la perte par mètre : h_f = i · L."""
        i = hydraulic_gradient(0.2, 0.5, 4.5e-5, 1e-6)
        hf = friction_head_loss_m(0.2, 5000.0, 0.5, 4.5e-5, 1e-6)
        assert i * 5000.0 == pytest.approx(hf, rel=1e-12)


class TestComparaisonFluids:
    def test_perte_de_charge_accord_avec_fluids(self):
        """Comparaison bout à bout avec ``fluids`` sur une conduite complète."""
        from fluids.friction import friction_factor as ff_fluids

        flow, length, diameter, roughness, nu, _rho = 0.35, 12_000.0, 0.6, 1e-4, 5e-6, 860.0
        v = velocity_m_s(flow, diameter)
        re = reynolds(v, diameter, nu)
        lam_reference = ff_fluids(Re=re, eD=roughness / diameter)
        hf_reference = lam_reference * (length / diameter) * v * v / (2 * G)

        calcule = friction_head_loss_m(flow, length, diameter, roughness, nu)
        assert calcule == pytest.approx(hf_reference, rel=1e-6)
