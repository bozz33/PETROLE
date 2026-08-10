"""Rapport RPT-08 pour une calibration contrôlée et sa validation tenue à part."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hydro_optimization.calibration import CalibrationResult, ErrorMetrics
from hydro_reporting.operational import (
    OperationalReportData,
    ReportTable,
    build_operational_report_pdf,
)


@dataclass(frozen=True, slots=True)
class CalibrationReportData:
    """Données traçables nécessaires au rapport de calibration D19."""

    generated_at: datetime
    reference: str
    source_reference: str
    calibration_regimes: tuple[str, ...]
    result: CalibrationResult
    template_version: str = "rpt-08/1.0"
    field_validation_status: str = "IMPLEMENTED_NOT_FIELD_VALIDATED"

    def __post_init__(self) -> None:
        if not self.reference.strip():
            raise ValueError("La référence du rapport RPT-08 est obligatoire.")
        if not self.source_reference.strip():
            raise ValueError("La référence de provenance des données est obligatoire.")
        if not self.calibration_regimes:
            raise ValueError("Au moins un régime de calibration doit être déclaré.")
        if not self.template_version.strip():
            raise ValueError("La version de modèle RPT-08 est obligatoire.")
        if not self.field_validation_status.strip():
            raise ValueError("Le statut de validation terrain est obligatoire.")


def _metric_rows(calibration: ErrorMetrics, validation: ErrorMetrics) -> tuple[tuple[object, ...], ...]:
    return (
        ("Échantillons", calibration.sample_count, validation.sample_count),
        ("MAE SI", calibration.mae_si, validation.mae_si),
        ("RMSE SI", calibration.rmse_si, validation.rmse_si),
        ("Biais SI", calibration.bias_si, validation.bias_si),
        (
            "Erreur absolue maximale SI",
            calibration.maximum_absolute_error_si,
            validation.maximum_absolute_error_si,
        ),
    )


def build_calibration_report_pdf(data: CalibrationReportData) -> bytes:
    """Produit RPT-08 sans convertir convergence numérique en verdict industriel."""

    result = data.result
    parameter_rows = tuple(
        (
            parameter.name,
            parameter.value,
            parameter.lower_bound,
            parameter.upper_bound,
            parameter.unit,
        )
        for parameter in result.parameters
    )
    report = OperationalReportData(
        code="RPT-08",
        title="Calibration et validation tenue à part",
        subject=(
            "Paramètres ajustés, métriques de calibration et évaluation indépendante "
            "sur le jeu tenu hors ajustement."
        ),
        generated_at=data.generated_at,
        reference=data.reference,
        template_version=data.template_version,
        metadata={
            "Source / provenance": data.source_reference,
            "Statut validation terrain": data.field_validation_status,
        },
        key_values=(
            ("Convergence numérique", result.converged),
            ("Évaluations de fonction", result.function_evaluations),
            ("Régimes de calibration", ", ".join(sorted(set(data.calibration_regimes)))),
            ("Régimes de validation", ", ".join(result.validation_regimes)),
            ("Message solveur", result.termination_message),
        ),
        tables=(
            ReportTable(
                title="Paramètres calibrés",
                headers=("Paramètre", "Valeur", "Borne basse", "Borne haute", "Unité"),
                rows=parameter_rows,
            ),
            ReportTable(
                title="Calibration versus validation tenue à part",
                headers=("Métrique", "Calibration", "Validation"),
                rows=_metric_rows(result.calibration_metrics, result.validation_metrics),
            ),
        ),
        observations=(
            "Le jeu de validation n'a pas participé à la fonction objectif de calibration.",
            "Une convergence numérique n'est pas un critère d'acceptation industrielle.",
            "Les seuils PASS/FAIL doivent provenir d'un protocole de pilote approuvé et traçable.",
        ),
        assumptions=(
            "Les paramètres et leurs bornes ont été définis avant l'exécution de la calibration.",
            "Les métriques sont descriptives et exprimées dans l'unité SI de la grandeur comparée.",
        ),
    )
    return build_operational_report_pdf(report)


__all__ = ["CalibrationReportData", "build_calibration_report_pdf"]
