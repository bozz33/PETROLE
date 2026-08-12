"""Contrat de campagne P7-I et évaluation de critères pré-enregistrés.

Les critères sont fournis explicitement par le protocole de validation avant
l'évaluation. PETROLE n'impose ici aucun seuil industriel et ne transforme pas
une campagne en certification ou en autorisation d'exploitation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_leak.metrics import DetectionPerformance


@dataclass(frozen=True, slots=True)
class LeakValidationCriteria:
    """Critères numériques pré-enregistrés, sans valeur par défaut implicite."""

    source_ref: str
    minimum_precision: float | None = None
    minimum_recall: float | None = None
    minimum_specificity: float | None = None
    maximum_false_positive_rate: float | None = None
    maximum_mean_detection_delay_s: float | None = None
    maximum_detection_delay_s: float | None = None
    minimum_sample_count: int | None = None

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("La provenance des critères de validation est obligatoire.")
        ratio_fields = (
            self.minimum_precision,
            self.minimum_recall,
            self.minimum_specificity,
            self.maximum_false_positive_rate,
        )
        if any(
            value is not None and (not math.isfinite(value) or not 0 <= value <= 1)
            for value in ratio_fields
        ):
            raise ValueError("Les critères de ratio doivent appartenir à [0, 1].")
        delay_fields = (
            self.maximum_mean_detection_delay_s,
            self.maximum_detection_delay_s,
        )
        if any(
            value is not None and (not math.isfinite(value) or value < 0) for value in delay_fields
        ):
            raise ValueError("Les critères de délai doivent être finis et positifs ou nuls.")
        if self.minimum_sample_count is not None and self.minimum_sample_count < 1:
            raise ValueError("Le nombre minimal d'échantillons doit être strictement positif.")
        if not self.configured_criteria:
            raise ValueError("Au moins un critère de validation doit être pré-enregistré.")

    @property
    def configured_criteria(self) -> tuple[str, ...]:
        values = {
            "minimum_precision": self.minimum_precision,
            "minimum_recall": self.minimum_recall,
            "minimum_specificity": self.minimum_specificity,
            "maximum_false_positive_rate": self.maximum_false_positive_rate,
            "maximum_mean_detection_delay_s": self.maximum_mean_detection_delay_s,
            "maximum_detection_delay_s": self.maximum_detection_delay_s,
            "minimum_sample_count": self.minimum_sample_count,
        }
        return tuple(name for name, value in values.items() if value is not None)


@dataclass(frozen=True, slots=True)
class LeakValidationCriterionResult:
    criterion: str
    observed_value: float | int | None
    required_value: float | int
    passed: bool | None
    reason: str


@dataclass(frozen=True, slots=True)
class LeakValidationAssessment:
    """Résultat factuel des critères configurés uniquement."""

    criteria_source_ref: str
    criterion_results: tuple[LeakValidationCriterionResult, ...]

    @property
    def all_evaluable_criteria_passed(self) -> bool | None:
        evaluable = [
            result.passed for result in self.criterion_results if result.passed is not None
        ]
        if not evaluable:
            return None
        return all(evaluable)

    @property
    def has_unevaluable_criteria(self) -> bool:
        return any(result.passed is None for result in self.criterion_results)


def _minimum_result(
    *,
    criterion: str,
    observed: float | int | None,
    required: float | int,
) -> LeakValidationCriterionResult:
    if observed is None:
        return LeakValidationCriterionResult(
            criterion=criterion,
            observed_value=None,
            required_value=required,
            passed=None,
            reason="metric_unavailable",
        )
    return LeakValidationCriterionResult(
        criterion=criterion,
        observed_value=observed,
        required_value=required,
        passed=observed >= required,
        reason="evaluated",
    )


def _maximum_result(
    *,
    criterion: str,
    observed: float | int | None,
    required: float | int,
) -> LeakValidationCriterionResult:
    if observed is None:
        return LeakValidationCriterionResult(
            criterion=criterion,
            observed_value=None,
            required_value=required,
            passed=None,
            reason="metric_unavailable",
        )
    return LeakValidationCriterionResult(
        criterion=criterion,
        observed_value=observed,
        required_value=required,
        passed=observed <= required,
        reason="evaluated",
    )


def assess_validation_criteria(
    performance: DetectionPerformance,
    criteria: LeakValidationCriteria,
) -> LeakValidationAssessment:
    """Évalue uniquement les critères explicitement présents dans le protocole."""

    sample_count = (
        performance.true_positive
        + performance.false_positive
        + performance.false_negative
        + performance.true_negative
    )
    results: list[LeakValidationCriterionResult] = []

    minimum_metrics = (
        ("minimum_precision", performance.precision, criteria.minimum_precision),
        ("minimum_recall", performance.recall, criteria.minimum_recall),
        ("minimum_specificity", performance.specificity, criteria.minimum_specificity),
        ("minimum_sample_count", sample_count, criteria.minimum_sample_count),
    )
    for criterion, observed, required in minimum_metrics:
        if required is not None:
            results.append(
                _minimum_result(criterion=criterion, observed=observed, required=required)
            )

    maximum_metrics = (
        (
            "maximum_false_positive_rate",
            performance.false_positive_rate,
            criteria.maximum_false_positive_rate,
        ),
        (
            "maximum_mean_detection_delay_s",
            performance.mean_detection_delay_s,
            criteria.maximum_mean_detection_delay_s,
        ),
        (
            "maximum_detection_delay_s",
            performance.maximum_detection_delay_s,
            criteria.maximum_detection_delay_s,
        ),
    )
    for criterion, observed, required in maximum_metrics:
        if required is not None:
            results.append(
                _maximum_result(criterion=criterion, observed=observed, required=required)
            )

    return LeakValidationAssessment(
        criteria_source_ref=criteria.source_ref,
        criterion_results=tuple(results),
    )


__all__ = [
    "LeakValidationAssessment",
    "LeakValidationCriteria",
    "LeakValidationCriterionResult",
    "assess_validation_criteria",
]
