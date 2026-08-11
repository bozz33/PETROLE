"""Contrat d'assurance d'identité entreprise pour la Phase 8 PETROLE.

Cette brique ne valide pas une signature JWT et ne contacte aucun fournisseur
OIDC. Elle évalue des claims déjà vérifiés cryptographiquement par un adaptateur
futur et applique une politique MFA explicite, sans choisir de fournisseur ou de
méthode MFA à la place de l'opérateur.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from urllib.parse import urlsplit


class IdentityAssuranceStatus(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"


@dataclass(frozen=True, slots=True)
class OidcProviderContract:
    """Paramètres publics attendus d'un fournisseur OIDC approuvé."""

    provider_id: str
    issuer: str
    audience: str
    configuration_ref: str

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.audience.strip() or not self.configuration_ref.strip():
            raise ValueError("Fournisseur, audience et référence de configuration OIDC sont obligatoires.")
        parsed = urlsplit(self.issuer)
        if parsed.scheme.lower() != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("L'issuer OIDC doit être une URL HTTPS absolue sans query ni fragment.")


@dataclass(frozen=True, slots=True)
class MfaAssurancePolicy:
    """Méthodes `amr` acceptées pour les rôles soumis à MFA."""

    required_roles: frozenset[str]
    accepted_amr: frozenset[str]
    policy_ref: str

    def __post_init__(self) -> None:
        if not self.required_roles:
            raise ValueError("La politique MFA doit viser au moins un rôle.")
        if not self.accepted_amr:
            raise ValueError("La politique MFA doit déclarer au moins une méthode amr acceptée.")
        if any(not value.strip() for value in (*self.required_roles, *self.accepted_amr)):
            raise ValueError("Les rôles et méthodes amr MFA ne peuvent pas être vides.")
        if not self.policy_ref.strip():
            raise ValueError("La référence de politique MFA est obligatoire.")


@dataclass(frozen=True, slots=True)
class VerifiedOidcClaims:
    """Snapshot minimal de claims après validation cryptographique externe."""

    issuer: str
    audiences: tuple[str, ...]
    subject: str
    authentication_methods: tuple[str, ...]
    authenticated_at: datetime
    token_id: str

    def __post_init__(self) -> None:
        if not self.issuer.strip() or not self.subject.strip() or not self.token_id.strip():
            raise ValueError("Issuer, subject et identifiant de jeton OIDC sont obligatoires.")
        if not self.audiences or any(not value.strip() for value in self.audiences):
            raise ValueError("Le jeton OIDC doit fournir au moins une audience non vide.")
        if any(not value.strip() for value in self.authentication_methods):
            raise ValueError("Les valeurs amr OIDC ne peuvent pas être vides.")
        if self.authenticated_at.tzinfo is None:
            raise ValueError("La date d'authentification OIDC doit être timezone-aware.")

    @property
    def authenticated_at_utc(self) -> datetime:
        return self.authenticated_at.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class IdentityAssuranceAssessment:
    status: IdentityAssuranceStatus
    provider_id: str
    role: str
    mfa_required: bool
    matched_mfa_methods: tuple[str, ...]
    violations: tuple[str, ...]
    policy_ref: str

    @property
    def allowed(self) -> bool:
        return self.status is IdentityAssuranceStatus.ALLOWED


def assess_verified_oidc_claims(
    claims: VerifiedOidcClaims,
    *,
    provider: OidcProviderContract,
    role: str,
    mfa_policy: MfaAssurancePolicy,
) -> IdentityAssuranceAssessment:
    """Applique issuer/audience/MFA à des claims déjà vérifiés cryptographiquement."""

    if not role.strip():
        raise ValueError("Le rôle PETROLE à évaluer est obligatoire.")

    violations: list[str] = []
    if claims.issuer.rstrip("/") != provider.issuer.rstrip("/"):
        violations.append("OIDC_ISSUER_MISMATCH")
    if provider.audience not in claims.audiences:
        violations.append("OIDC_AUDIENCE_MISMATCH")

    mfa_required = role in mfa_policy.required_roles
    matched = tuple(sorted(set(claims.authentication_methods) & mfa_policy.accepted_amr))
    if mfa_required and not matched:
        violations.append("MFA_ASSURANCE_MISSING")

    status = IdentityAssuranceStatus.ALLOWED if not violations else IdentityAssuranceStatus.DENIED
    return IdentityAssuranceAssessment(
        status=status,
        provider_id=provider.provider_id,
        role=role,
        mfa_required=mfa_required,
        matched_mfa_methods=matched,
        violations=tuple(violations),
        policy_ref=mfa_policy.policy_ref,
    )


__all__ = [
    "IdentityAssuranceAssessment",
    "IdentityAssuranceStatus",
    "MfaAssurancePolicy",
    "OidcProviderContract",
    "VerifiedOidcClaims",
    "assess_verified_oidc_claims",
]
