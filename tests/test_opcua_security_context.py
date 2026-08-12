from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hydro_api.industrial.opcua_config import OpcUaNodeMapping, OpcUaReadOnlyConnectorConfig
from hydro_api.industrial.opcua_security_context import (
    OpcUaCertificateMetadata,
    OpcUaSecurityApproval,
    OpcUaTrustListSnapshot,
    assess_opcua_security_context,
)

NOW = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
CLIENT_SHA = "11" * 32
SERVER_SHA = "22" * 32
TRUST_SHA = "33" * 32
POLICY = "http://opcfoundation.org/UA/SecurityPolicy#Aes256_Sha256_RsaPss"


def _config(**overrides) -> OpcUaReadOnlyConnectorConfig:
    payload = {
        "connector_id": "opcua-site-A",
        "endpoint_url": "opc.tcp://gateway.site-a.internal:4840",
        "security_policy_uri": POLICY,
        "application_certificate_ref": "certificate://opcua/site-A/client",
        "private_key_secret_ref": "secret://vault/opcua/site-A/client-key",
        "trust_list_ref": "trust-list://opcua/site-A/v3",
        "identity_secret_ref": "secret://vault/opcua/site-A/service-user",
        "node_mappings": (
            OpcUaNodeMapping(
                tag_ref="tag://PT-101",
                namespace_uri="urn:site-A:process",
                node_id="nsu=urn:site-A:process;s=PT-101",
                source_ref="engineering://opcua-node-list/rev-4",
            ),
        ),
        "configuration_source_ref": "config://opcua/site-A/v5",
    }
    payload.update(overrides)
    return OpcUaReadOnlyConnectorConfig(**payload)


def _client_certificate(**overrides) -> OpcUaCertificateMetadata:
    payload = {
        "certificate_ref": "certificate://opcua/site-A/client",
        "application_uri": "urn:petrole:gateway:site-A",
        "thumbprint_sha256": CLIENT_SHA,
        "not_before_utc": NOW - timedelta(days=30),
        "not_after_utc": NOW + timedelta(days=335),
        "dns_names": ("petrole-gateway.site-a.internal",),
        "evidence_ref": "evidence://opcua/site-A/client-certificate/2026-08-12",
    }
    payload.update(overrides)
    return OpcUaCertificateMetadata(**payload)


def _server_certificate(**overrides) -> OpcUaCertificateMetadata:
    payload = {
        "certificate_ref": "certificate://operator/site-A/opcua-server",
        "application_uri": "urn:operator:site-A:opcua-server",
        "thumbprint_sha256": SERVER_SHA,
        "not_before_utc": NOW - timedelta(days=15),
        "not_after_utc": NOW + timedelta(days=350),
        "dns_names": ("gateway.site-a.internal",),
        "evidence_ref": "evidence://opcua/site-A/server-certificate/2026-08-12",
    }
    payload.update(overrides)
    return OpcUaCertificateMetadata(**payload)


def _trust_list(**overrides) -> OpcUaTrustListSnapshot:
    payload = {
        "trust_list_ref": "trust-list://opcua/site-A/v3",
        "content_sha256": TRUST_SHA,
        "trusted_thumbprints_sha256": (SERVER_SHA,),
        "revoked_thumbprints_sha256": (),
        "evidence_ref": "evidence://opcua/site-A/trust-list/v3",
    }
    payload.update(overrides)
    return OpcUaTrustListSnapshot(**payload)


def _approval(**overrides) -> OpcUaSecurityApproval:
    payload = {
        "approval_ref": "ot-approval://site-A/opcua/security/v2",
        "approved_security_policy_uris": (POLICY,),
        "expected_server_application_uri": "urn:operator:site-A:opcua-server",
    }
    payload.update(overrides)
    return OpcUaSecurityApproval(**payload)


