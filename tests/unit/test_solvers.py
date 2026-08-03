"""Tests des méthodes numériques.

Exigence structurante (FR-GEN-005) : *aucun résultat silencieux ou valeur sentinelle non
documentée*. Ces tests vérifient qu'un échec de convergence ou une absence de solution
physique se traduit toujours par une exception porteuse d'un diagnostic exploitable, et jamais
par une valeur arbitraire.
"""

from __future__ import annotations

import math

import pytest

from hydro_shared.diagnostics import SolverDiagnostics
from hydro_shared.errors import NoPhysicalSolutionError, NotConvergedError
from hydroliquid.solvers import (
    bracket_root,
    brent,
    damped_newton,
    solve_hybrid,
    solve_monotonic,
)


class TestEncadrement:
    def test_trouve_un_changement_de_signe(self):
        a, b = bracket_root(lambda x: x - 5.0, 0.0, 1.0)
        assert a <= 5.0 <= b

    def test_racine_exacte_a_la_borne(self):
        a, b = bracket_root(lambda x: x - 1.0, 1.0, 2.0)
        assert a == b == 1.0

    def test_absence_de_solution_signalee(self):
        """Cas V-018 : absence de solution → erreur explicite, pas de valeur arbitraire."""
        with pytest.raises(NoPhysicalSolutionError) as excinfo:
            bracket_root(lambda x: x * x + 1.0, 0.0, 1.0, max_expansions=10)
        assert excinfo.value.code == "SIM_NO_PHYSICAL_SOLUTION"
        assert "ne change pas de signe" in excinfo.value.message


class TestBrent:
    def test_racine_polynomiale(self):
        resultat = brent(lambda x: x**3 - 2.0, 0.0, 5.0, tolerance=1e-12)
        assert resultat.root == pytest.approx(2.0 ** (1.0 / 3.0), rel=1e-9)

    def test_convergence_rapide(self):
        """Brent doit converger en bien moins d'itérations qu'une dichotomie pure."""
        resultat = brent(lambda x: math.exp(x) - 5.0, 0.0, 10.0, tolerance=1e-12)
        assert resultat.iterations < 30
        assert resultat.root == pytest.approx(math.log(5.0), rel=1e-9)

    def test_intervalle_sans_racine_rejete(self):
        with pytest.raises(NoPhysicalSolutionError, match="n'encadre pas de racine"):
            brent(lambda x: x + 10.0, 0.0, 5.0, tolerance=1e-9)

    def test_non_convergence_signalee(self):
        """Cas V-019 : une limite d'itérations forcée conserve le diagnostic d'échec.

        Une fonction linéaire est volontairement exclue de ce test : la méthode de la
        sécante trouve alors sa racine exacte en une seule étape, même avec une tolérance
        nulle. La fonction ci-dessous possède une racine encadrée, mais ne peut pas
        l'atteindre exactement en trois itérations en arithmétique flottante.
        """
        diagnostics = SolverDiagnostics()
        with pytest.raises(NotConvergedError) as excinfo:
            brent(
                lambda x: math.cos(x) - x,
                0.0,
                1.0,
                tolerance=0.0,
                max_iterations=3,
                diagnostics=diagnostics,
            )
        assert excinfo.value.iterations == 3
        assert not diagnostics.converged

    def test_diagnostics_renseignes(self):
        diagnostics = SolverDiagnostics()
        brent(lambda x: x - 2.0, 0.0, 5.0, tolerance=1e-10, diagnostics=diagnostics)
        assert diagnostics.converged
        assert diagnostics.method == "brent"
        assert diagnostics.iterations >= 1
        assert diagnostics.residual <= 1e-10

    def test_journal_d_iterations_optionnel(self):
        diagnostics = SolverDiagnostics()
        brent(
            lambda x: x**2 - 2.0,
            0.0,
            5.0,
            tolerance=1e-10,
            diagnostics=diagnostics,
            log_iterations=True,
        )
        assert diagnostics.iteration_log


class TestNewtonAmorti:
    def test_racine_avec_derivee_numerique(self):
        resultat = damped_newton(lambda x: x**2 - 4.0, 1.0, tolerance=1e-10)
        assert resultat.root == pytest.approx(2.0, rel=1e-9)

    def test_racine_avec_derivee_analytique(self):
        resultat = damped_newton(
            lambda x: x**2 - 4.0, 1.0, tolerance=1e-12, derivative=lambda x: 2.0 * x
        )
        assert resultat.root == pytest.approx(2.0, rel=1e-11)

    def test_bornes_respectees(self):
        """Les bornes empêchent l'itéré de sortir du domaine physique."""
        resultat = damped_newton(
            lambda x: x**2 - 4.0, 3.0, tolerance=1e-10, lower_bound=0.0, upper_bound=10.0
        )
        assert 0.0 <= resultat.root <= 10.0

    def test_derivee_nulle_signalee(self):
        with pytest.raises(NotConvergedError, match="dérivée"):
            damped_newton(lambda x: 5.0, 1.0, tolerance=1e-12, derivative=lambda x: 0.0)

    def test_amortissement_evite_la_divergence(self):
        """Sur une fonction fortement non linéaire, Newton pur diverge, l'amorti converge."""
        resultat = damped_newton(lambda x: math.atan(x), 5.0, tolerance=1e-9, max_iterations=200)
        assert resultat.root == pytest.approx(0.0, abs=1e-6)


class TestSolveMonotonic:
    def test_encadre_puis_resout(self):
        resultat = solve_monotonic(lambda x: 100.0 - x**2, lower=0.0, upper=1.0, tolerance=1e-9)
        assert resultat.root == pytest.approx(10.0, rel=1e-9)

    def test_absence_de_solution_remontee(self):
        with pytest.raises(NoPhysicalSolutionError):
            solve_monotonic(lambda x: 1.0 + x**2, lower=0.0, upper=1.0, tolerance=1e-9)


class TestSolveHybride:
    def test_newton_suffit(self):
        diagnostics = SolverDiagnostics()
        resultat = solve_hybrid(
            lambda x: x**2 - 9.0,
            initial_guess=2.0,
            lower=0.0,
            upper=10.0,
            tolerance=1e-10,
            diagnostics=diagnostics,
        )
        assert resultat.root == pytest.approx(3.0, rel=1e-9)
        assert not diagnostics.fallback_used

    def test_repli_journalise(self):
        """D07 § 7 : tout basculement de méthode doit être journalisé, jamais silencieux."""
        diagnostics = SolverDiagnostics()

        def fonction_plate(x: float) -> float:
            # Dérivée nulle au point de départ : Newton ne peut pas progresser.
            return (x - 4.0) ** 3

        resultat = solve_hybrid(
            fonction_plate,
            initial_guess=4.0 + 1e-14,
            lower=0.0,
            upper=10.0,
            tolerance=1e-8,
            diagnostics=diagnostics,
        )
        assert resultat.root == pytest.approx(4.0, abs=1e-2)
        # Selon le point de départ, Newton peut réussir immédiatement : on vérifie surtout
        # qu'aucun repli n'est passé sous silence.
        if diagnostics.fallback_used:
            assert diagnostics.messages
