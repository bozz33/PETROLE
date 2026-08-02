"""Interpolation contrôlée des tables métier.

Trois tables du MVP doivent être interpolées **et** inversées de façon fiable :

- le profil altimétrique (chainage → altitude) ;
- les courbes de pompe (débit → hauteur, rendement, puissance, NPSHr) ;
- la table de barémage d'un réservoir (hauteur → volume).

Ce module fournit un socle commun qui garantit trois propriétés indispensables :

1. la monotonie de l'abscisse est vérifiée à la construction (règles DQ-003 et DQ-004) ;
2. l'extrapolation est possible mais **toujours signalée** (contrôle C-011) ;
3. l'inversion d'une table monotone est exacte aux nœuds et cohérente entre les nœuds
   (exigence VAL-TNK-003 : « monotonie et inversion h(V) »).

L'interpolation par défaut est linéaire par morceaux : elle préserve la monotonie, ne crée
jamais d'oscillation parasite entre deux points de mesure et reste explicable dans une note
de calcul. Une interpolation par spline monotone (PCHIP) est proposée pour les courbes de
pompe, où la dérivée continue améliore la convergence du solveur.
"""

from __future__ import annotations

import bisect
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hydro_shared.errors import HydroError, InvalidInputError


class InterpolationKind(StrEnum):
    """Schémas d'interpolation autorisés."""

    #: Linéaire par morceaux : préserve la monotonie, aucune oscillation.
    LINEAR = "linear"
    #: Spline cubique monotone (PCHIP) : dérivée continue, monotonie préservée.
    PCHIP = "pchip"


class ExtrapolationPolicy(StrEnum):
    """Comportement hors du domaine tabulé."""

    #: Prolongement linéaire à partir des deux points extrêmes ; signalé.
    LINEAR = "linear"
    #: Maintien de la valeur extrême ; signalé.
    CLAMP = "clamp"
    #: Refus : lève une erreur explicite.
    FORBID = "forbid"


@dataclass(frozen=True, slots=True)
class TableEvaluation:
    """Valeur interpolée accompagnée de son statut d'extrapolation."""

    value: float
    extrapolated: bool
    detail: str | None = None


