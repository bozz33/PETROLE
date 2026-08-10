"""Baseline de prévision Phase 3 avec séparation train/validation/test.

Le module fournit une référence linéaire explicable. Il n'utilise que le jeu
d'entraînement pour ajuster le modèle et refuse les splits chronologiques qui
créeraient une fuite d'information. Aucun seuil de performance n'est implicite.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class ForecastObservation:
    """Observation SI horodatée utilisée par une campagne de prévision."""

    timestamp: datetime
    value_si: float

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("Les observations de prévision doivent être timezone-aware.")
        if not math.isfinite(self.value_si):
            raise ValueError("Les valeurs de prévision doivent être finies.")


@dataclass(frozen=True, slots=True)
class ForecastDatasetSplit:
    """Split chronologique strict empêchant l'utilisation du futur à l'entraînement."""

    train: tuple[ForecastObservation, ...]
    validation: tuple[ForecastObservation, ...]
    test: tuple[ForecastObservation, ...]

    def __post_init__(self) -> None:
        if len(self.train) < 2:
            raise ValueError("Le jeu d'entraînement linéaire exige au moins deux observations.")
        if not self.validation or not self.test:
            raise ValueError("Les jeux de validation et de test ne peuvent pas être vides.")
        train = sorted(self.train, key=lambda item: item.timestamp)
        validation = sorted(self.validation, key=lambda item: item.timestamp)
        test = sorted(self.test, key=lambda item: item.timestamp)
        if train[-1].timestamp >= validation[0].timestamp:
            raise ValueError("Le jeu de validation doit être strictement postérieur au train.")
        if validation[-1].timestamp >= test[0].timestamp:
            raise ValueError("Le jeu de test doit être strictement postérieur à la validation.")
        timestamps = [item.timestamp for item in (*self.train, *self.validation, *self.test)]
        if len(timestamps) != len(set(timestamps)):
            raise ValueError("Un timestamp ne peut appartenir qu'à un seul split.")


@dataclass(frozen=True, slots=True)
class ForecastMetrics:
    sample_count: int
    mae_si: float
    rmse_si: float
    bias_si: float


@dataclass(frozen=True, slots=True)
class LinearForecastResult:
    """Baseline linéaire ajustée uniquement sur train puis évaluée hors train."""

    origin_timestamp: datetime
    intercept_si: float
    slope_si_per_second: float
    train_metrics: ForecastMetrics
    validation_metrics: ForecastMetrics
    test_metrics: ForecastMetrics

    def predict(self, timestamp: datetime) -> float:
        if timestamp.tzinfo is None:
            raise ValueError("Le timestamp de prédiction doit être timezone-aware.")
        elapsed = (timestamp.astimezone(UTC) - self.origin_timestamp).total_seconds()
        return self.intercept_si + self.slope_si_per_second * elapsed


def _metrics(actual: tuple[ForecastObservation, ...], predictions: list[float]) -> ForecastMetrics:
    residuals = [
        prediction - observation.value_si
        for observation, prediction in zip(actual, predictions, strict=True)
    ]
    return ForecastMetrics(
        sample_count=len(residuals),
        mae_si=math.fsum(abs(value) for value in residuals) / len(residuals),
        rmse_si=math.sqrt(math.fsum(value * value for value in residuals) / len(residuals)),
        bias_si=math.fsum(residuals) / len(residuals),
    )


def fit_linear_forecast(split: ForecastDatasetSplit) -> LinearForecastResult:
    """Ajuste une régression OLS sur train et évalue validation/test sans réajustement."""

    train = tuple(sorted(split.train, key=lambda item: item.timestamp))
    origin = train[0].timestamp.astimezone(UTC)
    xs = [(item.timestamp.astimezone(UTC) - origin).total_seconds() for item in train]
    ys = [item.value_si for item in train]
    x_mean = math.fsum(xs) / len(xs)
    y_mean = math.fsum(ys) / len(ys)
    denominator = math.fsum((value - x_mean) ** 2 for value in xs)
    if math.isclose(denominator, 0.0, abs_tol=1e-15):
        raise ValueError("Les timestamps d'entraînement ne permettent pas d'ajuster une pente.")
    slope = math.fsum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(xs, ys, strict=True)
    ) / denominator
    intercept = y_mean - slope * x_mean

    def predict_set(observations: tuple[ForecastObservation, ...]) -> list[float]:
        return [
            intercept
            + slope * (item.timestamp.astimezone(UTC) - origin).total_seconds()
            for item in observations
        ]

    train_predictions = predict_set(train)
    validation_predictions = predict_set(split.validation)
    test_predictions = predict_set(split.test)
    return LinearForecastResult(
        origin_timestamp=origin,
        intercept_si=intercept,
        slope_si_per_second=slope,
        train_metrics=_metrics(train, train_predictions),
        validation_metrics=_metrics(split.validation, validation_predictions),
        test_metrics=_metrics(split.test, test_predictions),
    )


__all__ = [
    "ForecastDatasetSplit",
    "ForecastMetrics",
    "ForecastObservation",
    "LinearForecastResult",
    "fit_linear_forecast",
]
