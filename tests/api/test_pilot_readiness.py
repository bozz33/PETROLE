"""Tests déterministes des gates de readiness du pilote V1."""

from __future__ import annotations

import uuid

from pydantic import SecretStr

from hydro_api.config import Settings
from hydro_api.pilot_security import PilotSecurityEvidence, evaluate_pilot_security


def _settings() -> Settings:
    return Settings.model_validate(
        {
            "environment": "staging",
            "authentication_required": True,
            "jwt_secret": SecretStr("test-only-value-abcdefghijklmnopqrstuvwxyz-123456"),
            "build_git_sha": "a" * 40,
            "deployment_mode": "single_org",
            "default_organization_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        }
    )


def test_complete_non_ot_evidence_is_ready_with_warning() -> None:
    result = evaluate_pilot_security(
        _settings(),
        PilotSecurityEvidence(
            https_verified=True,
            backup_restore_verified=True,
            vulnerability_scan_passed=True,
            access_review_completed=True,
            incident_contacts_defined=True,
            ot_architecture_approved=False,
        ),
    )
    assert result.ready is True
    assert result.blockers == ()
    assert len(result.warnings) == 1
    assert "aucun connecteur SCADA/historian réel" in result.warnings[0]


def test_missing_evidence_blocks_readiness() -> None:
    result = evaluate_pilot_security(_settings(), PilotSecurityEvidence())
    assert result.ready is False
    assert len(result.blockers) == 5
    assert any("HTTPS" in blocker for blocker in result.blockers)
    assert any("sauvegarde/restauration" in blocker for blocker in result.blockers)


def test_incomplete_build_identity_blocks_readiness() -> None:
    settings = _settings().model_copy(update={"build_git_sha": "unknown"})
    evidence = PilotSecurityEvidence(
        https_verified=True,
        backup_restore_verified=True,
        vulnerability_scan_passed=True,
        access_review_completed=True,
        incident_contacts_defined=True,
        ot_architecture_approved=True,
    )
    result = evaluate_pilot_security(settings, evidence)
    assert result.ready is False
    assert any("SHA Git" in blocker for blocker in result.blockers)
