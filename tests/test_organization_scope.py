from __future__ import annotations

import uuid

import pytest

from hydro_api.organization_scope import resolve_organization_scope


def test_single_org_uses_internal_default_without_user_selection() -> None:
    organization_id = uuid.uuid4()
    assert (
        resolve_organization_scope(
            deployment_mode="single_org",
            default_organization_id=organization_id,
            requested_organization_id=None,
        )
        == organization_id
    )


def test_single_org_refuses_cross_organization_selection() -> None:
    with pytest.raises(PermissionError, match="ne permet pas"):
        resolve_organization_scope(
            deployment_mode="single_org",
            default_organization_id=uuid.uuid4(),
            requested_organization_id=uuid.uuid4(),
        )


def test_multi_org_requires_resolved_organization() -> None:
    with pytest.raises(ValueError, match="multi_org/saas"):
        resolve_organization_scope(
            deployment_mode="multi_org",
            default_organization_id=None,
            requested_organization_id=None,
        )


def test_multi_org_returns_identity_resolved_scope() -> None:
    organization_id = uuid.uuid4()
    assert (
        resolve_organization_scope(
            deployment_mode="multi_org",
            default_organization_id=None,
            requested_organization_id=organization_id,
        )
        == organization_id
    )
