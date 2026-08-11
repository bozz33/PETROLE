from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hydro_shared.enterprise_identity import (
    IdentityAssuranceStatus,
    MfaAssurancePolicy,
    OidcProviderContract,
    VerifiedOidcClaims,
    assess_verified_oidc_claims,
)

_AUTHENTICATED_AT = datetime(2026, 8, 11, 5, 50, tzinfo=UTC)


def _provider() -> OidcProviderContract:
    return OidcProviderContract(
        provider_id="operator-directory",
        issuer="https://identity.operator.example/realms/petrole",
        audience="petrole-api",
        configuration_ref="identity://operator-directory/v3",
    )


def _policy() -> MfaAssurancePolicy:
    return MfaAssurancePolicy(
        required_roles=frozenset({"admin"}),
        accepted_amr=frozenset({"hwk", "otp", "webauthn"}),
        policy_ref="policy://identity/pilot-v1",
    )


def _claims(*, issuer: str | None = None, amr: tuple[str, ...] = ("pwd", "webauthn")) -> VerifiedOidcClaims:
    return VerifiedOidcClaims(
        issuer=issuer or _provider().issuer,
        audiences=("petrole-api",),
        subject="00u-operator-123",
        authentication_methods=amr,
        authenticated_at=_AUTHENTICATED_AT,
        token_id="oidc-jti-123",
    )


def test_admin_requires_explicitly_accepted_mfa_method() -> None:
    assessment = assess_verified_oidc_claims(
        _claims(),
        provider=_provider(),
        role="admin",
        mfa_policy=_policy(),
    )

    assert assessment.status is IdentityAssuranceStatus.ALLOWED
    assert assessment.allowed is True
    assert assessment.mfa_required is True
    assert assessment.matched_mfa_methods == ("webauthn",)
    assert assessment.violations == ()


def test_password_only_admin_is_denied_without_guessing_a_fallback() -> None:
    assessment = assess_verified_oidc_claims(
        _claims(amr=("pwd",)),
        provider=_provider(),
        role="admin",
        mfa_policy=_policy(),
    )

    assert assessment.allowed is False
    assert assessment.violations == ("MFA_ASSURANCE_MISSING",)


def test_non_admin_role_does_not_inherit_an_unstated_mfa_requirement() -> None:
    assessment = assess_verified_oidc_claims(
        _claims(amr=("pwd",)),
        provider=_provider(),
        role="engineer",
        mfa_policy=_policy(),
    )

    assert assessment.allowed is True
    assert assessment.mfa_required is False


def test_issuer_and_audience_must_match_provider_contract() -> None:
    claims = VerifiedOidcClaims(
        issuer="https://unexpected.example/issuer",
        audiences=("other-api",),
        subject="subject-1",
        authentication_methods=("webauthn",),
        authenticated_at=_AUTHENTICATED_AT,
        token_id="jti-1",
    )

    assessment = assess_verified_oidc_claims(
        claims,
        provider=_provider(),
        role="admin",
        mfa_policy=_policy(),
    )

    assert assessment.allowed is False
    assert assessment.violations == (
        "OIDC_ISSUER_MISMATCH",
        "OIDC_AUDIENCE_MISMATCH",
    )


def test_oidc_provider_rejects_non_https_issuer() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        OidcProviderContract(
            provider_id="bad",
            issuer="http://identity.local/realm",
            audience="petrole-api",
            configuration_ref="identity://bad",
        )


def test_mfa_policy_requires_explicit_methods() -> None:
    with pytest.raises(ValueError, match="méthode amr"):
        MfaAssurancePolicy(
            required_roles=frozenset({"admin"}),
            accepted_amr=frozenset(),
            policy_ref="policy://invalid",
        )
