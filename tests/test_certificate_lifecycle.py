from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hydro_shared.certificate_lifecycle import (
    CertificateLifecyclePolicy,
    CertificateLifecycleStatus,
    CertificateMetadata,
    assess_certificate_lifecycle,
)

_BASE = datetime(2026, 8, 10, 22, 0, tzinfo=UTC)


def _metadata(*, not_before_days: int = -30, not_after_days: int = 30) -> CertificateMetadata:
    return CertificateMetadata(
        certificate_ref="certificate://opcua/site-A/client",
        sha256_fingerprint="a" * 64,
        subject_ref="subject://petrole-opcua-client",
        issuer_ref="issuer://site-A-ot-ca",
        not_before=_BASE + timedelta(days=not_before_days),
        not_after=_BASE + timedelta(days=not_after_days),
        source_ref="pki://site-A/inventory/v4",
    )


def test_certificate_lifecycle_classifies_valid_due_expired_and_not_yet_valid() -> None:
    policy = CertificateLifecyclePolicy(
        due_warning_seconds=7 * 24 * 3600,
        policy_ref="policy://site-A/certificates/v2",
    )

    valid = assess_certificate_lifecycle(_metadata(not_after_days=30), evaluated_at=_BASE, policy=policy)
    due = assess_certificate_lifecycle(_metadata(not_after_days=5), evaluated_at=_BASE, policy=policy)
    expired = assess_certificate_lifecycle(_metadata(not_after_days=-1), evaluated_at=_BASE, policy=policy)
    future = assess_certificate_lifecycle(
        _metadata(not_before_days=1, not_after_days=30),
        evaluated_at=_BASE,
        policy=policy,
    )

    assert valid.status is CertificateLifecycleStatus.VALID
    assert due.status is CertificateLifecycleStatus.DUE
    assert expired.status is CertificateLifecycleStatus.EXPIRED
    assert future.status is CertificateLifecycleStatus.NOT_YET_VALID
    assert due.seconds_until_expiry == pytest.approx(5 * 24 * 3600)


def test_certificate_metadata_requires_valid_sha256_fingerprint_and_period() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        CertificateMetadata(
            certificate_ref="certificate://bad",
            sha256_fingerprint="abc",
            subject_ref="subject://client",
            issuer_ref="issuer://ca",
            not_before=_BASE,
            not_after=_BASE + timedelta(days=1),
            source_ref="pki://inventory",
        )

    with pytest.raises(ValueError, match="postérieure"):
        CertificateMetadata(
            certificate_ref="certificate://bad",
            sha256_fingerprint="a" * 64,
            subject_ref="subject://client",
            issuer_ref="issuer://ca",
            not_before=_BASE,
            not_after=_BASE,
            source_ref="pki://inventory",
        )


def test_certificate_policy_rejects_non_finite_warning_window() -> None:
    with pytest.raises(ValueError, match="finie"):
        CertificateLifecyclePolicy(float("nan"), "policy://certificates")
