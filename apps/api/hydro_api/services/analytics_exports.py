"""Exports déterministes des agrégats Phase 3.

Le module sérialise un résultat déjà calculé par ``analyze_time_series``. Il ne
recalcule aucune statistique et conserve la version de traitement, l'unité SI,
les qualités incluses et la fenêtre source dans un manifeste empreinté.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

_BUCKET_COLUMNS = (
    "start_timestamp",
    "end_timestamp",
    "sample_count",
    "minimum_value_si",
    "maximum_value_si",
    "mean_value_si",
    "stddev_value_si",
    "expected_sample_count",
    "completeness_ratio",
)


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Les horodatages exportés doivent être timezone-aware.")
        return value.isoformat()
    raise TypeError(f"Type non sérialisable dans l'export analytique : {type(value)!r}")


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class AnalyticsExportArtifact:
    """Artefact de données avec empreinte SHA-256 de son contenu exact."""

    media_type: str
    filename: str
    content: bytes
    sha256: str


def export_analytics_json(
    payload: dict[str, Any],
    *,
    export_version: str = "phase3-analytics/1.0",
) -> AnalyticsExportArtifact:
    """Produit un JSON canonique enveloppant résultat et version d'export."""

    if not export_version.strip():
        raise ValueError("La version d'export analytique est obligatoire.")
    required = ("tag_id", "processing_version", "si_unit", "buckets", "trend")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"Résultat analytique incomplet : {', '.join(missing)}.")
    document = {
        "export_version": export_version,
        "tag_id": str(payload["tag_id"]),
        "processing_version": payload["processing_version"],
        "si_unit": payload["si_unit"],
        "included_qualities": payload.get("included_qualities", []),
        "requested_start_timestamp": payload.get("requested_start_timestamp"),
        "requested_end_timestamp": payload.get("requested_end_timestamp"),
        "source_start_timestamp": payload.get("source_start_timestamp"),
        "source_end_timestamp": payload.get("source_end_timestamp"),
        "candidate_sample_count": payload.get("candidate_sample_count"),
        "included_sample_count": payload.get("included_sample_count"),
        "excluded_sample_count": payload.get("excluded_sample_count"),
        "bucket_seconds": payload.get("bucket_seconds"),
        "expected_interval_seconds": payload.get("expected_interval_seconds"),
        "buckets": payload["buckets"],
        "trend": payload["trend"],
    }
    content = _canonical_json(document)
    return AnalyticsExportArtifact(
        media_type="application/json",
        filename="analytics.json",
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )


def export_analytics_buckets_csv(payload: dict[str, Any]) -> AnalyticsExportArtifact:
    """Produit un CSV des buckets exactement tels qu'ils existent dans le résultat."""

    buckets = payload.get("buckets")
    if not isinstance(buckets, list):
        raise ValueError("Le résultat analytique doit contenir une liste de buckets.")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=list(_BUCKET_COLUMNS),
        delimiter=";",
        lineterminator="\n",
        extrasaction="ignore",
    )
    writer.writeheader()
    for bucket in buckets:
        if not isinstance(bucket, dict):
            raise ValueError("Chaque bucket analytique doit être un objet.")
        row: dict[str, object] = {}
        for column in _BUCKET_COLUMNS:
            value = bucket.get(column)
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    raise ValueError("Les horodatages exportés doivent être timezone-aware.")
                row[column] = value.isoformat()
            elif value is None or isinstance(value, int | float | str):
                row[column] = value
            else:
                raise ValueError(f"Valeur de bucket non exportable pour {column}.")
        writer.writerow(row)
    content = b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")
    return AnalyticsExportArtifact(
        media_type="text/csv; charset=utf-8",
        filename="analytics-buckets.csv",
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )


__all__ = [
    "AnalyticsExportArtifact",
    "export_analytics_buckets_csv",
    "export_analytics_json",
]
