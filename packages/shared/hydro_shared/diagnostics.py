"""Diagnostics : sévérité, violations, avertissements, rapport de validation et journal solveur.

Deux exigences structurent ce module :

- *Aucun résultat silencieux* en cas de non-convergence ou d'entrée hors domaine (D-v2 § 12.2).
- *Aucun résultat n'est déclaré valide si le bilan de masse ou la convergence dépasse la
  tolérance* (NFR-SCI-005).

Chaque violation localise le point concerné, sa valeur, sa limite, son écart et une
recommandation exploitable (D-v2 § 4.9).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from hydro_shared.codes import ViolationCode, WarningCode


class Severity(IntEnum):
    """Niveaux d'alerte de l'interface et des rapports (D19 § 14).

    L'ordre est significatif : ``max()`` sur un ensemble de diagnostics donne la sévérité
    globale.
    """

    INFO = 10
    WARNING = 20
    CRITICAL = 30

    @property
    def label(self) -> str:
        return {
            Severity.INFO: "Information",
            Severity.WARNING: "Avertissement",
            Severity.CRITICAL: "Critique",
        }[self]


@dataclass(frozen=True, slots=True)
class Location:
    """Localisation d'un diagnostic dans le modèle ou le long du tracé."""

    object_type: str | None = None
    object_id: str | None = None
    object_label: str | None = None
    chainage_m: float | None = None

    def describe(self) -> str:
        parts: list[str] = []
        if self.object_label:
            parts.append(self.object_label)
        elif self.object_type:
            parts.append(f"{self.object_type} {self.object_id or ''}".strip())
        if self.chainage_m is not None:
            parts.append(f"PK {self.chainage_m / 1000.0:.3f} km")
        return " — ".join(parts) if parts else "réseau"

    def as_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "object_id": self.object_id,
            "object_label": self.object_label,
            "chainage_m": self.chainage_m,
        }


@dataclass(frozen=True, slots=True)
class Violation:
    """Contrainte physique ou normative non respectée.

    ``check_id`` référence le contrôle obligatoire correspondant (``C-001`` … ``C-012``)
    lorsqu'il en existe un.
    """

    code: ViolationCode
    severity: Severity
    message: str
    location: Location = field(default_factory=Location)
    value: float | None = None
    limit: float | None = None
    unit: str | None = None
    recommendation: str | None = None
    check_id: str | None = None

    @property
    def deviation(self) -> float | None:
        """Écart signé entre la valeur et sa limite, dans l'unité de la violation."""
        if self.value is None or self.limit is None:
            return None
        return self.value - self.limit

    @property
    def relative_deviation(self) -> float | None:
        """Écart relatif à la limite ; ``None`` si la limite est nulle ou absente."""
        deviation = self.deviation
        if deviation is None or self.limit in (None, 0.0):
            return None
        return deviation / abs(self.limit)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "severity": self.severity.name,
            "message": self.message,
            "location": self.location.as_dict(),
            "value": self.value,
            "limit": self.limit,
            "unit": self.unit,
            "deviation": self.deviation,
            "relative_deviation": self.relative_deviation,
            "recommendation": self.recommendation,
            "check_id": self.check_id,
        }


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """Avertissement ou information : le résultat existe mais doit être examiné."""

    code: WarningCode
    message: str
    severity: Severity = Severity.WARNING
    location: Location = field(default_factory=Location)
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "severity": self.severity.name,
            "message": self.message,
            "location": self.location.as_dict(),
            "details": self.details,
        }


@dataclass(slots=True)
class SolverDiagnostics:
    """Journal scientifique d'une résolution (NFR-OBS-003, D-v2 § 4.9).

    Ce journal est distinct du journal applicatif et accompagne systématiquement le résultat,
    y compris en cas d'échec.
    """

    method: str = "unspecified"
    converged: bool = False
    iterations: int = 0
    residual: float = float("nan")
    tolerance: float = 0.0
    mass_balance_residual: float | None = None
    mass_balance_tolerance: float | None = None
    elapsed_s: float | None = None
    fallback_used: bool = False
    messages: list[str] = field(default_factory=list)
    iteration_log: list[dict[str, float]] = field(default_factory=list)

    def record_iteration(self, index: int, **values: float) -> None:
        """Enregistre une itération. Le journal détaillé reste optionnel et borné."""
        entry: dict[str, float] = {"iteration": float(index)}
        entry.update({k: float(v) for k, v in values.items()})
        self.iteration_log.append(entry)

    def note(self, message: str) -> None:
        self.messages.append(message)

    @property
    def mass_balance_ok(self) -> bool:
        """Vrai si le bilan de masse est sous tolérance, ou s'il n'est pas applicable."""
        if self.mass_balance_residual is None or self.mass_balance_tolerance is None:
            return True
        return abs(self.mass_balance_residual) <= self.mass_balance_tolerance

    def as_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "converged": self.converged,
            "iterations": self.iterations,
            "residual": self.residual,
            "tolerance": self.tolerance,
            "mass_balance_residual": self.mass_balance_residual,
            "mass_balance_tolerance": self.mass_balance_tolerance,
            "mass_balance_ok": self.mass_balance_ok,
            "elapsed_s": self.elapsed_s,
            "fallback_used": self.fallback_used,
            "messages": list(self.messages),
            "iteration_count_logged": len(self.iteration_log),
        }


@dataclass(slots=True)
class ValidationReport:
    """Résultat d'une validation d'entrées ou d'un contrôle de résultat.

    Un rapport contenant au moins une erreur bloquante interdit le lancement du calcul ;
    un rapport contenant une violation critique interdit l'approbation du résultat.
    """

    errors: list[Violation] = field(default_factory=list)
    warnings: list[Diagnostic] = field(default_factory=list)

    def add_violation(self, violation: Violation) -> None:
        if violation.severity is Severity.CRITICAL:
            self.errors.append(violation)
        else:
            self.warnings.append(
                Diagnostic(
                    code=WarningCode.NEAR_LIMIT,
                    message=violation.message,
                    severity=violation.severity,
                    location=violation.location,
                    details={"violation_code": violation.code.value},
                )
            )

    def add_error(self, violation: Violation) -> None:
        self.errors.append(violation)

    def add_warning(self, diagnostic: Diagnostic) -> None:
        self.warnings.append(diagnostic)

    def extend(self, other: ValidationReport) -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

    @property
    def is_valid(self) -> bool:
        """Vrai s'il n'existe aucune erreur bloquante."""
        return not self.errors

    @property
    def severity(self) -> Severity:
        levels = [v.severity for v in self.errors] + [w.severity for w in self.warnings]
        return max(levels) if levels else Severity.INFO

    def as_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "severity": self.severity.name,
            "errors": [e.as_dict() for e in self.errors],
            "warnings": [w.as_dict() for w in self.warnings],
        }

    def summary(self) -> str:
        if self.is_valid and not self.warnings:
            return "Validation réussie : aucune anomalie détectée."
        return (
            f"Validation : {len(self.errors)} erreur(s) bloquante(s), "
            f"{len(self.warnings)} avertissement(s)."
        )
