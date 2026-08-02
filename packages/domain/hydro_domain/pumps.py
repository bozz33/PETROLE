"""Pompes centrifuges : courbes constructeur, ajustement, vitesse variable et NPSH.

Règle fondamentale (D07 § 6, FR-PMP-002) : *les points expérimentaux H(Q), η(Q), P(Q) et
NPSHr(Q) restent la source principale. L'approximation polynomiale sert au calcul mais ne
doit pas effacer les limites et les points d'origine.*

En conséquence, :class:`PumpCurve` conserve toujours les points constructeur et expose
séparément :

- une interpolation monotone, utilisée par défaut ;
- un ajustement ``H = a − b·Q²`` par moindres carrés, disponible en option et accompagné de
  son erreur d'ajustement (cas de validation VAL-PMP-002).

Le domaine de validité est explicite : toute évaluation en dehors de ``[q_min ; q_max]`` est
signalée (``WARN_PUMP_EXTRAPOLATION_NEAR_LIMIT``, contrôle C-006).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from hydro_shared.errors import PumpCurveError

from hydro_domain.enums import EquipmentStatus, PumpRole
from hydro_domain.interpolation import (
    ExtrapolationPolicy,
    InterpolationKind,
    MonotoneTable,
)

#: Accélération de la pesanteur normale (CGPM 1901), en m/s².
G = 9.80665


@dataclass(frozen=True, slots=True)
class QuadraticFit:
    """Ajustement ``H = a − b·Q²`` par moindres carrés, avec ses indicateurs d'erreur.

    La linéarisation par ``X = Q²`` transforme le problème en régression linéaire simple, ce
    qui donne une solution analytique exacte — la méthode décrite par le support académique
    fourni et reproduite dans le cas de validation VAL-PMP-002.

    Les débits sont en m³/s et les hauteurs en mètres : le coefficient ``b`` est donc exprimé
    en s²/m⁵, et non dans les unités du support d'origine (m³/h).
    """

    a: float
    b: float
    rms_error_m: float
    max_error_m: float
    point_count: int

    def head(self, flow_m3_s: float) -> float:
        return self.a - self.b * flow_m3_s**2

    @property
    def shutoff_head_m(self) -> float:
        """Hauteur à débit nul, ``H(0) = a``."""
        return self.a

    @property
    def max_flow_m3_s(self) -> float:
        """Débit annulant la hauteur, borne théorique de l'ajustement."""
        if self.b <= 0:
            return math.inf
        return math.sqrt(self.a / self.b)

    def as_dict(self) -> dict[str, Any]:
        return {
            "a": self.a,
            "b": self.b,
            "rms_error_m": self.rms_error_m,
            "max_error_m": self.max_error_m,
            "point_count": self.point_count,
        }


def fit_quadratic_head(
    flows_m3_s: Sequence[float], heads_m: Sequence[float]
) -> QuadraticFit:
    """Ajuste ``H = a − b·Q²`` par moindres carrés sur les points fournis.

    Résolution analytique de la régression linéaire ``H = a + k·X`` avec ``X = Q²`` et
    ``b = −k`` :

    .. math::

        k = \\frac{n\\sum X H - \\sum X \\sum H}{n\\sum X^2 - (\\sum X)^2},
        \\qquad a = \\frac{\\sum H - k \\sum X}{n}

    Lève :class:`PumpCurveError` si moins de trois points sont fournis (deux points
    définiraient exactement la parabole sans permettre d'estimer l'erreur d'ajustement) ou si
    tous les débits sont identiques (dénominateur nul).
    """
    n = len(flows_m3_s)
    if n != len(heads_m):
        raise PumpCurveError(
            "Le nombre de débits et de hauteurs doit être identique.",
            flow_count=n,
            head_count=len(heads_m),
        )
    if n < 3:
        raise PumpCurveError(
            "L'ajustement H = a − b·Q² exige au moins trois points pour estimer son erreur.",
            point_count=n,
        )

    xs = [q * q for q in flows_m3_s]
    sum_x = sum(xs)
    sum_h = sum(heads_m)
    sum_x2 = sum(x * x for x in xs)
    sum_xh = sum(x * h for x, h in zip(xs, heads_m, strict=True))

    denominator = n * sum_x2 - sum_x * sum_x
    if abs(denominator) < 1e-30:
        raise PumpCurveError(
            "Les débits fournis sont tous identiques : l'ajustement quadratique est indéterminé.",
            point_count=n,
        )

    k = (n * sum_xh - sum_x * sum_h) / denominator
    a = (sum_h - k * sum_x) / n
    b = -k

    residuals = [h - (a - b * q * q) for q, h in zip(flows_m3_s, heads_m, strict=True)]
    rms = math.sqrt(sum(r * r for r in residuals) / n)
    return QuadraticFit(
        a=a,
        b=b,
        rms_error_m=rms,
        max_error_m=max(abs(r) for r in residuals),
        point_count=n,
    )


