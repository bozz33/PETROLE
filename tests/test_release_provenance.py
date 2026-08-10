"""Tests du manifeste reproductible de Phase 8."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hydro_shared.release_provenance import (
    ReleaseArtifact,
    ReleaseManifest,
    sha256_bytes,
    verify_artifact_bytes,
    verify_sbom_bytes,
)


def test_release_manifest_is_canonical_and_verifies_artifact() -> None:
    content = b"PETROLE release artifact\n"
    sbom = b'{"bomFormat":"CycloneDX","specVersion":"1.6"}'
    artifact = ReleaseArtifact(
        name="petrole.tar.gz",
        sha256=sha256_bytes(content),
        size_bytes=len(content),
        media_type="application/gzip",
    )
    manifest = ReleaseManifest(
        release="v1.5.0",
        git_sha="a" * 40,
        created_at=datetime(2026, 8, 10, 6, 0, tzinfo=UTC),
        qualified=True,
        qualification_reference="var/qualification/20260810T060000Z",
        sbom_sha256=sha256_bytes(sbom),
        artifacts=(artifact,),
    )

    assert verify_artifact_bytes(artifact, content)
    assert not verify_artifact_bytes(artifact, content + b"tampered")
    assert verify_sbom_bytes(manifest, sbom)
    assert not verify_sbom_bytes(manifest, sbom + b"\n")
    assert manifest.sha256() == sha256_bytes(manifest.canonical_json())
    assert b'"git_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"' in manifest.canonical_json()
    assert b'"qualified":true' in manifest.canonical_json()


def test_release_without_sbom_binding_never_reports_verified_sbom() -> None:
    manifest = ReleaseManifest(
        release="v1.5.0",
        git_sha="d" * 40,
        created_at=datetime.now(UTC),
        qualified=False,
        qualification_reference=None,
        sbom_sha256=None,
        artifacts=(),
    )
    assert verify_sbom_bytes(manifest, b"anything") is False


def test_release_manifest_refuses_ambiguous_or_unqualified_metadata() -> None:
    with pytest.raises(ValueError, match="40 caractères"):
        ReleaseManifest(
            release="v1.5.0",
            git_sha="short",
            created_at=datetime.now(UTC),
            qualified=False,
            qualification_reference=None,
            sbom_sha256=None,
            artifacts=(),
        )

    with pytest.raises(ValueError, match="qualification"):
        ReleaseManifest(
            release="v1.5.0",
            git_sha="c" * 40,
            created_at=datetime.now(UTC),
            qualified=True,
            qualification_reference=None,
            sbom_sha256=None,
            artifacts=(),
        )
