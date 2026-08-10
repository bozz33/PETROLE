"""Suivi documentaire du cycle de vie des certificats PETROLE.

Le module classe la période de validité à partir de métadonnées déjà extraites
et d'une fenêtre d'anticipation explicite. Il ne valide ni signature, ni chaîne
PKI, ni révocation et ne remplace pas le moteur TLS/OPC UA.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class CertificateLifecycleStatus(StrEnum):
    NOT_YET_VALID = "not_yet_valid"
    VALID = "valid"
    DUE = "due"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class CertificateMetadata:
    """Identité et période d'un certificat sans conserver sa clé privée."""

    certificate_ref: str
    sha256_fingerprint: str
    subject_ref: str
    issuer_ref: str
    not_before: datetime
    not_after: datetime
    source_ref: str

    def __post_init__(self) -> None:
        references = (
            self.certificate_ref,
            self.subject_ref,
            self.issuer_ref,
            self.source_ref,
        )
        if any(not value.strip() for value in references):
            raise ValueError("Les références du certificat, sujet, émetteur et source sont obligatoires.")
        if not _SHA256_PATTERN.fullmatch(self.sha256_fingerprint):
            raise ValueError("Le certificat doit être identifié par une empreinte SHA-256 hexadécimale.")
        if self.not_before.tzinfo is None or self.not_after.tzinfo is None:
            raise ValueError("Les bornes de validité du certificat doivent être timezone-aware.")
        if self.not_after <= self.not_before:
            raise ValueError("La fin de validité du certificat doit être postérieure au début.")


@dataclass(frozen=True, slots=True)
class CertificateLifecyclePolicy:
    due_warning_seconds: float
    policy_ref: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.due_warning_seconds) or self.due_warning_seconds < 0:
            raise ValueError("La fenêtre d'anticipation certificat doit être finie et positive ou nulle.")
        if not self.policy_ref.strip():
            raise ValueError("La référence de politique certificat est obligatoire.")


@dataclass(frozen=True, slots=True)
class CertificateLifecycleAssessment:
    certificate_ref: str
    status: CertificateLifecycleStatus
    evaluated_at: datetime
    not_before: datetime
    not_after: datetime
    seconds_until_expiry: float
    sha256_fingerprint: str
    policy_ref: str


def assess_certificate_lifecycle(
    metadata: CertificateMetadata,
    *,
    evaluated_at: datetime,
    policy: CertificateLifecyclePolicy,
) -> CertificateLifecycleAssessment:
    """Classe l'échéance sans conclure à la confiance cryptographique."""

    if evaluated_at.tzinfo is None:
        raise ValueError("La date d'évaluation du certificat doit être timezone-aware.")
    evaluated_utc = evaluated_at.astimezone(UTC)
    not_before = metadata.not_before.astimezone(UTC)
    not_after = metadata.not_after.astimezone(UTC)
    seconds_until_expiry = (not_after - evaluated_utc).total_seconds()
    if evaluated_utc < not_before:
        status = CertificateLifecycleStatus.NOT_YET_VALID
    elif seconds_until_expiry < 0:
        status = CertificateLifecycleStatus.EXPIRED
    elif seconds_until_expiry <= policy.due_warning_seconds:
        status = CertificateLifecycleStatus.DUE
    else:
        status = CertificateLifecycleStatus.VALID
    return CertificateLifecycleAssessment(
        certificate_ref=metadata.certificate_ref,
        status=status,
        evaluated_at=evaluated_utc,
        not_before=not_before,
        not_after=not_after,
        seconds_until_expiry=seconds_until_expiry,
        sha256_fingerprint=metadata.sha256_fingerprint,
        policy_ref=policy.policy_ref,
    )


__all__ = [
    "CertificateLifecycleAssessment",
    "CertificateLifecyclePolicy",
    "CertificateLifecycleStatus",
    "CertificateMetadata",
    "assess_certificate_lifecycle",
]
