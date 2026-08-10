from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hydro_api.services.metrology_status import (
    InstrumentCalibrationRecord,
    MetrologyPolicy,
    MetrologyStatus,
    assess_metrology_status,
)

_BASE = datetime(2026, 8, 10, 22, 0, tzinfo=UTC)


def _record(valid_for_days: int) -> InstrumentCalibrationRecord:
    return InstrumentCalibrationRecord(
        instrument_ref="instrument://PT-101",
        source_ref="metrology://site-A/PT-101",
        calibrated_at=_BASE - timedelta(days=30),
        valid_until=_BASE + timedelta(days=valid_for_days),
        certificate_ref="certificate://PT-101/cal-2026-07",
    )


def test_metrology_status_uses_explicit_due_window() -> None:
    policy = MetrologyPolicy(
        due_warning_seconds=7 * 24 * 3600,
        policy_ref="policy://site-A/metrology/v1",
    )

    valid = assess_metrology_status(_record(30), evaluated_at=_BASE, policy=policy)
    due = assess_metrology_status(_record(5), evaluated_at=_BASE, policy=policy)
    expired = assess_metrology_status(_record(-1), evaluated_at=_BASE, policy=policy)

    assert valid.status is MetrologyStatus.VALID
    assert due.status is MetrologyStatus.DUE
    assert expired.status is MetrologyStatus.EXPIRED
    assert due.seconds_until_expiry == pytest.approx(5 * 24 * 3600)


def test_missing_calibration_metadata_is_explicitly_not_available() -> None:
    record = InstrumentCalibrationRecord(
        instrument_ref="instrument://FT-101",
        source_ref="metrology://site-A/FT-101",
        calibrated_at=None,
        valid_until=None,
        certificate_ref=None,
    )
    result = assess_metrology_status(
        record,
        evaluated_at=_BASE,
        policy=MetrologyPolicy(0.0, "policy://site-A/metrology/v1"),
    )

    assert result.status is MetrologyStatus.NOT_AVAILABLE
    assert result.seconds_until_expiry is None


def test_calibration_validity_cannot_precede_calibration_date() -> None:
    with pytest.raises(ValueError, match="postérieure"):
        InstrumentCalibrationRecord(
            instrument_ref="instrument://PT-101",
            source_ref="metrology://site-A/PT-101",
            calibrated_at=_BASE,
            valid_until=_BASE - timedelta(seconds=1),
            certificate_ref="certificate://PT-101/cal",
        )