@dataclass(frozen=True, slots=True)
class CurveEvaluation:
    """Point de fonctionnement évalué sur une courbe de pompe."""

    head_m: float
    efficiency: float | None = None
    power_w: float | None = None
    npshr_m: float | None = None
    extrapolated: bool = False
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "head_m": self.head_m,
            "efficiency": self.efficiency,
            "power_w": self.power_w,
            "npshr_m": self.npshr_m,
            "extrapolated": self.extrapolated,
            "detail": self.detail,
        }


class PumpCurve:
    """Courbes constructeur d'une pompe à sa vitesse de référence.

    Les débits sont en m³/s, les hauteurs et NPSHr en mètres de colonne de fluide, les
    puissances en watts et le rendement en fraction (0–1).

    ``H(Q)`` est obligatoire ; ``η(Q)``, ``P(Q)`` et ``NPSHr(Q)`` sont facultatifs mais
    conditionnent les contrôles C-003 (cavitation) et C-007 (puissance moteur).
    """

    __slots__ = (
        "_efficiency",
        "_fit",
        "_flows",
        "_head",
        "_heads",
        "_npshr",
        "_power",
        "reference_speed_rpm",
    )

    def __init__(
        self,
        flows_m3_s: Sequence[float],
        heads_m: Sequence[float],
        *,
        efficiencies: Sequence[float] | None = None,
        powers_w: Sequence[float] | None = None,
        npshr_m: Sequence[float] | None = None,
        reference_speed_rpm: float | None = None,
        interpolation: InterpolationKind = InterpolationKind.PCHIP,
    ) -> None:
        if len(flows_m3_s) < 2:
            raise PumpCurveError(
                "Une courbe de pompe exige au moins deux points de débit.",
                point_count=len(flows_m3_s),
            )
        if any(q < 0 for q in flows_m3_s):
            raise PumpCurveError("Les débits d'une courbe de pompe ne peuvent pas être négatifs.")
        if any(h < 0 for h in heads_m):
            raise PumpCurveError(
                "Les hauteurs manométriques d'une courbe de pompe ne peuvent pas être négatives."
            )

        self._flows = tuple(float(q) for q in flows_m3_s)
        self._heads = tuple(float(h) for h in heads_m)
        self.reference_speed_rpm = reference_speed_rpm

        self._head = MonotoneTable(
            self._flows,
            self._heads,
            kind=interpolation,
            extrapolation=ExtrapolationPolicy.LINEAR,
            label="courbe H(Q)",
            error_type=PumpCurveError,
        )
        # La caractéristique d'une pompe centrifuge est décroissante sur son domaine
        # d'exploitation. L'exiger strictement garantit qu'un point de fonctionnement
        # pompe-réseau existe et qu'il est unique, et rend la courbe inversible pour la
        # résolution du partage de débit en parallèle.
        strictly_decreasing = all(
            b < a for a, b in zip(self._heads, self._heads[1:], strict=False)
        )
        if not strictly_decreasing:
            raise PumpCurveError(
                "La courbe H(Q) doit être strictement décroissante pour qu'un point de "
                "fonctionnement soit unique ; vérifiez les points saisis.",
                heads=list(self._heads),
            )

        self._efficiency = self._optional_table(efficiencies, "courbe η(Q)")
        self._power = self._optional_table(powers_w, "courbe P(Q)")
        self._npshr = self._optional_table(npshr_m, "courbe NPSHr(Q)")

        if efficiencies is not None and any(not 0.0 < e <= 1.0 for e in efficiencies):
            raise PumpCurveError(
                "Le rendement doit être exprimé en fraction dans l'intervalle ]0 ; 1].",
                efficiencies=list(efficiencies),
            )

        self._fit: QuadraticFit | None = None

    def _optional_table(
        self, values: Sequence[float] | None, label: str
    ) -> MonotoneTable | None:
        if values is None:
            return None
        if len(values) != len(self._flows):
            raise PumpCurveError(
                f"{label} : le nombre de valeurs doit correspondre au nombre de débits.",
                expected=len(self._flows),
                received=len(values),
            )
        return MonotoneTable(
            self._flows,
            values,
            kind=InterpolationKind.LINEAR,
            extrapolation=ExtrapolationPolicy.CLAMP,
            label=label,
            error_type=PumpCurveError,
        )

    # ------------------------------------------------------------------ propriétés

    @property
    def flows_m3_s(self) -> tuple[float, ...]:
        return self._flows

    @property
    def heads_m(self) -> tuple[float, ...]:
        return self._heads

    @property
    def q_min_m3_s(self) -> float:
        return self._flows[0]

    @property
    def q_max_m3_s(self) -> float:
        return self._flows[-1]

    @property
    def has_efficiency(self) -> bool:
        return self._efficiency is not None

    @property
    def has_npshr(self) -> bool:
        return self._npshr is not None

    @property
    def quadratic_fit(self) -> QuadraticFit:
        """Ajustement ``H = a − b·Q²``, calculé à la demande et mis en cache."""
        if self._fit is None:
            self._fit = fit_quadratic_head(self._flows, self._heads)
        return self._fit

    def best_efficiency_point(self) -> tuple[float, float] | None:
        """Point de meilleur rendement (BEP) parmi les points constructeur.

        La recherche porte sur les points saisis et non sur l'interpolation : le BEP annoncé
        par le constructeur est un point mesuré, il ne doit pas être déplacé par un lissage.
        """
        if self._efficiency is None:
            return None
        efficiencies = self._efficiency.y
        index = max(range(len(efficiencies)), key=efficiencies.__getitem__)
        return (self._flows[index], efficiencies[index])

    # ------------------------------------------------------------------ évaluation

    def evaluate(self, flow_m3_s: float, *, speed_ratio: float = 1.0) -> CurveEvaluation:
        """Évalue la pompe au débit demandé, à la fraction de vitesse indiquée.

        Les lois d'affinité (D07 § 6) s'écrivent, pour un rapport de vitesse ``s = N/N₀`` :

        .. math::

            Q = s\\,Q_0,\\qquad H = s^2 H_0,\\qquad P = s^3 P_0

        Le rendement est supposé conservé pour un même point homologue, hypothèse usuelle des
        lois de similitude et valable tant que ``s`` reste proche de 1. Toute évaluation hors
        du domaine constructeur, ou à vitesse fortement réduite, est signalée.
        """
        if speed_ratio <= 0:
            raise PumpCurveError(
                "Le rapport de vitesse doit être strictement positif.", speed_ratio=speed_ratio
            )

        equivalent_flow = flow_m3_s / speed_ratio
        head_eval = self._head.evaluate(equivalent_flow)
        head = head_eval.value * speed_ratio**2

        efficiency = None
        if self._efficiency is not None:
            efficiency = self._efficiency.evaluate(equivalent_flow).value

        power = None
        if self._power is not None:
            power = self._power.evaluate(equivalent_flow).value * speed_ratio**3

        npshr = None
        if self._npshr is not None:
            npshr = self._npshr.evaluate(equivalent_flow).value * speed_ratio**2

        details: list[str] = []
        if head_eval.extrapolated:
            details.append(
                f"Débit équivalent {equivalent_flow * 3600:.1f} m³/h hors du domaine constructeur "
                f"[{self.q_min_m3_s * 3600:.1f} ; {self.q_max_m3_s * 3600:.1f}] m³/h."
            )
        if abs(speed_ratio - 1.0) > 0.5:
            details.append(
                f"Rapport de vitesse {speed_ratio:.2f} très éloigné de la vitesse de référence : "
                f"les lois d'affinité ne sont plus fiables."
            )

        return CurveEvaluation(
            head_m=max(head, 0.0),
            efficiency=efficiency,
            power_w=power,
            npshr_m=npshr,
            extrapolated=head_eval.extrapolated,
            detail=" ".join(details) if details else None,
        )

    def head(self, flow_m3_s: float, *, speed_ratio: float = 1.0) -> float:
        """Hauteur fournie, en mètres de colonne de fluide."""
        return self.evaluate(flow_m3_s, speed_ratio=speed_ratio).head_m

    def is_within_domain(self, flow_m3_s: float, *, speed_ratio: float = 1.0) -> bool:
        equivalent = flow_m3_s / speed_ratio
        return self.q_min_m3_s <= equivalent <= self.q_max_m3_s

    def as_dict(self) -> dict[str, Any]:
        return {
            "flows_m3_s": list(self._flows),
            "heads_m": list(self._heads),
            "efficiencies": self._efficiency.y if self._efficiency else None,
            "powers_w": self._power.y if self._power else None,
            "npshr_m": self._npshr.y if self._npshr else None,
            "reference_speed_rpm": self.reference_speed_rpm,
        }


