"""Contrat d'horizon métier pour les prévisions Phase 3.

Un horizon n'est jamais choisi par PETROLE. Il est fourni par une décision
métier traçable sous forme d'un nombre de pas et d'un intervalle d'échantillonnage.
L'évaluation refuse les points qui ne respectent pas exactement cet horizon afin
d'éviter de mélanger silencieusement des performances à des lead-times différents.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from hydro_api.services.forecasting import ForecastMetrics


@dataclass(frozen=True, slots=True)
class ForecastHorizonDefinition:
    """Horizon métier approuvé avant l'évaluation du jeu de test."""

    horizon_ref: str
    target_ref: str
    business_purpose_ref: str
    decision_ref: str
    source_ref: str
    sampling_interval_seconds: int
    lead_steps: int

    def __post_init__(self) -> None:
        required = (
            self.horizon_ref,
            self.target_ref,
            self.business_purpose_ref,
            self.decision_ref,
            self.source_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError(
                "Horizon, cible, usage métier, décision et provenance sont obligatoires."
            )
        if self.sampling_interval_seconds <= 0:
            raise ValueError("L'intervalle d'échantillonnage doit être strictement positif.")
        if self.lead_steps <= 0:
            raise ValueError("Le nombre de pas de l'horizon doit être strictement positif.")

    @property
    def lead_time(self) -> timedelta:
        return timedelta(seconds=self.sampling_interval_seconds * self.lead_steps)

    @property
    def lead_time_seconds(self) -> int:
        return self.sampling_interval_seconds * self.lead_steps


@dataclass(frozen=True, slots=True)
class ForecastHorizonEvaluationPoint:
    """Prévision émise avant la grandeur observée à l'horizon convenu."""

    point_ref: str
    issued_at: datetime
    target_timestamp: datetime
    predicted_value_si: float
    observed_value_si: float
    prediction_source_ref: str
    observation_source_ref: str

    def __post_init__(self) -> None:
        required = (self.point_ref, self.prediction_source_ref, self.observation_source_ref)
        if any(not value.strip() for value in required):
            raise ValueError(
                "Le point et les provenances prédiction/observation sont obligatoires."
            )
        if self.issued_at.tzinfo is None or self.target_timestamp.tzinfo is None:
            raise ValueError("Les timestamps d'horizon doivent être timezone-aware.")
        if self.target_timestamp.astimezone(UTC) <= self.issued_at.astimezone(UTC):
            raise ValueError(
                "La cible de prévision doit être strictement postérieure à son émission."
            )
        if not math.isfinite(self.predicted_value_si) or not math.isfinite(self.observed_value_si):
            raise ValueError("Les valeurs prédites et observées doivent être finies.")


@dataclass(frozen=True, slots=True)
class ForecastHorizonEvaluation:
    """Métriques comparables uniquement pour l'horizon référencé."""

    horizon_ref: str
    target_ref: str
    lead_time_seconds: int
    sample_count: int
    metrics: ForecastMetrics
    first_issued_at: datetime
    last_target_timestamp: datetime
    point_refs: tuple[str, ...]
    prediction_source_refs: tuple[str, ...]
    observation_source_refs: tuple[str, ...]


def evaluate_forecast_horizon(
    definition: ForecastHorizonDefinition,
    points: tuple[ForecastHorizonEvaluationPoint, ...],
) -> ForecastHorizonEvaluation:
    """Évalue uniquement des prévisions exactement alignées sur l'horizon métier."""

    if not points:
        raise ValueError("L'évaluation d'un horizon exige au moins un point de prévision.")

    point_refs = tuple(point.point_ref for point in points)
    if len(point_refs) != len(set(point_refs)):
        raise ValueError("Les références de points d'horizon doivent être uniques.")

    expected_lead = definition.lead_time
    ordered = tuple(sorted(points, key=lambda point: point.issued_at.astimezone(UTC)))
    previous_issue: datetime | None = None
    residuals: list[float] = []

    for point in ordered:
        issued = point.issued_at.astimezone(UTC)
        target = point.target_timestamp.astimezone(UTC)
        if target - issued != expected_lead:
            raise ValueError(
                f"Le point {point.point_ref} ne respecte pas l'horizon {definition.horizon_ref}."
            )
        if previous_issue is not None and issued == previous_issue:
            raise ValueError(
                "Deux points d'horizon ne peuvent pas partager le même instant d'émission."
            )
        previous_issue = issued
        residuals.append(point.predicted_value_si - point.observed_value_si)

    sample_count = len(residuals)
    metrics = ForecastMetrics(
        sample_count=sample_count,
        mae_si=math.fsum(abs(value) for value in residuals) / sample_count,
        rmse_si=math.sqrt(math.fsum(value * value for value in residuals) / sample_count),
        bias_si=math.fsum(residuals) / sample_count,
    )

    return ForecastHorizonEvaluation(
        horizon_ref=definition.horizon_ref,
        target_ref=definition.target_ref,
        lead_time_seconds=definition.lead_time_seconds,
        sample_count=sample_count,
        metrics=metrics,
        first_issued_at=ordered[0].issued_at.astimezone(UTC),
        last_target_timestamp=max(point.target_timestamp.astimezone(UTC) for point in ordered),
        point_refs=tuple(point.point_ref for point in ordered),
        prediction_source_refs=tuple(
            dict.fromkeys(point.prediction_source_ref for point in ordered)
        ),
        observation_source_refs=tuple(
            dict.fromkeys(point.observation_source_ref for point in ordered)
        ),
    )


__all__ = [
    "ForecastHorizonDefinition",
    "ForecastHorizonEvaluation",
    "ForecastHorizonEvaluationPoint",
    "evaluate_forecast_horizon",
]
