"""Analyse déterministe de la qualité des jeux de mesures importés.

Ce module ouvre la Phase 2 / Pilote-V1 sans introduire de calibration implicite.
Il exploite le lignage immuable déjà présent dans ``DatasetRow`` et expose des
indicateurs descriptifs alignés sur D04 FR-DAT-004 et D09 DQ-007/DQ-008.

La comparaison mesure-modèle (FR-DAT-005), l'identification de paramètres et
les tables temporelles dédiées de D12 restent des lots séparés. Les statistiques
ci-dessous ne modifient jamais les données brutes, normalisées ou corrigées.
"""

from __future__ import annotations

import math
import uuid
from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hydro_api.errors import ResourceConflictError
from hydro_api.models import DatasetRow
from hydro_api.services.data_import import get_dataset
from hydro_shared.units import SI_UNITS, Dimension


class _RunningStatistics:
    """Statistiques en un passage, stables numériquement et sans matérialisation."""

    def __init__(self) -> None:
        self.count = 0
        self.minimum: float | None = None
        self.maximum: float | None = None
        self.mean = 0.0
        self.m2 = 0.0

    def add(self, value: float) -> None:
        self.count += 1
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        delta = value - self.mean
        self.mean += delta / self.count
        self.m2 += delta * (value - self.mean)

    @property
    def stddev(self) -> float | None:
        if self.count == 0:
            return None
        return math.sqrt(self.m2 / self.count)


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _measurement_contract(dataset_mapping: dict[str, Any]) -> tuple[str, str]:
    raw_dimension = dataset_mapping.get("dimensions", {}).get("value")
    if raw_dimension is None:
        raise ResourceConflictError(
            "Le jeu de mesures ne possède pas de dimension normalisée pour value."
        )
    try:
        dimension = Dimension(str(raw_dimension))
    except ValueError as exc:
        raise ResourceConflictError(
            "La dimension du jeu de mesures n'est pas reconnue par le référentiel d'unités."
        ) from exc
    return dimension.value, SI_UNITS[dimension]


def summarize_measurement_quality(
    session: Session,
    dataset_id: uuid.UUID,
) -> dict[str, Any]:
    """Retourne un bilan descriptif d'un dataset ``measurements``.

    Les valeurs de statistique utilisent uniquement les échantillons exploitables :
    valeur numérique, timestamp UTC valide et code qualité différent de ``bad``.
    Une mesure ``bad`` reste comptée et traçable mais est exclue par défaut,
    conformément à D09 DQ-008.
    """

    dataset = get_dataset(session, dataset_id)
    if dataset.kind != "measurements":
        raise ResourceConflictError(
            "La synthèse qualité est disponible uniquement pour un jeu de mesures."
        )
    if not dataset.mapping:
        raise ResourceConflictError("Le mapping du jeu de mesures doit être validé.")

    dimension, si_unit = _measurement_contract(dataset.mapping)
    rows = session.scalars(
        select(DatasetRow)
        .where(DatasetRow.dataset_id == dataset.id)
        .order_by(DatasetRow.source_row)
    )

    quality_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    previous_timestamp_by_source: dict[str, datetime] = {}
    seen_timestamps: set[tuple[str, datetime]] = set()
    statistics = _RunningStatistics()

    sample_count = 0
    usable_sample_count = 0
    bad_quality_count = 0
    invalid_timestamp_count = 0
    invalid_value_count = 0
    missing_source_count = 0
    duplicate_timestamp_count = 0
    out_of_order_count = 0
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None

    for row in rows:
        sample_count += 1
        normalized = row.normalized_payload or {}
        quality = str(row.quality or normalized.get("quality") or "bad").strip().lower()
        quality_counts[quality] += 1

        raw_source = normalized.get("source")
        source = str(raw_source).strip() if raw_source is not None else ""
        if not source:
            source = "(source non renseignée)"
            missing_source_count += 1
        source_counts[source] += 1

        timestamp = _parse_timestamp(normalized.get("timestamp"))
        if timestamp is None:
            invalid_timestamp_count += 1
        else:
            key = (source, timestamp)
            if key in seen_timestamps:
                duplicate_timestamp_count += 1
            else:
                seen_timestamps.add(key)

            previous = previous_timestamp_by_source.get(source)
            if previous is not None and timestamp < previous:
                out_of_order_count += 1
            previous_timestamp_by_source[source] = timestamp

        raw_value = normalized.get("value")
        value = float(raw_value) if isinstance(raw_value, int | float) else None
        if value is None or not math.isfinite(value):
            invalid_value_count += 1
            value = None

        if quality == "bad":
            bad_quality_count += 1

        if quality != "bad" and timestamp is not None and value is not None:
            usable_sample_count += 1
            statistics.add(value)
            first_timestamp = timestamp if first_timestamp is None else min(first_timestamp, timestamp)
            last_timestamp = timestamp if last_timestamp is None else max(last_timestamp, timestamp)

    issues: list[dict[str, Any]] = []
    if invalid_timestamp_count or out_of_order_count:
        issues.append(
            {
                "code": "DQ-007",
                "severity": "warning",
                "count": invalid_timestamp_count + out_of_order_count,
                "message": (
                    "Horodatages invalides ou hors ordre détectés ; vérifier l'ordre et la source."
                ),
            }
        )
    if bad_quality_count:
        issues.append(
            {
                "code": "DQ-008",
                "severity": "warning",
                "count": bad_quality_count,
                "message": "Les mesures de qualité bad sont exclues des statistiques par défaut.",
            }
        )
    if duplicate_timestamp_count:
        issues.append(
            {
                "code": "TS-DUPLICATE",
                "severity": "warning",
                "count": duplicate_timestamp_count,
                "message": "Des horodatages dupliqués existent pour une même source.",
            }
        )
    if missing_source_count:
        issues.append(
            {
                "code": "TS-SOURCE-MISSING",
                "severity": "warning",
                "count": missing_source_count,
                "message": "Certaines mesures n'identifient pas explicitement leur source.",
            }
        )
    if invalid_value_count:
        issues.append(
            {
                "code": "TS-VALUE-INVALID",
                "severity": "warning",
                "count": invalid_value_count,
                "message": "Certaines valeurs normalisées ne sont pas numériques et sont exclues.",
            }
        )

    return {
        "dataset_id": dataset.id,
        "dimension": dimension,
        "si_unit": si_unit,
        "sample_count": sample_count,
        "usable_sample_count": usable_sample_count,
        "excluded_sample_count": sample_count - usable_sample_count,
        "quality_counts": dict(sorted(quality_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "start_timestamp": first_timestamp,
        "end_timestamp": last_timestamp,
        "minimum_value_si": statistics.minimum,
        "maximum_value_si": statistics.maximum,
        "mean_value_si": statistics.mean if statistics.count else None,
        "stddev_value_si": statistics.stddev,
        "duplicate_timestamp_count": duplicate_timestamp_count,
        "out_of_order_count": out_of_order_count,
        "issues": issues,
    }


__all__ = ["summarize_measurement_quality"]
