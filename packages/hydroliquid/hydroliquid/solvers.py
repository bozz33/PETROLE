"""Méthodes numériques du noyau : recherche de racine et diagnostics.

Stratégie (D07 § 7, D-v2 § 5.6) :

- **encadrement puis Brent** pour les équations à une inconnue dont la fonction résidu est
  monotone — c'est le cas du débit d'un pipeline linéaire, dont la perte de charge croît
  strictement avec le débit ;
- **Newton amorti** avec repli sur la dichotomie lorsque la dérivée est fiable ;
- **basculement journalisé** : tout repli est enregistré dans les diagnostics et remonté
  comme avertissement ``WARN_SOLVER_FALLBACK``, jamais silencieux.

Aucune de ces fonctions ne retourne un résultat non convergé : elles lèvent
:class:`NotConvergedError` ou :class:`NoPhysicalSolutionError`, à charge du moteur de traduire
l'échec en statut de simulation et en diagnostic exploitable (FR-LIQ-008, FR-GEN-005).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from hydro_shared.diagnostics import SolverDiagnostics
from hydro_shared.errors import NoPhysicalSolutionError, NotConvergedError

#: Nombre maximal d'élargissements successifs lors de la recherche d'un encadrement.
MAX_BRACKET_EXPANSIONS = 60


@dataclass(frozen=True, slots=True)
class RootResult:
    """Racine trouvée, accompagnée de ses indicateurs de convergence."""

    root: float
    residual: float
    iterations: int
    method: str
    bracket: tuple[float, float] | None = None


def bracket_root(
    f: Callable[[float], float],
    lower: float,
    upper: float,
    *,
    expansion: float = 2.0,
    max_expansions: int = MAX_BRACKET_EXPANSIONS,
    hard_upper: float | None = None,
) -> tuple[float, float]:
    """Cherche un intervalle ``[a, b]`` sur lequel ``f`` change de signe.

    L'intervalle initial est élargi vers le haut par multiplications successives. La borne
    basse n'est pas déplacée : dans nos problèmes elle correspond à une grandeur physique
    minimale (débit nul, hauteur nulle) qu'il n'y a pas lieu de franchir.

    Lève :class:`NoPhysicalSolutionError` si aucun changement de signe n'est trouvé : cela
    signifie qu'aucune solution n'existe dans le domaine physique exploré, ce qui est une
    information utilisable par l'ingénieur et non une erreur technique (cas V-018).
    """
    f_lower = f(lower)
    if f_lower == 0.0:
        return (lower, lower)

    if hard_upper is not None and hard_upper < lower:
        raise NoPhysicalSolutionError(
            "La borne supérieure physique est inférieure à la borne minimale.",
            lower=lower,
            hard_upper=hard_upper,
        )
    current_upper = min(upper, hard_upper) if hard_upper is not None else upper
    for _ in range(max_expansions + 1):
        f_upper = f(current_upper)
        if f_upper == 0.0:
            return (current_upper, current_upper)
        if f_lower * f_upper < 0.0:
            return (lower, current_upper)
        if hard_upper is not None and current_upper >= hard_upper:
            break
        expanded_upper = current_upper * expansion
        current_upper = (
            min(expanded_upper, hard_upper) if hard_upper is not None else expanded_upper
        )

    raise NoPhysicalSolutionError(
        "Aucune solution physique n'a été trouvée dans le domaine exploré : la fonction "
        "résidu ne change pas de signe. Vérifiez les conditions aux limites, la capacité de "
        "pompage et les pertes de charge.",
        lower=lower,
        upper=current_upper,
        hard_upper=hard_upper,
        residual_at_lower=f_lower,
    )


def brent(
    f: Callable[[float], float],
    lower: float,
    upper: float,
    *,
    tolerance: float,
    variable_tolerance: float | None = None,
    max_iterations: int = 100,
    diagnostics: SolverDiagnostics | None = None,
    log_iterations: bool = False,
) -> RootResult:
    """Recherche de racine par la méthode de Brent sur un intervalle encadrant.

    Brent combine dichotomie, sécante et interpolation quadratique inverse : il conserve la
    garantie de convergence de la dichotomie tout en atteignant en pratique une convergence
    superlinéaire. C'est la méthode de référence du produit pour les problèmes à une inconnue
    (D-v2 § 5.6).

    ``tolerance`` porte sur le **résidu**. ``variable_tolerance`` porte sur l'abscisse et sert
    uniquement à sécuriser les pas de Brent. Séparer ces unités évite notamment d'utiliser
    une tolérance en pascals sur une inconnue exprimée en m³/s.
    """
    x_tolerance = tolerance if variable_tolerance is None else variable_tolerance
    if x_tolerance < 0.0:
        raise ValueError("La tolérance sur l'inconnue doit être positive ou nulle.")
    a, b = lower, upper
    fa, fb = f(a), f(b)

    if fa * fb > 0.0:
        raise NoPhysicalSolutionError(
            "L'intervalle fourni n'encadre pas de racine : la fonction résidu garde le même "
            "signe à ses deux bornes.",
            lower=lower,
            upper=upper,
            residual_lower=fa,
            residual_upper=fb,
        )

    if abs(fa) < abs(fb):
        a, b = b, a
        fa, fb = fb, fa

    c, fc = a, fa
    mflag = True
    d = 0.0

    for iteration in range(1, max_iterations + 1):
        if abs(fb) <= tolerance:
            if diagnostics is not None:
                diagnostics.method = "brent"
                diagnostics.converged = True
                diagnostics.iterations = iteration
                diagnostics.residual = abs(fb)
                diagnostics.tolerance = tolerance
            return RootResult(
                root=b, residual=fb, iterations=iteration, method="brent", bracket=(lower, upper)
            )

        if fa != fc and fb != fc:
            # Interpolation quadratique inverse.
            s = (
                a * fb * fc / ((fa - fb) * (fa - fc))
                + b * fa * fc / ((fb - fa) * (fb - fc))
                + c * fa * fb / ((fc - fa) * (fc - fb))
            )
        else:
            # Sécante.
            s = b - fb * (b - a) / (fb - fa)

        # Conditions de Brent : on retombe sur la dichotomie si le pas proposé est douteux.
        delta = abs(2e-15 * abs(b)) + 0.5 * x_tolerance
        conditions = (
            not ((3 * a + b) / 4 < s < b or b < s < (3 * a + b) / 4),
            mflag and abs(s - b) >= abs(b - c) / 2,
            (not mflag) and abs(s - b) >= abs(c - d) / 2,
            mflag and abs(b - c) < delta,
            (not mflag) and abs(c - d) < delta,
        )
        if any(conditions):
            s = 0.5 * (a + b)
            mflag = True
        else:
            mflag = False

        fs = f(s)
        if log_iterations and diagnostics is not None:
            diagnostics.record_iteration(iteration, x=s, residual=fs)

        d, c, fc = c, b, fb
        if fa * fs < 0.0:
            b, fb = s, fs
        else:
            a, fa = s, fs
        if abs(fa) < abs(fb):
            a, b = b, a
            fa, fb = fb, fa

    if diagnostics is not None:
        diagnostics.method = "brent"
        diagnostics.converged = False
        diagnostics.iterations = max_iterations
        diagnostics.residual = abs(fb)
        diagnostics.tolerance = tolerance
    raise NotConvergedError(
        f"La méthode de Brent n'a pas atteint la tolérance {tolerance:.3g} en "
        f"{max_iterations} itérations ; résidu final {abs(fb):.6g}.",
        residual=abs(fb),
        iterations=max_iterations,
    )


def damped_newton(
    f: Callable[[float], float],
    x0: float,
    *,
    tolerance: float,
    max_iterations: int = 100,
    derivative: Callable[[float], float] | None = None,
    step_perturbation: float = 1e-6,
    lower_bound: float | None = None,
    upper_bound: float | None = None,
    diagnostics: SolverDiagnostics | None = None,
    log_iterations: bool = False,
) -> RootResult:
    """Newton amorti à une dimension, avec dérivée analytique ou différence centrée.

    L'amortissement divise le pas par deux tant que le résidu ne décroît pas, ce qui évite les
    divergences classiques du Newton pur sur les fonctions fortement non linéaires. Les bornes
    optionnelles empêchent l'itéré de sortir du domaine physique.

    Cette méthode est proposée pour les problèmes où la dérivée est fiable ; le moteur lui
    préfère Brent lorsqu'un encadrement est disponible, car Brent ne peut pas diverger.
    """

    def derivative_at(x: float) -> float:
        if derivative is not None:
            return derivative(x)
        h = step_perturbation * max(abs(x), 1.0)
        return (f(x + h) - f(x - h)) / (2.0 * h)

    x = x0
    fx = f(x)
    for iteration in range(1, max_iterations + 1):
        if abs(fx) <= tolerance:
            if diagnostics is not None:
                diagnostics.method = "newton-damped"
                diagnostics.converged = True
                diagnostics.iterations = iteration
                diagnostics.residual = abs(fx)
                diagnostics.tolerance = tolerance
            return RootResult(root=x, residual=fx, iterations=iteration, method="newton-damped")

        slope = derivative_at(x)
        if not math.isfinite(slope) or abs(slope) < 1e-30:
            raise NotConvergedError(
                "La dérivée de la fonction résidu est nulle ou non finie : Newton ne peut pas "
                "progresser. Un encadrement est nécessaire.",
                residual=abs(fx),
                iterations=iteration,
            )

        step = fx / slope
        damping = 1.0
        for _ in range(30):
            candidate = x - damping * step
            if lower_bound is not None:
                candidate = max(candidate, lower_bound)
            if upper_bound is not None:
                candidate = min(candidate, upper_bound)
            f_candidate = f(candidate)
            if abs(f_candidate) < abs(fx) or damping < 1e-8:
                x, fx = candidate, f_candidate
                break
            damping *= 0.5
        else:  # pragma: no cover - garde théorique
            break

        if log_iterations and diagnostics is not None:
            diagnostics.record_iteration(iteration, x=x, residual=fx, damping=damping)

    if diagnostics is not None:
        diagnostics.method = "newton-damped"
        diagnostics.converged = False
        diagnostics.iterations = max_iterations
        diagnostics.residual = abs(fx)
        diagnostics.tolerance = tolerance
    raise NotConvergedError(
        f"Newton amorti n'a pas atteint la tolérance {tolerance:.3g} en {max_iterations} "
        f"itérations ; résidu final {abs(fx):.6g}.",
        residual=abs(fx),
        iterations=max_iterations,
    )


def solve_monotonic(
    f: Callable[[float], float],
    *,
    lower: float,
    upper: float,
    tolerance: float,
    variable_tolerance: float | None = None,
    hard_upper: float | None = None,
    max_iterations: int = 100,
    diagnostics: SolverDiagnostics | None = None,
    log_iterations: bool = False,
) -> RootResult:
    """Résout ``f(x) = 0`` pour une fonction monotone, en cherchant d'abord un encadrement.

    C'est la méthode employée par le moteur longue distance pour trouver le débit compatible
    avec les conditions aux limites (cas UC-06 et V-006). L'encadrement est élargi
    automatiquement ; s'il ne peut pas être trouvé, l'absence de solution physique est
    signalée explicitement plutôt que masquée par une valeur arbitraire.
    """
    bracket = bracket_root(f, lower, upper, hard_upper=hard_upper)
    if bracket[0] == bracket[1]:
        if diagnostics is not None:
            diagnostics.method = "bracket-exact"
            diagnostics.converged = True
            diagnostics.iterations = 1
            diagnostics.residual = 0.0
            diagnostics.tolerance = tolerance
        return RootResult(
            root=bracket[0], residual=0.0, iterations=1, method="bracket-exact", bracket=bracket
        )
    return brent(
        f,
        bracket[0],
        bracket[1],
        tolerance=tolerance,
        variable_tolerance=variable_tolerance,
        max_iterations=max_iterations,
        diagnostics=diagnostics,
        log_iterations=log_iterations,
    )


def solve_hybrid(
    f: Callable[[float], float],
    *,
    initial_guess: float,
    lower: float,
    upper: float,
    tolerance: float,
    max_iterations: int = 100,
    diagnostics: SolverDiagnostics | None = None,
    log_iterations: bool = False,
) -> RootResult:
    """Newton amorti, avec repli **journalisé** sur l'encadrement et Brent.

    Le repli est enregistré dans ``diagnostics.fallback_used`` et dans les messages, afin que
    la note de calcul indique quelle méthode a réellement produit le résultat (D07 § 7 :
    « basculement journalisé »).
    """
    try:
        return damped_newton(
            f,
            initial_guess,
            tolerance=tolerance,
            max_iterations=max_iterations,
            lower_bound=lower,
            upper_bound=upper,
            diagnostics=diagnostics,
            log_iterations=log_iterations,
        )
    except (NotConvergedError, NoPhysicalSolutionError) as exc:
        if diagnostics is not None:
            diagnostics.fallback_used = True
            diagnostics.note(
                f"Newton amorti a échoué ({exc.message}) ; repli sur encadrement et Brent."
            )
        result = solve_monotonic(
            f,
            lower=lower,
            upper=upper,
            tolerance=tolerance,
            max_iterations=max_iterations,
            diagnostics=diagnostics,
            log_iterations=log_iterations,
        )
        if diagnostics is not None:
            diagnostics.fallback_used = True
            diagnostics.method = f"{result.method} (repli)"
        return result
