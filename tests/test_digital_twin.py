from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from hydro_leak import TwinStateVariable, build_twin_snapshot, state_delta


def _variable(name: str, value: float, unit: str = "Pa") -> TwinStateVariable:
    return TwinStateVariable(
        name=name,
        value_si=value,
        unit=unit,
        source_ref=f"tag://{name}",
    )


def test_snapshot_hash_is_independent_of_variable_order_and_timezone_representation() -> None:
    utc_time = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)
    offset_time = datetime(2026, 8, 10, 10, 0, tzinfo=timezone(timedelta(hours=2)))
    first = build_twin_snapshot(
        model_version="model-v12",
        observed_at=utc_time,
        sequence_number=7,
        variables=(_variable("pressure", 2.0e6), _variable("flow", 0.4, "m^3/s")),
    )
    second = build_twin_snapshot(
        model_version="model-v12",
        observed_at=offset_time,
        sequence_number=7,
        variables=(_variable("flow", 0.4, "m^3/s"), _variable("pressure", 2.0e6)),
    )

    assert first.content_hash == second.content_hash
    assert first.content_hash.startswith("sha256:")
    assert first.observed_at == utc_time


def test_state_delta_requires_same_model_version_and_units() -> None:
    previous = build_twin_snapshot(
        model_version="model-v12",
        observed_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
        sequence_number=10,
        variables=(_variable("pressure", 2.0e6), _variable("flow", 0.4, "m^3/s")),
    )
    current = build_twin_snapshot(
        model_version="model-v12",
        observed_at=datetime(2026, 8, 10, 8, 1, tzinfo=UTC),
        sequence_number=11,
        variables=(_variable("pressure", 2.1e6), _variable("flow", 0.35, "m^3/s")),
    )

    assert state_delta(previous, current) == {
        "flow": pytest.approx(-0.05),
        "pressure": pytest.approx(100_000.0),
    }


def test_snapshot_rejects_duplicate_variables_and_non_monotonic_comparison() -> None:
    with pytest.raises(ValueError, match="uniques"):
        build_twin_snapshot(
            model_version="model-v12",
            observed_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
            sequence_number=1,
            variables=(_variable("pressure", 1.0), _variable("pressure", 2.0)),
        )

    first = build_twin_snapshot(
        model_version="model-v12",
        observed_at=datetime(2026, 8, 10, 8, 0, tzinfo=UTC),
        sequence_number=2,
        variables=(_variable("pressure", 1.0),),
    )
    with pytest.raises(ValueError, match="séquence postérieure"):
        state_delta(first, first)
