"""Évaluation du statut métrologique d'un instrument/tag.

D15 demande de suivre le statut et l'échéance de calibration. Cette brique ne
calibre aucun instrument et ne déduit aucune périodicité : dates, certificat et
politique proviennent du système métrologique/opérateur.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class MetrologyStatus(StrEnum):
    """État documentaire de la calibration d'un instrument."""

    VALID = "valid"
    DUE = "due"
    EXPIRED = "expired"
    NOT_AVAILABLE = "not_available"


@dataclass(frozen=True, slots=True)
class InstrumentCalibrationRecord:
    """Métadonnées de calibration provenant d'une source métrologique."""

    instrument_ref: str
    source_ref: str
    calibrated_at: datetime | None
    valid_until: datetime | None
    certificate_ref: str | None

    def __post_init__(self) -> None:
        if not self.instrument_ref.strip() or not self.source_ref.strip():
            raise ValueError("Instrument et provenance métrologique sont obligatoires.")
        dates = (self.calibrated_at, self.valid_until)
        if any(value is not None and value.tzinfo is None for value in dates):
            raise ValueError("Les dates de calibration doivent être timezone-aware.")
        if (self.calibrated_at is None) != (self.valid_until is None):
            raise ValueError(
                "Date de calibration et date de validité doivent être fournies ensemble."
            )
        if (
            self.calibrated_at is not None
            and self.valid_until is not None
            and self.valid_until <= self.calibrated_at
        ):
            raise ValueError("La fin de validité doit être postérieure à la calibration.")
        if self.certificate_ref is not None and not self.certificate_ref.strip():
            raise ValueError("La référence du certificat ne peut pas être vide.")


@dataclass(frozen=True, slots=True)
class MetrologyPolicy:
    """Fenêtre d'anticipation explicitement retenue par l'opérateur."""

    due_warning_seconds: float
    policy_ref: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.due_warning_seconds) or self.due_warning_seconds < 0:
            raise ValueError("La fenêtre d'anticipation doit être finie et positive ou nulle.")
        if not self.policy_ref.strip():
            raise ValueError("La référence de politique métrologique est obligatoire.")


@dataclass(frozen=True, slots=True)
class MetrologyAssessment:
    instrument_ref: str
    status: MetrologyStatus
    evaluated_at: datetime
    valid_until: datetime | None
    seconds_until_expiry: float | None
    certificate_ref: str | None
    source_ref: str
    policy_ref: str


def assess_metrology_status(
    record: InstrumentCalibrationRecord,
    *,
    evaluated_at: datetime,
    policy: MetrologyPolicy,
) -> MetrologyAssessment:
    """Classe l'échéance sans inventer la période de calibration."""

    if evaluated_at.tzinfo is None:
        raise ValueError("La date d'évaluation métrologique doit être timezone-aware.")
    evaluated_utc = evaluated_at.astimezone(UTC)
    if record.valid_until is None:
        return MetrologyAssessment(
            instrument_ref=record.instrument_ref,
            status=MetrologyStatus.NOT_AVAILABLE,
            evaluated_at=evaluated_utc,
            valid_until=None,
            seconds_until_expiry=None,
            certificate_ref=record.certificate_ref,
            source_ref=record.source_ref,
            policy_ref=policy.policy_ref,
        )

    valid_until_utc = record.valid_until.astimezone(UTC)
    seconds_until_expiry = (valid_until_utc - evaluated_utc).total_seconds()
    if seconds_until_expiry < 0:
        status = MetrologyStatus.EXPIRED
    elif seconds_until_expiry <= policy.due_warning_seconds:
        status = MetrologyStatus.DUE
    else:
        status = MetrologyStatus.VALID
    return MetrologyAssessment(
        instrument_ref=record.instrument_ref,
        status=status,
        evaluated_at=evaluated_utc,
        valid_until=valid_until_utc,
        seconds_until_expiry=seconds_until_expiry,
        certificate_ref=record.certificate_ref,
        source_ref=record.source_ref,
        policy_ref=policy.policy_ref,
    )


__all__ = [
    "InstrumentCalibrationRecord",
    "MetrologyAssessment",
    "MetrologyPolicy",
    "MetrologyStatus",
    "assess_metrology_status",
]
