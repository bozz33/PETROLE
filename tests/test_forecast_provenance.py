from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hydro_api.services.forecast_provenance import build_forecast_run_manifest
from hydro_api.services.forecasting import (
    ForecastDatasetSplit,
    ForecastObservation,
    fit_linear_forecast,
)

_BASE = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)


def _point(hour: int, value: float) -> ForecastObservation:
    return ForecastObservation(timestamp=_BASE + timedelta(hours=hour), value_si=value)


def _split(test_last_value: float = 13.0) -> ForecastDatasetSplit:
    return ForecastDatasetSplit(
        train=(_point(0, 1.0), _point(1, 3.0), _point(2, 5.0)),
        validation=(_point(3, 7.0), _point(4, 9.0)),
        test=(_point(5, 11.0), _point(6, test_last_value)),
    )


def test_forecast_manifest_is_deterministic_and_keeps_split_hashes_separate() -> None:
    split = _split()
    result = fit_linear_forecast(split)
    first = build_forecast_run_manifest(
        run_reference="forecast://PT-101/run-001",
        source_reference="tag://PT-101",
        model_version="linear-ols-v1",
        code_version="git:abc123",
        created_at=datetime(2026, 8, 10, 22, 0, tzinfo=UTC),
        split=split,
        result=result,
    )
    second = build_forecast_run_manifest(
        run_reference="forecast://PT-101/run-001",
        source_reference="tag://PT-101",
        model_version="linear-ols-v1",
        code_version="git:abc123",
        created_at=datetime(2026, 8, 10, 22, 0, tzinfo=UTC),
        split=split,
        result=result,
    )

    assert first == second
    assert len(first.manifest_sha256) == 64
    assert len({first.train_sha256, first.validation_sha256, first.test_sha256}) == 3
    assert first.validation_metrics["rmse_si"] == 0.0
    assert first.test_metrics["rmse_si"] == 0.0


def test_changing_only_test_data_changes_test_and_manifest_hash_not_train_hash() -> None:
    original_split = _split(13.0)
    changed_split = _split(14.0)
    original = build_forecast_run_manifest(
        run_reference="forecast://PT-101/run-001",
        source_reference="tag://PT-101",
        model_version="linear-ols-v1",
        code_version="git:abc123",
        created_at=datetime(2026, 8, 10, 22, 0, tzinfo=UTC),
        split=original_split,
        result=fit_linear_forecast(original_split),
    )
    changed = build_forecast_run_manifest(
        run_reference="forecast://PT-101/run-002",
        source_reference="tag://PT-101",
        model_version="linear-ols-v1",
        code_version="git:abc123",
        created_at=datetime(2026, 8, 10, 22, 0, tzinfo=UTC),
        split=changed_split,
        result=fit_linear_forecast(changed_split),
    )

    assert original.train_sha256 == changed.train_sha256
    assert original.validation_sha256 == changed.validation_sha256
    assert original.test_sha256 != changed.test_sha256
    assert original.manifest_sha256 != changed.manifest_sha256
