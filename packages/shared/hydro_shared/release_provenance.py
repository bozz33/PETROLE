"""Manifestes de provenance des releases PETROLE.

Ce module ne signe pas lui-même les releases. Il produit un manifeste canonique
et vérifiable qui pourra être signé par la chaîne de release. Les clés privées
ne sont jamais gérées par le code applicatif.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class ReleaseArtifact:
    """Artefact immuable identifié par son hash SHA-256."""

    name: str
    sha256: str
    size_bytes: int
    media_type: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Le nom d'artefact ne peut pas être vide.")
        if not _SHA256_PATTERN.fullmatch(self.sha256):
            raise ValueError("Le hash d'artefact doit être un SHA-256 hexadécimal minuscule.")
        if self.size_bytes < 0:
            raise ValueError("La taille d'artefact ne peut pas être négative.")
        if not self.media_type.strip():
            raise ValueError("Le type MIME de l'artefact ne peut pas être vide.")


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    """Empreinte d'une release logicielle et de ses preuves.

    `qualified` décrit uniquement le statut de qualification logicielle interne
    du SHA déclaré. Il ne signifie ni certification normative ni autorisation
    d'exploitation industrielle.
    """

    release: str
    git_sha: str
    created_at: datetime
    qualified: bool
    qualification_reference: str | None
    sbom_sha256: str | None
    artifacts: tuple[ReleaseArtifact, ...]

    def __post_init__(self) -> None:
        if not self.release.strip():
            raise ValueError("L'identifiant de release ne peut pas être vide.")
        if not _GIT_SHA_PATTERN.fullmatch(self.git_sha):
            raise ValueError("git_sha doit contenir un SHA Git complet de 40 caractères.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at doit inclure un fuseau horaire.")
        if self.qualified and not (self.qualification_reference or "").strip():
            raise ValueError("Une release qualifiée doit référencer son dossier de qualification.")
        if self.sbom_sha256 is not None and not _SHA256_PATTERN.fullmatch(self.sbom_sha256):
            raise ValueError("sbom_sha256 doit être un SHA-256 hexadécimal minuscule.")
        names = [artifact.name for artifact in self.artifacts]
        if len(names) != len(set(names)):
            raise ValueError("Deux artefacts d'une même release ne peuvent pas partager le même nom.")

    def payload(self) -> dict[str, Any]:
        """Retourne le payload indépendant de l'ordre d'insertion Python."""

        return {
            "release": self.release,
            "git_sha": self.git_sha,
            "created_at": self.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "qualified": self.qualified,
            "qualification_reference": self.qualification_reference,
            "sbom_sha256": self.sbom_sha256,
            "artifacts": [
                asdict(artifact) for artifact in sorted(self.artifacts, key=lambda item: item.name)
            ],
        }

    def canonical_json(self) -> bytes:
        """Sérialise sans espace et avec clés triées pour une signature reproductible."""

        return json.dumps(
            self.payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def sha256(self) -> str:
        """Empreinte du manifeste canonique, à signer hors application."""

        return hashlib.sha256(self.canonical_json()).hexdigest()


def sha256_bytes(content: bytes) -> str:
    """Calcule l'empreinte SHA-256 d'un artefact binaire."""

    return hashlib.sha256(content).hexdigest()


def verify_artifact_bytes(artifact: ReleaseArtifact, content: bytes) -> bool:
    """Vérifie simultanément taille et hash d'un artefact."""

    return artifact.size_bytes == len(content) and artifact.sha256 == sha256_bytes(content)


__all__ = [
    "ReleaseArtifact",
    "ReleaseManifest",
    "sha256_bytes",
    "verify_artifact_bytes",
]
