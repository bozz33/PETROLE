"""Suivi descriptif des KPI mesure-modèle sur plusieurs régimes.

Les KPI d'entrée proviennent de comparaisons V1-B déjà figées. Le module ne
recalcule aucun résidu et ne crée aucun seuil d'acceptation. Les agrégats
pondérés sont mathématiquement reconstruits depuis n, biais, MAE et RMSE.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegimeKpiObservation:
    """KPI immuables d'une comparaison associée à un régime explicite."""

    regime_id: str
    comparison_ref: str
    si_unit: str
    sample_count: int
    bias_si: float
    mae_si: float
    rmse_si: float

    def __post_init__(self) -> None:
        if not self.regime_id.strip() or not self.comparison_ref.strip():
            raise ValueError("Le régime et la comparaison doivent être référencés.")
        if not self.si_unit.strip():
            raise ValueError("L'unité SI du KPI est obligatoire.")
        if self.sample_count <= 0:
            raise ValueError("Un régime suivi doit contenir au moins un point comparé.")
        metrics = (self.bias_si, self.mae_si, self.rmse_si)
        if any(not math.isfinite(value) for value in metrics):
            raise ValueError("Les KPI de régime doivent être finis.")
        if self.mae_si < 0 or self.rmse_si < 0:
            raise ValueError("MAE et RMSE doivent être positifs ou nuls.")


@dataclass(frozen=True, slots=True)
class MultiRegimeKpiSummary:
    """Synthèse exacte des KPI disponibles, sans verdict métier."""

    si_unit: str
    regime_count: int
    total_sample_count: int
    weighted_bias_si: float
    weighted_mae_si: float
    pooled_rmse_si: float
    minimum_regime_rmse_si: float
    maximum_regime_rmse_si: float
    observations: tuple[RegimeKpiObservation, ...]


def summarize_regime_kpis(
    observations: tuple[RegimeKpiObservation, ...],
) -> MultiRegimeKpiSummary:
    """Agrège des KPI homogènes en conservant les résultats de chaque régime.

    ``pooled_rmse`` utilise ``sqrt(sum(n_i * RMSE_i²) / sum(n_i))``. Cette
    relation est exacte pour des RMSE calculées comme racine de la moyenne des
    carrés des résidus sur des ensembles disjoints.
    """

    if not observations:
        raise ValueError("Le suivi multi-régimes exige au moins une observation.")
    regime_ids = [observation.regime_id for observation in observations]
    if len(regime_ids) != len(set(regime_ids)):
        raise ValueError("Chaque régime ne peut apparaître qu'une fois dans une synthèse.")
    units = {observation.si_unit for observation in observations}
    if len(units) != 1:
        raise ValueError("Tous les régimes d'une synthèse doivent utiliser la même unité SI.")

    total_samples = sum(observation.sample_count for observation in observations)
    weighted_bias = math.fsum(
        observation.sample_count * observation.bias_si for observation in observations
    ) / total_samples
    weighted_mae = math.fsum(
        observation.sample_count * observation.mae_si for observation in observations
    ) / total_samples
    pooled_rmse = math.sqrt(
        math.fsum(
            observation.sample_count * observation.rmse_si**2 for observation in observations
        )
        / total_samples
    )
    rmse_values = [observation.rmse_si for observation in observations]
    return MultiRegimeKpiSummary(
        si_unit=next(iter(units)),
        regime_count=len(observations),
        total_sample_count=total_samples,
        weighted_bias_si=weighted_bias,
        weighted_mae_si=weighted_mae,
        pooled_rmse_si=pooled_rmse,
        minimum_regime_rmse_si=min(rmse_values),
        maximum_regime_rmse_si=max(rmse_values),
        observations=observations,
    )


__all__ = [
    "MultiRegimeKpiSummary",
    "RegimeKpiObservation",
    "summarize_regime_kpis",
]
