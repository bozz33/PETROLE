"""Résidus mesure-modèle explicables pour les détecteurs analytiques P7-D.

Le module calcule uniquement un écart et son incertitude combinée. Il ne définit
aucun seuil de fuite, aucune alarme et aucune action opérateur automatique.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class MeasurementModelResidualInput:
    """Paire mesure/modèle exprimée dans la même grandeur SI."""

    timestamp: datetime
    measured_value_si: float
    modeled_value_si: float
    measurement_standard_uncertainty_si: float
    model_standard_uncertainty_si: float
    si_unit: str
    measurement_ref: str
    model_ref: str

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("Le résidu mesure-modèle exige un timestamp timezone-aware.")
        finite_values = (self.measured_value_si, self.modeled_value_si)
        if any(not math.isfinite(value) for value in finite_values):
            raise ValueError("Les valeurs mesure/modèle doivent être finies.")
        uncertainties = (
            self.measurement_standard_uncertainty_si,
            self.model_standard_uncertainty_si,
        )
        if any(not math.isfinite(value) or value < 0 for value in uncertainties):
            raise ValueError("Les incertitudes-types doivent être finies et positives ou nulles.")
        if (
            not self.si_unit.strip()
            or not self.measurement_ref.strip()
            or not self.model_ref.strip()
        ):
            raise ValueError("Unité et références mesure/modèle sont obligatoires.")

    @property
    def timestamp_utc(self) -> datetime:
        return self.timestamp.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class MeasurementModelResidual:
    """Preuve quantitative sans verdict de détection."""

    timestamp: datetime
    residual_si: float
    absolute_residual_si: float
    combined_standard_uncertainty_si: float
    normalized_residual: float | None
    si_unit: str
    measurement_ref: str
    model_ref: str


def compute_measurement_model_residual(
    residual_input: MeasurementModelResidualInput,
) -> MeasurementModelResidual:
    """Calcule mesure - modèle et l'incertitude RSS fournie par les deux sources."""

    residual = residual_input.measured_value_si - residual_input.modeled_value_si
    combined_uncertainty = math.hypot(
        residual_input.measurement_standard_uncertainty_si,
        residual_input.model_standard_uncertainty_si,
    )
    normalized = residual / combined_uncertainty if combined_uncertainty > 0 else None
    return MeasurementModelResidual(
        timestamp=residual_input.timestamp_utc,
        residual_si=residual,
        absolute_residual_si=abs(residual),
        combined_standard_uncertainty_si=combined_uncertainty,
        normalized_residual=normalized,
        si_unit=residual_input.si_unit,
        measurement_ref=residual_input.measurement_ref,
        model_ref=residual_input.model_ref,
    )


__all__ = [
    "MeasurementModelResidual",
    "MeasurementModelResidualInput",
    "compute_measurement_model_residual",
]
