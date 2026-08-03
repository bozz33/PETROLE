"""Hydraulique des conduites en charge : Reynolds, frottement et pertes de charge.

Équations de référence (D07 § 4 et § 5) :

.. math::

    v = \\frac{4Q}{\\pi D^2},
    \\qquad
    \\mathrm{Re} = \\frac{vD}{\\nu},
    \\qquad
    h_f = \\lambda \\frac{L}{D} \\frac{v^2}{2g},
    \\qquad
    h_m = \\sum K \\frac{v^2}{2g}

Le facteur de frottement est obtenu par la corrélation sélectionnée dans le scénario
(FR-LIQ-009). Colebrook–White est la référence ; les formes explicites servent de comparaison
et d'initialisation, et la corrélation d'Altshul est conservée pour reproduire à l'identique
le cas académique de 460 km (D10 § 5).

Toutes les fonctions sont pures et travaillent en unités SI. Elles sont testées contre des
valeurs analytiques et contre la bibliothèque ``fluids`` (D18 § 3).
"""

from __future__ import annotations

import math

from hydro_domain.enums import FrictionModel

#: Accélération de la pesanteur normale, en m/s².
G = 9.80665

#: Borne supérieure conventionnelle du régime laminaire.
LAMINAR_LIMIT_RE = 2000.0
#: Borne inférieure conventionnelle du régime pleinement turbulent.
TURBULENT_LIMIT_RE = 4000.0
#: Reynolds en deçà duquel l'écoulement est considéré comme nul (garde numérique).
NEGLIGIBLE_RE = 1e-9


def flow_area_m2(inner_diameter_m: float) -> float:
    """Section de passage d'une conduite circulaire, ``A = π D² / 4``."""
    return math.pi * inner_diameter_m * inner_diameter_m / 4.0


def velocity_m_s(flow_m3_s: float, inner_diameter_m: float) -> float:
    """Vitesse débitante ``v = Q / A``, en m/s. Le signe suit celui du débit."""
    return flow_m3_s / flow_area_m2(inner_diameter_m)


def reynolds(velocity: float, inner_diameter_m: float, kinematic_viscosity_m2_s: float) -> float:
    """Nombre de Reynolds ``Re = |v| D / ν``.

    La valeur absolue de la vitesse est utilisée : le régime d'écoulement ne dépend pas du
    sens de circulation, et un Reynolds négatif n'aurait pas de sens dans les corrélations.
    """
    if kinematic_viscosity_m2_s <= 0.0:
        raise ValueError(
            f"La viscosité cinématique doit être strictement positive "
            f"(reçue : {kinematic_viscosity_m2_s})."
        )
    return abs(velocity) * inner_diameter_m / kinematic_viscosity_m2_s


# --------------------------------------------------------------------------- frottement


def friction_laminar(re: float) -> float:
    """Régime laminaire : ``λ = 64/Re`` (conduite circulaire, fluide newtonien)."""
    if re < NEGLIGIBLE_RE:
        # Débit nul : la perte de charge est nulle quelle que soit la valeur retournée.
        # On évite une division par zéro sans introduire de valeur physique arbitraire.
        return 0.0
    return 64.0 / re


def friction_haaland(re: float, relative_roughness: float) -> float:
    """Approximation explicite de Haaland (1983).

    .. math::

        \\frac{1}{\\sqrt{\\lambda}} = -1{,}8 \\log_{10}\\left[
        \\left(\\frac{\\varepsilon/D}{3{,}7}\\right)^{1,11} + \\frac{6{,}9}{\\mathrm{Re}}\\right]

    Écart typique à Colebrook–White inférieur à 2 % sur le domaine turbulent usuel.
    """
    term = (relative_roughness / 3.7) ** 1.11 + 6.9 / re
    inv_sqrt = -1.8 * math.log10(term)
    return 1.0 / (inv_sqrt * inv_sqrt)


def friction_swamee_jain(re: float, relative_roughness: float) -> float:
    """Approximation explicite de Swamee–Jain (1976).

    .. math::

        \\lambda = \\frac{0{,}25}{\\left[\\log_{10}\\left(
        \\frac{\\varepsilon/D}{3{,}7} + \\frac{5{,}74}{\\mathrm{Re}^{0,9}}\\right)\\right]^2}

    Domaine de validité annoncé : ``10⁻⁶ ≤ ε/D ≤ 10⁻²`` et ``5·10³ ≤ Re ≤ 10⁸``.
    """
    denominator = math.log10(relative_roughness / 3.7 + 5.74 / re**0.9)
    return 0.25 / (denominator * denominator)


