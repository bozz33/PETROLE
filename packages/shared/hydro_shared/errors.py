"""Exceptions de la plateforme, porteuses d'un code stable et d'un contexte structuré.

Règle (D13 § 9) : *une non-convergence du solveur n'est pas une erreur HTTP du serveur.*
Les exceptions de ce module servent aux entrées invalides et aux situations où aucun résultat
ne peut être produit ; le diagnostic scientifique passe par `SolverDiagnostics`.
"""

from __future__ import annotations

from typing import Any

from hydro_shared.codes import ErrorCode


class HydroError(Exception):
    """Base des erreurs métier. Porte un code stable et un contexte sérialisable."""

    code: str = "ERR_UNSPECIFIED"
    retryable: bool = False

    def __init__(self, message: str, /, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = context

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "context": self.context,
        }

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.context:
            details = ", ".join(f"{k}={v!r}" for k, v in sorted(self.context.items()))
            return f"[{self.code}] {self.message} ({details})"
        return f"[{self.code}] {self.message}"


class InvalidInputError(HydroError):
    """Donnée d'entrée invalide : le calcul n'est pas lancé."""

    code = ErrorCode.SCENARIO_INVALID.value

    def __init__(self, message: str, /, code: ErrorCode | None = None, **context: Any) -> None:
        super().__init__(message, **context)
        if code is not None:
            self.code = code.value


class UnknownUnitError(HydroError):
    """Unité non reconnue par le registre (``ERR_UNIT_UNKNOWN``, règle DQ-001)."""

    code = ErrorCode.UNIT_UNKNOWN.value

    def __init__(self, unit: str) -> None:
        super().__init__(
            f"Unité inconnue : {unit!r}. Utilisez une unité du registre "
            f"(exemples : 'bar', 'MPa', 'm ** 3 / hour', 'cSt').",
            unit=unit,
        )


class DimensionalityMismatchError(HydroError):
    """Unité incompatible avec la grandeur attendue (``ERR_UNIT_DIMENSION_MISMATCH``)."""

    code = ErrorCode.UNIT_DIMENSION_MISMATCH.value

    def __init__(self, unit: str, dimension: str, expected: str) -> None:
        super().__init__(
            f"L'unité {unit!r} n'est pas compatible avec la grandeur {dimension!r} "
            f"(unité interne attendue : {expected!r}).",
            unit=unit,
            dimension=dimension,
            expected=expected,
        )


class TopologyError(HydroError):
    """Réseau incohérent : nœud isolé, arête pendante, sens contradictoire."""

    code = ErrorCode.TOPOLOGY_INVALID.value


class BoundaryConditionError(HydroError):
    """Problème sous-contraint, sur-contraint ou contradictoire (D07 § 7)."""

    code = ErrorCode.BOUNDARY_CONDITIONS_INVALID.value


class PumpCurveError(HydroError):
    """Courbe de pompe incohérente ou de domaine insuffisant (``ERR_PUMP_CURVE_INVALID``)."""

    code = ErrorCode.PUMP_CURVE_INVALID.value


class StrappingTableError(HydroError):
    """Table de barémage non monotone ou incomplète (``ERR_TANK_TABLE_INVALID``)."""

    code = ErrorCode.TANK_TABLE_INVALID.value


class ProfileError(HydroError):
    """Profil altimétrique non ordonné ou incohérent (``ERR_PROFILE_NOT_MONOTONIC``)."""

    code = ErrorCode.PROFILE_NOT_MONOTONIC.value


class FluidPropertyError(HydroError):
    """Propriété de fluide manquante ou hors domaine bloquant."""

    code = ErrorCode.FLUID_PROPERTIES_MISSING.value


class UnsupportedCaseError(HydroError):
    """Le moteur sélectionné ne couvre pas ce cas ; un autre moteur doit être utilisé."""

    code = ErrorCode.ENGINE_UNSUPPORTED_CASE.value


class NotConvergedError(HydroError):
    """Tolérance non atteinte. Porte le résidu et le nombre d'itérations."""

    code = "SIM_NOT_CONVERGED"
    retryable = True

    def __init__(self, message: str, residual: float, iterations: int, **context: Any) -> None:
        super().__init__(message, residual=residual, iterations=iterations, **context)
        self.residual = residual
        self.iterations = iterations


class NoPhysicalSolutionError(HydroError):
    """Aucune solution physique n'existe dans le domaine exploré (``SIM_NO_PHYSICAL_SOLUTION``)."""

    code = "SIM_NO_PHYSICAL_SOLUTION"
