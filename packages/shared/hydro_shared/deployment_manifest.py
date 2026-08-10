"""Manifeste immuable d'un déploiement PETROLE.

Cette brique relie une release qualifiée, des images OCI adressées par digest,
une révision de migration et un plan de rollback. Elle ne déclenche aucun
déploiement et ne transforme pas la présence d'un manifeste en preuve de HA.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_OCI_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class DeploymentImage:
    """Image d'un service identifiée uniquement par digest OCI immuable."""

    service: str
    repository: str
    digest: str

    def __post_init__(self) -> None:
        if not self.service.strip() or not self.repository.strip():
            raise ValueError("Le service et le dépôt d'image sont obligatoires.")
        if not _OCI_DIGEST_PATTERN.fullmatch(self.digest):
            raise ValueError("L'image doit être référencée par un digest OCI sha256 complet.")


@dataclass(frozen=True, slots=True)
class DeploymentManifest:
    """Entrées reproductibles d'une tentative de déploiement."""

    deployment_id: str
    environment: str
    release: str
    git_sha: str
    release_manifest_sha256: str
    migration_revision: str
    configuration_sha256: str
    created_at: datetime
    images: tuple[DeploymentImage, ...]
    previous_release: str | None
    rollback_document_ref: str | None

    def __post_init__(self) -> None:
        required = (self.deployment_id, self.environment, self.release, self.migration_revision)
        if any(not value.strip() for value in required):
            raise ValueError("Identifiant, environnement, release et migration sont obligatoires.")
        if not _GIT_SHA_PATTERN.fullmatch(self.git_sha):
            raise ValueError("git_sha doit être un SHA Git complet de 40 caractères.")
        if not _SHA256_PATTERN.fullmatch(self.release_manifest_sha256):
            raise ValueError("release_manifest_sha256 doit être un SHA-256 hexadécimal.")
        if not _SHA256_PATTERN.fullmatch(self.configuration_sha256):
            raise ValueError("configuration_sha256 doit être un SHA-256 hexadécimal.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at doit inclure un fuseau horaire.")
        if not self.images:
            raise ValueError("Un déploiement doit référencer au moins une image immuable.")
        services = [image.service for image in self.images]
        if len(services) != len(set(services)):
            raise ValueError("Chaque service ne peut avoir qu'une image dans le manifeste.")
        if (self.previous_release is None) != (self.rollback_document_ref is None):
            raise ValueError(
                "La release précédente et le document de rollback doivent être renseignés ensemble."
            )
        if self.previous_release is not None and not self.previous_release.strip():
            raise ValueError("La release précédente ne peut pas être vide.")
        if self.rollback_document_ref is not None and not self.rollback_document_ref.strip():
            raise ValueError("La référence de rollback ne peut pas être vide.")

    def canonical_json(self) -> bytes:
        """Sérialise le manifeste de manière stable pour archivage/signature."""

        payload = {
            "deployment_id": self.deployment_id,
            "environment": self.environment,
            "release": self.release,
            "git_sha": self.git_sha,
            "release_manifest_sha256": self.release_manifest_sha256,
            "migration_revision": self.migration_revision,
            "configuration_sha256": self.configuration_sha256,
            "created_at": self.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "images": [asdict(image) for image in sorted(self.images, key=lambda item: item.service)],
            "previous_release": self.previous_release,
            "rollback_document_ref": self.rollback_document_ref,
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json()).hexdigest()


__all__ = ["DeploymentImage", "DeploymentManifest"]