@dataclass(frozen=True, slots=True)
class PumpModel:
    """Référence catalogue d'une pompe (D09 § 5).

    Une même référence peut être instanciée dans plusieurs stations ; les paramètres propres
    à l'installation (rôle, état, vitesse) appartiennent à :class:`PumpInstance`.
    """

    id: str
    name: str
    curve: PumpCurve
    manufacturer: str | None = None
    #: Puissance nominale du moteur d'entraînement, en watts (contrôle C-007).
    motor_rated_power_w: float | None = None
    #: Marge de sécurité NPSH exigée par le projet, en mètres (contrôle C-003).
    npsh_margin_m: float = 0.5
    #: Bornes de vitesse admissibles pour une pompe à vitesse variable, en fraction.
    min_speed_ratio: float = 0.7
    max_speed_ratio: float = 1.0
    #: Débit minimal continu admissible constructeur, en m³/s.
    minimum_continuous_flow_m3_s: float | None = None
    data_source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.motor_rated_power_w is not None and self.motor_rated_power_w <= 0:
            raise PumpCurveError(
                f"Pompe {self.name} : la puissance moteur doit être strictement positive."
            )
        if self.npsh_margin_m < 0:
            raise PumpCurveError(f"Pompe {self.name} : la marge NPSH ne peut pas être négative.")
        if not 0 < self.min_speed_ratio <= self.max_speed_ratio:
            raise PumpCurveError(
                f"Pompe {self.name} : les bornes de vitesse sont incohérentes "
                f"({self.min_speed_ratio} ; {self.max_speed_ratio})."
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "manufacturer": self.manufacturer,
            "curve": self.curve.as_dict(),
            "motor_rated_power_w": self.motor_rated_power_w,
            "npsh_margin_m": self.npsh_margin_m,
            "min_speed_ratio": self.min_speed_ratio,
            "max_speed_ratio": self.max_speed_ratio,
            "minimum_continuous_flow_m3_s": self.minimum_continuous_flow_m3_s,
            "data_source": self.data_source,
        }


