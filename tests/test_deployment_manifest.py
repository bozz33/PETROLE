from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hydro_shared.deployment_manifest import DeploymentImage, DeploymentManifest


def _digest(character: str) -> str:
    return "sha256:" + character * 64


def test_deployment_manifest_is_canonical_and_requires_immutable_images() -> None:
    manifest = DeploymentManifest(
        deployment_id="prod-2026-08-10-01",
        environment="production",
        release="v1.2.0",
        git_sha="a" * 40,
        release_manifest_sha256="b" * 64,
        migration_revision="a2f0d9e1c3b4",
        configuration_sha256="c" * 64,
        created_at=datetime(2026, 8, 10, 22, 0, tzinfo=UTC),
        images=(
            DeploymentImage(service="web", repository="registry/petrole-web", digest=_digest("d")),
            DeploymentImage(service="api", repository="registry/petrole-api", digest=_digest("e")),
        ),
        previous_release="v1.1.0",
        rollback_document_ref="runbook://deploy/rollback-v1",
    )

    first = manifest.canonical_json()
    second = manifest.canonical_json()
    assert first == second
    assert len(manifest.sha256()) == 64
    assert first.find(b'"service":"api"') < first.find(b'"service":"web"')


def test_deployment_manifest_rejects_mutable_image_tag() -> None:
    with pytest.raises(ValueError, match="digest OCI"):
        DeploymentImage(
            service="api",
            repository="registry/petrole-api",
            digest="latest",
        )


def test_rollback_reference_and_previous_release_are_atomic() -> None:
    with pytest.raises(ValueError, match="renseignés ensemble"):
        DeploymentManifest(
            deployment_id="prod-2026-08-10-02",
            environment="production",
            release="v1.2.0",
            git_sha="a" * 40,
            release_manifest_sha256="b" * 64,
            migration_revision="a2f0d9e1c3b4",
            configuration_sha256="c" * 64,
            created_at=datetime(2026, 8, 10, 22, 0, tzinfo=UTC),
            images=(
                DeploymentImage(
                    service="api",
                    repository="registry/petrole-api",
                    digest=_digest("d"),
                ),
            ),
            previous_release="v1.1.0",
            rollback_document_ref=None,
        )
