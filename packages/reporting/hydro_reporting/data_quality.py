"""Générateur RPT-07 — qualité des données temporelles.

Le générateur reçoit uniquement des diagnostics déjà calculés. Il ne nettoie,
ne corrige et n'interpole aucune mesure ; il transforme une preuve structurée
en document PDF archivable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from hydro_reporting.operational import (
    OperationalReportData,
    ReportTable,
    build_operational_report_pdf,
)


@dataclass(frozen=True, slots=True)
class DataQualityReportData:
    """Entrée indépendante de FastAPI pour le rapport RPT-07."""

    tag_id: str
    tag_name: str
    external_name: str
    processing_version: str
    generated_at: datetime
    start_timestamp: datetime | None
    end_timestamp: datetime | None
    si_unit: str
    candidate_sample_count: int
    included_sample_count: int
    excluded_sample_count: int
    quality_counts: dict[str, int]
    minimum_value_si: float | None
    maximum_value_si: float | None
    mean_value_si: float | None
    stddev_value_si: float | None
    duplicate_timestamp_count: int
    out_of_order_count: int
    gap_count: int
    observed_interval_seconds: float | None
    reference_interval_seconds: float | None
    outlier_method: str
    outlier_threshold: float | None
    outlier_count: int
    issues: tuple[dict[str, Any], ...] = ()
    included_qualities: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        counts = (
            self.candidate_sample_count,
            self.included_sample_count,
            self.excluded_sample_count,
            self.duplicate_timestamp_count,
            self.out_of_order_count,
            self.gap_count,
            self.outlier_count,
        )
        if any(value < 0 for value in counts):
            raise ValueError("Les compteurs RPT-07 ne peuvent pas être négatifs.")
        if self.included_sample_count + self.excluded_sample_count != self.candidate_sample_count:
            raise ValueError("Les compteurs inclus/exclus doivent reconstituer le total candidat.")
        if not self.processing_version.strip() or not self.si_unit.strip():
            raise ValueError("Version de traitement et unité SI sont obligatoires.")


def _issue_message(issue: dict[str, Any]) -> str:
    code = str(issue.get("code") or "DQ").strip()
    message = str(issue.get("message") or issue.get("detail") or "Diagnostic sans message").strip()
    return f"{code} — {message}"


def build_data_quality_report_pdf(data: DataQualityReportData) -> bytes:
    """Produit le PDF RPT-07 sans recalculer les diagnostics."""

    quality_rows = tuple((quality, count) for quality, count in sorted(data.quality_counts.items()))
    diagnostics = (
        ("Doublons d'horodatage", data.duplicate_timestamp_count),
        ("Points hors ordre source", data.out_of_order_count),
        ("Trous détectés", data.gap_count),
        ("Aberrants signalés", data.outlier_count),
        ("Méthode aberrants", data.outlier_method),
        ("Seuil / multiplicateur", data.outlier_threshold),
    )
    report = OperationalReportData(
        code="RPT-07",
        title="Qualité des données",
        subject="Diagnostic traçable d'une projection temporelle normalisée en SI.",
        generated_at=data.generated_at,
        reference=data.tag_id,
        template_version="rpt-07/1.0",
        metadata={
            "Tag": data.external_name,
            "Nom": data.tag_name,
            "Version de traitement": data.processing_version,
            **data.metadata,
        },
        key_values=(
            ("Période début", data.start_timestamp),
            ("Période fin", data.end_timestamp),
            ("Unité SI", data.si_unit),
            ("Points candidats", data.candidate_sample_count),
            ("Points inclus", data.included_sample_count),
            ("Points exclus", data.excluded_sample_count),
            ("Qualités incluses", ", ".join(data.included_qualities) or "—"),
            ("Minimum SI", data.minimum_value_si),
            ("Maximum SI", data.maximum_value_si),
            ("Moyenne SI", data.mean_value_si),
            ("Écart-type SI", data.stddev_value_si),
            ("Intervalle observé s", data.observed_interval_seconds),
            ("Intervalle de référence s", data.reference_interval_seconds),
        ),
        tables=(
            ReportTable(
                title="Répartition par qualité",
                headers=("Qualité", "Nombre"),
                rows=quality_rows,
            ),
            ReportTable(
                title="Diagnostics temporels",
                headers=("Contrôle", "Valeur"),
                rows=diagnostics,
            ),
        ),
        observations=tuple(_issue_message(issue) for issue in data.issues),
        assumptions=(
            "Les mesures brutes et normalisées ne sont jamais modifiées par ce rapport.",
            "Les exclusions correspondent à la sélection de qualité explicitement enregistrée.",
            "Un point signalé comme aberrant reste une observation conservée, pas une donnée supprimée.",
        ),
        footer_note=(
            "RPT-07 décrit la qualité des données disponibles. Il ne constitue ni une validation "
            "métrologique du capteur ni une certification de l'installation."
        ),
    )
    return build_operational_report_pdf(report)


__all__ = ["DataQualityReportData", "build_data_quality_report_pdf"]