def friction_altshul(re: float, relative_roughness: float) -> float:
    """Corrélation d'Altshul, forme universelle.

    .. math::

        \\lambda = 0{,}11 \\left(\\frac{\\varepsilon}{D} + \\frac{68}{\\mathrm{Re}}\\right)^{0,25}

    Cette corrélation est employée par le support académique fourni. Elle est conservée pour
    reproduire à l'identique le cas de référence de 460 km (D10 § 5) et pour permettre la
    comparaison avec Colebrook–White ; elle n'est pas la corrélation par défaut du produit.
    """
    return 0.11 * (relative_roughness + 68.0 / re) ** 0.25


def friction_colebrook_white(
    re: float, relative_roughness: float, *, tolerance: float = 1e-12, max_iterations: int = 60
) -> float:
    """Colebrook–White, résolu implicitement.

    .. math::

        \\frac{1}{\\sqrt{\\lambda}} = -2 \\log_{10}\\left(
        \\frac{\\varepsilon/D}{3{,}7} + \\frac{2{,}51}{\\mathrm{Re}\\sqrt{\\lambda}}\\right)

    La résolution se fait par itération de point fixe sur ``x = 1/√λ``, initialisée par
    Swamee–Jain. Cette forme est **inconditionnellement convergente** : la fonction
    d'itération est contractante sur le domaine physique, ce qui évite les échecs d'un Newton
    mal initialisé. La convergence est atteinte en moins de dix itérations en pratique.

    Lève :class:`RuntimeError` si la tolérance n'est pas atteinte : le produit ne retourne
    jamais un facteur de frottement non convergé (FR-GEN-005).
    """
    x = 1.0 / math.sqrt(friction_swamee_jain(re, relative_roughness))
    for _ in range(max_iterations):
        x_next = -2.0 * math.log10(relative_roughness / 3.7 + 2.51 * x / re)
        if abs(x_next - x) < tolerance:
            return 1.0 / (x_next * x_next)
        x = x_next
    raise RuntimeError(
        f"Colebrook–White n'a pas convergé en {max_iterations} itérations "
        f"(Re={re:.4g}, ε/D={relative_roughness:.4g})."
    )


def _turbulent_friction(re: float, relative_roughness: float, model: FrictionModel) -> float:
    if model is FrictionModel.COLEBROOK_WHITE:
        return friction_colebrook_white(re, relative_roughness)
    if model is FrictionModel.HAALAND:
        return friction_haaland(re, relative_roughness)
    if model is FrictionModel.SWAMEE_JAIN:
        return friction_swamee_jain(re, relative_roughness)
    if model is FrictionModel.ALTSHUL:
        return friction_altshul(re, relative_roughness)
    raise ValueError(f"Modèle de frottement inconnu : {model!r}")


def friction_factor(
    re: float,
    relative_roughness: float,
    model: FrictionModel = FrictionModel.COLEBROOK_WHITE,
) -> float:
    """Facteur de frottement de Darcy sur l'ensemble des régimes.

    Stratégie de transition (D07 § 5, D-v2 § 5.3) : entre ``Re = 2 000`` et ``Re = 4 000``,
    aucune corrélation n'est physiquement fondée. Le produit interpole **linéairement** entre
    la valeur laminaire à 2 000 et la valeur turbulente à 4 000.

    Ce choix est délibéré et documenté :

    - il assure la **continuité** de ``λ(Re)``, indispensable à la convergence du solveur —
      un saut de facteur de frottement crée une discontinuité de la fonction résidu et fait
      échouer aussi bien Newton que la dichotomie ;
    - il est **monotone** et borné par les deux régimes encadrants ;
    - il est **signalé** : tout résultat calculé dans cette plage porte l'avertissement
      ``WARN_TRANSITION_REGIME``, car la valeur reste une convention, pas une mesure.

    La corrélation d'Altshul, continue par construction sur tout le domaine turbulent, est
    appliquée sans interpolation au-dessus de 2 000 lorsqu'elle est sélectionnée : c'est le
    comportement du support académique que le cas de référence doit reproduire.
    """
    if re < NEGLIGIBLE_RE:
        return 0.0
    if re < LAMINAR_LIMIT_RE:
        return friction_laminar(re)
    if model is FrictionModel.ALTSHUL:
        return friction_altshul(re, relative_roughness)
    if re >= TURBULENT_LIMIT_RE:
        return _turbulent_friction(re, relative_roughness, model)

    laminar = friction_laminar(LAMINAR_LIMIT_RE)
    turbulent = _turbulent_friction(TURBULENT_LIMIT_RE, relative_roughness, model)
    weight = (re - LAMINAR_LIMIT_RE) / (TURBULENT_LIMIT_RE - LAMINAR_LIMIT_RE)
    return laminar + weight * (turbulent - laminar)


