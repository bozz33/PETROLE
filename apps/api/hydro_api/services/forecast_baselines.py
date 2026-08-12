"""Baselines naïves et comparaison hors échantillon pour la Phase 3.

La baseline de persistance conserve la dernière valeur chronologique du jeu
train et l'applique sans réajustement aux jeux validation/test. La comparaison
avec la baseline OLS reste factuelle : aucun seuil de supériorité ou verdict de
publication n'est codé en dur.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from hydro_api.services.forecasting import (
    ForecastDatasetSplit,
    ForecastMetrics,
    ForecastObservation,
    LinearForecastResult,
)


@dataclass(frozen=True, slots=True)
class PersistenceForecastResult:
    """Baseline naïve : dernière valeur du train maintenue dans le futur."""

    reference_value_si: float
    validation_metrics: ForecastMetrics
    test_metrics: ForecastMetrics


@dataclass(frozen=True, slots=True)
class ForecastMetricComparison:
    """Écart modèle - baseline ; une valeur négative signifie une erreur moindre."""

    model_metrics: ForecastMetrics
    baseline_metrics: ForecastMetrics
    mae_delta_si: float
    rmse_delta_si: float
    absolute_bias_delta_si: float


@dataclass(frozen=True, slots=True)
class ForecastBaselineComparison:
    validation: ForecastMetricComparison
    test: ForecastMetricComparison


def _constant_metrics(
    observations: tuple[ForecastObservation, ...],
    value_si: float,
) -> ForecastMetrics:
    residuals = [value_si - observation.value_si for observation in observations]
    return ForecastMetrics(
        sample_count=len(residuals),
        mae_si=math.fsum(abs(value) for value in residuals) / len(residuals),
        rmse_si=math.sqrt(math.fsum(value * value for value in residuals) / len(residuals)),
        bias_si=math.fsum(residuals) / len(residuals),
    )


def fit_persistence_forecast(split: ForecastDatasetSplit) -> PersistenceForecastResult:
    """Évalue la dernière valeur du train sur validation et test, sans fuite future."""

    latest_train = max(split.train, key=lambda observation: observation.timestamp)
    reference_value = latest_train.value_si
    return PersistenceForecastResult(
        reference_value_si=reference_value,
        validation_metrics=_constant_metrics(split.validation, reference_value),
        test_metrics=_constant_metrics(split.test, reference_value),
    )


def _compare_metrics(
    model: ForecastMetrics,
    baseline: ForecastMetrics,
) -> ForecastMetricComparison:
    if model.sample_count != baseline.sample_count:
        raise ValueError("Le modèle et la baseline doivent être évalués sur le même nombre de points.")
    return ForecastMetricComparison(
        model_metrics=model,
        baseline_metrics=baseline,
        mae_delta_si=model.mae_si - baseline.mae_si,
        rmse_delta_si=model.rmse_si - baseline.rmse_si,
        absolute_bias_delta_si=abs(model.bias_si) - abs(baseline.bias_si),
    )


def compare_linear_to_persistence(
    linear: LinearForecastResult,
    persistence: PersistenceForecastResult,
) -> ForecastBaselineComparison:
    """Compare les métriques hors train sans produire de verdict automatique."""

    return ForecastBaselineComparison(
        validation=_compare_metrics(linear.validation_metrics, persistence.validation_metrics),
        test=_compare_metrics(linear.test_metrics, persistence.test_metrics),
    )


__all__ = [
    "ForecastBaselineComparison",
    "ForecastMetricComparison",
    "PersistenceForecastResult",
    "compare_linear_to_persistence",
    "fit_persistence_forecast",
]
