"""Calibration paramétrique contrôlée avec validation indépendante tenue à part.

Ce module fournit une brique déterministe pour V1-C. Il ne transforme pas une
calibration en validation scientifique : les observations utilisées pour
ajuster les paramètres sont séparées des observations de validation, et aucun
seuil d'acceptation industriel n'est inventé par le moteur.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares


@dataclass(frozen=True, slots=True)
class CalibrationParameter:
    """Paramètre borné et traçable à ajuster."""

    name: str
    initial_value: float
    lower_bound: float
    upper_bound: float
    unit: str = "1"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Le nom du paramètre de calibration est obligatoire.")
        values = (self.initial_value, self.lower_bound, self.upper_bound)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("Les valeurs du paramètre doivent être finies.")
        if self.lower_bound >= self.upper_bound:
            raise ValueError("La borne basse doit être strictement inférieure à la borne haute.")
        if not self.lower_bound <= self.initial_value <= self.upper_bound:
            raise ValueError("La valeur initiale doit appartenir à l'intervalle autorisé.")
        if not self.unit.strip():
            raise ValueError("L'unité du paramètre est obligatoire.")


@dataclass(frozen=True, slots=True)
class CalibrationObservation:
    """Observation indépendante du modèle avec contexte numérique explicite."""

    observation_id: str
    measured_value_si: float
    regime: str
    inputs: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("L'identifiant d'observation est obligatoire.")
        if not self.regime.strip():
            raise ValueError("Le régime de l'observation est obligatoire.")
        if not math.isfinite(self.measured_value_si):
            raise ValueError("La mesure SI doit être finie.")
        if any(not math.isfinite(value) for value in self.inputs):
            raise ValueError("Les entrées de l'observation doivent être finies.")


@dataclass(frozen=True, slots=True)
class CalibrationDataset:
    """Jeux d'ajustement et de validation explicitement disjoints."""

    calibration: tuple[CalibrationObservation, ...]
    validation: tuple[CalibrationObservation, ...]
    require_distinct_validation_regime: bool = True

    def __post_init__(self) -> None:
        if not self.calibration:
            raise ValueError("Le jeu de calibration ne peut pas être vide.")
        if not self.validation:
            raise ValueError("Le jeu de validation tenu à part ne peut pas être vide.")
        calibration_ids = {item.observation_id for item in self.calibration}
        validation_ids = {item.observation_id for item in self.validation}
        overlap = calibration_ids & validation_ids
        if overlap:
            raise ValueError(
                "Les jeux de calibration et de validation doivent être disjoints : "
                + ", ".join(sorted(overlap))
            )
        if len(calibration_ids) != len(self.calibration) or len(validation_ids) != len(
            self.validation
        ):
            raise ValueError("Chaque observation doit avoir un identifiant unique dans son jeu.")
        if self.require_distinct_validation_regime:
            calibration_regimes = {item.regime for item in self.calibration}
            validation_regimes = {item.regime for item in self.validation}
            if not validation_regimes - calibration_regimes:
                raise ValueError(
                    "Au moins un régime de validation doit être absent du jeu de calibration."
                )


@dataclass(frozen=True, slots=True)
class ErrorMetrics:
    """Métriques descriptives sans verdict d'acceptation implicite."""

    sample_count: int
    mae_si: float
    rmse_si: float
    bias_si: float
    maximum_absolute_error_si: float


@dataclass(frozen=True, slots=True)
class CalibratedParameter:
    """Valeur ajustée accompagnée de ses bornes et de son unité."""

    name: str
    value: float
    lower_bound: float
    upper_bound: float
    unit: str


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    """Résultat complet de l'ajustement et de l'évaluation tenue à part."""

    parameters: tuple[CalibratedParameter, ...]
    calibration_metrics: ErrorMetrics
    validation_metrics: ErrorMetrics
    validation_regimes: tuple[str, ...]
    converged: bool
    function_evaluations: int
    termination_message: str


ModelEvaluator = Callable[[Mapping[str, float], CalibrationObservation], float]