class MonotoneTable:
    """Table à abscisse strictement croissante, interpolable et inversible.

    L'inversion n'est autorisée que si les ordonnées sont elles aussi monotones : sans cette
    condition, ``inverse`` n'aurait pas de solution unique et le produit ne doit pas prétendre
    en fournir une (par exemple pour une table de barémage non monotone, règle DQ-004).
    """

    __slots__ = (
        "_error_type",
        "_kind",
        "_pchip",
        "_policy",
        "_x",
        "_y",
        "_y_increasing",
        "label",
    )

    def __init__(
        self,
        x: Sequence[float],
        y: Sequence[float],
        *,
        kind: InterpolationKind = InterpolationKind.LINEAR,
        extrapolation: ExtrapolationPolicy = ExtrapolationPolicy.LINEAR,
        label: str = "table",
        error_type: type[HydroError] = InvalidInputError,
    ) -> None:
        if len(x) != len(y):
            raise error_type(
                f"{label} : les abscisses et les ordonnées doivent avoir la même longueur.",
                x_count=len(x),
                y_count=len(y),
            )
        if len(x) < 2:
            raise error_type(
                f"{label} : au moins deux points sont nécessaires pour interpoler.",
                point_count=len(x),
            )
        xs = [float(v) for v in x]
        ys = [float(v) for v in y]
        for i in range(len(xs) - 1):
            if xs[i + 1] <= xs[i]:
                raise error_type(
                    f"{label} : les abscisses doivent être strictement croissantes ; "
                    f"rupture à l'indice {i + 1} ({xs[i]} → {xs[i + 1]}).",
                    index=i + 1,
                    previous=xs[i],
                    current=xs[i + 1],
                )
        self._x = xs
        self._y = ys
        self._kind = kind
        self._policy = extrapolation
        # Le type d'erreur est conservé pour que le code remonté reste celui de la table
        # concernée (``ERR_TANK_TABLE_INVALID``, ``ERR_PROFILE_NOT_MONOTONIC``…), y compris
        # lors des dépassements de domaine détectés à l'évaluation et non à la construction.
        self._error_type = error_type
        self.label = label
        self._y_increasing = self._detect_monotonicity(ys)
        self._pchip: Any = None
        if kind is InterpolationKind.PCHIP:
            self._pchip = self._build_pchip(xs, ys)

    # ------------------------------------------------------------------ construction

    @staticmethod
    def _detect_monotonicity(ys: Sequence[float]) -> bool | None:
        """Retourne ``True`` si croissante, ``False`` si décroissante, ``None`` sinon."""
        increasing = all(b >= a for a, b in zip(ys, ys[1:], strict=False))
        decreasing = all(b <= a for a, b in zip(ys, ys[1:], strict=False))
        if increasing and not decreasing:
            return True
        if decreasing and not increasing:
            return False
        if increasing and decreasing:
            # Table constante : monotone au sens large mais non inversible.
            return None
        return None

    @staticmethod
    def _build_pchip(xs: Sequence[float], ys: Sequence[float]) -> Any:
        from scipy.interpolate import PchipInterpolator  # import local : coût de chargement

        return PchipInterpolator(xs, ys, extrapolate=True)

    # ------------------------------------------------------------------ accès

    @property
    def x(self) -> list[float]:
        return list(self._x)

    @property
    def y(self) -> list[float]:
        return list(self._y)

    @property
    def domain(self) -> tuple[float, float]:
        return (self._x[0], self._x[-1])

    @property
    def codomain(self) -> tuple[float, float]:
        return (min(self._y), max(self._y))

    @property
    def is_invertible(self) -> bool:
        """Vrai si les ordonnées sont **strictement** monotones.

        Une table seulement monotone au sens large comporte un palier : sur ce palier
        l'antécédent n'est pas unique, et le produit ne doit pas prétendre en fournir un.
        """
        if self._y_increasing is None:
            return False
        pairs = list(zip(self._y, self._y[1:], strict=False))
        if self._y_increasing:
            return all(b > a for a, b in pairs)
        return all(b < a for a, b in pairs)

    def contains(self, value: float) -> bool:
        return self._x[0] <= value <= self._x[-1]

    # ------------------------------------------------------------------ évaluation

    def evaluate(self, value: float) -> TableEvaluation:
        """Interpole en signalant explicitement toute sortie de domaine."""
        lo, hi = self.domain
        if lo <= value <= hi:
            return TableEvaluation(value=self._interpolate_inside(value), extrapolated=False)

        detail = (
            f"{self.label} : abscisse {value:.6g} hors du domaine tabulé "
            f"[{lo:.6g} ; {hi:.6g}]."
        )
        if self._policy is ExtrapolationPolicy.FORBID:
            raise self._error_type(detail, value=value, domain=(lo, hi))
        if self._policy is ExtrapolationPolicy.CLAMP:
            clamped = self._y[0] if value < lo else self._y[-1]
            return TableEvaluation(value=clamped, extrapolated=True, detail=detail)
        return TableEvaluation(
            value=self._extrapolate_linear(value), extrapolated=True, detail=detail
        )

    def __call__(self, value: float) -> float:
        """Raccourci retournant uniquement la valeur ; l'extrapolation reste silencieuse ici.

        À n'utiliser que dans un contexte où l'appelant a déjà vérifié le domaine, ou lorsque
        l'extrapolation est traitée séparément par :meth:`evaluate`.
        """
        return self.evaluate(value).value

    def _interpolate_inside(self, value: float) -> float:
        if self._pchip is not None:
            return float(self._pchip(value))
        i = bisect.bisect_right(self._x, value) - 1
        i = min(max(i, 0), len(self._x) - 2)
        x0, x1 = self._x[i], self._x[i + 1]
        y0, y1 = self._y[i], self._y[i + 1]
        t = (value - x0) / (x1 - x0)
        return y0 + t * (y1 - y0)

    def _extrapolate_linear(self, value: float) -> float:
        if value < self._x[0]:
            slope = (self._y[1] - self._y[0]) / (self._x[1] - self._x[0])
            return self._y[0] + slope * (value - self._x[0])
        slope = (self._y[-1] - self._y[-2]) / (self._x[-1] - self._x[-2])
        return self._y[-1] + slope * (value - self._x[-1])

    # ------------------------------------------------------------------ inversion

    def inverse(self, target: float) -> TableEvaluation:
        """Résout ``f(x) = target``. Exige une table strictement monotone.

        L'inversion est faite sur l'interpolation linéaire par morceaux, même lorsque la
        table est déclarée PCHIP : cela garantit une inversion exacte aux nœuds et une
        bijection stricte, ce qu'une spline ne garantit pas hors des nœuds.
        """
        if not self.is_invertible:
            raise self._error_type(
                f"{self.label} : la table n'est pas strictement monotone, son inversion n'a pas "
                f"de solution unique.",
                label=self.label,
            )
        ys = self._y if self._y_increasing else list(reversed(self._y))
        xs = self._x if self._y_increasing else list(reversed(self._x))

        y_lo, y_hi = ys[0], ys[-1]
        if target < y_lo or target > y_hi:
            detail = (
                f"{self.label} : valeur cible {target:.6g} hors de l'image tabulée "
                f"[{y_lo:.6g} ; {y_hi:.6g}]."
            )
            if self._policy is ExtrapolationPolicy.FORBID:
                raise self._error_type(detail, target=target, codomain=(y_lo, y_hi))
            if self._policy is ExtrapolationPolicy.CLAMP:
                return TableEvaluation(
                    value=xs[0] if target < y_lo else xs[-1], extrapolated=True, detail=detail
                )
            if target < y_lo:
                slope = (xs[1] - xs[0]) / (ys[1] - ys[0])
                value = xs[0] + slope * (target - y_lo)
            else:
                slope = (xs[-1] - xs[-2]) / (ys[-1] - ys[-2])
                value = xs[-1] + slope * (target - y_hi)
            return TableEvaluation(value=value, extrapolated=True, detail=detail)

        i = bisect.bisect_right(ys, target) - 1
        i = min(max(i, 0), len(ys) - 2)
        y0, y1 = ys[i], ys[i + 1]
        x0, x1 = xs[i], xs[i + 1]
        t = 0.0 if y1 == y0 else (target - y0) / (y1 - y0)
        return TableEvaluation(value=x0 + t * (x1 - x0), extrapolated=False)

    # ------------------------------------------------------------------ divers

    def derivative(self, value: float) -> float:
        """Pente locale df/dx, utile aux solveurs et à dh/dV pour les réservoirs."""
        if self._pchip is not None:
            return float(self._pchip.derivative()(value))
        i = bisect.bisect_right(self._x, value) - 1
        i = min(max(i, 0), len(self._x) - 2)
        return (self._y[i + 1] - self._y[i]) / (self._x[i + 1] - self._x[i])

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "kind": self._kind.value,
            "extrapolation": self._policy.value,
            "x": list(self._x),
            "y": list(self._y),
        }

    def __len__(self) -> int:
        return len(self._x)

    def __repr__(self) -> str:  # pragma: no cover - confort de débogage
        lo, hi = self.domain
        return f"MonotoneTable({self.label!r}, {len(self)} points, domaine=[{lo:.4g}; {hi:.4g}])"
