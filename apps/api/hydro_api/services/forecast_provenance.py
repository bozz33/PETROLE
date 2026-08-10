"""Provenance déterministe d'un run de prévision Phase 3.

Le manifeste empreinte séparément train/validation/test, conserve le modèle et
les métriques hors entraînement. Il permet de reproduire/auditer une exécution,
mais un hash identique ne constitue pas une validation prédictive terrain.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from hydro_api.services.forecasting import ForecastDatasetSplit, LinearForecastResult


def _observation_payload(split_part: tuple[object, ...]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for item in split_part:
        timestamp = getattr(item, "timestamp")
        value_si = getattr(item, "value_si")
        if not isinstance(timestamp, datetime):
            raise TypeError("Une observation de prévision doit exposer un timestamp datetime.")
        payload.append(
            {
                "timestamp": timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                "value_si": float(value_si),
            }
        )
    return payload


def _sha256_payload(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ForecastRunManifest:
    """Identité complète des entrées et sorties d'une baseline de prévision."""

    run_reference: str
    source_reference: str
    model_family: str
    model_version: str
    code_version: str
    created_at: datetime
    train_sha256: str
    validation_sha256: str
    test_sha256: str
    train_sample_count: int
    validation_sample_count: int
    test_sample_count: int
    intercept_si: float
    slope_si_per_second: float
    train_metrics: dict[str, float | int]
    validation_metrics: dict[str, float | int]
    test_metrics: dict[str, float | int]
    manifest_sha256: str


def build_forecast_run_manifest(
    *,
    run_reference: str,
    source_reference: str,
    model_version: str,
    code_version: str,
    created_at: datetime,
    split: ForecastDatasetSplit,
    result: LinearForecastResult,
) -> ForecastRunManifest:
    """Construit un manifeste canonique pour la baseline OLS Phase 3."""

    required = (run_reference, source_reference, model_version, code_version)
    if any(not value.strip() for value in required):
        raise ValueError("Run, source, version modèle et version code sont obligatoires.")
    if created_at.tzinfo is None:
        raise ValueError("La date du run de prévision doit être timezone-aware.")

    train_payload = _observation_payload(split.train)
    validation_payload = _observation_payload(split.validation)
    test_payload = _observation_payload(split.test)
    train_metrics = asdict(result.train_metrics)
    validation_metrics = asdict(result.validation_metrics)
    test_metrics = asdict(result.test_metrics)
    manifest_payload = {
        "run_reference": run_reference,
        "source_reference": source_reference,
        "model_family": "linear_ols",
        "model_version": model_version,
        "code_version": code_version,
        "created_at": created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "train_sha256": _sha256_payload(train_payload),
        "validation_sha256": _sha256_payload(validation_payload),
        "test_sha256": _sha256_payload(test_payload),
        "train_sample_count": len(split.train),
        "validation_sample_count": len(split.validation),
        "test_sample_count": len(split.test),
        "intercept_si": result.intercept_si,
        "slope_si_per_second": result.slope_si_per_second,
        "train_metrics": train_metrics,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
    }
    manifest_hash = _sha256_payload(manifest_payload)
    return ForecastRunManifest(
        **manifest_payload,
        manifest_sha256=manifest_hash,
    )


__all__ = ["ForecastRunManifest", "build_forecast_run_manifest"]