def test_security_context_passes_only_with_approved_trusted_current_identity() -> None:
    assessment = assess_opcua_security_context(
        config=_config(),
        approval=_approval(),
        client_certificate=_client_certificate(),
        server_certificate=_server_certificate(),
        trust_list=_trust_list(),
        evaluated_at=NOW,
    )

    assert assessment.passed is True
    assert assessment.violations == ()
    assert assessment.approval_ref == "ot-approval://site-A/opcua/security/v2"
    assert assessment.trust_list_content_sha256 == TRUST_SHA
    assert len(assessment.evidence_refs) == 3


def test_security_context_reports_policy_reference_and_trust_failures() -> None:
    assessment = assess_opcua_security_context(
        config=_config(application_certificate_ref="certificate://unexpected"),
        approval=_approval(approved_security_policy_uris=("policy://other",)),
        client_certificate=_client_certificate(),
        server_certificate=_server_certificate(),
        trust_list=_trust_list(
            trust_list_ref="trust-list://different",
            trusted_thumbprints_sha256=(),
            revoked_thumbprints_sha256=(SERVER_SHA,),
        ),
        evaluated_at=NOW,
    )

    assert assessment.passed is False
    assert assessment.violations == (
        "security_policy_not_approved",
        "client_certificate_ref_mismatch",
        "trust_list_ref_mismatch",
        "server_certificate_untrusted",
        "server_certificate_revoked",
    )


def test_security_context_checks_certificate_validity_and_server_identity() -> None:
    assessment = assess_opcua_security_context(
        config=_config(),
        approval=_approval(expected_server_application_uri="urn:operator:expected"),
        client_certificate=_client_certificate(
            not_before_utc=NOW + timedelta(minutes=1),
            not_after_utc=NOW + timedelta(days=2),
        ),
        server_certificate=_server_certificate(
            not_before_utc=NOW - timedelta(days=2),
            not_after_utc=NOW - timedelta(seconds=1),
            dns_names=("different.site-a.internal",),
        ),
        trust_list=_trust_list(),
        evaluated_at=NOW,
    )

    assert assessment.passed is False
    assert assessment.violations == (
        "client_certificate_not_yet_valid",
        "server_certificate_expired",
        "server_application_uri_mismatch",
        "server_certificate_endpoint_host_mismatch",
    )


def test_certificate_metadata_requires_aware_dates_and_sha256_thumbprint() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _client_certificate(not_before_utc=datetime(2026, 1, 1))

    with pytest.raises(ValueError, match="64 caractères hexadécimaux"):
        _client_certificate(thumbprint_sha256="not-a-sha256")

    with pytest.raises(ValueError, match="période de validité"):
        _client_certificate(
            not_before_utc=NOW + timedelta(days=2),
            not_after_utc=NOW + timedelta(days=1),
        )


def test_thumbprints_are_canonicalized_without_losing_traceability() -> None:
    colonized = ":".join(["AA"] * 32)
    certificate = _server_certificate(thumbprint_sha256=colonized)
    trust = _trust_list(
        trusted_thumbprints_sha256=(colonized, colonized.lower()),
        revoked_thumbprints_sha256=(),
    )

    assert certificate.thumbprint_sha256 == "aa" * 32
    assert trust.trusted_thumbprints_sha256 == ("aa" * 32,)


def test_security_approval_never_selects_a_default_policy() -> None:
    with pytest.raises(ValueError, match="SecurityPolicy"):
        _approval(approved_security_policy_uris=())

    with pytest.raises(ValueError, match="ApplicationUri"):
        _approval(expected_server_application_uri="")


def test_security_context_requires_timezone_aware_evaluation_instant() -> None:
    with pytest.raises(ValueError, match="evaluated_at"):
        assess_opcua_security_context(
            config=_config(),
            approval=_approval(),
            client_certificate=_client_certificate(),
            server_certificate=_server_certificate(),
            trust_list=_trust_list(),
            evaluated_at=datetime(2026, 8, 12, 12, 0),
        )