def _metrics(residuals: list[float]) -> ErrorMetrics:
    if not residuals:
        raise ValueError("Le calcul de métriques exige au moins un résidu.")
    absolute = [abs(value) for value in residuals]
    squared = [value * value for value in residuals]
    return ErrorMetrics(
        sample_count=len(residuals),
        mae_si=math.fsum(absolute) / len(residuals),
        rmse_si=math.sqrt(math.fsum(squared) / len(residuals)),
        bias_si=math.fsum(residuals) / len(residuals),
        maximum_absolute_error_si=max(absolute),
    )


def _evaluate_residuals(
    observations: tuple[CalibrationObservation, ...],
    parameter_values: Mapping[str, float],
    evaluator: ModelEvaluator,
) -> list[float]:
    residuals: list[float] = []
    for observation in observations:
        predicted = float(evaluator(parameter_values, observation))
        if not math.isfinite(predicted):
            raise ValueError(
                f"Le modèle a produit une valeur non finie pour {observation.observation_id}."
            )
        residuals.append(predicted - observation.measured_value_si)
    return residuals


def calibrate_parameters(
    *,
    parameters: tuple[CalibrationParameter, ...],
    dataset: CalibrationDataset,
    evaluator: ModelEvaluator,
    maximum_function_evaluations: int | None = None,
) -> CalibrationResult:
    """Ajuste des paramètres bornés sur le jeu de calibration uniquement.

    Le jeu de validation n'intervient jamais dans la fonction objectif. Les
    métriques de validation sont calculées une seule fois après l'ajustement.
    Aucun seuil ``PASS/FAIL`` n'est appliqué ici : ce seuil appartient au
    protocole d'essai approuvé pour le pilote concerné.
    """

    if not parameters:
        raise ValueError("Au moins un paramètre doit être fourni.")
    names = [parameter.name for parameter in parameters]
    if len(set(names)) != len(names):
        raise ValueError("Les noms de paramètres de calibration doivent être uniques.")
    if len(dataset.calibration) < len(parameters):
        raise ValueError(
            "Le jeu de calibration contient moins d'observations que de paramètres ajustés."
        )
    if maximum_function_evaluations is not None and maximum_function_evaluations < 1:
        raise ValueError("maximum_function_evaluations doit être positif.")

    initial = np.asarray([parameter.initial_value for parameter in parameters], dtype=float)
    lower = np.asarray([parameter.lower_bound for parameter in parameters], dtype=float)
    upper = np.asarray([parameter.upper_bound for parameter in parameters], dtype=float)

    def as_mapping(values: np.ndarray) -> dict[str, float]:
        return {name: float(value) for name, value in zip(names, values, strict=True)}

    def objective(values: np.ndarray) -> np.ndarray:
        residuals = _evaluate_residuals(dataset.calibration, as_mapping(values), evaluator)
        return np.asarray(residuals, dtype=float)

    fit = least_squares(
        objective,
        initial,
        bounds=(lower, upper),
        max_nfev=maximum_function_evaluations,
    )
    fitted_values = as_mapping(fit.x)
    calibration_residuals = _evaluate_residuals(dataset.calibration, fitted_values, evaluator)
    validation_residuals = _evaluate_residuals(dataset.validation, fitted_values, evaluator)

    return CalibrationResult(
        parameters=tuple(
            CalibratedParameter(
                name=parameter.name,
                value=fitted_values[parameter.name],
                lower_bound=parameter.lower_bound,
                upper_bound=parameter.upper_bound,
                unit=parameter.unit,
            )
            for parameter in parameters
        ),
        calibration_metrics=_metrics(calibration_residuals),
        validation_metrics=_metrics(validation_residuals),
        validation_regimes=tuple(sorted({item.regime for item in dataset.validation})),
        converged=bool(fit.success),
        function_evaluations=int(fit.nfev),
        termination_message=str(fit.message),
    )


__all__ = [
    "CalibratedParameter",
    "CalibrationDataset",
    "CalibrationObservation",
    "CalibrationParameter",
    "CalibrationResult",
    "ErrorMetrics",
    "ModelEvaluator",
    "calibrate_parameters",
]
