"""Validation déterministe du contexte de sécurité OPC UA P5-C.

Cette couche ne crée aucun SecureChannel et ne lit aucun fichier secret. Elle
évalue les métadonnées X.509 et les décisions de confiance déjà extraites par
la passerelle dédiée. Le réseau réel reste derrière l'adapter open62541 prévu
par D14/POC-OS-08.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit

from hydro_api.industrial.opcua_config import OpcUaReadOnlyConnectorConfig

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _normalize_thumbprint(value: str) -> str:
    normalized = value.replace(":", "").strip().lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(
            "Une empreinte de certificat SHA-256 doit contenir 64 caractères hexadécimaux."
        )
    return normalized


def _require_aware_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} doit être timezone-aware.")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class OpcUaCertificateMetadata:
    """Métadonnées de certificat extraites hors de cette couche.

    Aucun certificat PEM/DER ni clé privée n'est conservé ici. `dns_names`
    correspond aux identités réseau validables fournies par le certificat.
    """

    certificate_ref: str
    application_uri: str
    thumbprint_sha256: str
    not_before_utc: datetime
    not_after_utc: datetime
    dns_names: tuple[str, ...]
    evidence_ref: str

    def __post_init__(self) -> None:
        required = (self.certificate_ref, self.application_uri, self.evidence_ref)
        if any(not value.strip() for value in required):
            raise ValueError("Référence certificat, ApplicationUri et preuve sont obligatoires.")
        object.__setattr__(self, "thumbprint_sha256", _normalize_thumbprint(self.thumbprint_sha256))
        not_before = _require_aware_utc(self.not_before_utc, "not_before_utc")
        not_after = _require_aware_utc(self.not_after_utc, "not_after_utc")
        if not_after <= not_before:
            raise ValueError("La période de validité du certificat est incohérente.")
        object.__setattr__(self, "not_before_utc", not_before)
        object.__setattr__(self, "not_after_utc", not_after)
        normalized_names = tuple(
            dict.fromkeys(name.strip().lower() for name in self.dns_names if name.strip())
        )
        object.__setattr__(self, "dns_names", normalized_names)


@dataclass(frozen=True, slots=True)
class OpcUaTrustListSnapshot:
    """Snapshot versionné d'une trust-list et de sa révocation observée."""

    trust_list_ref: str
    content_sha256: str
    trusted_thumbprints_sha256: tuple[str, ...]
    revoked_thumbprints_sha256: tuple[str, ...]
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.trust_list_ref.strip() or not self.evidence_ref.strip():
            raise ValueError("La trust-list et sa preuve doivent être référencées.")
        object.__setattr__(self, "content_sha256", _normalize_thumbprint(self.content_sha256))
        trusted = tuple(
            dict.fromkeys(_normalize_thumbprint(value) for value in self.trusted_thumbprints_sha256)
        )
        revoked = tuple(
            dict.fromkeys(_normalize_thumbprint(value) for value in self.revoked_thumbprints_sha256)
        )
        object.__setattr__(self, "trusted_thumbprints_sha256", trusted)
        object.__setattr__(self, "revoked_thumbprints_sha256", revoked)


@dataclass(frozen=True, slots=True)
class OpcUaSecurityApproval:
    """Décisions de sécurité approuvées hors du connecteur.

    PETROLE n'invente pas de SecurityPolicy : la ou les URI autorisées et
    l'ApplicationUri serveur attendue proviennent de la revue OT du site.
    """

    approval_ref: str
    approved_security_policy_uris: tuple[str, ...]
    expected_server_application_uri: str

    def __post_init__(self) -> None:
        if not self.approval_ref.strip() or not self.expected_server_application_uri.strip():
            raise ValueError(
                "La référence d'approbation et l'ApplicationUri serveur sont obligatoires."
            )
        policies = tuple(
            dict.fromkeys(
                value.strip() for value in self.approved_security_policy_uris if value.strip()
            )
        )
        if not policies:
            raise ValueError("Au moins une SecurityPolicy OPC UA approuvée est obligatoire.")
        object.__setattr__(self, "approved_security_policy_uris", policies)


@dataclass(frozen=True, slots=True)
class OpcUaSecurityContextAssessment:
    """Résultat P5-C limité aux preuves et à l'instant évalués."""

    passed: bool
    violations: tuple[str, ...]
    connector_id: str
    endpoint_url: str
    evaluated_at_utc: datetime
    approval_ref: str
    client_certificate_ref: str
    server_certificate_ref: str
    trust_list_ref: str
    trust_list_content_sha256: str
    evidence_refs: tuple[str, ...]


def assess_opcua_security_context(
    *,
    config: OpcUaReadOnlyConnectorConfig,
    approval: OpcUaSecurityApproval,
    client_certificate: OpcUaCertificateMetadata,
    server_certificate: OpcUaCertificateMetadata,
    trust_list: OpcUaTrustListSnapshot,
    evaluated_at: datetime,
) -> OpcUaSecurityContextAssessment:
    """Évalue le contexte avant ouverture du canal réseau réel.

    Les vérifications sont fail-closed : politique non approuvée, certificat
    expiré/non encore valide, serveur non approuvé/révoqué, identité serveur
    inattendue ou hôte absent du certificat rendent l'évaluation négative.
    """

    instant = _require_aware_utc(evaluated_at, "evaluated_at")
    violations: list[str] = []

    if config.security_policy_uri not in approval.approved_security_policy_uris:
        violations.append("security_policy_not_approved")
    if client_certificate.certificate_ref != config.application_certificate_ref:
        violations.append("client_certificate_ref_mismatch")
    if trust_list.trust_list_ref != config.trust_list_ref:
        violations.append("trust_list_ref_mismatch")

    for role, certificate in (
        ("client", client_certificate),
        ("server", server_certificate),
    ):
        if instant < certificate.not_before_utc:
            violations.append(f"{role}_certificate_not_yet_valid")
        if instant > certificate.not_after_utc:
            violations.append(f"{role}_certificate_expired")

    server_thumbprint = server_certificate.thumbprint_sha256
    if server_thumbprint not in trust_list.trusted_thumbprints_sha256:
        violations.append("server_certificate_untrusted")
    if server_thumbprint in trust_list.revoked_thumbprints_sha256:
        violations.append("server_certificate_revoked")
    if server_certificate.application_uri != approval.expected_server_application_uri:
        violations.append("server_application_uri_mismatch")

    endpoint_host = (urlsplit(config.endpoint_url).hostname or "").lower()
    if endpoint_host not in server_certificate.dns_names:
        violations.append("server_certificate_endpoint_host_mismatch")

    return OpcUaSecurityContextAssessment(
        passed=not violations,
        violations=tuple(violations),
        connector_id=config.connector_id,
        endpoint_url=config.endpoint_url,
        evaluated_at_utc=instant,
        approval_ref=approval.approval_ref,
        client_certificate_ref=client_certificate.certificate_ref,
        server_certificate_ref=server_certificate.certificate_ref,
        trust_list_ref=trust_list.trust_list_ref,
        trust_list_content_sha256=trust_list.content_sha256,
        evidence_refs=(
            client_certificate.evidence_ref,
            server_certificate.evidence_ref,
            trust_list.evidence_ref,
        ),
    )


__all__ = [
    "OpcUaCertificateMetadata",
    "OpcUaSecurityApproval",
    "OpcUaSecurityContextAssessment",
    "OpcUaTrustListSnapshot",
    "assess_opcua_security_context",
]