def is_transition_regime(re: float) -> bool:
    """Vrai si le Reynolds tombe dans la zone de transition, qui exige un avertissement."""
    return LAMINAR_LIMIT_RE <= re < TURBULENT_LIMIT_RE


def flow_regime(re: float) -> str:
    """Libellé du régime d'écoulement, repris dans la note de calcul."""
    if re < LAMINAR_LIMIT_RE:
        return "laminaire"
    if re < TURBULENT_LIMIT_RE:
        return "transition"
    return "turbulent"


# --------------------------------------------------------------------------- pertes


def velocity_head_m(velocity: float) -> float:
    """Hauteur cinétique ``v²/(2g)``, en mètres."""
    return velocity * velocity / (2.0 * G)


def friction_head_loss_m(
    flow_m3_s: float,
    length_m: float,
    inner_diameter_m: float,
    roughness_m: float,
    kinematic_viscosity_m2_s: float,
    model: FrictionModel = FrictionModel.COLEBROOK_WHITE,
) -> float:
    """Perte de charge linéaire de Darcy–Weisbach, en mètres de colonne de fluide.

    .. math::

        h_f = \\lambda \\frac{L}{D} \\frac{v |v|}{2g}

    Le produit ``v|v|`` conserve le signe du débit : la perte s'oppose toujours à
    l'écoulement, ce qui est indispensable dans un solveur de réseau où le sens de
    circulation d'une branche est une inconnue.
    """
    velocity = velocity_m_s(flow_m3_s, inner_diameter_m)
    re = reynolds(velocity, inner_diameter_m, kinematic_viscosity_m2_s)
    lam = friction_factor(re, roughness_m / inner_diameter_m, model)
    return lam * (length_m / inner_diameter_m) * velocity * abs(velocity) / (2.0 * G)


def minor_head_loss_m(flow_m3_s: float, inner_diameter_m: float, total_k: float) -> float:
    """Perte de charge singulière ``h_m = ΣK · v|v|/(2g)``, en mètres."""
    if total_k == 0.0:
        return 0.0
    if math.isinf(total_k):
        # Un accessoire fermé interdit tout écoulement : la perte est infinie dès que le
        # débit est non nul, et nulle à débit nul.
        return 0.0 if flow_m3_s == 0.0 else math.copysign(math.inf, flow_m3_s)
    velocity = velocity_m_s(flow_m3_s, inner_diameter_m)
    return total_k * velocity * abs(velocity) / (2.0 * G)


def hydraulic_gradient(
    flow_m3_s: float,
    inner_diameter_m: float,
    roughness_m: float,
    kinematic_viscosity_m2_s: float,
    model: FrictionModel = FrictionModel.COLEBROOK_WHITE,
) -> float:
    """Gradient hydraulique ``i = h_f / L``, en mètre par mètre.

    C'est la grandeur naturelle pour parcourir un pipeline pas à pas : la perte sur un
    intervalle vaut ``i · Δx``, ce qui évite de recalculer le frottement à chaque sous-pas
    lorsque la géométrie et le débit sont constants.
    """
    return friction_head_loss_m(
        flow_m3_s, 1.0, inner_diameter_m, roughness_m, kinematic_viscosity_m2_s, model
    )


def pressure_to_head_m(pressure_pa: float, density_kg_m3: float) -> float:
    """Convertit une pression en hauteur de colonne de fluide, ``h = p/(ρg)``."""
    return pressure_pa / (density_kg_m3 * G)


def head_to_pressure_pa(head_m: float, density_kg_m3: float) -> float:
    """Convertit une hauteur de colonne de fluide en pression, ``p = ρgh``."""
    return head_m * density_kg_m3 * G


def total_head_m(pressure_pa: float, elevation_m: float, density_kg_m3: float) -> float:
    """Charge piézométrique ``H = z + p/(ρg)``, en mètres.

    La hauteur cinétique est omise : sur un oléoduc, ``v²/2g`` vaut quelques centimètres face
    à des charges de plusieurs centaines de mètres, et le diamètre étant constant sur un
    tronçon, ce terme se simplifie dans le bilan. Il est réintroduit explicitement là où il
    compte, notamment dans le calcul du NPSH disponible.
    """
    return elevation_m + pressure_to_head_m(pressure_pa, density_kg_m3)


def pressure_from_head_pa(head_m: float, elevation_m: float, density_kg_m3: float) -> float:
    """Pression déduite d'une charge et d'une altitude, ``p = ρg(H − z)``."""
    return head_to_pressure_pa(head_m - elevation_m, density_kg_m3)
