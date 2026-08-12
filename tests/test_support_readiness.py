from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hydro_shared.support_readiness import (
    IncidentClassRequirement,
    IncidentResponsePhase,
    SupportOrganizationEvidence,
    SupportRunbookDescriptor,
    assess_support_readiness,
)

NOW = datetime(2026, 8, 12, 20, 0, tzinfo=UTC)
RUNBOOK_SHA = "11" * 32


def _organization(**overrides) -> SupportOrganizationEvidence:
    payload = {
        "support_policy_ref": "policy://support/pilot-v1",
        "escalation_matrix_ref": "support://escalation/pilot-v1",
        "contact_roster_ref": "support://contacts/pilot-v1",
        "maintenance_policy_ref": "policy://maintenance/pilot-v1",
        "evidence_archive_ref": "evidence://support/readiness/2026-08-12",
    }
    payload.update(overrides)
    return SupportOrganizationEvidence(**payload)


def _requirement(
    incident_class_ref: str,
    phases: tuple[IncidentResponsePhase, ...],
) -> IncidentClassRequirement:
    return IncidentClassRequirement(
        incident_class_ref=incident_class_ref,
        required_phases=phases,
        requirement_source_ref="protocol://support/pilot-v1",
    )


def _runbook(
    incident_class_ref: str,
    phases: tuple[IncidentResponsePhase, ...],
    *,
    runbook_ref: str | None = None,
) -> SupportRunbookDescriptor:
    return SupportRunbookDescriptor(
        incident_class_ref=incident_class_ref,
        runbook_ref=runbook_ref or f"runbook://{incident_class_ref}",
        version="1.0",
        content_sha256=RUNBOOK_SHA,
        owner_role_ref="role://incident-commander",
        review_ref="review://support/2026-08-12",
        reviewed_at=NOW,
        covered_phases=phases,
    )


def test_support_readiness_passes_when_all_required_classes_and_phases_are_covered() -> None:
    requirements = (
        _requirement(
            "incident://database-unavailable",
            (
                IncidentResponsePhase.DETECT,
                IncidentResponsePhase.CONTAIN,
                IncidentResponsePhase.RESTORE,
                IncidentResponsePhase.LEARN,
            ),
        ),
        _requirement(
            "incident://credential-compromise",
            (
                IncidentResponsePhase.DETECT,
                IncidentResponsePhase.CONTAIN,
                IncidentResponsePhase.PRESERVE,
                IncidentResponsePhase.ERADICATE,
                IncidentResponsePhase.NOTIFY,
            ),
        ),
    )
    runbooks = tuple(
        _runbook(requirement.incident_class_ref, requirement.required_phases)
        for requirement in requirements
    )

    assessment = assess_support_readiness(
        protocol_ref="protocol://support/pilot-v1",
        requirements=requirements,
        runbooks=runbooks,
        organization=_organization(),
        assessed_at=NOW,
    )

    assert assessment.passed is True
    assert assessment.violations == ()
    assert all(item.passed for item in assessment.class_assessments)
    assert assessment.contact_roster_ref == "support://contacts/pilot-v1"


def test_support_readiness_reports_missing_runbook_and_missing_phases() -> None:
    requirements = (
        _requirement(
            "incident://database-unavailable",
            (IncidentResponsePhase.DETECT, IncidentResponsePhase.RESTORE),
        ),
        _requirement(
            "incident://certificate-compromise",
            (IncidentResponsePhase.CONTAIN, IncidentResponsePhase.PRESERVE),
        ),
    )
    runbooks = (
        _runbook(
            "incident://database-unavailable",
            (IncidentResponsePhase.DETECT,),
        ),
    )

    assessment = assess_support_readiness(
        protocol_ref="protocol://support/pilot-v1",
        requirements=requirements,
        runbooks=runbooks,
        organization=_organization(),
        assessed_at=NOW,
    )

    assert assessment.passed is False
    assert assessment.class_assessments[0].missing_phases == (
        IncidentResponsePhase.RESTORE,
    )
    assert assessment.class_assessments[1].violations == ("runbook_missing",)
    assert assessment.violations == (
        "phase_missing:restore:incident://database-unavailable",
        "runbook_missing:incident://certificate-compromise",
    )


def test_support_readiness_does_not_ignore_orphan_active_runbooks() -> None:
    assessment = assess_support_readiness(
        protocol_ref="protocol://support/pilot-v1",
        requirements=(
            _requirement(
                "incident://database-unavailable",
                (IncidentResponsePhase.RESTORE,),
            ),
        ),
        runbooks=(
            _runbook(
                "incident://database-unavailable",
                (IncidentResponsePhase.RESTORE,),
            ),
            _runbook(
                "incident://legacy-class",
                (IncidentResponsePhase.DETECT,),
            ),
        ),
        organization=_organization(),
        assessed_at=NOW,
    )

    assert assessment.passed is False
    assert assessment.violations == (
        "runbook_without_active_requirement:incident://legacy-class",
    )


def test_support_runbook_requires_content_identity_review_and_covered_phase() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        _runbook(
            "incident://db",
            (IncidentResponsePhase.DETECT,),
        ).__class__(
            incident_class_ref="incident://db",
            runbook_ref="runbook://db",
            version="1.0",
            content_sha256="bad",
            owner_role_ref="role://owner",
            review_ref="review://1",
            reviewed_at=NOW,
            covered_phases=(IncidentResponsePhase.DETECT,),
        )

    with pytest.raises(ValueError, match="timezone-aware"):
        SupportRunbookDescriptor(
            incident_class_ref="incident://db",
            runbook_ref="runbook://db",
            version="1.0",
            content_sha256=RUNBOOK_SHA,
            owner_role_ref="role://owner",
            review_ref="review://1",
            reviewed_at=datetime(2026, 8, 12, 20, 0),
            covered_phases=(IncidentResponsePhase.DETECT,),
        )

    with pytest.raises(ValueError, match="au moins une phase"):
        SupportRunbookDescriptor(
            incident_class_ref="incident://db",
            runbook_ref="runbook://db",
            version="1.0",
            content_sha256=RUNBOOK_SHA,
            owner_role_ref="role://owner",
            review_ref="review://1",
            reviewed_at=NOW,
            covered_phases=(),
        )


def test_support_readiness_requires_explicit_requirements_and_organization_refs() -> None:
    with pytest.raises(ValueError, match="Au moins une classe"):
        assess_support_readiness(
            protocol_ref="protocol://support/pilot-v1",
            requirements=(),
            runbooks=(),
            organization=_organization(),
            assessed_at=NOW,
        )

    with pytest.raises(ValueError, match="contacts"):
        _organization(contact_roster_ref="")


def test_support_readiness_rejects_duplicate_requirements_and_runbook_classes() -> None:
    requirement = _requirement(
        "incident://db",
        (IncidentResponsePhase.RESTORE,),
    )
    with pytest.raises(ValueError, match="qu'une exigence"):
        assess_support_readiness(
            protocol_ref="protocol://support/pilot-v1",
            requirements=(requirement, requirement),
            runbooks=(),
            organization=_organization(),
            assessed_at=NOW,
        )

    with pytest.raises(ValueError, match="qu'à un runbook actif"):
        assess_support_readiness(
            protocol_ref="protocol://support/pilot-v1",
            requirements=(requirement,),
            runbooks=(
                _runbook("incident://db", (IncidentResponsePhase.RESTORE,), runbook_ref="runbook://db/a"),
                _runbook("incident://db", (IncidentResponsePhase.RESTORE,), runbook_ref="runbook://db/b"),
            ),
            organization=_organization(),
            assessed_at=NOW,
        )
