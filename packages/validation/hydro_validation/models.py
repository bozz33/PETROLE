"""Structures du dossier de preuve scientifique exécutable."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ValidationObservation:
    """Comparaison numérique entre une sortie et sa référence indépendante."""

    name: str
    actual: float
    expected: float
    unit: str = ""
    absolute_tolerance: float = 0.0
    relative_tolerance: float = 0.0
    detail: str | None = None

    @property
    def absolute_error(self) -> float:
        return abs(self.actual - self.expected)

    @property
    def relative_error(self) -> float | None:
        if self.expected == 0.0:
            return None
        return self.absolute_error / abs(self.expected)

    @property
    def acceptance_limit(self) -> float:
        return max(
            self.absolute_tolerance,
            self.relative_tolerance * abs(self.expected),
        )

    @property
    def passed(self) -> bool:
        return (
            math.isfinite(self.actual)
            and math.isfinite(self.expected)
            and self.absolute_error <= self.acceptance_limit
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "actual": self.actual,
            "expected": self.expected,
            "unit": self.unit,
            "absolute_tolerance": self.absolute_tolerance,
            "relative_tolerance": self.relative_tolerance,
            "acceptance_limit": self.acceptance_limit,
            "absolute_error": self.absolute_error,
            "relative_error": self.relative_error,
            "passed": self.passed,
            "detail": self.detail,
        }


ValidationExecutor = Callable[[], tuple[ValidationObservation, ...]]


@dataclass(frozen=True, slots=True)
class ValidationCase:
    """Définition stable d'un cas du plan D10."""

    id: str
    title: str
    category: str
    reference: str
    executor: ValidationExecutor = field(repr=False)


@dataclass(frozen=True, slots=True)
class ValidationCaseResult:
    """Résultat horodatable d'un cas, exception comprise."""

    case_id: str
    title: str
    category: str
    reference: str
    observations: tuple[ValidationObservation, ...]
    duration_s: float
    error: str | None = None

    @property
    def passed(self) -> bool:
        return (
            self.error is None
            and bool(self.observations)
            and all(observation.passed for observation in self.observations)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "category": self.category,
            "reference": self.reference,
            "passed": self.passed,
            "duration_s": self.duration_s,
            "error": self.error,
            "observations": [observation.as_dict() for observation in self.observations],
        }