@dataclass(frozen=True, slots=True)
class PumpInstance:
    """Pompe installée dans une station.

    ``running`` traduit l'état commandé par le scénario : une pompe disponible mais à l'arrêt
    ne fournit aucune hauteur et ne consomme aucune énergie. Une pompe de secours est
    disponible mais ne démarre que si le scénario l'active (FR-PMP-004).
    """

    id: str
    model: PumpModel
    role: PumpRole = PumpRole.MAIN
    status: EquipmentStatus = EquipmentStatus.AVAILABLE
    running: bool = True
    speed_ratio: float = 1.0
    label: str | None = None

    def __post_init__(self) -> None:
        if not self.model.min_speed_ratio <= self.speed_ratio <= self.model.max_speed_ratio:
            raise PumpCurveError(
                f"Pompe {self.id} : le rapport de vitesse {self.speed_ratio} sort des bornes "
                f"constructeur [{self.model.min_speed_ratio} ; {self.model.max_speed_ratio}].",
                pump_id=self.id,
            )

    @property
    def is_active(self) -> bool:
        """Vrai si la pompe contribue effectivement à la hauteur fournie par la station."""
        return self.status is EquipmentStatus.AVAILABLE and self.running

    @property
    def display_name(self) -> str:
        return self.label or f"{self.model.name} ({self.id})"

    def evaluate(self, flow_m3_s: float) -> CurveEvaluation:
        """Évalue la pompe au débit qui la traverse, à sa vitesse courante."""
        return self.model.curve.evaluate(flow_m3_s, speed_ratio=self.speed_ratio)

    def head(self, flow_m3_s: float) -> float:
        """Hauteur fournie ; nulle si la pompe n'est pas active."""
        if not self.is_active:
            return 0.0
        return self.evaluate(flow_m3_s).head_m

    def with_state(
        self,
        *,
        status: EquipmentStatus | None = None,
        running: bool | None = None,
        speed_ratio: float | None = None,
    ) -> PumpInstance:
        """Copie avec un autre état, pour l'application d'un override de scénario."""
        return PumpInstance(
            id=self.id,
            model=self.model,
            role=self.role,
            status=self.status if status is None else status,
            running=self.running if running is None else running,
            speed_ratio=self.speed_ratio if speed_ratio is None else speed_ratio,
            label=self.label,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "model_id": self.model.id,
            "role": self.role.value,
            "status": self.status.value,
            "running": self.running,
            "speed_ratio": self.speed_ratio,
        }


def hydraulic_power_w(flow_m3_s: float, head_m: float, density_kg_m3: float) -> float:
    """Puissance hydraulique ``P_h = ρ g Q H`` en watts (D07 § 6)."""
    return density_kg_m3 * G * flow_m3_s * head_m


def absorbed_power_w(hydraulic_power: float, efficiency: float) -> float:
    """Puissance absorbée ``P_abs = P_h / η`` en watts.

    Lève une erreur si le rendement est nul ou négatif : une division silencieuse produirait
    une puissance infinie que le contrôle C-007 interpréterait à tort.
    """
    if efficiency <= 0:
        raise PumpCurveError(
            "Le rendement doit être strictement positif pour calculer la puissance absorbée.",
            efficiency=efficiency,
        )
    return hydraulic_power / efficiency
